"""Inject timeline.json into stage.html -> stage.built.html"""
import json, os
d = os.path.dirname(os.path.abspath(__file__))
tl = open(os.path.join(d, "timeline.json")).read()
html = open(os.path.join(d, "stage.html")).read()
html = html.replace("__TIMELINE__", tl)
open(os.path.join(d, "stage.built.html"), "w").write(html)
print("built stage.built.html", len(html), "bytes")
