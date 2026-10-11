from __future__ import annotations

import unittest

from hydra_constraint.polling import PollRunner, PollSpec


class PollPreflightTests(unittest.TestCase):
    class Cursors:
        def __init__(self):
            self.reads = 0

        def adapter(self, _source):
            self.reads += 1
            return {"cursor": None}

    class Transport:
        def __init__(self):
            self.calls = 0

        def fetch(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("invalid SEC spec must fail before transport")

    def make_spec(self, *, max_rps=1.0, user_agent="HYDRA test contact@example.invalid"):
        return PollSpec(
            name="sec",
            adapter="sec_edgar",
            source_class="sec_edgar",
            url="https://www.sec.gov/data",
            parser="sec_json",
            cadence_minutes=1,
            stale_after_minutes=5,
            max_rps=max_rps,
            headers={"User-Agent": user_agent},
        )

    def test_sec_fair_access_ceiling_is_enforced_before_cursor_or_transport(self):
        cursors = self.Cursors()
        transport = self.Transport()
        runner = PollRunner(None, cursors, None, transport)

        with self.assertRaisesRegex(ValueError, "SEC max_rps exceeds fair-access ceiling"):
            runner.poll(self.make_spec(max_rps=20))

        self.assertEqual(cursors.reads, 0)
        self.assertEqual(transport.calls, 0)

    def test_sec_user_agent_preflight_is_enforced_before_cursor_or_transport(self):
        cursors = self.Cursors()
        transport = self.Transport()
        runner = PollRunner(None, cursors, None, transport)

        with self.assertRaisesRegex(ValueError, "SEC live polling requires real User-Agent/contact"):
            runner.poll(self.make_spec(user_agent="REPLACE_ME"))

        self.assertEqual(cursors.reads, 0)
        self.assertEqual(transport.calls, 0)


if __name__ == "__main__":
    unittest.main()
