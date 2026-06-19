# YouTube video context

Give an agent a YouTube link and let it turn the video into a local, timestamped context pack.

This is useful when a video is part of the evidence: gameplay footage, UI references, tutorials, demos, talks, walkthroughs, bug repros, or research. The agent gets a saved context file it can read later instead of guessing from the title or asking you to summarize the clip by hand.

It also works with playlists and search topics. Those are kept bounded with `--max-videos`, so a broad playlist does not turn into an accidental research dump.

## Install

Install with the Skills CLI:

```bash
bunx skills add ifBars/youtube-video-context
```

You can also use npm or another package runner:

```bash
npx skills add ifBars/youtube-video-context
```

For a global install:

```bash
bunx skills add -g ifBars/youtube-video-context
```

Then ask your agent to use `$youtube-video-context` with a YouTube video URL, playlist URL, or search topic.

## What it does

- Ingests one public YouTube video.
- Expands playlist URLs into per-video context packs.
- Searches YouTube from a topic or task when the input is not a URL, or when `--source-type search` is set.
- Captures metadata and captions with `yt-dlp` when available.
- Can use Gemini for direct visual and audio analysis of public YouTube links.
- Can download video and sample frames when local visual evidence is needed.
- Writes everything under `.codex/video-context/` so future agents can inspect the same evidence.

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

- Python 3.10+
- `yt-dlp` for playlists, search, metadata, captions, and media downloads
- `ffmpeg` only when using `--download-video` for frame extraction
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` for optional Gemini analysis

No API keys are stored in the skill. Set them in your shell when you need Gemini.

## Output

Single-video packs:

```text
.codex/video-context/<video-id>/
  metadata.json
  captions/
  gemini_video_analysis.md
  codex_context.md
  run_manifest.json
```

Playlist and search runs also create a collection pack:

```text
.codex/video-context/_collections/<collection-slug>/
  collection_manifest.json
  codex_context.md
```

Read `codex_context.md` first. Open captions, frame indexes, or metadata only when you need to verify a timestamped claim.

## Validate

Run the tests:

```bash
bun run test
```

Build the distribution zip:

```bash
bun run package
```

The zip is written to `dist/youtube-video-context.zip`.

## skills.sh

There is no separate skills.sh submission step. Once users install the public GitHub repo with the Skills CLI, it can appear on skills.sh through anonymous install telemetry.

## License

MIT
