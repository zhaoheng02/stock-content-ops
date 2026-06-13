import unittest

from content_ops.x_api import XApiPostProvider


class FakeTransport:
    def __init__(self):
        self.urls = []

    def get_json(self, url, bearer_token):
        self.urls.append(url)
        if "/users/by/username/" in url:
            username = url.split("/users/by/username/")[1].split("?")[0]
            return {"data": {"id": f"id-{username}", "username": username}}
        return {
            "data": [
                {
                    "id": "tweet-1",
                    "text": "AI startup shared exact pricing onboarding ROI metrics.",
                    "public_metrics": {"like_count": 30, "retweet_count": 4, "reply_count": 2},
                }
            ]
        }


class XApiProviderTest(unittest.TestCase):
    def test_fetch_posts_maps_x_public_metrics(self):
        transport = FakeTransport()
        provider = XApiPostProvider(
            handles=["builder_a"],
            bearer_token="token",
            transport=transport,
            max_results_per_account=5,
        )

        posts = list(provider.fetch_posts())

        self.assertEqual(posts[0].id, "tweet-1")
        self.assertEqual(posts[0].account, "builder_a")
        self.assertEqual(posts[0].metrics, {"likes": 30, "reposts": 4, "replies": 2})
        self.assertIn("/users/by/username/builder_a", transport.urls[0])


if __name__ == "__main__":
    unittest.main()
