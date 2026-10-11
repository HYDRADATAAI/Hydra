from __future__ import annotations

import io
import unittest
import urllib.error
from unittest.mock import patch

from hydra_constraint.polling import UrllibTransport


class HttpErrorResponseCloseTests(unittest.TestCase):
    def test_http_error_response_is_closed_after_body_is_read(self):
        error = urllib.error.HTTPError(
            "https://example.test/feed",
            503,
            "unavailable",
            {"Retry-After": "5"},
            io.BytesIO(b"retry later"),
        )

        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.side_effect = error
            response = UrllibTransport().fetch("https://example.test/feed")

        self.assertEqual(response.status, 503)
        self.assertEqual(response.body, b"retry later")
        self.assertEqual(response.headers["retry-after"], "5")
        self.assertTrue(error.fp.closed)


if __name__ == "__main__":
    unittest.main()
