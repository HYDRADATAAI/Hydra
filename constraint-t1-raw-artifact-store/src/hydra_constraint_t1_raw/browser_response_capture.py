"""Extract one exact registered HTTP response body from a private sanitized HAR.

This module performs no network access. It exists for reviewed browser-session
captures where a public site permits normal browser access but blocks direct
non-browser byte capture. It consumes only a HAR exported from the browser's
Network panel and writes the received response body to a private path.

The HAR and extracted body must remain outside the public repository.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any


class BrowserResponseCaptureError(ValueError):
    pass


SENSITIVE_HEADER_NAMES = {"cookie", "set-cookie", "authorization", "proxy-authorization"}
CLOUDFLARE_BLOCK_MARKERS = (
    b"attention required! | cloudflare",
    b"just a moment...",
    b"enable javascript and cookies to continue",
    b"cf-chl-",
    b"cloudflare ray id",
)


def _outside_repo(path: Path, public_repo_root: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    repo = public_repo_root.expanduser().resolve()
    if resolved == repo or resolved.is_relative_to(repo):
        raise BrowserResponseCaptureError(f"{label} must remain outside the public repository")
    return resolved


def _headers(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for container in ("request", "response"):
        obj = entry.get(container)
        if isinstance(obj, dict):
            value = obj.get("headers")
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
    return rows


def _reject_sensitive_headers(entry: dict[str, Any]) -> None:
    for header in _headers(entry):
        name = header.get("name")
        if isinstance(name, str) and name.lower() in SENSITIVE_HEADER_NAMES:
            raise BrowserResponseCaptureError(
                f"HAR contains sensitive header {name!r}; export a sanitized HAR"
            )


def _decode_content(content: dict[str, Any]) -> bytes:
    text = content.get("text")
    if not isinstance(text, str) or not text:
        raise BrowserResponseCaptureError("HAR response body content is missing")

    encoding = content.get("encoding")
    if encoding is None:
        return text.encode("utf-8")
    if encoding == "base64":
        try:
            return base64.b64decode(text, validate=True)
        except Exception as exc:
            raise BrowserResponseCaptureError("HAR base64 response body is invalid") from exc
    raise BrowserResponseCaptureError(f"unsupported HAR response encoding: {encoding!r}")


def extract_exact_response(
    *,
    har: dict[str, Any],
    exact_url: str,
    expected_mime_prefix: str,
    expected_text: str | None = None,
) -> tuple[bytes, dict[str, Any]]:
    log = har.get("log")
    entries = log.get("entries") if isinstance(log, dict) else None
    if not isinstance(entries, list):
        raise BrowserResponseCaptureError("HAR log.entries is missing")

    matches: list[dict[str, Any]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        request = raw.get("request")
        if isinstance(request, dict) and request.get("url") == exact_url:
            matches.append(raw)

    if not matches:
        raise BrowserResponseCaptureError("exact registered URL not present in HAR")

    rejection_reasons: list[str] = []
    for entry in reversed(matches):
        try:
            _reject_sensitive_headers(entry)

            response = entry.get("response")
            if not isinstance(response, dict):
                raise BrowserResponseCaptureError("HAR entry response object missing")
            status = response.get("status")
            if status != 200:
                raise BrowserResponseCaptureError(f"response status is {status!r}, expected 200")

            content = response.get("content")
            if not isinstance(content, dict):
                raise BrowserResponseCaptureError("HAR response content object missing")
            mime = content.get("mimeType")
            if not isinstance(mime, str) or not mime.lower().startswith(expected_mime_prefix.lower()):
                raise BrowserResponseCaptureError(
                    f"response MIME type {mime!r} does not match {expected_mime_prefix!r}"
                )

            body = _decode_content(content)
            if not body:
                raise BrowserResponseCaptureError("HAR response body is empty")
            lower = body.lower()
            for marker in CLOUDFLARE_BLOCK_MARKERS:
                if marker in lower:
                    raise BrowserResponseCaptureError(
                        f"response body contains Cloudflare challenge/block marker {marker!r}"
                    )
            if expected_text is not None and expected_text.encode("utf-8").lower() not in lower:
                raise BrowserResponseCaptureError(
                    f"response body is missing expected source marker {expected_text!r}"
                )

            metadata = {
                "exact_url": exact_url,
                "status": status,
                "mime_type": mime,
                "started_date_time": entry.get("startedDateTime"),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "byte_length": len(body),
                "capture_method": "SANITIZED_BROWSER_HAR_EXACT_RESPONSE_BODY",
                "rendered_dom_used": False,
                "linked_file_substituted": False,
                "cloudflare_bypass_attempted": False,
            }
            return body, metadata
        except BrowserResponseCaptureError as exc:
            rejection_reasons.append(str(exc))

    raise BrowserResponseCaptureError(
        "no acceptable exact-URL browser response found; " + " | ".join(rejection_reasons)
    )


def capture_from_har(
    *,
    har_path: str | Path,
    output_path: str | Path,
    metadata_output_path: str | Path,
    exact_url: str,
    expected_mime_prefix: str,
    expected_text: str | None,
    public_repo_root: str | Path,
) -> dict[str, Any]:
    repo = Path(public_repo_root).expanduser().resolve()
    har_file = _outside_repo(Path(har_path), repo, "HAR input")
    output = _outside_repo(Path(output_path), repo, "response-body output")
    metadata_output = _outside_repo(Path(metadata_output_path), repo, "capture metadata output")

    try:
        har = json.loads(har_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BrowserResponseCaptureError("unable to parse HAR JSON") from exc
    if not isinstance(har, dict):
        raise BrowserResponseCaptureError("HAR top-level object required")

    body, metadata = extract_exact_response(
        har=har,
        exact_url=exact_url,
        expected_mime_prefix=expected_mime_prefix,
        expected_text=expected_text,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(body)
    metadata_output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--har", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata-output", required=True)
    parser.add_argument("--exact-url", required=True)
    parser.add_argument("--expected-mime-prefix", default="text/html")
    parser.add_argument("--expected-text")
    parser.add_argument("--public-repo-root", required=True)
    args = parser.parse_args()

    try:
        metadata = capture_from_har(
            har_path=args.har,
            output_path=args.output,
            metadata_output_path=args.metadata_output,
            exact_url=args.exact_url,
            expected_mime_prefix=args.expected_mime_prefix,
            expected_text=args.expected_text,
            public_repo_root=args.public_repo_root,
        )
    except BrowserResponseCaptureError as exc:
        print("HYDRA_BROWSER_RESPONSE_CAPTURE=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("HYDRA_BROWSER_RESPONSE_CAPTURE=PASS")
    print(f"BODY_SHA256={metadata['body_sha256']}")
    print(f"BYTE_LENGTH={metadata['byte_length']}")
    print("RENDERED_DOM_USED=NO")
    print("LINKED_FILE_SUBSTITUTED=NO")
    print("CLOUDFLARE_BYPASS_ATTEMPTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
