# SystemAnalyzer

A **web reconnaissance and CVE-intelligence platform** for security research and
lab use. It combines a tracking/telemetry web endpoint, network and service
scanning, IP intelligence, CVE lookups, and LLM-assisted analysis behind a
dashboard, plus a self-contained vulnerability lab for practising on
Docker-based targets.

## Components
- **Dashboard** — real-time target list with CVE-based risk scoring
- **Network scanning** — port/service enumeration (nmap)
- **IP intelligence** — geolocation / ISP / proxy-VPN indicators
- **CVE intelligence** — vulnerability lookups and scoring (`cve_lookup.py`)
- **LLM analysis** — Ollama (local) → Anthropic → OpenAI fallback (`llm_analyst.py`)
- **Vulnerability lab** — Docker-based CTF targets with flag scoring (`lab/`)

## Stack
Python · Flask · SQLite · nmap · Docker · local/hosted LLMs

## Getting started
```bash
./start.sh          # checks deps, launches the Flask app, opens the dashboard
# or: python app.py   (http://localhost:5000)
```

## Notes
> **Authorised use only.** This is a security-research / red-team lab tool.
> Run it only against systems and targets you own or have explicit written
> permission to test. You are responsible for complying with all applicable
> laws and for handling any collected data lawfully (consent, privacy, retention).
