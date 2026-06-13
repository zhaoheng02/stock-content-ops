import unittest

from content_ops.x_ingest import (
    content_hash,
    parse_publish_time,
    normalize_airtap_payload,
    extract_airtap_json,
)


class ContentHashTests(unittest.TestCase):
    def test_stable_and_handle_insensitive(self):
        a = content_hash("@Foo", "hello world", "123")
        b = content_hash("foo", "hello world", "123")
        self.assertEqual(a, b)

    def test_different_text_changes_hash(self):
        a = content_hash("foo", "hello", "1")
        b = content_hash("foo", "hello!", "1")
        self.assertNotEqual(a, b)


class PublishTimeTests(unittest.TestCase):
    def test_chinese_pm(self):
        iso = parse_publish_time("下午10:52 · 2026年6月12日")
        self.assertEqual(iso, "2026-06-12T22:52:00+08:00")

    def test_chinese_am(self):
        iso = parse_publish_time("上午9:05 2026年6月12日")
        self.assertEqual(iso, "2026-06-12T09:05:00+08:00")

    def test_iso_passthrough(self):
        iso = parse_publish_time("2026-06-12T22:52:00+08:00")
        self.assertEqual(iso, "2026-06-12T22:52:00+08:00")

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_publish_time("just now"))

    def test_relative_time_returns_none(self):
        self.assertIsNone(parse_publish_time("5h"))


class NormalizeTests(unittest.TestCase):
    def test_normalize_and_dedupe(self):
        payload = {
            "collected_at": "2026-06-13T11:20:00+08:00",
            "profiles": [
                {"author_handle": "hanking66", "author_name": "Han", "avatar_url": "https://pbs.twimg.com/profile_images/a.jpg", "bio": "trader"}
            ],
            "posts": [
                {"id": "1", "author_handle": "hanking66", "text": "post one", "published_at": "下午10:52 · 2026年6月12日", "image_urls": ["https://pbs.twimg.com/media/x.jpg"], "metrics": {"likes": 10}},
                {"id": "1", "author_handle": "hanking66", "text": "post one", "published_at": "下午10:52 · 2026年6月12日"},
            ],
        }
        records = normalize_airtap_payload(payload, source_id="x", run_id="run1")
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["author_avatar_url"], "https://pbs.twimg.com/profile_images/a.jpg")
        self.assertEqual(r["url"], "https://x.com/hanking66/status/1")
        self.assertEqual(r["published_at"], "2026-06-12T22:52:00+08:00")
        self.assertEqual(r["run_id"], "run1")
        self.assertEqual(r["image_urls"], ["https://pbs.twimg.com/media/x.jpg"])

    def test_extract_json_from_fenced(self):
        text = "Here is the result:\n```json\n{\"posts\": [], \"profiles\": []}\n```\nDone."
        data = extract_airtap_json(text)
        self.assertEqual(data, {"posts": [], "profiles": []})

    def test_skips_replies_and_relative_times(self):
        payload = {
            "posts": [
                {"id": "1", "author_handle": "hanking66", "text": "@someone reply", "published_at": "2026-06-12T22:52:00+08:00"},
                {"id": "2", "author_handle": "hanking66", "text": "relative only", "published_at": "5h"},
                {"id": "3", "author_handle": "hanking66", "text": "original", "published_at": "2026-06-12T23:52:00+08:00"},
            ],
        }

        records = normalize_airtap_payload(payload, source_id="x", run_id="run1")

        self.assertEqual([r["post_id"] for r in records], ["3"])

    def test_uses_stored_profile_without_collection_profiles(self):
        payload = {
            "posts": [
                {"id": "1", "author_handle": "HanKing66", "author_name": "", "text": "original", "published_at": "2026-06-12T22:52:00+08:00"},
            ],
        }

        records = normalize_airtap_payload(
            payload,
            source_id="x",
            run_id="run1",
            profiles_by_handle={"hanking66": {"author_name": "Han", "avatar_url": "https://pbs.twimg.com/profile_images/a.jpg"}},
        )

        self.assertEqual(records[0]["author_name"], "Han")
        self.assertEqual(records[0]["author_avatar_url"], "https://pbs.twimg.com/profile_images/a.jpg")


if __name__ == "__main__":
    unittest.main()
