"""Single source of truth for the Defender tutorial video.

Each cue = (chapter, act, seconds, caption_text). Start times are computed
sequentially. This module writes:
  - captions.srt      (burned into the video; also for the user's voice)
  - narration.txt     (clean script to paste into ElevenLabs / `say`)
  - timeline.json     (chapters + cues + acts, consumed by stage.html)
"""
import json, os

# (chapter title, act id, duration seconds, caption)
CUES = [
    # ---------------- INTRO ----------------
    ("INTRO", "intro1", 5.0, "In 2026, Japan declared a cybersecurity state of emergency."),
    ("INTRO", "intro1", 5.0, "The reason was new: the attacks were powered by AI."),
    ("INTRO", "intro2", 5.0, "Automated, adaptive, and faster than any human team could respond."),
    ("INTRO", "intro2", 5.0, "Signature-based tools miss them, because AI never reuses the same pattern twice."),
    ("INTRO", "intro3", 5.0, "So I built a tool to fight back. It's called Defender."),
    ("INTRO", "intro3", 5.5, "An AI-powered attack detection and mitigation console."),
    ("INTRO", "intro3", 5.0, "It runs completely offline, and nothing it scans ever leaves your machine."),
    ("INTRO", "intro3", 5.5, "No cloud, no account, and no third-party service ever sees your data."),
    ("INTRO", "intro3", 5.5, "And here's the key idea: to catch an AI attack, you use AI to defend."),
    ("INTRO", "intro3", 4.5, "In the next twelve minutes, I'll show you everything it does."),

    # ---------------- PART 1: THE DASHBOARD ----------------
    ("PART 1 — THE DASHBOARD", "dash_all", 5.0, "Everything starts on the dashboard."),
    ("PART 1 — THE DASHBOARD", "dash_all", 6.0, "One screen gives you your full security picture at a glance."),
    ("PART 1 — THE DASHBOARD", "dash_gauge", 5.5, "In the center is your overall threat level."),
    ("PART 1 — THE DASHBOARD", "dash_gauge", 6.0, "Right now this demo machine reads critical, with several serious findings."),
    ("PART 1 — THE DASHBOARD", "dash_ports", 6.0, "On the left, your most exposed ports, ranked by risk."),
    ("PART 1 — THE DASHBOARD", "dash_ports", 5.5, "Each one shows the application that opened it, and a clear verdict."),
    ("PART 1 — THE DASHBOARD", "dash_vuln", 6.0, "On the right, the vulnerability board counts open issues by severity."),
    ("PART 1 — THE DASHBOARD", "dash_vuln", 6.0, "Including the ones attackers are actively exploiting in the wild."),
    ("PART 1 — THE DASHBOARD", "dash_out", 5.5, "Below that, every outbound connection, and its current state."),
    ("PART 1 — THE DASHBOARD", "dash_feed", 6.0, "The live alert feed streams detections as they happen."),
    ("PART 1 — THE DASHBOARD", "dash_feed", 6.0, "Every alert carries a severity, a score, the evidence, and a fix."),
    ("PART 1 — THE DASHBOARD", "dash_modules", 6.0, "All of it is powered by seven specialized detection modules."),
    ("PART 1 — THE DASHBOARD", "dash_modules", 6.0, "Log traffic, phishing, endpoints, prompt injection, ports, posture, and outbound."),
    ("PART 1 — THE DASHBOARD", "dash_theme", 6.0, "And the whole console is zero-dependency Python. No framework, no install."),
    ("PART 1 — THE DASHBOARD", "dash_modules", 5.5, "Let's see them run against a real machine."),

    # ---------------- PART 2: SCAN THIS MACHINE ----------------
    ("PART 2 — SCANNING A MACHINE", "scan_btn", 5.0, "To analyze your own system, click scan this machine."),
    ("PART 2 — SCANNING A MACHINE", "scan_run", 5.5, "Defender detects your operating system automatically."),
    ("PART 2 — SCANNING A MACHINE", "scan_run", 5.5, "Windows, macOS, or Linux. It runs the right checks for each."),
    ("PART 2 — SCANNING A MACHINE", "scan_run", 6.0, "Everything it does here is strictly read-only. It never changes a thing."),
    ("PART 2 — SCANNING A MACHINE", "scan_run", 6.0, "It reads your listening ports, running processes, and live connections."),
    ("PART 2 — SCANNING A MACHINE", "scan_run", 5.5, "Then your security posture: firewall, encryption, patch status."),
    ("PART 2 — SCANNING A MACHINE", "scan_done", 6.0, "Watch the threat level. It resets, and reflects only this machine."),
    ("PART 2 — SCANNING A MACHINE", "scan_done", 6.0, "No leftover demo data. Just the real state of your system, right now."),
    ("PART 2 — SCANNING A MACHINE", "scan_done", 6.0, "Anything that needs admin to read is marked, never guessed."),
    ("PART 2 — SCANNING A MACHINE", "scan_done", 5.5, "And the input consoles fill with exactly what was found."),
    ("PART 2 — SCANNING A MACHINE", "scan_done", 6.0, "Your real hostname, your real ports, your real processes. Not a demo."),

    # ---------------- PART 3: PORT EXPOSURE ----------------
    ("PART 3 — PORT EXPOSURE", "ports_focus", 5.0, "Let's start with your open ports."),
    ("PART 3 — PORT EXPOSURE", "ports_focus", 6.0, "Defender scores every listening socket by how exposed it is."),
    ("PART 3 — PORT EXPOSURE", "ports_focus", 5.5, "Local-only ports are low risk. Ports open to the whole network are not."),
    ("PART 3 — PORT EXPOSURE", "port_row", 6.0, "Each row shows the port, the service, and the program behind it."),
    ("PART 3 — PORT EXPOSURE", "port_detail", 6.0, "This one is a red flag: port four-four-four-four."),
    ("PART 3 — PORT EXPOSURE", "port_detail", 6.0, "The default port for Metasploit reverse shells."),
    ("PART 3 — PORT EXPOSURE", "port_detail", 6.0, "Opened by a program running from a temporary folder. A classic intrusion sign."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 6.0, "Defender's verdict is clear: close. And it gives you the exact command."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 5.5, "A reversible firewall rule, tailored to your operating system."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 5.5, "Risky services like R-D-P and S-M-B are flagged the same way."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 6.0, "On Windows it's a firewall rule. On Linux, a u-f-w command. On Mac, a p-f anchor."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 6.0, "And every block is reversible, so you can undo it at any time."),
    ("PART 3 — PORT EXPOSURE", "port_verdict", 5.5, "Low-risk, local-only ports are left alone, so you're not drowning in noise."),

    # ---------------- PART 4: VULNERABILITIES & CVEs ----------------
    ("PART 4 — VULNERABILITIES", "vuln_focus", 5.0, "Next, the vulnerability and posture audit."),
    ("PART 4 — VULNERABILITIES", "vuln_focus", 6.0, "Defender audits your operating system's security controls."),
    ("PART 4 — VULNERABILITIES", "vuln_focus", 6.0, "Firewall, disk encryption, automatic updates, and more."),
    ("PART 4 — VULNERABILITIES", "vuln_patch", 6.0, "It flags how far behind your patches are."),
    ("PART 4 — VULNERABILITIES", "vuln_patch", 6.0, "Because automated exploit kits target known gaps first."),
    ("PART 4 — VULNERABILITIES", "vuln_cve", 6.0, "Then it checks your installed software against a database of known exploits."),
    ("PART 4 — VULNERABILITIES", "vuln_cve", 6.0, "Here, an outdated OpenSSH version matches a critical remote-code-execution flaw."),
    ("PART 4 — VULNERABILITIES", "vuln_cve", 5.5, "Anything being exploited in the wild is marked clearly."),
    ("PART 4 — VULNERABILITIES", "vuln_fix", 6.0, "And every finding comes with a full fix playbook."),
    ("PART 4 — VULNERABILITIES", "vuln_fix", 6.0, "Why it matters, the steps, and the exact command to run."),
    ("PART 4 — VULNERABILITIES", "vuln_fix", 6.0, "The CVE list is a starter set you can extend with your own feeds."),
    ("PART 4 — VULNERABILITIES", "vuln_fix", 6.0, "Import a fuller database, and the matcher just gets smarter."),
    ("PART 4 — VULNERABILITIES", "vuln_score", 6.0, "Each finding is scored, so you always know what's urgent and what can wait."),

    # ---------------- PART 5: OUTBOUND MONITOR ----------------
    ("PART 5 — OUTBOUND MONITOR", "out_focus", 5.0, "Now the outbound connection monitor."),
    ("PART 5 — OUTBOUND MONITOR", "out_focus", 6.0, "It watches which applications are connecting out, and exactly where to."),
    ("PART 5 — OUTBOUND MONITOR", "out_anom", 6.0, "Here it caught a program sending traffic to a crypto-mining pool."),
    ("PART 5 — OUTBOUND MONITOR", "out_anom", 5.5, "A textbook sign of cryptojacking."),
    ("PART 5 — OUTBOUND MONITOR", "out_anom", 6.0, "And this file, run from Downloads, is talking to a known command-and-control port."),
    ("PART 5 — OUTBOUND MONITOR", "out_base", 6.0, "But here's the clever part. Defender learns what's normal for each app."),
    ("PART 5 — OUTBOUND MONITOR", "out_base", 6.0, "After a learning window, any brand-new destination is flagged as an anomaly."),
    ("PART 5 — OUTBOUND MONITOR", "out_base", 6.0, "That's the behavioral baseline. It catches what no signature could."),
    ("PART 5 — OUTBOUND MONITOR", "out_base", 6.0, "Each destination is also checked against reputation and known-bad ranges."),
    ("PART 5 — OUTBOUND MONITOR", "out_block", 5.5, "One click blocks the destination, and can stop the program behind it."),
    ("PART 5 — OUTBOUND MONITOR", "out_block", 6.0, "And if the app is trusted, you mark the destination safe to refine the baseline."),

    # ---------------- PART 6: THE OTHER MODULES ----------------
    ("PART 6 — MORE DETECTION", "logs", 5.5, "Four more modules handle input you feed in."),
    ("PART 6 — MORE DETECTION", "logs", 6.0, "The log analyzer reads web and auth logs."),
    ("PART 6 — MORE DETECTION", "logs", 6.0, "It catches credential stuffing, recon sweeps, and injection payloads."),
    ("PART 6 — MORE DETECTION", "phish", 6.0, "The content analyzer scores messages for AI-generated phishing."),
    ("PART 6 — MORE DETECTION", "phish", 6.0, "Urgency language, look-alike domains, and mismatched links."),
    ("PART 6 — MORE DETECTION", "endpoint", 6.0, "The endpoint module inspects running processes."),
    ("PART 6 — MORE DETECTION", "endpoint", 6.0, "Reverse shells, encoded commands, and ransomware-rate file activity."),
    ("PART 6 — MORE DETECTION", "llm", 6.0, "And the L-L-M defense module protects your own AI applications."),
    ("PART 6 — MORE DETECTION", "llm", 6.0, "It detects prompt injection, jailbreaks, and secrets leaking in model output."),
    ("PART 6 — MORE DETECTION", "llm", 6.0, "As AI gets woven into more apps, that attack surface only grows."),
    ("PART 6 — MORE DETECTION", "llm", 5.5, "Seven modules, one unified view of your risk."),

    # ---------------- PART 7: RESOLVE ----------------
    ("PART 7 — RESOLVE", "resolve", 5.0, "Detection is only half the job. Let's fix things."),
    ("PART 7 — RESOLVE", "resolve", 6.0, "Every alert has a resolve block with concrete, reversible steps."),
    ("PART 7 — RESOLVE", "resolve", 6.0, "The commands are tailored to your operating system."),
    ("PART 7 — RESOLVE", "resolve_copy", 5.5, "One click copies the exact command to your clipboard."),
    ("PART 7 — RESOLVE", "resolve_copy", 6.0, "But Defender never runs it for you. You review, you decide, you run it."),
    ("PART 7 — RESOLVE", "resolve_copy", 5.5, "No automated changes you didn't approve. You stay in control."),

    # ---------------- PART 8: AI ADVISOR ----------------
    ("PART 8 — THE AI ADVISOR", "advisor_plan", 5.0, "All of this feeds the AI advisor."),
    ("PART 8 — THE AI ADVISOR", "advisor_plan", 6.0, "A real scan can surface dozens of issues. Where do you start?"),
    ("PART 8 — THE AI ADVISOR", "advisor_plan", 6.0, "The advisor ranks everything by impact divided by effort."),
    ("PART 8 — THE AI ADVISOR", "advisor_plan", 6.0, "So the highest-value fixes rise straight to the top."),
    ("PART 8 — THE AI ADVISOR", "advisor_ask", 6.0, "And you can just ask it anything about your system."),
    ("PART 8 — THE AI ADVISOR", "advisor_ask", 6.0, "It answers using only your live scan results. No hallucinations."),
    ("PART 8 — THE AI ADVISOR", "advisor_ask", 6.0, "No internet, and no cloud model required."),
    ("PART 8 — THE AI ADVISOR", "advisor_ollama", 6.0, "If you run a local model with Ollama, answers get more conversational."),
    ("PART 8 — THE AI ADVISOR", "advisor_ask", 6.0, "Each answer is grounded in the exact findings behind it, so you can verify."),
    ("PART 8 — THE AI ADVISOR", "advisor_ollama", 6.0, "If you run a local model with Ollama, answers get more conversational."),
    ("PART 8 — THE AI ADVISOR", "advisor_ollama", 5.5, "But everything works without it. All on-device."),
    ("PART 8 — THE AI ADVISOR", "advisor_refresh", 6.0, "Fix something, hit refresh, and anything resolved drops off the plan."),

    # ---------------- OUTRO ----------------
    ("OUTRO", "outro", 5.0, "So that's Defender."),
    ("OUTRO", "outro", 6.0, "Seven modules, real machine scanning, and reversible fixes."),
    ("OUTRO", "outro", 5.5, "A grounded AI advisor, and zero dependencies."),
    ("OUTRO", "outro", 5.5, "To run it yourself, it's one command: python three, app dot py."),
    ("OUTRO", "outro", 5.5, "It opens in your browser, and everything stays on your machine."),
    ("OUTRO", "outro_end", 6.0, "If this was useful, like, subscribe, and share it with someone who cares about security."),
    ("OUTRO", "outro_end", 4.0, "Thanks for watching."),
]

GAP = 0.35  # small silence between cues


def build():
    cues = []
    t = 0.0
    for ch, act, dur, text in CUES:
        start = t
        end = t + dur
        cues.append({"chapter": ch, "act": act, "start": round(start, 2),
                     "end": round(end, 2), "text": text})
        t = end + GAP
    total = round(t, 2)

    # chapters with their time ranges
    chapters = []
    for c in cues:
        if not chapters or chapters[-1]["title"] != c["chapter"]:
            chapters.append({"title": c["chapter"], "start": c["start"], "end": c["end"]})
        else:
            chapters[-1]["end"] = c["end"]

    out = os.path.dirname(os.path.abspath(__file__))

    # SRT
    def ts(s):
        h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
    with open(os.path.join(out, "captions.srt"), "w") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n\n")

    # narration (plain, for TTS)
    with open(os.path.join(out, "narration.txt"), "w") as f:
        cur = None
        for c in cues:
            if c["chapter"] != cur:
                cur = c["chapter"]
                f.write(f"\n\n[{cur}]\n")
            f.write(c["text"] + " ")

    # timeline json for the stage
    with open(os.path.join(out, "timeline.json"), "w") as f:
        json.dump({"total": total, "chapters": chapters, "cues": cues}, f, indent=1)

    mins = int(total // 60); secs = int(total % 60)
    print(f"cues={len(cues)} chapters={len(chapters)} total={mins}:{secs:02d} ({total}s)")
    return total


if __name__ == "__main__":
    build()
