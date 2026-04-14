# SystemAnalyzer — Code Review Graph

> **Purpose:** Use this file to locate relevant code before reading any source file.
> Find the section for your task → read only the listed file(s) → skip everything else.

---

## File Map (what each file owns)

| File | Owns |
|---|---|
| `app.py` | Flask routes, background workers, tunnel, SSE bus |
| `db.py` | All SQLite reads/writes, schema, migrations |
| `fingerprint.py` | UA parsing, CVE search-term building |
| `cve_lookup.py` | NVD API calls, CVSS parsing |
| `llm_analyst.py` | All LLM calls (Ollama/Anthropic/OpenAI), prompts |
| `lab/__init__.py` | Lab Flask blueprint — auth routes, container routes |
| `lab/challenges.py` | Static challenge catalog (images, flags, hints, points) |
| `lab/docker_manager.py` | Docker SDK — start/stop/reset/status containers |
| `lab/scorer.py` | Flag hash verification, score recording |
| `static/fp.js` | Browser fingerprinting, app probing, GPS, media |
| `templates/base.html` | Shared layout, header nav, tunnel widget |
| `templates/dashboard.html` | Targets table, filter chips, SSE toasts |
| `templates/target.html` | Full target detail — fingerprint, nmap, CVEs, IP intel |
| `templates/lab_dashboard.html` | Lab machine cards, scoreboard preview |
| `templates/lab_challenge.html` | Per-challenge flags, hints, flag submit form |
| `templates/lab_login.html` | Login form |
| `templates/lab_register.html` | Register form |
| `templates/lab_scoreboard.html` | Full leaderboard |
| `templates/lab_admin_users.html` | Admin user management |
| `templates/generate.html` | Pixel generator UI |
| `templates/report.html` | LLM-generated pentest report shell |
| `templates/demo.html` | Lure/demo page (embeds fp.js) |

---

## Import Graph

```
app.py
├── db.py
├── fingerprint.py
├── cve_lookup.py
├── llm_analyst.py          (lazy-imported per route)
└── lab/__init__.py  (blueprint)
    ├── db.py
    ├── lab/challenges.py
    ├── lab/docker_manager.py
    │   └── lab/challenges.py
    └── lab/scorer.py
        ├── db.py
        └── lab/challenges.py

static/fp.js                (standalone browser JS, no imports)
templates/*.html            (extend base.html via Jinja2)
```

---

## Route → File Index

### Core app routes (`app.py`)

| Route | Function | Line |
|---|---|---|
| `GET /` | `index` | 497 |
| `GET /dashboard` | `dashboard` | 502 |
| `GET /target/<id>` | `target_detail` | 508 |
| `GET /generate` | `generate_pixel` | 553 |
| `GET /demo/<id>` | `demo_page` | 575 |
| `GET /demo-go/<id>` | `demo_go` | 650 |
| `GET /pixel/<id>.png` | `pixel` | 663 |
| `POST /collect` | `collect` | 709 |
| `GET /fp.js` | `serve_fp_js` | 768 |
| `GET /ntlm-probe/<id>` | `ntlm_probe` | 590 |
| `GET /report/<id>` | `report_page` | 1103 |
| `GET /lure/<id>` | `lure_page` | 1184 |

### API routes (`app.py`)

| Route | Function | Line |
|---|---|---|
| `GET /api/tunnel/status` | `api_tunnel_status` | 790 |
| `POST /api/tunnel/restart` | `api_tunnel_restart` | 799 |
| `GET /api/events` | `api_events` (SSE) | 819 |
| `POST /api/scan/<id>` | `api_scan` | 852 |
| `GET /api/nmap/<id>` | `api_nmap_status` | 867 |
| `GET /api/ip-intel/<id>` | `api_ip_intel` | 879 |
| `GET /api/ai-analyze/<id>` | `api_ai_analyze` | 887 |
| `GET /api/attack-paths/<id>` | `api_attack_paths` | 909 |
| `POST /api/nl-query` | `api_nl_query` | 926 |
| `GET /api/ai-status` | `api_ai_status` | 938 |
| `GET /api/models` | `api_models` | 945 |
| `POST /api/models/select` | `api_model_select` | 952 |
| `GET /api/profile/<id>` | `api_profile` | 967 |
| `POST /api/phishing/<id>` | `api_phishing` | 982 |
| `GET /api/behaviour/<id>` | `api_behaviour` | 1005 |
| `GET /api/session-summary` | `api_session_summary` | 1019 |
| `GET /api/network-topology` | `api_network_topology` | 1037 |
| `GET/POST /api/alerts/rules` | `api_alert_rules_*` | 1048 |
| `GET /api/alerts/check` | `api_alerts_check` | 1073 |
| `GET /api/report-data/<id>` | `api_report_data` | 1118 |
| `POST /api/deception/generate/<id>` | `api_deception_generate` | 1171 |
| `GET /api/targets` | `api_targets` | 1200 |
| `GET /api/target/<id>` | `api_target` | 1205 |
| `POST /api/refresh_cves/<id>` | `api_refresh_cves` | 1210 |

### Lab routes (`lab/__init__.py`)

| Route | Function | Line |
|---|---|---|
| `GET/POST /lab/login` | `login` | 56 |
| `GET /lab/logout` | `logout` | 69 |
| `GET/POST /lab/register` | `register` | 75 |
| `GET /lab/` | `dashboard` | 118 |
| `GET /lab/challenge/<name>` | `challenge_detail` | 138 |
| `POST /lab/start/<name>` | `start` | 164 |
| `POST /lab/stop/<name>` | `stop` | 183 |
| `POST /lab/reset/<name>` | `reset` | 194 |
| `GET /lab/status/<name>` | `status` | 210 |
| `POST /lab/submit/<name>/<key>` | `submit_flag` | 220 |
| `GET /lab/scoreboard` | `scoreboard` | 235 |
| `GET /lab/admin/users` | `admin_users` | 246 |
| `POST /lab/admin/users/delete/<u>` | `admin_delete_user` | 255 |

---

## DB Table → Function Index (`db.py`)

| Table | Read | Write | Line range |
|---|---|---|---|
| `hits` | — | `insert_hit` | 188 |
| `fingerprints` | `get_target`, `get_all_targets` | `insert_fingerprint`, `update_gps`, `update_resolved_hostname`, `update_ntlm` | 198–300 |
| `cve_results` | `get_target` | `insert_cves` | 288 |
| `ip_intel` | `get_ip_intel` | `upsert_ip_intel` | 368 |
| `nmap_scans` | `get_nmap` | `upsert_nmap` | 412 |
| `lab_users` | `lab_get_user`, `lab_list_users` | `lab_create_user`, `lab_delete_user` | 452 |
| `lab_sessions` | `lab_get_session` | `lab_upsert_session`, `lab_set_session_status` | 486 |
| `lab_scores` | `lab_get_scoreboard`, `lab_get_user_solves`, `lab_already_solved` | `lab_submit_flag` | 516 |

---

## Background Worker Map (`app.py`)

| Worker function | Triggered by | Does |
|---|---|---|
| `_do_ip_intel` (L259) | pixel hit, /collect | Calls ip-api.com, stores in `ip_intel` |
| `_do_nmap_scan` (L368) | pixel hit, `/api/scan`, lab start | Runs nmap, stores ports + OS, auto-CVE |
| `_do_nmap_cve_lookup` (L437) | after nmap completes | NVD lookup per discovered service |
| `_do_cve_lookup` (L461) | pixel hit, /collect | NVD lookup for browser/OS/app CVEs |
| `_do_hostname_lookup` (L186) | pixel hit | rDNS + NetBIOS + mDNS hostname resolution |
| `_tunnel_watchdog` (L91) | daemon thread at startup | Keeps cloudflared alive |

All workers run as `daemon=True` threads. SSE push via `_push_event` (L155).

---

## LLM Function Map (`llm_analyst.py`)

| Function | Called by route | Does | Line |
|---|---|---|---|
| `analyze_target_stream` | `/api/ai-analyze/<id>` | Stream CVE analysis | 437 |
| `suggest_attack_paths` | `/api/attack-paths/<id>`, report | Attack chain list | 536 |
| `profile_target` | `/api/profile/<id>`, report | Threat actor profile | 573 |
| `run_nl_query` | `/api/nl-query` | NL → SQL → results | 496 |
| `build_phishing_payload` | `/api/phishing/<id>` | Lure page HTML | 647 |
| `analyse_behaviour` | `/api/behaviour/<id>` | Hit pattern analysis | 740 |
| `session_summary` | `/api/session-summary` | All-targets briefing | 782 |
| `build_network_topology` | `/api/network-topology` | Target graph nodes | 812 |
| `nl_to_alert_rule` | `/api/alerts/rules` POST | NL → SQL rule | 861 |
| `generate_deception_page` | `/api/deception/generate`, `/lure` | AI lure page | 893 |
| `generate_report_data` | `/api/report-data/<id>` | Full report narrative | 700 |

Provider fallback order: **Ollama → Anthropic → OpenAI** (set by `select_model`/`ai_status`).

---

## fp.js Stage Pipeline (`static/fp.js`)

```
Stage 1 — Immediate (on load)
  canvas hash, WebGL vendor/renderer, audio hash,
  screen res, color depth, timezone, platform,
  CPU cores, memory, touch, fonts, plugins,
  UA hints (ua_os, ua_architecture, ua_model),
  CSS media (dark mode, pointer, HDR),
  connection type, battery

Stage 2 — Async (Promise.all)
  getMediaDevices()   → camera/mic/speaker counts
  getPermissions()    → camera/mic/notifications/geo/clipboard state
  getSpeechVoices()   → TTS voice list

Stage 3 — App probing
  probeLocalServers() → WS probes (Discord 6463-6465, Spotify 4381,
                         VS Code 9229, Zoom 19421, Figma 18412,
                         Steam 27060, Epic 9002)
                      → HTTP timing probes (Spotify, Discord, Steam,
                         Epic, Battle.net, Slack, WhatsApp, Zoom)
  probeViaSchemes()   → URI scheme + window.blur detection

Stage 4 — GPS (only if __ENABLE_GEO__ === '1')
  tryGeolocation()    → navigator.geolocation → POST /collect?stage=4
```

All stages POST to `/collect`. Pixel fetch to `/pixel/<id>.png` triggers server-side workers.

---

## Task → Files Cheatsheet

| Task | Read these files only |
|---|---|
| Add/change a Flask route | `app.py` (find line from Route Index above) |
| Change what's stored in DB | `db.py` + the route in `app.py` that calls it |
| Fix fingerprinting collection | `static/fp.js` + `app.py:collect` (L709) |
| Change CVE lookup logic | `cve_lookup.py` + `fingerprint.py` |
| Change LLM prompt/behaviour | `llm_analyst.py` (find function from LLM Map above) |
| Change dashboard UI | `templates/dashboard.html` + `templates/base.html` |
| Change target detail UI | `templates/target.html` |
| Add a lab challenge | `lab/challenges.py` only |
| Fix container start/stop | `lab/docker_manager.py` |
| Change flag scoring | `lab/scorer.py` + `lab/challenges.py` |
| Fix lab auth/login | `lab/__init__.py` (L22–115) + `templates/lab_login.html` |
| Change lab UI | `templates/lab_dashboard.html` or `templates/lab_challenge.html` |
| Nmap scan behaviour | `app.py:_do_nmap_scan` (L368) |
| Hostname resolution | `app.py:_do_hostname_lookup` (L186) |
| Tunnel management | `app.py:_tunnel_watchdog` (L91), `_launch_cloudflared` (L69) |
| IP intelligence | `app.py:_do_ip_intel` (L259) |
