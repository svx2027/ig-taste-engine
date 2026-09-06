# ig-taste-engine

Turn **your own saved Instagram reels** into a structured knowledge base you (or an
AI) can use to understand your taste — the formats, hooks, audio, and themes you
keep saving — and to generate new content ideas in that same style.

This is a personal-use pipeline: you point it at your own logged-in Instagram
session and your own Saved collections. It never touches anyone else's account,
and it never posts, likes, follows, or comments — it only reads what you've
already saved.

## What it does, in 60 seconds

1. You open your own `instagram.com/<you>/saved/` in a logged-in browser and pick
   which saved collections to process.
2. The pipeline enumerates every saved post in those collections, downloads the
   video (anonymously, via `yt-dlp` — no cookies, no login risk), extracts
   candidate frames, transcribes the audio, and reads on-screen text verbatim.
3. An AI enrichment pass tags each item with a taste taxonomy (format, theme,
   tone, hook type, audio type, language, why you probably saved it) and writes
   a short "why it works" / "recreation angle" note.
4. Everything lands in one flat CSV (`master.csv`) plus a browsable, image-embedded
   Excel workbook (`content_brain_vault.xlsx`) with editable review columns
   (Liked? / Recreate? / My twist / Priority / Status).
5. A taste-profile script distills the whole corpus into a one-page summary
   (top formats, hooks, audio, tone) and a calendar builder can turn scored
   concepts into a ready-to-shoot posting schedule.

Nothing here scrapes competitors or other people's accounts. Every reel it reads
is one *you* already saved to your own account.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # no secrets required today; kept for future config knobs
mkdir -p data
```

You'll also need on your `PATH`: `yt-dlp`, `ffmpeg`/`ffprobe`, and (for local
transcription on Apple Silicon) `mlx-whisper`. All are optional in the sense that
each stage degrades gracefully if its input files aren't there yet — but without
them you won't get video, frames, or transcripts.

### The pipeline, stage by stage

| Stage | Script | Reads | Writes |
|---|---|---|---|
| 0. Enumerate | *(browser, manual)* | your Saved folders | `data/manifest.json`, `data/feed-<slug>.json` |
| 1. Download | `dl_feed.py` | `feed-<slug>.json` | `videos/`, `thumbnails/`, `metadata/`, `dl-status-<slug>.json` |
| 1b. Batch download | `run_downloads.sh` | every `feed-*.json` | (calls `dl_feed.py` per collection) |
| 2. Frames | `frames.py` | `videos/` | `candidates/<slug>/<code>/*.jpg`, `candidates_index.json` |
| 3. Transcribe | `whisper_transcribe.py` | `videos/` | `transcripts/<slug>/<code>.txt` |
| 2+3 loop | `run_offline.sh` | (polls a downloads-done marker) | runs frames + transcribe repeatedly |
| 4a. Rich worklist *(optional)* | `make_vision_worklist.py` | `candidates_index.json`, metadata, transcripts | `vision-worklist.json` |
| 4b. Vision OCR + pick | `vision_workflow.js` | `candidates_index.json` | vision output JSON |
| 4c. Apply picks | `apply_picks.py` | vision output JSON | `onscreen_verbatim.json`, `frames_multi/` |
| 5. Merge partial runs *(optional)* | `build_combined.py` | two `master*.csv` files | `master_combined.csv` |
| 6. Assemble | `build_master.py` | everything above | `master.csv` |
| 6b. Aggregate | `build_aggregations.py` | `master.csv` | `audio_library.csv`, `creator_leaderboard.csv` |
| 7. Vault | `build_vault.py` | `master.csv` | `content_brain_vault.xlsx` |
| 8. Taste profile | `taste_profile.py` | `master.csv` (+ aggregates if present) | `TASTE_PROFILE.md` |
| 9. Calendar | `build_content_calendar.py` | a judged-concepts JSON (from your own idea-generation pass) | `REEL_IDEAS.md`, `CONTENT_CALENDAR.md`, `reel_queue.csv` |

Supporting tools: `capture_page.py` (macOS: screenshot the foregrounded Instagram
browser window by window ID), `montage_thumbs.py` (grid thumbnails for fast manual
review), `verify_feed.py` / `verify_master.py` (integrity re-derivation — re-count
everything from raw files rather than trusting the build script that produced it),
`make_judge_batches.py` (chunk recreation-angle text for a second-pass quality
judge), `make_vision_worklist.py` (an *optional* richer manifest — audio name,
caption head, transcript head per shortcode — for anyone wiring up their own,
more context-aware enrichment pass instead of the shipped `vision_workflow.js`,
which is self-contained and only needs `candidates_index.json`).

`vision_workflow.js` is written for a Claude Code-style agent-workflow runtime
that supplies `readFile()`, `agent()`, `parallel()`, and `env` as globals (it is
not a plain Node script you run with `node vision_workflow.js`). If you don't
have that kind of runtime, treat it as a reference implementation of the
prompt/schema/batching approach and swap in your own vision-model call.

Every script takes `--data-dir` (default `data`) so you can run multiple
accounts or re-runs side by side without editing any code.

### Data layout

```
data/
  manifest.json                 # [{"slug": "...", "name": "Display Name"}, ...]
  feed-<slug>.json              # {"slug", "reels": [{"code","mt","audio"}, ...]}
  manual_overrides.json         # {code: {creator, likes, comments, date, caption, duration}}
                                 #   — for login-gated / non-video items you captured by hand
  metadata/<slug>/<code>.info.json   # yt-dlp metadata
  videos/<slug>/<code>.mp4
  thumbnails/<slug>/<code>.jpg
  candidates/<slug>/<code>/c##.jpg, s##.jpg
  candidates_index.json
  frames_multi/<slug>/<code>_1..3.jpg
  transcripts/<slug>/<code>.txt
  enrichment.json               # {code: {title, onscreen_text, about, why_it_works,
                                 #   recreation_angle, format_template, theme, tone,
                                 #   hook_type, audio_type, language, why_saved, lyrics}}
  onscreen_verbatim.json
  master.csv
  content_brain_vault.xlsx
```

## The taste taxonomy

Each item is labeled with:

| Field | Example values |
|---|---|
| `format_template` | text-overlay-meme · POV · talking-head-rant · cinematic-b-roll · dance/transition · fact-card/bio · ad/promo · relatable-text · green-screen-react · carousel-tips · selfie-flex |
| `theme` | whatever recurring subjects show up in *your* saves — motivational, relatable/emotional, comedy/skit, travel/aesthetic, work/hustle, etc. |
| `tone` | deadpan · wholesome · cocky/flex · melancholic · satirical · hype · earnest |
| `hook_type` | question · POV · bold-claim · relatable-confession · visual-transition · listicle · shock-stat |
| `audio_type` | trending-sound · original-VO · song/lyric · instrumental · dialogue/meme-sound |
| `language` | whatever languages/scripts actually appear in your saves |
| `why_saved` (inferred) | recreate-template · reuse-audio · aesthetic-ref · idea-seed · personal |
| `shareability` (derived) | shares ÷ likes band: low / mid / high / viral |

The one-page taste profile (`taste_profile.py`) aggregates these across every
saved item into: top formats, recurring hooks, preferred audio types, dominant
themes, tone signature, language mix, and what "high-shareability for you" looks
like. That summary — not the raw rows — is what should seed new ideas: *"generate
10 reel concepts in my top 3 formats × top themes, with hooks of my preferred
type and an audio_type I reuse."*

## Reusable capture prompt

Paste this into an agent session with browser access to your own logged-in
Instagram to drive Phases 0–4 above:

> **ROLE & GOAL.** Build my "taste engine" from my own *saved* Instagram reels on
> my logged-in Chrome session. Capture one structured row per saved item, with
> verbatim on-screen text, audio, punchline frames, counts, AI analysis, and
> taste labels. Output under `data/`, one flat `master.csv` +
> `content_brain_vault.xlsx` (a `collection` column keeps folders separate —
> never split into different files). Reuse the scripts in this repo.
>
> **SAFETY (never break).** Read-only: never like, follow, comment, save,
> share, or DM. Human pace (a few seconds between actions), small batches
> (roughly 5–10 items), a longer pause between folders. **Pilot gate:** on the
> first folder, capture 5 items, then STOP and show me the rows and confirm
> there's no Instagram warning before continuing. Stop immediately on any
> captcha, "suspicious activity," a forced login, "try again later," or a load
> failure, and tell me exactly what you saw — do not push through. Never extract
> the browser's login cookies; login-gated items still get a row with a
> `status`, they just don't get a downloaded video. Never silently drop an item.
>
> **PHASE 0 — access audit, first.** Confirm you can reach the logged-in
> browser session, run `yt-dlp`/`ffmpeg`/a local transcriber, and write to the
> data directory. Report anything missing before proceeding.
>
> **PHASE 1 — enumerate folders, then stop.** Open your own Saved page, list
> every collection (name + item count if visible), and wait for me to pick
> which ones to process.
>
> **PHASES 2–5 — capture and build (resumable).** For each chosen folder:
> enumerate items into `feed-<slug>.json`; download video + cover + metadata;
> extract candidate frames; transcribe; run the vision pass for verbatim
> on-screen text and frame picks; run the enrichment pass for taste labels and
> analysis; assemble `master.csv` and `content_brain_vault.xlsx`. Verify by
> re-derivation (`verify_master.py`) before calling anything done.
>
> **PHASE 6 — taste profile.** After I've tagged what I liked, distill a
> one-page taste profile and use it to generate new reel concepts in my style.
>
> **Progress updates** at whichever comes first: every ~15 items, every 10%
> band, or ~15 minutes.

## Honest limitations

- **Requires a logged-in browser session for enumeration.** The download step
  (`yt-dlp`) runs anonymously and never touches your session cookies — by
  design, this pipeline refuses to extract or reuse browser login cookies, even
  though that would make gated content downloadable. Login-gated reels get a
  metadata-only row instead of a video.
- **No view counts.** Instagram doesn't expose reel play counts publicly, so
  every "engagement" signal here is likes/comments/shares only, and shares are
  the repost count (not always visible per post).
- **Transcription is unreliable on music and non-English speech.** Whisper
  hallucinates on song audio and some non-English audio; treat `audio_name` as
  the trustworthy field for music, and transcripts as best-effort.
- **Vision OCR can still miss very fast flash-text.** Sampling is time-based
  plus scene-cut detection, not exhaustive frame-by-frame.
- **This is designed to run at human pace and respect Instagram's terms.** It
  is not built for, and should not be used for, bulk scraping of other
  accounts' content — every capture stage here assumes you're pointing it at
  your own account's own saved posts.
- **Page screenshots (macOS) require the Instagram browser window to be
  foregrounded on the active Space.** Off-screen or occluded windows produce a
  blank capture; `capture_page.py` refuses rather than silently grabbing the
  wrong window.

## Safety rules (do not weaken)

- Read-only on Instagram: never like, follow, comment, save, share, or DM.
- Human pace, small batches, a pause between batches and between folders.
- Pilot gate on any new run: 5 items, stop, confirm no warning, then continue.
- Stop immediately on any captcha, "suspicious activity," forced login, or
  "try again later" — report exactly what was seen, don't retry blindly.
- Never extract or reuse the browser's login cookie store.
- One CSV per capture run; combine runs explicitly and traceably
  (`build_combined.py`), never by silent overwrite.

## License

MIT — see `LICENSE`.
