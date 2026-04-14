"""
Docker container lifecycle manager for the SystemAnalyzer lab.
Uses the Docker Python SDK (pip install docker).
"""
import os
import threading

# Ensure Docker's credential helpers are on PATH regardless of how the app was launched.
# Docker Desktop on macOS installs binaries under the app bundle; the /usr/local/bin
# symlinks may point to a stale DMG mount, so we prepend the real path explicitly.
_DOCKER_BIN_DIRS = [
    "/Applications/Docker.app/Contents/Resources/bin",
    "/usr/local/bin",
]
_patched = os.environ.get("PATH", "")
for _d in _DOCKER_BIN_DIRS:
    if _d not in _patched:
        _patched = _d + os.pathsep + _patched
os.environ["PATH"] = _patched

try:
    import docker
    _client = docker.from_env()
    DOCKER_AVAILABLE = True
except Exception:
    _client = None
    DOCKER_AVAILABLE = False

from lab.challenges import CHALLENGES

_lock = threading.Lock()


def _container_name(challenge: str) -> str:
    return f"lab-{challenge}"


def get_status(challenge: str) -> dict:
    """
    Returns dict with keys: status, container_id, ip, port, uptime_seconds.
    status values: 'running' | 'stopped' | 'not_pulled' | 'docker_unavailable'
    """
    if not DOCKER_AVAILABLE:
        return {"status": "docker_unavailable"}

    name = _container_name(challenge)
    cfg = CHALLENGES.get(challenge, {})

    try:
        container = _client.containers.get(name)
        state = container.status  # 'running', 'exited', 'created', etc.

        if state == "running":
            # Get uptime from container start time
            import dateutil.parser
            import datetime
            started = container.attrs["State"]["StartedAt"]
            started_dt = dateutil.parser.parse(started)
            now = datetime.datetime.now(datetime.timezone.utc)
            uptime = int((now - started_dt).total_seconds())
        else:
            uptime = 0

        return {
            "status": "running" if state == "running" else "stopped",
            "container_id": container.short_id,
            "port": cfg.get("host_port"),
            "uptime_seconds": uptime,
        }
    except docker.errors.NotFound:
        return {"status": "stopped", "port": cfg.get("host_port")}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def start_challenge(challenge: str) -> dict:
    """
    Pull image if needed, start container.
    Returns get_status() dict on success, or {'status': 'error', 'error': ...}
    """
    if not DOCKER_AVAILABLE:
        return {"status": "error", "error": "Docker is not available on this host."}

    cfg = CHALLENGES.get(challenge)
    if not cfg:
        return {"status": "error", "error": f"Unknown challenge: {challenge}"}

    name = _container_name(challenge)

    with _lock:
        # If already running, just return status
        existing = get_status(challenge)
        if existing.get("status") == "running":
            return existing

        # Remove stopped container if present
        try:
            old = _client.containers.get(name)
            old.remove(force=True)
        except Exception:
            pass

        # Pull image (no-op if already pulled)
        try:
            _client.images.pull(cfg["image"])
        except Exception as e:
            return {"status": "error", "error": f"Image pull failed: {e}"}

        # Build port binding
        port_bindings = {
            f"{cfg['container_port']}/tcp": ("0.0.0.0", cfg["host_port"])
        }

        # Start container
        try:
            container = _client.containers.run(
                image=cfg["image"],
                name=name,
                detach=True,
                ports=port_bindings,
                network="systemanalyzer_lab-net" if _lab_network_exists() else None,
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "lab.challenge": challenge,
                    "lab.managed": "systemanalyzer",
                },
            )
            return {
                "status": "running",
                "container_id": container.short_id,
                "port": cfg["host_port"],
                "uptime_seconds": 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def stop_challenge(challenge: str) -> dict:
    """Stop and remove the challenge container."""
    if not DOCKER_AVAILABLE:
        return {"status": "error", "error": "Docker is not available."}

    name = _container_name(challenge)
    with _lock:
        try:
            container = _client.containers.get(name)
            container.stop(timeout=5)
            container.remove()
            return {"status": "stopped"}
        except docker.errors.NotFound:
            return {"status": "stopped"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


def reset_challenge(challenge: str) -> dict:
    """Stop then start a fresh container (wipes all state)."""
    stop_challenge(challenge)
    return start_challenge(challenge)


def list_all_statuses() -> dict:
    """Return status dict for every challenge."""
    return {name: get_status(name) for name in CHALLENGES}


def _lab_network_exists() -> bool:
    """Check if the lab-net Docker network exists."""
    try:
        networks = _client.networks.list(names=["systemanalyzer_lab-net", "lab-net"])
        return len(networks) > 0
    except Exception:
        return False
