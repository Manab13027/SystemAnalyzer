"""Re-time timeline.json + captions.srt to match the generated voice-over.

Model matches say_lines.txt exactly:
  lead 0.40s, 0.70s pause after every cue, +1.30s at each chapter change.
Speech time (audio_total - pauses) is distributed across cues by the character
count of the *spoken* (pronunciation-fixed) text, so each caption lands on its
line. Pass the real audio duration as argv[1].
"""
import json, os, re, sys

AUD = float(sys.argv[1]) if len(sys.argv) > 1 else 579.567
LEAD, SENT, CHAP = 0.40, 0.70, 1.30

d = os.path.dirname(os.path.abspath(__file__))
tl = json.load(open(os.path.join(d, "timeline.json")))
cues = tl["cues"]

def fix(t):
    t = re.sub(r"\bAI\b", "A.I.", t)
    t = t.replace("four-four-four-four", "forty-four, forty-four")
    t = t.replace("R-D-P","R.D.P.").replace("S-M-B","S.M.B.").replace("L-L-M","L.L.M.")
    t = t.replace("u-f-w","U.F.W.").replace("p-f","P.F.")
    t = t.replace("OpenSSH","Open S.S.H.").replace("CVE","C.V.E.").replace("macOS","mac O.S.")
    return t

chars = [max(4, len(fix(c["text"]))) for c in cues]
n_chap_changes = sum(1 for i in range(1, len(cues)) if cues[i]["chapter"] != cues[i-1]["chapter"])
pause_total = LEAD + SENT*len(cues) + CHAP*n_chap_changes
speech_total = max(1.0, AUD - pause_total)
csum = sum(chars)

t = LEAD
prev = None
for i, c in enumerate(cues):
    if prev is not None and c["chapter"] != prev:
        t += CHAP
    sp = speech_total * chars[i] / csum
    c["start"] = round(t, 3)
    t += sp
    c["end"] = round(t, 3)
    # caption persists through the trailing pause (ends at next cue start)
    c["disp_end"] = round(t + SENT, 3)
    t += SENT
    prev = c["chapter"]

# rebuild chapters
chapters = []
for c in cues:
    if not chapters or chapters[-1]["title"] != c["chapter"]:
        chapters.append({"title": c["chapter"], "start": c["start"], "end": c["disp_end"]})
    else:
        chapters[-1]["end"] = c["disp_end"]

tl["total"] = round(t, 3)
tl["chapters"] = chapters
json.dump(tl, open(os.path.join(d, "timeline.json"), "w"), indent=1)

def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".",",")
with open(os.path.join(d, "captions.srt"), "w") as f:
    for i,c in enumerate(cues,1):
        f.write(f"{i}\n{ts(c['start'])} --> {ts(c['disp_end'])}\n{c['text']}\n\n")

print(f"retimed: total={round(t,2)}s (audio={AUD}s) cues={len(cues)} chapters={len(chapters)} pauses={round(pause_total,1)}s speech={round(speech_total,1)}s")
