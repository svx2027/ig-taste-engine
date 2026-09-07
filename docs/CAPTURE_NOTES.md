# Capture notes: platform quirks this pipeline works around

Lessons learned running the enumerate → download → frame → transcribe → vision
loop against real Instagram reels. Every one of these cost a wasted run before
the code accounted for it; recording them here so they don't have to be
re-discovered.

## `yt-dlp` on Instagram: what "no video" actually means

Anonymous `yt-dlp` (no cookies, no login) downloads most public reels cleanly,
but two failure strings mean two different things and the pipeline should not
treat them the same:

- **"There is no video in this post"** — the post is a photo or a carousel, not
  a reel. It has no video to fetch; this is expected, not an error.
- **An empty/failed media response** — the post is login-gated (a private
  account, or a post Instagram is throttling to anonymous fetchers). This is
  also expected, and the right response is to record it as such and move on,
  never to fall back to reusing a logged-in session's cookies for the fetch
  (see Safety rules in the README — this pipeline deliberately never does
  that).

A grid's own "this is a video" icon in the Instagram UI is not fully reliable
either — verify per item from the actual fetch result, not from what the
saved-collection grid implies.

## Counts: prefer the exact field, then a manual fallback, then blank

`yt-dlp`'s own metadata (`like_count`, `comment_count`) is the accurate source
when present, and it's what `build_master.py` reads first. When a post's
counts are hidden from `yt-dlp`, the page's `og:description` meta tag is a
reliable backup during the manual browser-enumeration step — it renders as
prose ("1.2K likes, 43 comments - user on DATE: caption") and a human or
capture agent can read the numbers off it by eye and record them in
`manual_overrides.json`, which `build_master.py` does read as its second
source. There's no automated `og:description` parser in this repo — this is a
technique for the browser step, not pipeline code. When *both* sources are
empty (Instagram fully hides engagement counts on some posts), leave the
field blank rather than guessing — a blank cell is honest, a fabricated one is
not.

## Frame sampling: time-slices union scene-cuts, not one frame

Sampling a single early frame per clip misses the moment that actually matters:
the reveal or punchline in a text-overlay or meme-style reel is very often in
the last third, and a static on-screen caption can change between scene cuts
with no camera motion to key off of. The fix that worked: sample candidate
frames at fixed time percentages (roughly 10/30/50/72/90% of the clip) *union*
`ffmpeg` scene-cut detection (`select=gt(scene,0.4)`, capped at a few extra
frames), then let a vision pass read every candidate and pick up to three
distinct frames spanning hook → transition → punchline. Any on-screen text
transcription is done **verbatim, in the original script** — no translation or
romanization — since that text is often the actual creative artifact being
studied.

## Visual assets: screenshot the real page, don't scrape the CDN

Instagram's own image/CDN URLs are stripped by query-string signing in a way
that makes them unusable once pulled out of a page's JS state — a URL that
loads fine in the browser context returns nothing when re-requested outside
it. The reliable path for anything visual that isn't already a downloaded
video frame (e.g. a full-page reference screenshot) is a real, rendered
screenshot of the actual browser window, not a fetch of an asset URL scraped
from the page.

On macOS specifically, a window-targeted screenshot only works if that browser
window is on the **active Space** and not occluded by another window — an
off-Space or covered capture silently returns a blank page (just chrome, no
content). `capture_page.py` locates its target window by title and refuses to
proceed rather than risk grabbing the wrong (or an empty) window if it can't
confirm the right one is frontmost.

## Whisper is unreliable on music and non-English speech

Local Whisper transcription hallucinates readily on song audio (music reels
transcribe as garbled or entirely wrong text, not the creator's voice) and is
materially less reliable on non-English speech than on English. For a reel
built around a trending audio track, treat the audio-track name (when the
platform exposes one) as the trustworthy field describing what's playing, and
treat the Whisper transcript as best-effort — useful for spoken voiceover,
not to be trusted blindly for music or a language it wasn't tuned for.

## Integrity: a count mismatch is a defect until explained

Every stage that enumerates or transforms items should let a later, independent
pass re-derive the same totals from the raw files on disk (see
`verify_feed.py` / `verify_master.py` in this repo) rather than trusting the
count a build script reports about its own output. A mismatch between "how
many items were enumerated" and "how many rows exist downstream" is always
worth chasing down: it is exactly the kind of gap a mundane bug (a
misclassified item, a scripting error that silently drops a batch) hides
behind. Treat "the numbers don't match" as a bug until you've found the
specific item that explains the gap, never as noise to average away.
