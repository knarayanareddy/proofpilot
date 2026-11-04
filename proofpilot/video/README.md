# ProofPilot — demo film (Remotion → MP4)

A ~3:03 product film for ProofPilot, built entirely as code: every scene is a React
component, `npx remotion render` drives headless Chrome frame-by-frame and ffmpeg
encodes the result to H.264. No After Effects, no screen recorder, no manual edit.

## Output

- `out/proofpilot-demo.mp4` — 1920×1080, 30 fps, 5495 frames (183.2 s ≈ 3:03), with narration.

## Run it

```bash
cd video
npm install
npx remotion studio src/index.js        # live preview at http://localhost:3000
npx remotion render src/index.js ProofPilot out/proofpilot-demo.mp4 --concurrency=2
```

Single-frame check (fast feedback while designing a scene):

```bash
npx remotion still src/index.js ProofPilot out/frame.png --frame=1600
```

## How it is put together

| File | Role |
| --- | --- |
| `narration.md` | The spoken script, cut into 10 segments. Source of truth for the words. |
| `public/audio/01..10.mp3` | Narration, one file per segment. |
| `src/timings.json` | Generated from the real MP3 durations (+0.9 s breathing room per segment). Holds fps, size, and each scene's `from` / `dur` in frames. |
| `src/Root.jsx` | Registers the `ProofPilot` composition and lays the 10 scenes end to end with `<Sequence>`, so each scene's internal timeline starts at its own frame 0. |
| `src/scenes/Part1.jsx` | S01 Hook · S02 Gap · S03 Intro · S04 Contract |
| `src/scenes/Part2.jsx` | S05 Ambiguity · S06 Model · S07 Sandbox |
| `src/scenes/Part3.jsx` | S08 Server write · S09 Read-back · S10 Results |
| `src/components/Ui.jsx` | Shared kit: backdrop, grid, panel, browser frame, field, chip, check, caption. Inline styles only — no web fonts, no CSS files, so the render is deterministic offline. |
| `src/theme.js` | Palette plus `fade()`, `rise()`, `lerp()`, `clamp01()` animation helpers. |
| `qa_overflow.py` | Playwright check that drives Remotion Studio and reports any text node that is clipped or that escapes the 1920×1080 frame. |

## Scene map (local frames)

| # | Scene | Frames | What it shows |
| --- | --- | --- | --- |
| 01 | Hook | 480 | A legitimate-looking supplier request; the second field change is the one that costs you. |
| 02 | Gap | 442 | What agents can do now vs. what has to be bounded (which record, field, value, version). |
| 03 | Intro | 382 | ProofPilot: contract → decision → bounded write → read-back → evidence. |
| 04 | Contract | 587 | Approval is bound to a contract hash; one character changed and the approval expires. |
| 05 | Ambiguity | 466 | Two similar supplier rows → the run pauses instead of guessing; a record version change stops it too. |
| 06 | Model | 569 | The Meta model proposes an action; the policy gate allows the in-scope one and denies the out-of-scope one. |
| 07 | Sandbox | 481 | Isolation probes: host port, external network, system paths, workspace mount, key — all unreachable/absent. |
| 08 | Server write | 565 | Authority lives on the server: approval re-checked at commit, cancelled and unknown-state branches. |
| 09 | Read-back | 619 | A separate read-only identity re-reads the record and only a successful comparison earns `VERIFIED`. Evidence export. |
| 10 | Results | 904 | Measured numbers and the outro. |

## Regenerating narration

1. Edit `narration.md`.
2. Re-record the segments (10 MP3s in `public/audio/`, same names).
3. Re-measure and rewrite the timings:

   ```bash
   python3 - <<'PY'
   import json, glob
   from mutagen.mp3 import MP3
   fps, pad = 30, 0.9
   scenes, cur = [], 0
   for i, f in enumerate(sorted(glob.glob('public/audio/*.mp3')), start=1):
       secs = MP3(f).info.length
       dur = round((secs + pad) * fps)
       scenes.append({"id": f"s{i:02d}", "index": i, "audio": f"audio/{i:02d}.mp3",
                      "seconds": round(secs, 2), "from": cur, "dur": dur})
       cur += dur
   json.dump({"fps": fps, "width": 1920, "height": 1080, "scenes": scenes, "total": cur},
             open('src/timings.json', 'w'), indent=2)
   print('total frames', cur, cur / fps, 's')
   PY
   ```

## Claims discipline

The film shows **measured** numbers from `reports/measurement.json`, stylised for screen
(shortened hashes, no raw provider request IDs). It does not say "computer use", does not
claim an external audit, and does not claim production readiness. Live-model results and
scripted-fixture results are never merged into a single success rate — see the repo
README for the split.
