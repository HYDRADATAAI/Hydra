"""Dormant HYDRA T6 fail-closed validator.

Importing this package registers nothing and performs no I/O.
"""

from .authority import HMACSHA256Verifier, sign_hmac_sha256
from .service import FailClosedValidator

__all__ = ["FailClosedValidator", "HMACSHA256Verifier", "sign_hmac_sha256"]
