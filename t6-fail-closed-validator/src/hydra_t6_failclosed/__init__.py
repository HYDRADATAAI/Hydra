"""Dormant HYDRA T6 fail-closed validator.

Importing this package registers nothing and performs no I/O.
"""

from .authority import HMACSHA256Verifier, sign_hmac_sha256
from .native_binding_admission import (
    NativeBindingAdmissionResult,
    sign_native_binding_admission,
    validate_native_binding_admission,
)
from .service import FailClosedValidator

__all__ = [
    "FailClosedValidator",
    "HMACSHA256Verifier",
    "NativeBindingAdmissionResult",
    "sign_hmac_sha256",
    "sign_native_binding_admission",
    "validate_native_binding_admission",
]
