import unittest

from backend.core.usage import read_usage


class UsageTests(unittest.TestCase):
    def test_numbers_are_sane(self):
        usage = read_usage()
        self.assertTrue(0 <= usage["cpu_percent"] <= 100)
        self.assertTrue(0 < usage["ram_used"] <= usage["ram_total"])
        gpu = usage["gpu"]
        if gpu:      # no gpu on this machine is fine
            self.assertTrue(0 <= gpu["memory_used"] <= gpu["memory_total"])


if __name__ == "__main__":
    unittest.main()
