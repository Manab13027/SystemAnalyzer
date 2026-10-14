# SystemAnalyzer — YouTube Walkthrough Production Package

**Target length:** 8–12 minutes · **Audience:** security researchers / red team · **Angle:** authorized-testing & lab tooling demo

> **Framing note (read first):** SystemAnalyzer includes genuinely offensive capabilities (tracking-pixel fingerprinting, visitor geolocation, local-app probing, AI-generated lure pages). For a public video, keep every demo on assets *you own or are authorized to test* and say so on camera. Use your own machines / a VM / the lab for every live hit. This keeps the video legitimate for your audience and keeps it off the wrong side of YouTube's "harmful/dangerous content" policy. The script below bakes this framing in.

---

## PART 1 — NARRATION SCRIPT

Timings are approximate for a natural ~150 wpm pace. Bracketed `[B-ROLL]` cues map to the shot list in Part 2. `[LOWER-THIRD]` = on-screen text.

### 0:00 – 0:25 — Cold open / hook
> "In security, the first 90% of a real engagement isn't the exploit — it's reconnaissance. Who is this target, what are they running, and what's already known-vulnerable about it. I built a tool that does all of that in one dashboard — and then has a language model reason over the results for you. This is SystemAnalyzer."

`[B-ROLL: fast cut — pixel generator → a hit lands on the dashboard → CVE chips light up → AI panel streaming text]`
`[LOWER-THIRD: SystemAnalyzer — recon + CVE intelligence platform]`

### 0:25 – 1:10 — Authorized-use disclaimer + what it is
> "Quick but important: everything I show today runs against machines I own or a lab I control. This is tooling for authorized testing and for learning — treat it that way. Okay. SystemAnalyzer is a Flask app. It's one self-hosted dashboard that ties together browser fingerprinting, nmap scanning, IP intelligence, live CVE lookups against the NVD, and an LLM analyst layer — with a built-in CTF lab on top. Let me show you the stack, then we'll watch a target come in live."

`[B-ROLL: README/architecture diagram, then the running dashboard]`
`[LOWER-THIRD: Python 3.12 · Flask · SQLite · nmap · Ollama/Anthropic/OpenAI]`

### 1:10 – 2:20 — Architecture at a glance
> "Under the hood it's deliberately boring in the right places. Backend is Python and Flask, storage is SQLite — every read and write goes through one `db.py` module, nothing scattered. The front end is vanilla JS, no framework, dark GitHub-style theme. The interesting design choice is concurrency: the second a target hits the app, the heavy work — the nmap scan, IP geolocation, hostname resolution, CVE lookups — all fans out into background daemon threads, and results stream back to the browser over Server-Sent Events. So the page never blocks; tiles just fill in as each worker finishes. There's also a cloudflared tunnel with a watchdog, so the whole thing gets a public URL and restarts itself if the tunnel drops."

`[B-ROLL: CODE_GRAPH.md import graph; then split-screen of worker log tags scrolling next to tiles populating]`
`[LOWER-THIRD: background workers → SSE bus → live UI]`

### 2:20 – 3:30 — The tracking pixel / fingerprint engine
> "Here's the data-collection side. You generate a 1-by-1 pixel, and when it loads it pulls a JS payload that fingerprints the browser in stages. Stage one is instant — canvas and WebGL hashes, audio hash, screen resolution, timezone, platform, CPU cores, memory, fonts, the user-agent client hints. Stage two goes async for media-device and permission states. Stage three is the fun one for a red-teamer: it probes for local apps — it'll WebSocket- and timing-probe for things like Discord, Spotify, Steam, a running VS Code debug port — to infer what software is on the box. And stage four, only if you explicitly enable geo, requests GPS. Every stage posts back to `/collect`, and that fires the server-side workers."

`[B-ROLL: generate.html pixel UI → target.html fingerprint panel filling in → highlight the local-app probe results]`
`[LOWER-THIRD: fp.js — 4-stage collection pipeline]`

### 3:30 – 4:40 — nmap + IP intelligence
> "While the browser side is collecting, the server kicks off an nmap scan against the source — ports, services, OS guess — and runs the IP through geolocation: country, ISP, and a VPN/proxy flag. This is where it stops being passive. You're not just seeing a user-agent string; you're seeing open ports and a service inventory, correlated with where the connection actually came from. And all of it lands in the same target record."

`[B-ROLL: nmap tile populating with ports/services; IP-intel tile with map/ISP/VPN flag]`
`[LOWER-THIRD: nmap auto-scan + ip-api geolocation]`

### 4:40 – 6:00 — CVE intelligence (the core value)
> "Now the part I actually built this for. Every service and version the scan finds, plus the browser and OS from the fingerprint, gets turned into search terms and queried live against the National Vulnerability Database. So instead of a flat port list, each target gets a ranked set of real CVEs with CVSS scores attached. The dashboard scores overall risk from that, so you can sort a whole target list by who's most exposed. This is the difference between 'host is running an old nginx' and 'host is running a version with these three scored CVEs, here's the worst one.'"

`[B-ROLL: CVE chips on target page; sort dashboard by risk score; click into a CVE]`
`[LOWER-THIRD: live NVD lookup → CVSS-scored CVEs → risk ranking]`

### 6:00 – 7:30 — The LLM analyst layer
> "On top of the raw data there's a language-model layer, and it's provider-flexible — it tries a local Ollama model first, then falls back to Anthropic or OpenAI, so you can keep everything on-box if you want. It does a few things. It streams a written analysis of a target's CVEs. It suggests plausible attack paths as a chain. It builds a threat-actor-style profile. There's a natural-language query box — you type a question in English, it turns it into SQL against your target database and shows you the rows. And it'll generate a full written recon report for a target. For an operator, this is the triage layer — it reads the mess so you can decide where to spend time."

`[B-ROLL: AI analysis streaming; attack-paths list; NL query box → results table; report page]`
`[LOWER-THIRD: Ollama → Anthropic → OpenAI · NL-to-SQL · streamed reports]`

### 7:30 – 9:00 — The Vulnerability Lab (CTF)
> "Last major piece, and the one I'd point a learner to first: the built-in vulnerability lab. It's a CTF environment. You log in, spin up intentionally-vulnerable targets as Docker containers on demand, work the challenge, and submit flags — which get hash-verified and scored on a live leaderboard. There's user registration, an admin view, per-challenge hints and points. So the same platform that does recon also doubles as a safe, self-contained place to *practice* on machines that are meant to be broken into — no external targets involved."

`[B-ROLL: lab login → challenge cards → start container → submit flag → scoreboard updates]`
`[LOWER-THIRD: Dockerized CTF lab · flag scoring · leaderboard]`

### 9:00 – 10:00 — Wrap + responsible-use close + CTA
> "So that's SystemAnalyzer: fingerprinting, scanning, IP intel, live CVE correlation, an LLM analyst, and a CTF lab, in one self-hosted Flask app. If you take one thing from this: a tool like this is only legitimate when it's pointed at assets you own or are explicitly authorized to test — the lab exists precisely so you can learn without crossing that line. I'll put the stack and setup notes below. If you want a deeper dive on any one piece — the SSE worker model, the CVE pipeline, or the LLM fallback chain — tell me in the comments and I'll make it. Thanks for watching."

`[B-ROLL: montage of all panels; end card with subscribe]`
`[LOWER-THIRD: ⚠ For authorized testing & lab use only]`

---

## PART 2 — SHOT LIST / STORYBOARD

| # | Time | Scene | What's on screen | Capture notes |
|---|------|-------|------------------|---------------|
| 1 | 0:00 | Hook montage | 4 fast cuts: pixel gen, hit landing, CVE chips, AI stream | Record each at full res, cut to ~1.5s each. Punchy. |
| 2 | 0:25 | Disclaimer card | Full-screen text slate: "Authorized testing & lab use only" | Hold 3s; also keep a persistent corner watermark the whole video. |
| 3 | 0:40 | Dashboard idle | Clean dashboard, empty-ish target list | Dark theme reads great; hide any real IPs/hostnames. |
| 4 | 1:10 | Architecture | `CODE_GRAPH.md` import graph + a simple animated diagram | Make a clean slide; don't just screen-read the markdown. |
| 5 | 1:40 | Worker/SSE demo | Split screen: terminal with `[nmap]`/`[tunnel]` log tags left, UI tiles filling right | The "tiles fill live" moment is your best visual — get it clean. |
| 6 | 2:20 | Pixel generator | `generate.html` creating a pixel | |
| 7 | 2:45 | Fingerprint panel | `target.html` fingerprint section populating; zoom local-app probe results | Blur/zero out any identifying values. |
| 8 | 3:30 | nmap tile | Ports/services/OS filling in | Use a lab VM as the target so results are real but safe. |
| 9 | 4:00 | IP-intel tile | Geo/ISP/VPN flag | **Censor real geolocation** — use a VPN/lab so the shown location isn't your home. |
| 10 | 4:40 | CVE chips | Target page CVE list with CVSS | Hero shot of the product's core value. |
| 11 | 5:20 | Risk sort | Dashboard sorted by risk score; click into one CVE | |
| 12 | 6:00 | AI analysis | Streaming analysis panel | Screen-record the stream in real time — the typing effect sells it. |
| 13 | 6:30 | Attack paths + NL query | Attack-path list; type an English question → SQL → rows | Pick a clean, impressive NL query. |
| 14 | 7:10 | Report page | Generated recon report | |
| 15 | 7:30 | Lab login → cards | `/lab` login, challenge grid | Use the demo creds on screen only if the instance is throwaway. |
| 16 | 8:00 | Start container + flag | Spin up a challenge, submit a flag, watch scoreboard update | Satisfying "correct flag" moment — keep it. |
| 17 | 9:00 | Wrap montage | Quick recap cuts of every panel | |
| 18 | 9:40 | End card | Subscribe + "deep dive?" prompt + watermark | Standard YT end screen, 20s. |

**Global capture checklist**
- Record at 1080p or 1440p, 60fps for smooth tile animations.
- Persistent corner watermark: `⚠ Authorized testing / lab only` the entire runtime.
- **Redact before publishing:** real public IPs, hostnames, MAC/geo data, API keys in configs, the real cloudflared tunnel URL, and the lab admin password. Do a dedicated redaction pass on the final cut.
- Keep the terminal font large (16–18pt) so log tags are readable on mobile.

---

## PART 3 — YOUTUBE METADATA

### Title options (pick one — A/B if you can)
1. **I Built a Recon + CVE Intelligence Platform (with an AI Analyst)**
2. **This Flask App Does Recon, nmap, CVE Lookup & AI Analysis — In One Dashboard**
3. **Automating Recon: Fingerprinting + Live CVE Intel + LLM Triage | SystemAnalyzer**
4. **I Built My Own Red-Team Recon Dashboard — Here's How It Works**

> Recommended: #1 or #4 (first-person "I built" over-performs for dev/security project reveals; keep the main keyword early).

### Description

```
SystemAnalyzer is a self-hosted Flask platform that unifies the recon stage of a
security engagement: browser fingerprinting, nmap scanning, IP geolocation, live
CVE lookups against the NVD, an LLM analyst layer, and a built-in Dockerized CTF
lab — all in one dashboard.

⚠️ For authorized security testing and lab/educational use ONLY. Everything in
this video runs against machines I own or a controlled lab environment. Don't
point tooling like this at systems you don't own or have written permission to test.

What's in the build:
• Background workers + Server-Sent Events for a non-blocking live dashboard
• 4-stage browser fingerprinting pipeline (fp.js)
• Automated nmap scan + service/OS inventory on every hit
• IP intelligence: geolocation, ISP, VPN/proxy detection
• Live CVE correlation with CVSS scoring and target risk ranking
• LLM analyst: streamed CVE analysis, attack-path suggestions, NL-to-SQL queries,
  generated recon reports — Ollama → Anthropic → OpenAI fallback
• Vulnerability Lab: on-demand vulnerable Docker containers, flag scoring, leaderboard

Stack: Python 3.12 · Flask · SQLite · nmap · cloudflared · Docker · Ollama/Anthropic/OpenAI

Chapters:
00:00 Intro
00:25 What it is + authorized-use note
01:10 Architecture (Flask, SQLite, SSE workers)
02:20 Browser fingerprinting pipeline
03:30 nmap + IP intelligence
04:40 Live CVE intelligence
06:00 The LLM analyst layer
07:30 The Vulnerability Lab (CTF)
09:00 Wrap-up + responsible use

#cybersecurity #redteam #infosec #pentesting #python #flask

Tooling shown is for authorized testing and education. Use responsibly and legally.
```

### Tags
```
cybersecurity, security research, red team, penetration testing, pentest, recon,
reconnaissance, cve, nvd, vulnerability scanning, nmap, browser fingerprinting,
osint, ip intelligence, flask, python, self-hosted, ctf, capture the flag,
docker, llm security, ollama, security tools, ethical hacking, infosec project
```

### Pinned first comment (recommended)
```
⚠️ Reminder: this is for AUTHORIZED testing and the built-in lab only. Every demo
here is against machines I own or a controlled environment. Want a deep dive on one
piece — the SSE worker model, the CVE pipeline, or the LLM fallback chain? Tell me below.
```

---

## PART 4 — THUMBNAIL CONCEPT

**Layout (1280×720):**
- Dark background (#0d1117, matching the app's GitHub-dark theme) with a faint grid / circuit texture.
- **Left ~60%:** large bold text, two lines:
  - Line 1 (white): `RECON + CVE`
  - Line 2 (accent green `#3fb950`): `INTELLIGENCE`
  - Small kicker above in muted gray: `I BUILT A`
- **Right ~40%:** a stylized dashboard screenshot fragment — CVE chips with red/orange CVSS badges and an AI panel mid-stream. Give it a subtle glow/border so it pops.
- **Bottom-left corner:** small amber pill badge: `⚠ AUTHORIZED / LAB ONLY`.
- **Accent:** one red "critical" CVE badge as the focal color pop against the green/dark palette.

**Text rules:** ≤ 4 words of big text, readable at 320px wide (mobile). High contrast. No clutter.

I've generated an actual thumbnail image to this spec — see `SystemAnalyzer_thumbnail.png`.

---

## QUICK PRE-PUBLISH CHECKLIST
- [ ] Watermark present entire runtime
- [ ] Authorized-use stated verbally (0:25) and on end card
- [ ] All real IPs / hostnames / geo / keys / tunnel URL redacted
- [ ] Lab admin password not shown (or instance is throwaway)
- [ ] Chapters match final cut timestamps
- [ ] Thumbnail text readable at mobile size
