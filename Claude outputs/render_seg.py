"""Render one time segment [t0,t1) of stage.built.html to an mp4 segment.

Usage: python3 render_seg.py <t0> <t1> <out_mp4> [fps]
Deterministic: calls window.renderAt(t) per frame and screenshots.
"""
import sys, os, subprocess, shutil, math
from playwright.sync_api import sync_playwright

t0 = float(sys.argv[1]); t1 = float(sys.argv[2]); out = sys.argv[3]
fps = int(sys.argv[4]) if len(sys.argv) > 4 else 12
d = os.path.dirname(os.path.abspath(__file__))
url = "file://" + os.path.join(d, "stage.built.html")
frames = "/tmp/segframes"
shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)

n = int(round((t1 - t0) * fps))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox","--force-color-profile=srgb"])
    pg = b.new_page(viewport={"width":1920,"height":1080}, device_scale_factor=1)
    pg.goto(url)
    pg.wait_for_function("window.__ready===true", timeout=15000)
    for i in range(n):
        t = t0 + i / fps
        pg.evaluate(f"window.renderAt({t})")
        pg.screenshot(path=f"{frames}/f_{i:05d}.jpg", type="jpeg", quality=70)
    b.close()

subprocess.run([
    "ffmpeg","-y","-v","error","-framerate",str(fps),"-i",f"{frames}/f_%05d.jpg",
    "-c:v","libx264","-pix_fmt","yuv420p","-r",str(fps),"-crf","23",out
], check=True)
shutil.rmtree(frames, ignore_errors=True)
print(f"segment {out}: {n} frames, {round(n/fps,2)}s")
