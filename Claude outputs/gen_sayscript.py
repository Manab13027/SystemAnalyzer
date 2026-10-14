"""Generate a CUE-ALIGNED say script from timeline.json.

One spoken line per caption cue, in order, each followed by a clear pause so
the finished audio can be auto-segmented (one speech block per caption).
Applies pronunciation fixes so TTS doesn't mangle acronyms/numbers.
Writes: say_lines.txt
"""
import json, os, re

d = os.path.dirname(os.path.abspath(__file__))
tl = json.load(open(os.path.join(d, "timeline.json")))

SENT_PAUSE = 700      # ms between caption lines (dramatic + detectable)
CHAP_PAUSE = 1300     # ms at a chapter change

def fix(t):
    t = re.sub(r"\bAI\b", "A.I.", t)
    t = t.replace("four-four-four-four", "forty-four, forty-four")
    t = t.replace("R-D-P", "R.D.P.").replace("S-M-B", "S.M.B.").replace("L-L-M", "L.L.M.")
    t = t.replace("u-f-w", "U.F.W.").replace("p-f", "P.F.")
    t = t.replace("OpenSSH", "Open S.S.H.").replace("CVE", "C.V.E.")
    t = t.replace("macOS", "mac O.S.")
    return t

lines = ["[[slnc 400]]"]
prev_ch = None
for c in tl["cues"]:
    if prev_ch is not None and c["chapter"] != prev_ch:
        lines.append(f"[[slnc {CHAP_PAUSE}]]")
    lines.append(fix(c["text"]) + f" [[slnc {SENT_PAUSE}]]")
    prev_ch = c["chapter"]

open(os.path.join(d, "say_lines.txt"), "w").write("\n".join(lines) + "\n")
print(f"say_lines.txt: {len(tl['cues'])} cue-aligned lines, "
      f"{SENT_PAUSE}ms sentence / {CHAP_PAUSE}ms chapter pauses")
