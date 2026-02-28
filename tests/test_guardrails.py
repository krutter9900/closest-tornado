import time
import unittest

from api.app.guardrails import RateLimitConfig, SimpleRateLimiter, TTLCache


class GuardrailTests(unittest.TestCase):
    def test_rate_limiter_blocks_after_limit(self):
        limiter = SimpleRateLimiter(RateLimitConfig(max_requests=2, window_seconds=60))
        self.assertTrue(limiter.allow("ip"))
        self.assertTrue(limiter.allow("ip"))
        self.assertFalse(limiter.allow("ip"))

    def test_ttl_cache_expires(self):
        cache = TTLCache(ttl_seconds=1, max_items=10)
        key = ("a",)
        cache.set(key, {"ok": True})
        self.assertEqual(cache.get(key), {"ok": True})
        time.sleep(1.1)
        self.assertIsNone(cache.get(key))


if __name__ == "__main__":
    unittest.main()
