# Context Pack Format

The context pack should be self-contained and safe for future agents to read without fetching the video again.

## Single-Video Required Files

- `metadata.json`: Raw or mostly raw `yt-dlp -J` metadata.
- `run_manifest.json`: Tool versions, options, source URL, and generated file list.
- `codex_context.md`: The first file agents should read.

## Optional Files

- `captions/`: Manual or automatic subtitle files downloaded by `yt-dlp`.
- `gemini_video_analysis.md`: Direct Gemini analysis of the public YouTube URL.
- `frames/`: Sampled frames when local media extraction was requested.
- `frame_index.json`: Timestamps and frame paths for sampled frames.

If `yt-dlp` is unavailable, `metadata.json` may contain only the URL, a parsed video id, and a warning. This is acceptable for Gemini-only context packs, but not for evidence-heavy analysis.

## Collection Required Files

Playlist and search ingestion creates a parent collection directory under:

```text
.codex/video-context/_collections/<collection-slug>/
```

Required collection files:

- `collection_manifest.json`: Source kind, source string, focus, model, tool versions, and generated per-video pack paths.
- `codex_context.md`: The first file agents should read for playlist/search ingestion.

The collection directory does not duplicate captions, frames, or Gemini analysis. It points to normal per-video packs under `.codex/video-context/<video-id>/`.

## `codex_context.md` Sections

Use this order for single-video packs:

1. Source
2. Capture Status
3. High-Level Loop
4. Mechanics Observed
5. UI And Feedback
6. Progression And Economy
7. Level Or Encounter Design
8. Implementation Inspiration
9. Evidence Index
10. Raw Analysis

Keep entries timestamped whenever the upstream analysis gives timestamps. If timestamps are not available, say so instead of inventing them.

For collection packs, use:

1. Source
2. Video Packs
3. Agent Reading Order

Each listed video pack should include the source URL, generated context-pack path, and first-read `codex_context.md` path.
