---
name: youtube-video-context
description: Use when the user gives a YouTube/video link, playlist link, or search topic and wants Codex agents to use the audio, visuals, UI, gameplay, mechanics, or walkthrough content as coding or design context. Converts discovered videos into timestamped local context packs with metadata, captions, visual observations, and an agent-facing synthesis.
---

# YouTube Video Context

## Purpose

Turn a public YouTube video, playlist, or search topic into inspectable local context packs before using them as agent context. The goal is not a generic summary; the goal is timestamped, evidence-backed text that a coding agent can use for implementation, design analysis, bug reproduction, or mechanic inspiration.

## Quick Start

Run the bundled script from the installed skill directory:

```powershell
python scripts/ingest_youtube_video.py "https://www.youtube.com/watch?v=..." --focus "extract gameplay mechanics, UI feedback, progression, and implementation inspiration"
```

You can also hand it a playlist URL:

```powershell
python scripts/ingest_youtube_video.py "https://www.youtube.com/playlist?list=..." --max-videos 8 --focus "extract reusable UI and gameplay references"
```

Or a search topic/task:

```powershell
python scripts/ingest_youtube_video.py "cozy factory automation UI references" --source-type search --max-videos 5 --focus "find implementation inspiration for management-game HUDs"
```

Single-video outputs default to:

```text
.codex/video-context/<video-id>/
  metadata.json
  captions/
  gemini_video_analysis.md
  codex_context.md
  run_manifest.json
```

Playlist and search outputs also create a parent collection pack:

```text
.codex/video-context/_collections/<collection-slug>/
  collection_manifest.json
  codex_context.md
```

Read `codex_context.md` first. Load raw captions, metadata, or frame notes only when the task needs timestamp evidence.

## Local Dependencies

- `yt-dlp`: required for playlist expansion and search discovery; preferred for metadata, captions, audio/video download, and local evidence artifacts.
- `ffmpeg`: needed only for frame extraction after `--download-video`.
- Gemini API key: optional, but recommended for direct public YouTube visual and audio analysis.

The script detects optional tools and degrades to partial context packs when possible. Playlist expansion and search discovery require `yt-dlp`.

## API Keys

The script must not hardcode or persist Gemini keys. It reads Gemini keys from environment variables:

```powershell
$env:GEMINI_API_KEY = "<key>"
```

or:

```powershell
$env:GOOGLE_API_KEY = "<key>"
```

If no Gemini key is present, the script still collects metadata and captions when `yt-dlp` can access them, then writes partial context packs. If `yt-dlp` is not installed, the script can still run in Gemini-only mode for a single public YouTube URL, but title, duration, captions, local media extraction, playlist expansion, and search discovery will be unavailable.

If Gemini rejects the key or request, the generated `codex_context.md` includes the failure and asks the user to rotate/create a Google AI Studio key and set `GEMINI_API_KEY` before rerunning. Do not paste API keys into skill files, source files, manifests, or generated context packs.

## Workflow

1. Resolve the source:
   - direct video URL: ingest one video
   - playlist URL: expand playlist entries with `yt-dlp --flat-playlist`
   - search topic/task: run `yt-dlp` search discovery, bounded by `--max-videos`
2. Capture metadata with `yt-dlp` for each selected video.
3. Download manual and automatic captions when available.
4. Ask Gemini to analyze each public YouTube URL directly when an API key is available.
5. Write a concise per-video `codex_context.md` with:
   - source and metadata
   - available transcript artifacts
   - timestamped visual/audio observations
   - mechanics, UI, systems, progression, and implementation inspiration
   - evidence index for deeper review
6. For playlists/searches, write a parent `_collections/<collection-slug>/codex_context.md` that lists the generated per-video packs in reading order.

## Source Selection

The script defaults to `--source-type auto`:

- URL with `playlist` path or a `list=` query: playlist, including copied watch-page playlist URLs.
- Non-URL text: search topic/task.
- Other URL: single video.

Use `--source-type video`, `--source-type playlist`, or `--source-type search` to override the auto-detection. If you want only one video from a copied `watch?v=...&list=...` URL, pass `--source-type video`. `--max-videos` defaults to `5` for playlist and search ingestion so broad sources do not accidentally create large context packs. Raise it when the task needs wider coverage.

## When To Use Gemini Direct Video

Use the Gemini path for public YouTube links when the user wants visual and audio context quickly. Gemini can process public YouTube URLs directly, which avoids downloading full videos and gives a useful first pass over both speech and visuals.

Keep the local artifacts even when Gemini succeeds. The point of this skill is repeatability: future agents should read the saved context pack instead of re-querying the video blindly.

## When To Download Media

Use `--download-video` only when the task needs local frame evidence, OCR, or visual verification beyond the Gemini pass. This requires `ffmpeg` for frame extraction.

```powershell
python scripts/ingest_youtube_video.py "https://www.youtube.com/watch?v=..." --download-video --sample-interval 3
```

## Output Discipline

Prefer timestamped observations over broad prose. For game videos, extract:

- core gameplay loop
- player verbs and controls implied by the footage
- combat, traversal, economy, crafting, inventory, dialogue, or mission systems
- UI affordances, feedback, HUD state, menus, tooltips, and readable text
- progression, reward cadence, failure states, and pacing
- implementation ideas separated from direct copying

Do not treat model output as ground truth for exact mechanics. If a design decision depends on a specific value, animation, UI label, or timestamp, inspect the evidence artifact or rerun with a narrower focus.

## References

- `references/context-pack-format.md` describes the expected artifact shape.
- `scripts/ingest_youtube_video.py` performs the ingestion.
