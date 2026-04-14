# SystemAnalyzer — Claude Code Instructions

## Navigation Rule (token efficiency)

**Before using Grep, Glob, or Read to explore the codebase, always consult `CODE_GRAPH.md` first.**

`CODE_GRAPH.md` contains a complete index of every file, route, function, DB table, and background worker in this project with exact line numbers. Use it to find the precise file and line range needed, then read only that slice.

```
Step 1 — Read CODE_GRAPH.md  →  find file + line number
Step 2 — Read <file> offset=<line> limit=60  →  read only what's needed
Step 3 — Edit/fix/extend  →  done
```

Never read `app.py`, `db.py`, or `llm_analyst.py` in full — they are 400–1300 lines each. Always use offset + limit after looking up the line in CODE_GRAPH.md.

---

## Project Overview

**SystemAnalyzer** is a Flask-based web reconnaissance and CVE intelligence platform.

| Component | Description |
|---|---|
| Tracking pixel + `fp.js` | Passive browser fingerprinting via 1×1 PNG + JS payload |
| Dashboard | Real-time target list with CVE risk scoring |
| Nmap integration | Auto port/service scan on every new hit |
| IP intelligence | ip-api.com geolocation, ISP, VPN/proxy detection |
| LLM analysis | Ollama (primary) → Anthropic → OpenAI fallback |
| Vulnerability Lab | CTF environment with Docker containers + flag scoring |
| Cloudflared tunnel | Automatic public URL with watchdog restart |

---

## Stack

- **Backend:** Python 3.12, Flask 3.x, SQLite (via `db.py`)
- **Frontend:** Vanilla JS, no frameworks, dark GitHub-style theme
- **Tunnel:** `cloudflared` (auto-managed daemon thread)
- **Scanning:** `nmap` (brew install nmap)
- **Lab containers:** Docker Desktop (macOS) via Python `docker` SDK
- **LLM:** Ollama local / Anthropic API / OpenAI API

---

## Running the App

```bash
cd /Users/fighter/Documents/SystemAnalyzer
./start.sh          # starts Docker, checks deps, launches Flask, opens browser
```

Or manually:
```bash
python app.py       # runs on http://localhost:5000
```

Lab login: `http://localhost:5000/lab` — username: `fighter`, password: `admin123`

---

## Key Conventions

### Files never to read in full
| File | Lines | Use instead |
|---|---|---|
| `app.py` | ~1280 | CODE_GRAPH.md → route index → offset+limit |
| `llm_analyst.py` | ~900 | CODE_GRAPH.md → LLM function map |
| `db.py` | ~560 | CODE_GRAPH.md → DB table index |
| `static/fp.js` | ~600 | CODE_GRAPH.md → fp.js stage pipeline |

### DB access
All DB reads/writes go through `db.py` functions — never write raw SQL in `app.py` or blueprints. Check the DB table index in CODE_GRAPH.md before adding new functions.

### Background workers
All heavy work (nmap, IP intel, CVE lookup, hostname resolution) runs in `daemon=True` threads. Results are pushed to the SSE bus via `_push_event()` at `app.py:155`.

### Lab blueprint
Lab routes live in `lab/__init__.py`, not `app.py`. The blueprint is registered at `app.py:44` (`app.register_blueprint(lab_bp)`). Auth uses Flask `session["lab_user"]` — no JWT.

### Templates
All templates extend `templates/base.html`. The shared header, tunnel widget, nav, and CSS variables are defined there. Add nav links only in `base.html`.

### Docker (lab)
Docker credential helpers require `/Applications/Docker.app/Contents/Resources/bin` on PATH — this is patched at import time in `lab/docker_manager.py`. Do not remove this patch.

---

## Common Tasks (quick reference)

| Task | File(s) | Where in CODE_GRAPH.md |
|---|---|---|
| Add Flask route | `app.py` | Route Index section |
| Add lab challenge | `lab/challenges.py` only | Challenge catalog |
| Change LLM prompt | `llm_analyst.py` | LLM Function Map |
| Add DB column | `db.py:init_db` migration loop | DB Table Index |
| Fix fingerprint collection | `static/fp.js` | fp.js Stage Pipeline |
| Change dashboard UI | `templates/dashboard.html` | — |
| Fix container start/stop | `lab/docker_manager.py` | — |
| Change flag scoring | `lab/scorer.py` | — |

---

## Do Not

- Do not read `node_modules/` — it contains unrelated JS build artifacts
- Do not run `app.py` in background during edits — the user runs it manually via `./start.sh`
- Do not add `print()` debug statements — use the existing `[tag]` log format (e.g. `[nmap]`, `[tunnel]`)
- Do not create new template files without extending `base.html`
- Do not write raw SQL outside `db.py`
