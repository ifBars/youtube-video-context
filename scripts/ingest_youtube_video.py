#!/usr/bin/env python3
"""Create timestamped Codex context packs from YouTube URLs, playlists, or searches."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any


DEFAULT_FOCUS = (
    "Extract practical coding and design context from this video. Focus on "
    "gameplay mechanics, player actions, UI feedback, progression systems, "
    "audio cues, visible text, and implementation inspiration. Use timestamps "
    "whenever possible."
)


@dataclass(frozen=True)
class VideoItem:
    url: str
    id: str
    title: str
    index: int


@dataclass(frozen=True)
class VideoCollection:
    kind: str
    source: str
    title: str
    items: list[VideoItem]


def run(cmd: list[str], cwd: Path | None = None, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Missing required tool: {name}. Install it and rerun.")
    return path


def optional_tool(name: str) -> str | None:
    return shutil.which(name)


def yt_dlp_command() -> list[str] | None:
    exe = optional_tool("yt-dlp")
    if exe:
        return [exe]
    probe = run([sys.executable, "-m", "yt_dlp", "--version"])
    if probe.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    return None


def slugify(value: str, fallback: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return value[:90] or fallback


def video_id_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if query.get("v"):
        return slugify(query["v"][0], "video")
    parts = [part for part in parsed.path.split("/") if part]
    return slugify(parts[-1] if parts else parsed.netloc, "video")


def is_probable_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_probable_playlist_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    query = urllib.parse.parse_qs(parsed.query)
    path_parts = {part.lower() for part in parsed.path.split("/") if part}
    return "playlist" in path_parts or "list" in query


def youtube_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def entry_url(entry: dict[str, Any]) -> str:
    url = entry.get("webpage_url") or entry.get("url") or ""
    if is_probable_url(url):
        return url
    video_id = entry.get("id") or url
    return youtube_watch_url(str(video_id))


def yt_dlp_json(args: list[str]) -> dict[str, Any]:
    yt_dlp = yt_dlp_command()
    if not yt_dlp:
        raise SystemExit("yt-dlp is required for playlist expansion and search discovery.")
    proc = run([*yt_dlp, "-J", "--no-warnings", *args])
    if proc.returncode != 0:
        raise SystemExit(f"yt-dlp discovery failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def collection_from_payload(kind: str, source: str, payload: dict[str, Any], max_videos: int) -> VideoCollection:
    entries = [entry for entry in payload.get("entries", []) if entry]
    items: list[VideoItem] = []
    for index, entry in enumerate(entries[:max_videos], start=1):
        url = entry_url(entry)
        video_id = str(entry.get("id") or video_id_from_url(url))
        title = str(entry.get("title") or f"Video {index}")
        items.append(VideoItem(url=url, id=slugify(video_id, f"video-{index}"), title=title, index=index))

    if not items:
        raise SystemExit(f"No videos were discovered for {kind}: {source}")

    title = str(payload.get("title") or source)
    return VideoCollection(kind=kind, source=source, title=title, items=items)


def resolve_collection(source: str, source_type: str, max_videos: int) -> VideoCollection | None:
    if max_videos < 1:
        raise SystemExit("--max-videos must be at least 1.")

    if source_type == "video":
        return None

    if source_type == "playlist" or (source_type == "auto" and is_probable_playlist_url(source)):
        payload = yt_dlp_json(["--flat-playlist", "--yes-playlist", source])
        return collection_from_payload("playlist", source, payload, max_videos)

    if source_type == "search" or (source_type == "auto" and not is_probable_url(source)):
        query = f"ytsearch{max_videos}:{source}"
        payload = yt_dlp_json(["--flat-playlist", query])
        collection = collection_from_payload("search", source, payload, max_videos)
        return VideoCollection(kind=collection.kind, source=source, title=source, items=collection.items)

    return None


def load_metadata(url: str) -> dict[str, Any]:
    yt_dlp = yt_dlp_command()
    if not yt_dlp:
        return {
            "id": video_id_from_url(url),
            "webpage_url": url,
            "title": "Metadata unavailable; yt-dlp was not found",
            "_context_pack_warning": "Install yt-dlp for title, duration, captions, and local media extraction.",
        }
    proc = run([*yt_dlp, "-J", "--no-warnings", "--no-playlist", url])
    if proc.returncode != 0:
        raise SystemExit(f"yt-dlp metadata extraction failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def download_captions(url: str, out_dir: Path, stem: str) -> list[str]:
    yt_dlp = yt_dlp_command()
    if not yt_dlp:
        (out_dir / "caption_download_error.txt").write_text(
            "yt-dlp was not found on PATH or as a Python module.",
            encoding="utf-8",
        )
        return []
    captions_dir = out_dir / "captions"
    captions_dir.mkdir(parents=True, exist_ok=True)
    output = str(captions_dir / f"{stem}.%(ext)s")
    cmd = [
        *yt_dlp,
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en.*,en",
        "--sub-format",
        "vtt/srt/best",
        "-o",
        output,
        url,
    ]
    proc = run(cmd)
    files = sorted(str(p.relative_to(out_dir)) for p in captions_dir.glob("*") if p.is_file())
    if proc.returncode != 0 and not files:
        (out_dir / "caption_download_error.txt").write_text(proc.stderr, encoding="utf-8")
    return files


def call_gemini(url: str, focus: str, model: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return textwrap.dedent("""
        ## Gemini Analysis Not Run

        No Gemini API key was found. Create or rotate a key in Google AI Studio, then set it before rerunning:

        ```powershell
        $env:GEMINI_API_KEY = "<new-key>"
        ```

        For a persistent Windows user-level variable:

        ```powershell
        setx GEMINI_API_KEY "<new-key>"
        ```
        """).strip()

    prompt = f"""
You are converting a YouTube video into context for coding agents.

Return concise Markdown with these sections:
- High-Level Loop
- Mechanics Observed
- UI And Feedback
- Audio And Dialogue
- Progression And Economy
- Level Or Encounter Design
- Implementation Inspiration
- Evidence Index

Rules:
- Use timestamps whenever possible.
- Separate observed facts from implementation ideas.
- Do not claim exact values unless they are visible or spoken.
- Optimize for a future coding agent building related mechanics.

Focus: {focus}
""".strip()

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"file_data": {"file_uri": url}},
                ]
            }
        ]
    }
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        action = "Check the Gemini API key, model name, and video URL, then rerun."
        if exc.code in {400, 401, 403}:
            action = (
                "The Gemini API key or request was rejected. Rotate/create a key in Google AI Studio, "
                "set `GEMINI_API_KEY` in your shell, then rerun."
            )
        return textwrap.dedent(f"""
        ## Gemini Analysis Failed

        HTTP status: {exc.code}

        Action: {action}

        Response:

        ```json
        {detail}
        ```
        """).strip()
    except urllib.error.URLError as exc:
        return textwrap.dedent(f"""
        ## Gemini Analysis Failed

        Network error: {exc}

        Action: Check connectivity, confirm the public YouTube URL is reachable, then rerun.
        """).strip()

    parts = (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n\n".join(text_parts).strip() or json.dumps(payload, indent=2)


def download_video(url: str, out_dir: Path, stem: str, max_height: int) -> Path | None:
    yt_dlp = yt_dlp_command()
    if not yt_dlp:
        (out_dir / "video_download_error.txt").write_text(
            "yt-dlp was not found on PATH or as a Python module.",
            encoding="utf-8",
        )
        return None
    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    output = str(media_dir / f"{stem}.%(ext)s")
    fmt = f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best"
    proc = run([*yt_dlp, "-f", fmt, "--merge-output-format", "mp4", "-o", output, url])
    files = sorted(media_dir.glob(f"{stem}.*"))
    if proc.returncode != 0 and not files:
        (out_dir / "video_download_error.txt").write_text(proc.stderr, encoding="utf-8")
        return None
    return files[0] if files else None


def extract_frames(video: Path, out_dir: Path, interval: int) -> list[dict[str, str]]:
    ffmpeg = optional_tool("ffmpeg")
    if not ffmpeg:
        (out_dir / "frame_extraction_error.txt").write_text("ffmpeg was not found on PATH.", encoding="utf-8")
        return []

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "frame_%06d.jpg"
    proc = run([
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps=1/{interval}",
        "-q:v",
        "3",
        str(pattern),
    ])
    if proc.returncode != 0:
        (out_dir / "frame_extraction_error.txt").write_text(proc.stderr, encoding="utf-8")
        return []

    index = []
    for idx, frame in enumerate(sorted(frames_dir.glob("frame_*.jpg"))):
        seconds = idx * interval
        timestamp = str(dt.timedelta(seconds=seconds))
        index.append({"timestamp": timestamp, "path": str(frame.relative_to(out_dir))})
    return index


def render_context(
    url: str,
    metadata: dict[str, Any],
    caption_files: list[str],
    gemini_text: str | None,
    frame_index: list[dict[str, str]],
    focus: str,
) -> str:
    title = metadata.get("title") or "Unknown title"
    uploader = metadata.get("uploader") or metadata.get("channel") or "Unknown uploader"
    duration = metadata.get("duration")
    duration_text = str(dt.timedelta(seconds=int(duration))) if isinstance(duration, (int, float)) else "unknown"

    lines = [
        "# Video Context",
        "",
        "## Source",
        "",
        f"- URL: {url}",
        f"- Title: {title}",
        f"- Uploader: {uploader}",
        f"- Duration: {duration_text}",
        f"- Focus: {focus}",
        "",
        "## Capture Status",
        "",
        f"- Captions: {len(caption_files)} file(s)" if caption_files else "- Captions: none captured",
        "- Gemini analysis: available" if gemini_text else "- Gemini analysis: not available",
        f"- Sampled frames: {len(frame_index)} file(s)" if frame_index else "- Sampled frames: not captured",
        "",
        "## Evidence Index",
        "",
    ]

    if caption_files:
        lines.extend(f"- Caption file: `{path}`" for path in caption_files)
    if frame_index:
        lines.extend(f"- Frame {item['timestamp']}: `{item['path']}`" for item in frame_index[:80])
        if len(frame_index) > 80:
            lines.append(f"- Frame index truncated here; see `frame_index.json` for {len(frame_index)} entries.")
    if not caption_files and not frame_index:
        lines.append("- No local evidence files beyond metadata were captured.")

    lines.extend(["", "## Raw Analysis", ""])
    if gemini_text:
        lines.append(gemini_text)
    else:
        lines.append(
            "No Gemini analysis was generated. Set `GEMINI_API_KEY` or `GOOGLE_API_KEY`, "
            "then rerun the script for direct visual and audio analysis of public YouTube URLs."
        )

    return "\n".join(lines).rstrip() + "\n"


def tool_versions() -> dict[str, str | None]:
    yt_dlp = yt_dlp_command()
    return {
        "yt-dlp": run([*yt_dlp, "--version"]).stdout.strip() if yt_dlp else None,
        "ffmpeg": "available" if optional_tool("ffmpeg") else None,
    }


def ingest_video(
    url: str,
    out_root: Path,
    focus: str,
    model: str,
    no_gemini: bool,
    download_video_enabled: bool,
    sample_interval: int,
    max_height: int,
) -> Path:
    metadata = load_metadata(url)
    video_id = metadata.get("id") or slugify(metadata.get("title", ""), "video")
    stem = slugify(str(video_id), "video")
    out_dir = out_root / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "metadata.json", metadata)
    caption_files = download_captions(url, out_dir, stem)

    gemini_text = None if no_gemini else call_gemini(url, focus, model)
    if gemini_text:
        (out_dir / "gemini_video_analysis.md").write_text(gemini_text + "\n", encoding="utf-8")

    frame_index: list[dict[str, str]] = []
    video_path = None
    if download_video_enabled:
        video_path = download_video(url, out_dir, stem, max_height)
        if video_path:
            frame_index = extract_frames(video_path, out_dir, max(1, sample_interval))
            write_json(out_dir / "frame_index.json", frame_index)

    context = render_context(url, metadata, caption_files, gemini_text, frame_index, focus)
    (out_dir / "codex_context.md").write_text(context, encoding="utf-8")

    generated_files = sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob("*") if p.is_file())
    if "run_manifest.json" not in generated_files:
        generated_files.append("run_manifest.json")
        generated_files.sort()

    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "url": url,
        "model": None if no_gemini else model,
        "focus": focus,
        "caption_files": caption_files,
        "downloaded_video": str(video_path.relative_to(out_dir)) if video_path else None,
        "frame_count": len(frame_index),
        "tools": tool_versions(),
        "files": generated_files,
    }
    write_json(out_dir / "run_manifest.json", manifest)
    return out_dir


def collection_slug(collection: VideoCollection) -> str:
    marker = collection.kind
    if collection.kind == "playlist":
        marker = f"playlist-{video_id_from_url(collection.source)}"
    return slugify(f"{marker}-{collection.title}", f"{collection.kind}-collection")


def render_collection_context(collection: VideoCollection, item_results: list[dict[str, Any]], focus: str) -> str:
    lines = [
        "# Video Collection Context",
        "",
        "## Source",
        "",
        f"- Kind: {collection.kind}",
        f"- Source: {collection.source}",
        f"- Title: {collection.title}",
        f"- Videos ingested: {len(item_results)}",
        f"- Focus: {focus}",
        "",
        "## Video Packs",
        "",
    ]
    for result in item_results:
        lines.extend([
            f"### {result['index']}. {result['title']}",
            "",
            f"- URL: {result['url']}",
            f"- Context pack: `{result['context_pack']}`",
            f"- First-read file: `{result['context_file']}`",
            "",
        ])

    lines.extend([
        "## Agent Reading Order",
        "",
        "1. Read this collection summary to understand the selected videos.",
        "2. Read each listed `codex_context.md` in order until the task has enough evidence.",
        "3. Inspect captions, frames, or raw manifests only when a timestamped claim needs verification.",
        "",
    ])
    return "\n".join(lines).rstrip() + "\n"


def ingest_collection(
    collection: VideoCollection,
    out_root: Path,
    focus: str,
    model: str,
    no_gemini: bool,
    download_video_enabled: bool,
    sample_interval: int,
    max_height: int,
) -> Path:
    collection_dir = out_root / "_collections" / collection_slug(collection)
    collection_dir.mkdir(parents=True, exist_ok=True)
    item_results: list[dict[str, Any]] = []

    for item in collection.items:
        out_dir = ingest_video(
            item.url,
            out_root=out_root,
            focus=focus,
            model=model,
            no_gemini=no_gemini,
            download_video_enabled=download_video_enabled,
            sample_interval=sample_interval,
            max_height=max_height,
        )
        metadata_path = out_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        pack_title = str(metadata.get("title") or item.title)
        item_results.append({
            "index": item.index,
            "id": item.id,
            "title": pack_title,
            "discovered_title": item.title,
            "url": item.url,
            "context_pack": str(out_dir.relative_to(out_root)),
            "context_file": str((out_dir / "codex_context.md").relative_to(out_root)),
        })

    manifest = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "kind": collection.kind,
        "source": collection.source,
        "title": collection.title,
        "focus": focus,
        "model": None if no_gemini else model,
        "max_videos": len(collection.items),
        "tools": tool_versions(),
        "items": item_results,
    }
    write_json(collection_dir / "collection_manifest.json", manifest)
    (collection_dir / "codex_context.md").write_text(
        render_collection_context(collection, item_results, focus),
        encoding="utf-8",
    )
    return collection_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Public YouTube URL, playlist URL, or search topic/task to ingest")
    parser.add_argument("--out", default=".codex/video-context", help="Output root directory")
    parser.add_argument("--focus", default=DEFAULT_FOCUS, help="Analysis focus for the context pack")
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-flash-latest"))
    parser.add_argument(
        "--source-type",
        choices=["auto", "video", "playlist", "search"],
        default="auto",
        help="How to interpret source. Auto treats playlist URLs as playlists and non-URLs as searches.",
    )
    parser.add_argument("--max-videos", type=int, default=5, help="Maximum videos to ingest for playlists/searches")
    parser.add_argument("--no-gemini", action="store_true", help="Skip Gemini direct video analysis")
    parser.add_argument("--download-video", action="store_true", help="Download video for local frame extraction")
    parser.add_argument("--sample-interval", type=int, default=5, help="Frame sample interval in seconds")
    parser.add_argument("--max-height", type=int, default=720, help="Maximum downloaded video height")
    args = parser.parse_args(argv)

    out_root = Path(args.out)
    collection = resolve_collection(args.source, args.source_type, args.max_videos)
    if collection:
        out_dir = ingest_collection(
            collection,
            out_root=out_root,
            focus=args.focus,
            model=args.model,
            no_gemini=args.no_gemini,
            download_video_enabled=args.download_video,
            sample_interval=args.sample_interval,
            max_height=args.max_height,
        )
        print(out_dir.resolve())
        print(textwrap.dedent(f"""
        Wrote collection context pack:
          {out_dir / "codex_context.md"}

        Next step for agents:
          Read the collection codex_context.md first, then read the listed per-video packs as needed.
        """).strip())
        return 0

    out_dir = ingest_video(
        args.source,
        out_root=out_root,
        focus=args.focus,
        model=args.model,
        no_gemini=args.no_gemini,
        download_video_enabled=args.download_video,
        sample_interval=args.sample_interval,
        max_height=args.max_height,
    )

    print(out_dir.resolve())
    print(textwrap.dedent(f"""
    Wrote context pack:
      {out_dir / "codex_context.md"}

    Next step for agents:
      Read codex_context.md first, then inspect captions or frames only when timestamp evidence matters.
    """).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
