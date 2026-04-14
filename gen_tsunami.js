const pptxgen = require("pptxgenjs");

const C = {
  navy:      "1E2761",
  navyMid:   "2A3A8A",
  iceBlue:   "D6E4F7",
  white:     "FFFFFF",
  orange:    "F97316",
  amber:     "FBBF24",
  red:       "C0392B",
  redLight:  "E74C3C",
  redDark:   "922B21",
  green:     "1A7A4A",
  greenMid:  "27AE60",
  cloudBlue: "2980B9",
  cloudLight:"AED6F1",
};

const makeShadow  = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.18 });
const makeShadowSm= () => ({ type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.15 });

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";   // 13.3" × 7.5"
pres.title  = "Data Tsunami Prevention Architecture";

const s = pres.addSlide();
s.background = { color: "1C1C2E" };

// ── TITLE BANNER ─────────────────────────────────────────────
s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.78, fill:{color:C.navy}, line:{color:C.navy} });
s.addShape(pres.shapes.RECTANGLE, { x:0, y:0.74, w:13.3, h:0.06, fill:{color:C.amber}, line:{color:C.amber} });
s.addText("Data Tsunami Prevention Architecture", {
  x:0.2, y:0, w:12.9, h:0.46,
  fontSize:20, bold:true, color:C.white, fontFace:"Calibri",
  align:"center", valign:"middle", charSpacing:2,
});
s.addText("65 PTZ Cameras  +  90 EIO Radars  |  40 km OS2 SMF Fiber to MER Switch", {
  x:0.2, y:0.44, w:12.9, h:0.32,
  fontSize:9.5, color:C.iceBlue, fontFace:"Calibri",
  align:"center", valign:"middle",
});

// ═══════════════════════════════════════════════════
// LEFT PANEL — PROBLEM (The Tsunami)
// ═══════════════════════════════════════════════════
const LP = { x:0.18, y:0.88, w:6.3, h:6.42 };

s.addShape(pres.shapes.RECTANGLE, { x:LP.x, y:LP.y, w:LP.w, h:LP.h, fill:{color:"2D0A0A"}, line:{color:C.redLight, pt:1.5}, shadow:makeShadow() });

// Header
s.addShape(pres.shapes.RECTANGLE, { x:LP.x, y:LP.y, w:LP.w, h:0.58, fill:{color:C.redDark}, line:{color:C.redDark} });
s.addText("WITHOUT OPTIMISATION", { x:LP.x, y:LP.y, w:LP.w, h:0.3, fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("The Data Tsunami — Unfiltered Raw Stream", { x:LP.x, y:LP.y+0.28, w:LP.w, h:0.3, fontSize:9, color:"FFCCCC", fontFace:"Calibri", align:"center", valign:"middle" });

// PTZ box
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+1.3, y:LP.y+0.72, w:3.6, h:0.85, fill:{color:"3D1010"}, line:{color:C.redLight, pt:0.8}, shadow:makeShadowSm() });
s.addText("📷  65 PTZ Cameras", { x:LP.x+1.3, y:LP.y+0.72, w:3.6, h:0.38, fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("H.264:  260 Mbps  →  1.0 – 1.3 TB/Day", { x:LP.x+1.3, y:LP.y+1.1, w:3.6, h:0.38, fontSize:9, color:"FFAAAA", fontFace:"Calibri", align:"center", valign:"middle" });

// Arrow up
s.addText("▲", { x:LP.x+2.9, y:LP.y+1.6, w:0.44, h:0.72, fontSize:22, color:C.amber, fontFace:"Calibri", align:"center", valign:"middle" });

// Overload box
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+1.5, y:LP.y+2.34, w:3.2, h:1.28, fill:{color:C.redLight}, line:{color:C.amber, pt:2}, shadow:makeShadow() });
s.addText("DATA OVERLOAD!", { x:LP.x+1.5, y:LP.y+2.34, w:3.2, h:0.55, fontSize:16, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("Up to  2.5 TB / Day", { x:LP.x+1.5, y:LP.y+2.9, w:3.2, h:0.52, fontSize:20, bold:true, color:C.amber, fontFace:"Calibri", align:"center", valign:"middle" });

// Warning badges
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+0.2, y:LP.y+2.5, w:1.1, h:0.38, fill:{color:C.red}, line:{color:C.amber, pt:1}, shadow:makeShadowSm() });
s.addText("⚠ ALERT!", { x:LP.x+0.2, y:LP.y+2.5, w:1.1, h:0.38, fontSize:9.5, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+5.0, y:LP.y+2.5, w:1.1, h:0.38, fill:{color:C.red}, line:{color:C.amber, pt:1}, shadow:makeShadowSm() });
s.addText("⚠ WARNING!", { x:LP.x+5.0, y:LP.y+2.5, w:1.1, h:0.38, fontSize:9.5, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });

// Arrow down
s.addText("▼", { x:LP.x+2.9, y:LP.y+3.64, w:0.44, h:0.58, fontSize:22, color:C.redLight, fontFace:"Calibri", align:"center", valign:"middle" });

// EIO Radars box
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+0.14, y:LP.y+4.26, w:2.7, h:0.9, fill:{color:"3D1010"}, line:{color:C.redLight, pt:0.8}, shadow:makeShadowSm() });
s.addText("📡  90 EIO Radars", { x:LP.x+0.14, y:LP.y+4.26, w:2.7, h:0.38, fontSize:10, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("Hi-Fi:  180 Mbps\n~2 TB/Day", { x:LP.x+0.14, y:LP.y+4.64, w:2.7, h:0.48, fontSize:9, color:"FFAAAA", fontFace:"Calibri", align:"center", valign:"middle" });

// Fiber saturated box
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+3.4, y:LP.y+4.26, w:2.72, h:0.9, fill:{color:"3D1010"}, line:{color:C.redLight, pt:0.8}, shadow:makeShadowSm() });
s.addText("🔗  Fiber Link Saturated", { x:LP.x+3.4, y:LP.y+4.26, w:2.72, h:0.38, fontSize:10, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("528 Mbps required\nExceeds unmanaged capacity", { x:LP.x+3.4, y:LP.y+4.64, w:2.72, h:0.48, fontSize:9, color:"FFAAAA", fontFace:"Calibri", align:"center", valign:"middle" });

// Bottom summary
s.addShape(pres.shapes.RECTANGLE, { x:LP.x+0.14, y:LP.y+5.26, w:6.0, h:0.88, fill:{color:C.red}, line:{color:C.amber, pt:1.5}, shadow:makeShadow() });
s.addText("TSUNAMI:  H.264 + Raw Radar  =  528 Mbps  |  ~2.5 TB/Day", { x:LP.x+0.14, y:LP.y+5.26, w:6.0, h:0.44, fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("No compression  ·  No edge filtering  ·  Full raw data streaming 40 km over fiber", { x:LP.x+0.14, y:LP.y+5.7, w:6.0, h:0.38, fontSize:8.5, color:"FFDDDD", fontFace:"Calibri", align:"center", valign:"middle" });

// ═══════════════════════════════════════════════════
// RIGHT PANEL — SOLUTION (Prevention)
// ═══════════════════════════════════════════════════
const RP = { x:6.82, y:0.88, w:6.3, h:6.42 };

s.addShape(pres.shapes.RECTANGLE, { x:RP.x, y:RP.y, w:RP.w, h:RP.h, fill:{color:"071A35"}, line:{color:C.cloudBlue, pt:1.5}, shadow:makeShadow() });

// Header
s.addShape(pres.shapes.RECTANGLE, { x:RP.x, y:RP.y, w:RP.w, h:0.58, fill:{color:C.green}, line:{color:C.green} });
s.addText("TSUNAMI PREVENTION  —  Three-Layer Defence", { x:RP.x, y:RP.y, w:RP.w, h:0.3, fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("OS2 SMF Fiber  +  H.265  +  Edge AI  |  40 km to MER Switch", { x:RP.x, y:RP.y+0.28, w:RP.w, h:0.3, fontSize:9, color:"CCFFDD", fontFace:"Calibri", align:"center", valign:"middle" });

// Layer 1 sidebar
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.14, y:RP.y+0.66, w:0.4, h:1.78, fill:{color:C.cloudBlue}, line:{color:C.cloudBlue} });
s.addText("L\nA\nY\nE\nR\n1", { x:RP.x+0.14, y:RP.y+0.66, w:0.4, h:1.78, fontSize:7, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });

// PTZ H.265
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+0.72, w:2.62, h:0.82, fill:{color:"0A2744"}, line:{color:C.cloudBlue, pt:0.8}, shadow:makeShadowSm() });
s.addText("📷  65 PTZ  —  H.265", { x:RP.x+0.62, y:RP.y+0.72, w:2.62, h:0.38, fontSize:10, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("162.5 Mbps  |  ~650 GB/Day", { x:RP.x+0.62, y:RP.y+1.1, w:2.62, h:0.38, fontSize:9, color:C.cloudLight, fontFace:"Calibri", align:"center", valign:"middle" });

// EIO Metadata
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+3.42, y:RP.y+0.72, w:2.72, h:0.82, fill:{color:"0A2744"}, line:{color:C.cloudBlue, pt:0.8}, shadow:makeShadowSm() });
s.addText("📡  90 EIO  —  Metadata", { x:RP.x+3.42, y:RP.y+0.72, w:2.72, h:0.38, fontSize:10, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("4.5 Mbps  |  ~45 GB/Day", { x:RP.x+3.42, y:RP.y+1.1, w:2.72, h:0.38, fontSize:9, color:C.cloudLight, fontFace:"Calibri", align:"center", valign:"middle" });

// Arrows down to Layer 2
s.addText("▼", { x:RP.x+1.22, y:RP.y+1.56, w:0.5, h:0.38, fontSize:18, color:C.cloudBlue, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("▼", { x:RP.x+4.62, y:RP.y+1.56, w:0.5, h:0.38, fontSize:18, color:C.cloudBlue, fontFace:"Calibri", align:"center", valign:"middle" });

// Layer 2 sidebar
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.14, y:RP.y+1.96, w:0.4, h:1.0, fill:{color:C.amber}, line:{color:C.amber} });
s.addText("L\n2", { x:RP.x+0.14, y:RP.y+1.96, w:0.4, h:1.0, fontSize:7, bold:true, color:C.navy, fontFace:"Calibri", align:"center", valign:"middle" });

// Edge AI box
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+1.96, w:5.52, h:0.98, fill:{color:"0D3B6E"}, line:{color:C.amber, pt:1.5}, shadow:makeShadow() });
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+1.96, w:0.06, h:0.98, fill:{color:C.amber}, line:{color:C.amber} });
s.addText("🧠  EDGE AI  —  On-Device Intelligence (Breakwater)", { x:RP.x+0.76, y:RP.y+1.96, w:5.3, h:0.42, fontSize:10.5, bold:true, color:C.amber, fontFace:"Calibri", valign:"middle" });
s.addText("Motion-triggered only  ·  90% bandwidth cut  ·  <200 ms response  ·  Works offline if fiber fails", { x:RP.x+0.76, y:RP.y+2.38, w:5.3, h:0.5, fontSize:8.5, color:C.iceBlue, fontFace:"Calibri", valign:"middle" });

// Arrow to Layer 3
s.addText("▼", { x:RP.x+2.85, y:RP.y+2.98, w:0.6, h:0.38, fontSize:18, color:C.greenMid, fontFace:"Calibri", align:"center", valign:"middle" });

// Layer 3 sidebar
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.14, y:RP.y+3.38, w:0.4, h:1.0, fill:{color:C.greenMid}, line:{color:C.greenMid} });
s.addText("L\n3", { x:RP.x+0.14, y:RP.y+3.38, w:0.4, h:1.0, fontSize:7, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });

// OS2 SMF box
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+3.38, w:5.52, h:0.98, fill:{color:"0A1F44"}, line:{color:C.greenMid, pt:1.5}, shadow:makeShadow() });
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+3.38, w:0.06, h:0.98, fill:{color:C.greenMid}, line:{color:C.greenMid} });
s.addText("🔆  OS2 SMF FIBER  —  40 km  |  1 Gbps  |  1550 nm (Channel)", { x:RP.x+0.76, y:RP.y+3.38, w:5.3, h:0.42, fontSize:10.5, bold:true, color:C.greenMid, fontFace:"Calibri", valign:"middle" });
s.addText("SFP-ZX  ·  8.8 dB margin  ·  ~1.5 ms latency  ·  34% headroom  ·  10G upgrade: swap SFP only", { x:RP.x+0.76, y:RP.y+3.8, w:5.3, h:0.5, fontSize:8.5, color:C.iceBlue, fontFace:"Calibri", valign:"middle" });

// Arrow to MER
s.addText("▼", { x:RP.x+2.85, y:RP.y+4.4, w:0.6, h:0.36, fontSize:18, color:C.greenMid, fontFace:"Calibri", align:"center", valign:"middle" });

// MER Switch
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.62, y:RP.y+4.78, w:5.52, h:0.64, fill:{color:C.navy}, line:{color:C.cloudBlue, pt:1}, shadow:makeShadowSm() });
s.addText("🖥  MER SWITCH  —  Controlled Inflow  |  ~200 Mbps  |  ~0.7 TB/Day  (Edge AI: ~36 Mbps / 150 GB)", { x:RP.x+0.76, y:RP.y+4.78, w:5.3, h:0.64, fontSize:9, bold:true, color:C.white, fontFace:"Calibri", valign:"middle" });

// Bottom summary right
s.addShape(pres.shapes.RECTANGLE, { x:RP.x+0.14, y:RP.y+5.52, w:6.0, h:0.72, fill:{color:C.green}, line:{color:C.greenMid, pt:1.5}, shadow:makeShadow() });
s.addText("TSUNAMI TAMED:  ~200 Mbps  |  ~0.7 TB/Day  (–73% vs unoptimised)", { x:RP.x+0.14, y:RP.y+5.52, w:6.0, h:0.36, fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle" });
s.addText("With Edge AI:  ~36 Mbps  |  ~150 GB/Day  (–94% vs unoptimised)", { x:RP.x+0.14, y:RP.y+5.88, w:6.0, h:0.3, fontSize:9, color:"CCFFDD", fontFace:"Calibri", align:"center", valign:"middle" });

// ── CENTRE VS BADGE ───────────────────────────────────────────
s.addShape(pres.shapes.RECTANGLE, { x:6.56, y:0.88, w:0.26, h:6.42, fill:{color:"1C1C2E"}, line:{color:"1C1C2E"} });
s.addShape(pres.shapes.OVAL, { x:6.44, y:3.68, w:0.5, h:0.5, fill:{color:C.amber}, line:{color:C.amber}, shadow:makeShadow() });
s.addText("VS", { x:6.44, y:3.68, w:0.5, h:0.5, fontSize:9, bold:true, color:C.navy, fontFace:"Calibri", align:"center", valign:"middle" });

// ── FOOTER ────────────────────────────────────────────────────
s.addShape(pres.shapes.RECTANGLE, { x:0, y:7.34, w:13.3, h:0.16, fill:{color:C.navy}, line:{color:C.navy} });
s.addText("Data Tsunami Prevention Architecture  ·  Without Opt: 528 Mbps / 2.5 TB/Day  ──────────────────────────────  With OS2 SMF + H.265 + Edge AI: ~36 Mbps / 150 GB/Day  ·  94% Reduction", {
  x:0, y:7.34, w:13.3, h:0.16,
  fontSize:7.5, color:C.white, fontFace:"Calibri",
  align:"center", valign:"middle",
});

// ── SAVE ──────────────────────────────────────────────────────
const outFile = "/Users/fighter/Documents/SystemAnalyzer/Data_Tsunami_Prevention_Architecture.pptx";
pres.writeFile({ fileName: outFile })
  .then(() => console.log("✅  Saved: " + outFile))
  .catch(err => { console.error("❌  Error:", err); process.exit(1); });
