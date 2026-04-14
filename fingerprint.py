"""
Parse User-Agent strings and produce structured OS/browser data
suitable for CVE lookups.
"""
import re
from user_agents import parse as ua_parse


# ── OS version normalisation ──────────────────────────────────────────────────

_WINDOWS_NT_MAP = {
    "10.0": ("Windows", "10 / 11"),
    "6.3":  ("Windows", "8.1"),
    "6.2":  ("Windows", "8"),
    "6.1":  ("Windows", "7"),
    "6.0":  ("Windows", "Vista"),
    "5.2":  ("Windows", "XP x64 / Server 2003"),
    "5.1":  ("Windows", "XP"),
}

_MACOS_VERSION_NAMES = {
    "15": "Sequoia",
    "14": "Sonoma",
    "13": "Ventura",
    "12": "Monterey",
    "11": "Big Sur",
    "10.15": "Catalina",
    "10.14": "Mojave",
    "10.13": "High Sierra",
    "10.12": "Sierra",
    "10.11": "El Capitan",
    "10.10": "Yosemite",
    "10.9":  "Mavericks",
}


def _normalise_macos(ver_str):
    """'10_15_7' → '10.15.7'"""
    return ver_str.replace("_", ".")


def parse_ua(user_agent_string: str) -> dict:
    """Return a flat dict with os/browser/device parsed fields."""
    ua = ua_parse(user_agent_string)

    result = {
        "user_agent":      user_agent_string,
        "os_family":       ua.os.family,
        "os_version":      ".".join(str(v) for v in ua.os.version if v),
        "os_raw":          f"{ua.os.family} {ua.os.version_string}".strip(),
        "browser_family":  ua.browser.family,
        "browser_version": ua.browser.version_string,
        "device_type":     "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop"),
        "device_brand":    ua.device.brand or "",
        "device_model":    ua.device.model or "",
        "is_bot":          ua.is_bot,
    }

    # ── iOS: "CPU iPhone OS 17_2_1 like Mac OS X" ─────────────────────────
    ios_match = re.search(r"CPU (?:iPhone )?OS ([\d_]+) like Mac OS X", user_agent_string)
    if ios_match:
        ver = _normalise_macos(ios_match.group(1))
        result["os_family"]  = "iOS"
        result["os_version"] = ver
        result["os_raw"]     = f"iOS {ver}"
        if result["device_type"] == "desktop":
            result["device_type"] = "mobile"

    # ── Android: extract version from "Android 14" token ──────────────────
    android_match = re.search(r"Android ([\d.]+)", user_agent_string)
    if android_match:
        ver = android_match.group(1)
        result["os_family"]  = "Android"
        result["os_version"] = ver
        result["os_raw"]     = f"Android {ver}"
        # Try to get device model from "Build/..." block
        model_match = re.search(r"\(Linux;[^)]*;\s*([^;)]+)\s+Build/", user_agent_string)
        if model_match:
            result["device_model"] = model_match.group(1).strip()

    # ── Windows NT refinement ──────────────────────────────────────────────
    nt_match = re.search(r"Windows NT (\d+\.\d+)", user_agent_string)
    if nt_match:
        nt = nt_match.group(1)
        if nt in _WINDOWS_NT_MAP:
            result["os_family"], result["os_version"] = _WINDOWS_NT_MAP[nt]

    # ── macOS refinement (only if not iOS) ────────────────────────────────
    if "iOS" not in result["os_family"]:
        mac_match = re.search(r"Mac OS X ([\d_]+)", user_agent_string)
        if mac_match:
            ver = _normalise_macos(mac_match.group(1))
            result["os_version"] = ver
            major_minor = ".".join(ver.split(".")[:2])
            major = ver.split(".")[0]
            name = _MACOS_VERSION_NAMES.get(major_minor) or _MACOS_VERSION_NAMES.get(major, "")
            result["os_raw"] = f"macOS {ver}" + (f" ({name})" if name else "")

    return result


# ── CVE search terms builder ──────────────────────────────────────────────────

def build_search_terms(parsed: dict) -> list[dict]:
    """
    Return a list of {component, version, keyword} dicts to query NVD for.
    """
    terms = []
    os_fam = parsed.get("os_family", "")
    os_ver = parsed.get("os_version", "")
    br_fam = parsed.get("browser_family", "")
    br_ver = parsed.get("browser_version", "")

    # ── OS ────────────────────────────────────────────────────────────────────
    if "Windows" in os_fam:
        ver_label = os_ver.split(" ")[0]  # "10", "8.1", etc.
        terms.append({
            "component": f"Microsoft Windows {os_ver}",
            "version":   ver_label,
            "keyword":   f"Microsoft Windows {os_ver}",
        })
    elif "iOS" in os_fam:
        major = os_ver.split(".")[0] if os_ver else ""
        terms.append({
            "component": f"Apple iOS {os_ver}",
            "version":   os_ver,
            "keyword":   f"Apple iOS {major}",
        })
        # WebKit is the only engine on iOS — always relevant
        terms.append({
            "component": "Apple WebKit (iOS)",
            "version":   "",
            "keyword":   "Apple WebKit iOS",
        })
    elif "Mac OS X" in os_fam or "macOS" in os_fam:
        terms.append({
            "component": parsed.get("os_raw", os_fam),
            "version":   os_ver,
            "keyword":   f"Apple macOS {os_ver}",
        })
    elif "Android" in os_fam:
        major = os_ver.split(".")[0] if os_ver else ""
        terms.append({
            "component": f"Google Android {os_ver}",
            "version":   os_ver,
            "keyword":   f"Google Android {major}",
        })
        # Android WebView is bundled and often unpatched
        terms.append({
            "component": "Android WebView",
            "version":   "",
            "keyword":   "Android WebView",
        })
    elif "Linux" in os_fam or "Ubuntu" in os_fam or "Debian" in os_fam or "Fedora" in os_fam:
        terms.append({
            "component": os_fam,
            "version":   os_ver,
            "keyword":   f"Linux Kernel",
        })

    # ── Browser ───────────────────────────────────────────────────────────────
    br_major = br_ver.split(".")[0] if br_ver else ""

    browser_map = {
        "Chrome Mobile iOS": ("Google Chrome Mobile iOS", "Google Chrome iOS"),
        "Chrome Mobile":     ("Google Chrome Mobile", "Google Chrome Android"),
        "Chrome":            ("Google Chrome", "Google Chrome"),
        "Firefox for iOS":   ("Mozilla Firefox iOS", "Mozilla Firefox iOS"),
        "Firefox Mobile":    ("Mozilla Firefox Android", "Mozilla Firefox Android"),
        "Firefox":           ("Mozilla Firefox", "Mozilla Firefox"),
        "Mobile Safari":     ("Apple Mobile Safari", "Apple Safari iOS"),
        "Safari":            ("Apple Safari", "Apple Safari"),
        "Edge Mobile":       ("Microsoft Edge Mobile", "Microsoft Edge Android"),
        "Edge":              ("Microsoft Edge", "Microsoft Edge"),
        "Internet Explorer": ("Microsoft Internet Explorer", "Microsoft Internet Explorer"),
        "Opera Mini":        ("Opera Mini", "Opera Mini"),
        "Opera Mobile":      ("Opera Mobile", "Opera Mobile"),
        "Opera":             ("Opera", "Opera"),
        "Samsung Internet":  ("Samsung Internet", "Samsung Internet Browser"),
        "UC Browser":        ("UCWeb UC Browser", "UC Browser"),
        "Silk":              ("Amazon Silk", "Amazon Silk browser"),
    }

    for key, (component, keyword) in browser_map.items():
        if key.lower() in br_fam.lower():
            terms.append({
                "component": f"{component} {br_major}",
                "version":   br_ver,
                "keyword":   f"{keyword} {br_major}",
            })
            break

    # ── Detected applications (from JS URI scheme / MIME probing) ─────────────
    app_cve_map = {
        # ── Conferencing / comms ──────────────────────────────────────────────
        "Zoom":              ("Zoom Video Communications", "Zoom"),
        "Microsoft Teams":   ("Microsoft Teams", "Microsoft Teams"),
        "Slack":             ("Slack", "Slack"),
        "Discord":           ("Discord", "Discord"),
        "Skype":             ("Microsoft Skype", "Skype"),
        "Webex":             ("Cisco Webex", "Cisco Webex"),
        "Google Meet":       ("Google Meet", "Google Meet"),
        # ── Messaging ─────────────────────────────────────────────────────────
        "WhatsApp":          ("WhatsApp", "WhatsApp"),
        "Telegram":          ("Telegram", "Telegram"),
        "Signal":            ("Signal Messenger", "Signal"),
        "Snapchat":          ("Snap Snapchat", "Snapchat"),
        "Instagram":         ("Meta Instagram", "Instagram"),
        "Facebook":          ("Meta Facebook", "Facebook"),
        "Twitter/X":         ("Twitter X", "Twitter"),
        "TikTok":            ("ByteDance TikTok", "TikTok"),
        "LinkedIn":          ("Microsoft LinkedIn", "LinkedIn"),
        # ── Productivity ──────────────────────────────────────────────────────
        "Outlook":           ("Microsoft Outlook", "Microsoft Outlook"),
        "Word":              ("Microsoft Word", "Microsoft Office Word"),
        "Excel":             ("Microsoft Excel", "Microsoft Office Excel"),
        "PowerPoint":        ("Microsoft PowerPoint", "Microsoft Office PowerPoint"),
        "OneNote":           ("Microsoft OneNote", "Microsoft OneNote"),
        "OneDrive":          ("Microsoft OneDrive", "OneDrive"),
        "Dropbox":           ("Dropbox", "Dropbox"),
        "Notion":            ("Notion", "Notion"),
        "Figma":             ("Figma", "Figma"),
        # ── Apple native ──────────────────────────────────────────────────────
        "FaceTime":          ("Apple FaceTime", "Apple FaceTime"),
        "Apple Maps":        ("Apple Maps", "Apple Maps"),
        "Apple Music":       ("Apple Music", "Apple Music"),
        "iTunes":            ("Apple iTunes", "Apple iTunes"),
        # ── Google native ─────────────────────────────────────────────────────
        "Gmail":             ("Google Gmail", "Google Gmail"),
        "Google Maps":       ("Google Maps", "Google Maps"),
        "Google Drive":      ("Google Drive", "Google Drive"),
        "YouTube":           ("Google YouTube", "YouTube"),
        "Google Pay":        ("Google Pay", "Google Pay"),
        # ── Remote access ─────────────────────────────────────────────────────
        "AnyDesk":           ("AnyDesk", "AnyDesk remote desktop"),
        "TeamViewer":        ("TeamViewer", "TeamViewer"),
        # ── Developer tools ───────────────────────────────────────────────────
        "VS Code":           ("Microsoft Visual Studio Code", "Visual Studio Code"),
        "Visual Studio":     ("Microsoft Visual Studio", "Visual Studio"),
        "Xcode":             ("Apple Xcode", "Xcode"),
        # ── Other desktop ─────────────────────────────────────────────────────
        "Spotify":           ("Spotify", "Spotify"),
        "Adobe Acrobat":     ("Adobe Acrobat", "Adobe Acrobat Reader"),
        "VLC":               ("VideoLAN VLC", "VLC media player"),
        "WinRAR":            ("RARLAB WinRAR", "WinRAR"),
        "OpenVPN":           ("OpenVPN", "OpenVPN"),
        "Wireshark":         ("Wireshark", "Wireshark"),
        "Java":              ("Oracle Java", "Java Runtime Environment"),
        "VMware":            ("VMware Workstation", "VMware"),
        "VirtualBox":        ("Oracle VirtualBox", "VirtualBox"),
        "Netflix":           ("Netflix", "Netflix"),
        "Uber":              ("Uber", "Uber"),
    }

    detected_apps = parsed.get("detected_apps", [])
    for app_name in detected_apps:
        for key, (component, keyword) in app_cve_map.items():
            if key.lower() in app_name.lower():
                terms.append({
                    "component": component,
                    "version":   "",
                    "keyword":   keyword,
                })
                break

    return terms


def build_search_terms_with_apps(parsed: dict, detected_apps: list) -> list[dict]:
    """Wrapper that injects detected_apps into parsed dict before building terms."""
    parsed_copy = dict(parsed)
    parsed_copy["detected_apps"] = detected_apps
    return build_search_terms(parsed_copy)
