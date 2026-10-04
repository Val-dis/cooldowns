import json
import os
import tempfile
import unittest

from cooldowns import CooldownManager, format_remaining


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class CooldownTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cd = CooldownManager(clock=self.clock)

    def test_start_and_expire(self):
        ok, _ = self.cd.check_and_start(1, "work", 3600)
        self.assertTrue(ok)
        ok, left = self.cd.check_and_start(1, "work", 3600)
        self.assertFalse(ok)
        self.assertEqual(left, 3600)
        self.clock.now += 3601
        self.assertTrue(self.cd.is_ready(1, "work"))

    def test_users_and_commands_are_independent(self):
        self.cd.start(1, "work", 100)
        self.assertTrue(self.cd.is_ready(2, "work"))
        self.assertTrue(self.cd.is_ready(1, "mine"))

    def test_reset_specific_and_all(self):
        for cmd in ("work", "beg", "daily"):
            self.cd.start(1, cmd, 1000)
        self.cd.reset(1, "work", "beg")  # like a coffee item
        self.assertTrue(self.cd.is_ready(1, "work"))
        self.assertFalse(self.cd.is_ready(1, "daily"))
        self.cd.reset(1)
        self.assertTrue(self.cd.is_ready(1, "daily"))

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cd.json")
            CooldownManager(path, clock=self.clock).start(7, "daily", 86400)
            again = CooldownManager(path, clock=self.clock)
            self.assertEqual(again.remaining(7, "daily"), 86400)

    def test_corrupt_file_is_set_aside(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cd.json")
            with open(path, "w") as f:
                f.write("{not json")
            cd = CooldownManager(path, clock=self.clock)
            self.assertTrue(cd.is_ready(1, "work"))
            self.assertTrue(os.path.exists(path + ".corrupt"))

    def test_expired_entries_are_pruned_on_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cd.json")
            cd = CooldownManager(path, clock=self.clock)
            cd.start(1, "beg", 300)
            self.clock.now += 1000
            cd.start(2, "work", 3600)
            with open(path) as f:
                saved = json.load(f)
            self.assertNotIn("1", saved)
            self.assertIn("2", saved)

    def test_format_remaining(self):
        self.assertEqual(format_remaining(3900), "1h 5m")
        self.assertEqual(format_remaining(252), "4m 12s")
        self.assertEqual(format_remaining(30), "30s")
        self.assertEqual(format_remaining(0), "0s")


if __name__ == "__main__":
    unittest.main()
