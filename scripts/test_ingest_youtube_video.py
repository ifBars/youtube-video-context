import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ingest_youtube_video as ingest


class DiscoveryTests(unittest.TestCase):
    def test_playlist_url_discovers_entries_with_watch_urls(self):
        payload = {
            "id": "playlist-id",
            "title": "Reference Playlist",
            "webpage_url": "https://www.youtube.com/playlist?list=playlist-id",
            "entries": [
                {"id": "aaa111", "url": "https://www.youtube.com/watch?v=aaa111", "title": "First"},
                {"id": "bbb222", "url": "bbb222", "title": "Second"},
            ],
        }

        with patch.object(ingest, "yt_dlp_command", return_value=["yt-dlp"]), patch.object(
            ingest,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
        ):
            collection = ingest.resolve_collection(
                "https://www.youtube.com/playlist?list=playlist-id",
                source_type="auto",
                max_videos=10,
            )

        self.assertEqual(collection.kind, "playlist")
        self.assertEqual(collection.title, "Reference Playlist")
        self.assertEqual(
            [item.url for item in collection.items],
            ["https://www.youtube.com/watch?v=aaa111", "https://www.youtube.com/watch?v=bbb222"],
        )

    def test_search_topic_discovers_limited_results(self):
        payload = {
            "title": "ytsearch3:cozy factory automation UI references",
            "entries": [
                {"id": "aaa111", "title": "First", "webpage_url": "https://youtu.be/aaa111"},
                {"id": "bbb222", "title": "Second", "webpage_url": "https://youtu.be/bbb222"},
                {"id": "ccc333", "title": "Third", "webpage_url": "https://youtu.be/ccc333"},
            ],
        }

        calls = []

        def fake_run(cmd, cwd=None, capture=True):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

        with patch.object(ingest, "yt_dlp_command", return_value=["yt-dlp"]), patch.object(ingest, "run", fake_run):
            collection = ingest.resolve_collection(
                "cozy factory automation UI references",
                source_type="auto",
                max_videos=2,
            )

        self.assertEqual(collection.kind, "search")
        self.assertEqual(collection.title, "cozy factory automation UI references")
        self.assertEqual(len(collection.items), 2)
        self.assertIn("ytsearch2:cozy factory automation UI references", calls[0])

    def test_watch_url_with_list_query_is_playlist_in_auto_mode(self):
        payload = {
            "id": "playlist-id",
            "title": "Watch Page Playlist",
            "entries": [{"id": "aaa111", "title": "First"}],
        }

        with patch.object(ingest, "yt_dlp_command", return_value=["yt-dlp"]), patch.object(
            ingest,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
        ):
            collection = ingest.resolve_collection(
                "https://www.youtube.com/watch?v=start123&list=playlist-id",
                source_type="auto",
                max_videos=5,
            )

        self.assertIsNotNone(collection)
        self.assertEqual(collection.kind, "playlist")


class CollectionIngestionTests(unittest.TestCase):
    def test_collection_ingestion_writes_manifest_and_reuses_video_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_root = Path(tmp)
            collection = ingest.VideoCollection(
                kind="search",
                source="third person shop UI references",
                title="third person shop UI references",
                items=[
                    ingest.VideoItem(
                        url="https://www.youtube.com/watch?v=aaa111",
                        id="aaa111",
                        title="First",
                        index=1,
                    ),
                    ingest.VideoItem(
                        url="https://www.youtube.com/watch?v=bbb222",
                        id="bbb222",
                        title="Second",
                        index=2,
                    ),
                ],
            )

            def fake_metadata(url):
                video_id = url.rsplit("=", 1)[-1]
                return {
                    "id": video_id,
                    "title": f"Video {video_id}",
                    "webpage_url": url,
                    "duration": 30,
                }

            with patch.object(ingest, "load_metadata", side_effect=fake_metadata), patch.object(
                ingest,
                "download_captions",
                return_value=[],
            ), patch.object(ingest, "call_gemini", return_value="## Evidence Index\n\n- 0:01 visible UI"), patch.object(
                ingest,
                "yt_dlp_command",
                return_value=None,
            ), patch.object(
                ingest,
                "optional_tool",
                return_value=None,
            ):
                collection_dir = ingest.ingest_collection(
                    collection,
                    out_root=out_root,
                    focus="extract UI patterns",
                    model="gemini-flash-latest",
                    no_gemini=False,
                    download_video_enabled=False,
                    sample_interval=5,
                    max_height=720,
                )

            manifest = json.loads((collection_dir / "collection_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["kind"], "search")
            self.assertEqual(len(manifest["items"]), 2)
            self.assertTrue((out_root / "aaa111" / "codex_context.md").exists())
            self.assertTrue((out_root / "bbb222" / "codex_context.md").exists())
            self.assertIn("Video aaa111", (collection_dir / "codex_context.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
