# YouTube Video Context

Turn public YouTube videos, playlists, or search topics into timestamped local context packs that coding agents can use as evidence.

This skill is for agentic coding workflows where a human provides YouTube evidence, research, gameplay footage, UI references, walkthroughs, demos, talks, or tutorials and expects the agent to extract only the context it needs.

## Install

With the Skills CLI:

```bash
bunx skills add ifBars/youtube-video-context
```

The official Skills CLI docs also show:

```bash
npx skills add ifBars/youtube-video-context
```

Install globally when you want the skill available across projects:

```bash
bunx skills add -g ifBars/youtube-video-context
```

After install, ask your agent to use `$youtube-video-context` with a YouTube video URL, playlist URL, or search topic.

## What It Does

- Ingests a single public YouTube URL.
- Expands playlist URLs into bounded per-video context packs.
- Searches YouTube from a topic or task when `--source-type search` is used, or automatically when the input is not a URL.
- Captures metadata and captions with `yt-dlp` when available.
- Optionally asks Gemini to analyze public YouTube URLs directly for visual and audio observations.
- Optionally downloads media and samples frames when local visual evidence is needed.
- Writes self-contained context packs under `.codex/video-context/`.

## Examples

Single video:

```bash
python scripts/ingest_youtube_video.py "https://www.youtube.com/watch?v=VIDEO_ID" --focus "extract UI states, visible labels, and implementation details"
```

Playlist:

```bash
python scripts/ingest_youtube_video.py "https://www.youtube.com/playlist?list=PLAYLIST_ID" --max-videos 8 --focus "extract reusable gameplay and HUD references"
```

Search topic:

```bash
python scripts/ingest_youtube_video.py "cozy factory automation UI references" --source-type search --max-videos 5 --focus "find management-game HUD and feedback patterns"
```

## Dependencies

- Python 3.10+.
- `yt-dlp` is required for playlist expansion, search discovery, rich metadata, captions, and media downloads.
- `ffmpeg` is required only for frame extraction after `--download-video`.
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` is optional but recommended for public YouTube visual/audio analysis.

No API keys are stored in the skill. Set keys in your shell environment when needed.

## Generated Context

Single-video packs are written to:

```text
.codex/video-context/<video-id>/
  metadata.json
  captions/
  gemini_video_analysis.md
  codex_context.md
  run_manifest.json
```

Playlist and search ingestion also create:

```text
.codex/video-context/_collections/<collection-slug>/
  collection_manifest.json
  codex_context.md
```

Agents should read `codex_context.md` first, then inspect raw captions, frame indexes, or metadata only when timestamp evidence matters.

## Validate

Run the included unit tests:

```bash
bun run test
```

Create a distribution zip:

```bash
bun run package
```

The zip is written to `dist/youtube-video-context.zip`.

## Publishing And skills.sh

skills.sh does not require a separate registry submission. Public GitHub repos with discoverable `SKILL.md` files can be installed with the Skills CLI, and installs are reflected on skills.sh through anonymous install telemetry.

## License

MIT
