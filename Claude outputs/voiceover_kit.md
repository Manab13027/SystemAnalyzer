# SystemAnalyzer — Voiceover Kit (macOS)

Generate the full narration as an audio track on your own Mac, free and offline, using the built-in `say` command. Then drop it under your screen recording in any editor.

The full script is in **`narration_full.txt`** (clean spoken prose, no stage directions — safe to feed straight to `say`).

---

## 1. Quick start (one command)

```bash
# cd into the folder where you saved narration_full.txt, then:
say -v Ava -r 150 -f narration_full.txt -o voiceover.aiff
```

- `-v Ava` picks the voice (see the list below).
- `-r 150` sets the rate in words per minute. 150 is a calm, clear tutorial pace. Lower = slower.
- `-o voiceover.aiff` writes an audio file instead of speaking aloud.

That single file is your whole narration. Import it into iMovie / DaVinci Resolve / CapCut / Premiere and line up the on-screen action to it.

> **On length:** the script runs ~11–12 min of pure speech at `-r 150`. Your finished video reaches 15–20 min once you add the natural pauses while scans run, the intro/outro, and b-roll. Want it longer on narration alone? Use `-r 135`, or split and add your own commentary between sections.

---

## 2. Pick a better voice

List every voice installed on your Mac:

```bash
say -v '?'            # all voices
say -v '?' | grep en_  # English only
```

Good English choices that ship with macOS: **Ava, Samantha, Allison, Tom, Evan, Zoe**.

**Big upgrade — premium neural voices (free):** System Settings → Accessibility → Spoken Content → System Voice → **Manage Voices…** → download an *(Enhanced)* or *(Premium)* voice such as **Ava (Premium)** or **Zoe (Premium)**. Then:

```bash
say -v "Ava (Premium)" -r 150 -f narration_full.txt -o voiceover.aiff
```

Premium voices sound dramatically more natural than the default — worth the 1-minute download.

---

## 3. Convert to MP3 / M4A for your editor

`.aiff` is large and some editors prefer compressed audio:

```bash
# Built-in, no install needed:
afconvert voiceover.aiff voiceover.m4a -d aac -f m4af

# Or, if you have ffmpeg (brew install ffmpeg):
ffmpeg -i voiceover.aiff -b:a 192k voiceover.mp3
```

---

## 4. Record it section by section (recommended for syncing)

Doing it in chunks makes it far easier to match narration to what's on screen. Split `narration_full.txt` into per-chapter text files (the paragraph breaks already mark the beats), then:

```bash
for f in 01_intro 02_setup 03_fingerprint 04_recon 05_cve 06_ai 07_lab 08_outro; do
  say -v "Ava (Premium)" -r 150 -f "$f.txt" -o "$f.aiff"
done
```

Now each section is its own clip you can slide around on the timeline.

---

## 5. Tips for a clean result

- **Preview before rendering:** drop `-o …` to hear it live first: `say -v Ava -r 150 "test sentence"`.
- **Fix pronunciations:** spell tricky terms phonetically in a copy of the script — e.g. write `nmap` as `N-map`, `CVE` as `C-V-E`, `vsftpd` as `V-S-F-T-P-D`, `CVSS` as `C-V-S-S`, `SQLi` as `sequel-eye`. `say` reads letters better when hyphenated.
- **Add breathing room:** insert `[[slnc 400]]` in the text for a 400 ms pause (e.g. between chapters). Example: `... respect the boundary. [[slnc 600]] With that said, let's build.`
- **Match the animated demo:** the MP4 I made follows this same narrative order, so you can use it as the intro/teaser or cut its scenes in as b-roll between your live screens.

---

## 6. If you'd rather use a cloud voice

For the most human-sounding result, paste `narration_full.txt` into a service like ElevenLabs or PlayHT (free tiers exist) and export the audio. The script is written to read naturally either way.
