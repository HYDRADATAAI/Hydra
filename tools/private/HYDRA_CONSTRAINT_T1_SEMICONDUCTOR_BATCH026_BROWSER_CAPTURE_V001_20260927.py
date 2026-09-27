from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin, urlparse

QUEUE_RELATIVE_PATH = Path(
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)
LOCATOR_OVERLAY_RELATIVE_PATH = Path(
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_V001_20260927.json"
)
EXPECTED_SLICE_ID = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
EXPECTED_SOURCE_COUNT = 41
OPERATOR_BLOCKED_SOURCE_IDS = (
    "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
    "SRC-SEMI-B021-MICRON-Q1FY26-REMARKS-2025-12-17",
    "SRC-SEMI-B021-MICRON-Q3FY24-REMARKS-2024-06-26",
    "SRC-SEMI-B021-MICRON-Q3FY25-REMARKS-2025-06-25",
    "SRC-SEMI-B021-MICRON-Q4FY25-REMARKS-2025-09-23",
    "SRC-SEMI-B022-GLOBENEWSWIRE-MICRON-HBM3E-2024-02-26",
    "SRC-SEMI-B022-MICRON-HBM3E-VOLUME-2024-02-26",
    "SRC-SEMI-B023-MICRON-Q1FY24-REMARKS-2023-12-20",
    "SRC-SEMI-B023-MICRON-Q2FY26-MARKET-OUTLOOK-2026-03-18",
)
EXPECTED_BLOCKED_SOURCE_COUNT = 9
EXPECTED_ELIGIBLE_SOURCE_COUNT = EXPECTED_SOURCE_COUNT - EXPECTED_BLOCKED_SOURCE_COUNT
BLOCKED_SOURCE_STATUS = "BLOCKED_BY_OPERATOR"
SIDECAR_SCHEMA = "hydra-semiconductor-private-capture-sidecar/v1"
JOURNAL_SCHEMA = "hydra-constraint-semiconductor-batch026-browser-capture-journal/v1"

# Explicit authorization is limited to these four queued TSMC PDFs whose raw
# request-context acquisition returned HTTP 403. Keep the complete identity
# tuple so an ID reused with a different locator or source version cannot
# inherit the fallback.
B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS = {
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17": (
        "SV-SEMI-B026-006",
        "https://investor.tsmc.com/schinese/encrypt/files/encrypt_file/reports/2025-04/"
        "7630274eecc1197a4e3ea6a415f44a47204fe10a/TSMC%201Q25%20Transcript.pdf",
    ),
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20": (
        "SV-SEMI-B026-022",
        "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2023-07/"
        "7ec677062ca442e429b632ccd6d4f31ad53b1ce7/TSMC%202Q23%20Transcript.pdf",
    ),
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK": (
        "SV-SEMI-B026-036",
        "https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20Annual%20Report.E.pdf",
    ),
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16": (
        "SV-SEMI-B026-037",
        "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-07/"
        "57b65edbfe6e480e74abe202be983ecbde79e934/TSMC%202Q26%20Transcript.pdf",
    ),
}

HTML_BLOCK_MARKERS = (
    b"attention required! | cloudflare",
    b"just a moment...",
    b"enable javascript and cookies to continue",
    b"checking your browser",
    b"verify you are human",
    b"cf-chl-",
    b"cloudflare ray id",
    b"request blocked",
    b"access denied",
)
MAX_PDF_HTTP_REDIRECTS = 10


class CaptureError(RuntimeError):
    pass


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CaptureError(f"unable to read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CaptureError(f"top-level JSON object required: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assert_outside_repo(path: Path, repo_root: Path, label: str) -> Path:
    resolved_path = path.expanduser().resolve()
    resolved_repo = repo_root.expanduser().resolve()
    try:
        resolved_path.relative_to(resolved_repo)
    except ValueError:
        return resolved_path
    raise CaptureError(f"{label} must remain outside the public repository: {resolved_path}")


def normalize_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def load_locator_remediations(doc: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if doc.get("slice_id") != EXPECTED_SLICE_ID:
        raise CaptureError("locator remediation slice_id mismatch")
    rows = doc.get("remediations")
    if not isinstance(rows, list):
        raise CaptureError("locator remediation rows missing")
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CaptureError("locator remediation row must be an object")
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise CaptureError("locator remediation source_id missing")
        if source_id in mapping:
            raise CaptureError(f"duplicate locator remediation: {source_id}")
        mapping[source_id] = dict(row)
    return mapping


def validate_effective_locator(
    *,
    item: Mapping[str, Any],
    locator: str,
    remediation: Mapping[str, Any] | None,
) -> None:
    if remediation is None:
        if locator != item.get("source_locator"):
            raise CaptureError(f"{item['source_id']}: capture locator differs from registered locator")
        return

    parsed = urlparse(locator)
    if parsed.scheme.lower() != "https":
        raise CaptureError(f"{item['source_id']}: remediated capture locator must be HTTPS")
    if normalize_host(locator) != "s25.q4cdn.com":
        raise CaptureError(f"{item['source_id']}: remediated capture locator host is not Micron Q4CDN")
    prefix = remediation.get("required_path_prefix")
    if not isinstance(prefix, str) or not parsed.path.startswith(prefix):
        raise CaptureError(f"{item['source_id']}: remediated capture locator quarter path mismatch")


def _matches_document_kind(*, href: str, text: str, kind: str) -> bool:
    combined = (href + " " + text).lower().replace("_", " ").replace("-", " ")
    if kind == "prepared_remarks":
        return "prepared" in combined and "remark" in combined
    if kind == "presentation":
        return (
            "presentation" in combined
            or "earnings deck" in combined
            or "earnings slides" in combined
            or ("earning" in combined and "slide" in combined)
        ) and "prepared" not in combined
    raise CaptureError(f"unsupported locator-remediation document kind: {kind}")


def resolve_remediated_locator(
    *,
    context: Any,
    item: Mapping[str, Any],
    remediation: Mapping[str, Any],
    navigation_timeout_seconds: int,
) -> str:
    authority_page = "https://investors.micron.com/financials/quarterly-results/default.aspx"
    page = context.new_page()
    try:
        page.goto(
            authority_page,
            wait_until="domcontentloaded",
            timeout=max(1, navigation_timeout_seconds) * 1000,
        )
        page.wait_for_timeout(1500)
        links = page.locator("a").evaluate_all(
            """els => els.map(a => ({
                href: a.href || "",
                text: (a.innerText || a.textContent || "").trim()
            }))"""
        )
    finally:
        try:
            page.close()
        except Exception:
            pass

    candidates: list[str] = []
    for raw in links:
        if not isinstance(raw, dict):
            continue
        href = str(raw.get("href") or "")
        text = str(raw.get("text") or "")
        if not href:
            continue
        try:
            validate_effective_locator(item=item, locator=href, remediation=remediation)
        except CaptureError:
            continue
        if _matches_document_kind(
            href=href,
            text=text,
            kind=str(remediation.get("document_kind")),
        ):
            candidates.append(href)

    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        raise CaptureError(
            f"{item['source_id']}: official Micron quarterly-results resolver found "
            f"{len(candidates)} matching capture locators: {candidates!r}"
        )
    resolved = candidates[0]
    validate_effective_locator(item=item, locator=resolved, remediation=remediation)
    return resolved


def redirect_chain(response: Any) -> tuple[str, ...]:
    request = response.request
    chain: list[str] = []
    while request is not None:
        chain.append(str(request.url))
        request = request.redirected_from
    chain.reverse()
    return tuple(chain)


def response_header_value(response: Any, name: str) -> str | None:
    getter = getattr(response, "header_value", None)
    if callable(getter):
        try:
            value = getter(name)
        except Exception:
            value = None
        if value is not None:
            return str(value)

    headers = getattr(response, "headers", None)
    if isinstance(headers, Mapping):
        requested_name = name.lower()
        for key, value in headers.items():
            if str(key).lower() == requested_name:
                return str(value)
    return None


def validate_redirects(*, exact_locator: str, response_url: str, chain: Sequence[str], policy: str) -> None:
    if not chain or chain[0] != exact_locator:
        raise CaptureError(f"redirect chain does not start at exact source locator: {list(chain)!r}")
    if policy == "exact":
        if response_url != exact_locator or list(chain) != [exact_locator]:
            raise CaptureError(
                f"exact redirect policy rejected response URL/chain: final={response_url!r} chain={list(chain)!r}"
            )
        return
    if policy != "same-origin":
        raise CaptureError(f"unsupported redirect policy: {policy}")

    expected_host = normalize_host(exact_locator)
    for url in chain:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https":
            raise CaptureError(f"same-origin redirect policy rejected non-HTTPS URL: {url!r}")
        if normalize_host(url) != expected_host:
            raise CaptureError(
                f"same-origin redirect policy rejected host change: {url!r} expected_host={expected_host!r}"
            )


def dispose_api_response(response: Any) -> None:
    try:
        response.dispose()
    except Exception:
        pass


def fetch_pdf_response(
    *,
    context: Any,
    exact_locator: str,
    policy: str,
    timeout_milliseconds: int,
) -> tuple[Any, tuple[str, ...]]:
    request_context = getattr(context, "request", None)
    if request_context is None or not callable(getattr(request_context, "get", None)):
        raise CaptureError("browser context does not expose a Playwright API request context")

    timeout_ms = max(1, int(timeout_milliseconds))
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    chain = [exact_locator]
    current_url = exact_locator
    redirects_followed = 0
    redirect_statuses = {301, 302, 303, 307, 308}

    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise CaptureError(f"PDF raw HTTP request exceeded its {timeout_ms} ms total timeout")
        remaining_ms = max(1, int(remaining_seconds * 1000))
        response = request_context.get(
            current_url,
            timeout=remaining_ms,
            max_redirects=0,
            max_retries=0,
            fail_on_status_code=False,
        )
        if int(response.status) not in redirect_statuses:
            return response, tuple(chain)

        location = response_header_value(response, "location")
        if not location:
            dispose_api_response(response)
            raise CaptureError(f"PDF raw HTTP redirect from {current_url!r} omitted Location")
        if redirects_followed >= MAX_PDF_HTTP_REDIRECTS:
            dispose_api_response(response)
            raise CaptureError(f"PDF raw HTTP redirect limit exceeded ({MAX_PDF_HTTP_REDIRECTS})")

        next_url = urljoin(current_url, location)
        proposed_chain = (*chain, next_url)
        try:
            validate_redirects(
                exact_locator=exact_locator,
                response_url=next_url,
                chain=proposed_chain,
                policy=policy,
            )
        except Exception:
            dispose_api_response(response)
            raise

        dispose_api_response(response)
        chain.append(next_url)
        current_url = next_url
        redirects_followed += 1


def validate_body(
    *,
    item: Mapping[str, Any],
    response: Any,
    body: bytes,
    policy: str,
    effective_locator: str,
    redirect_chain_override: Sequence[str] | None = None,
) -> tuple[str, tuple[str, ...], str]:
    source_id = str(item["source_id"])
    locator = effective_locator
    expected = str(item["content_type_hint"])
    chain = (
        tuple(redirect_chain_override)
        if redirect_chain_override is not None
        else redirect_chain(response)
    )
    final_url = str(response.url)
    validate_redirects(exact_locator=locator, response_url=final_url, chain=chain, policy=policy)

    if int(response.status) != 200:
        raise CaptureError(f"{source_id}: HTTP status {response.status} is not acceptable")
    if not body:
        raise CaptureError(f"{source_id}: empty main-document body")

    observed = (response_header_value(response, "content-type") or "").strip().lower()
    if expected == "application/pdf":
        if not observed.startswith("application/pdf"):
            raise CaptureError(f"{source_id}: expected PDF content type, observed {observed!r}")
        if len(body) < 1024 or not body.startswith(b"%PDF-"):
            raise CaptureError(f"{source_id}: invalid or suspiciously small PDF body ({len(body)} bytes)")
        normalized = "application/pdf"
    elif expected == "text/html":
        html_like = observed.startswith("text/html") or observed.startswith("application/xhtml+xml")
        if not html_like:
            raise CaptureError(f"{source_id}: expected HTML content type, observed {observed!r}")
        if len(body) < 512:
            raise CaptureError(f"{source_id}: suspiciously small HTML body ({len(body)} bytes)")
        lower = body[:2_000_000].lower()
        if b"<html" not in lower and b"<!doctype html" not in lower:
            raise CaptureError(f"{source_id}: HTML document marker missing")
        for marker in HTML_BLOCK_MARKERS:
            if marker in lower:
                raise CaptureError(
                    f"{source_id}: challenge/error/interstitial marker present: "
                    f"{marker.decode('ascii', errors='replace')}"
                )
        normalized = "text/html"
    else:
        raise CaptureError(f"{source_id}: unsupported queue content_type_hint {expected!r}")

    return normalized, chain, final_url


def validate_queue(queue_doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    if queue_doc.get("slice_id") != EXPECTED_SLICE_ID:
        raise CaptureError(f"unexpected queue slice_id: {queue_doc.get('slice_id')!r}")
    queue = queue_doc.get("queue")
    if not isinstance(queue, list) or len(queue) != EXPECTED_SOURCE_COUNT:
        raise CaptureError(f"queue must contain exactly {EXPECTED_SOURCE_COUNT} capture intents")

    source_ids: set[str] = set()
    versions: set[str] = set()
    filenames: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(queue):
        if not isinstance(raw, Mapping):
            raise CaptureError(f"queue[{index}] must be an object")
        source_id = raw.get("source_id")
        source_version_id = raw.get("source_version_id")
        locator = raw.get("source_locator")
        filename = raw.get("inbox_filename")
        if not isinstance(source_id, str) or not source_id:
            raise CaptureError(f"queue[{index}].source_id missing")
        if source_id in source_ids:
            raise CaptureError(f"duplicate source_id: {source_id}")
        if not isinstance(source_version_id, str) or not source_version_id:
            raise CaptureError(f"{source_id}: source_version_id missing")
        if source_version_id in versions:
            raise CaptureError(f"duplicate source_version_id: {source_version_id}")
        if not isinstance(locator, str) or not locator.startswith("https://"):
            raise CaptureError(f"{source_id}: exact HTTPS source_locator required")
        if not isinstance(filename, str) or not filename:
            raise CaptureError(f"{source_id}: inbox_filename missing")
        if Path(filename).name != filename:
            raise CaptureError(f"{source_id}: inbox_filename must not contain directories")
        if filename in filenames:
            raise CaptureError(f"duplicate inbox_filename: {filename}")
        if raw.get("historical_backdating_authorized") is not False:
            raise CaptureError(f"{source_id}: historical backdating must remain unauthorized")
        if raw.get("processing_disposition") != "ELIGIBLE":
            raise CaptureError(f"{source_id}: queue disposition must remain ELIGIBLE")
        if raw.get("content_type_hint") not in {"application/pdf", "text/html"}:
            raise CaptureError(f"{source_id}: unsupported content type hint")

        source_ids.add(source_id)
        versions.add(source_version_id)
        filenames.add(filename)
        normalized.append(dict(raw))
    return normalized


def partition_capture_queue(
    queue: Sequence[Mapping[str, Any]],
    blocked_source_ids: Sequence[str] = OPERATOR_BLOCKED_SOURCE_IDS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(blocked_source_ids, (list, tuple)):
        raise CaptureError("blocked-source set must be a list or tuple of source IDs")
    blocked_ids = list(blocked_source_ids)
    if any(not isinstance(source_id, str) or not source_id or source_id.strip() != source_id for source_id in blocked_ids):
        raise CaptureError("blocked-source set contains a malformed source ID")
    if len(set(blocked_ids)) != len(blocked_ids):
        raise CaptureError("duplicate blocked source ID")

    if len(OPERATOR_BLOCKED_SOURCE_IDS) != EXPECTED_BLOCKED_SOURCE_COUNT:
        raise CaptureError("configured operator blocked-source count is invalid")
    if len(set(OPERATOR_BLOCKED_SOURCE_IDS)) != len(OPERATOR_BLOCKED_SOURCE_IDS):
        raise CaptureError("configured operator blocked-source set contains duplicates")
    if len(queue) != EXPECTED_SOURCE_COUNT:
        raise CaptureError(f"canonical queue must retain all {EXPECTED_SOURCE_COUNT} rows before exclusion")

    queue_ids = {str(item["source_id"]) for item in queue}
    requested_ids = set(blocked_ids)
    unknown_ids = sorted(requested_ids - queue_ids)
    if unknown_ids:
        raise CaptureError(f"unknown blocked source ID(s): {unknown_ids}")

    required_ids = set(OPERATOR_BLOCKED_SOURCE_IDS)
    missing_ids = sorted(required_ids - requested_ids)
    unexpected_ids = sorted(requested_ids - required_ids)
    if missing_ids or unexpected_ids:
        raise CaptureError(
            "required blocked-source set mismatch: "
            f"missing={missing_ids} unexpected={unexpected_ids}"
        )

    blocked_set = required_ids
    blocked = [dict(item) for item in queue if item["source_id"] in blocked_set]
    eligible = [dict(item) for item in queue if item["source_id"] not in blocked_set]
    if len(blocked) != EXPECTED_BLOCKED_SOURCE_COUNT:
        raise CaptureError("canonical queue does not contain every required blocked source")
    if len(eligible) != EXPECTED_ELIGIBLE_SOURCE_COUNT:
        raise CaptureError("canonical queue eligible-source accounting mismatch")
    return blocked, eligible


def validate_existing_pair(
    *,
    item: Mapping[str, Any],
    capture_path: Path,
    sidecar_path: Path,
    remediation: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    file_exists = capture_path.is_file()
    sidecar_exists = sidecar_path.is_file()
    if not file_exists and not sidecar_exists:
        return None
    if file_exists != sidecar_exists:
        raise CaptureError(
            f"{item['source_id']}: partial existing capture pair; remove or repair both "
            f"{capture_path} and {sidecar_path}"
        )
    sidecar = load_json(sidecar_path)
    required = {
        "schema_version", "capture_intent_id", "source_id", "source_version_id",
        "source_locator", "capture_completed_at", "content_type",
        "processing_disposition", "historical_backdating_authorized",
    }
    if set(sidecar) != required:
        raise CaptureError(f"{item['source_id']}: existing sidecar field set invalid")
    if sidecar.get("schema_version") != SIDECAR_SCHEMA:
        raise CaptureError(f"{item['source_id']}: existing sidecar schema invalid")
    for field in ("capture_intent_id", "source_id", "source_version_id"):
        if sidecar.get(field) != item.get(field):
            raise CaptureError(f"{item['source_id']}: existing sidecar {field} mismatch")
    validate_effective_locator(
        item=item,
        locator=str(sidecar.get("source_locator") or ""),
        remediation=remediation,
    )
    if sidecar.get("processing_disposition") != "ELIGIBLE":
        raise CaptureError(f"{item['source_id']}: existing sidecar disposition invalid")
    if sidecar.get("historical_backdating_authorized") is not False:
        raise CaptureError(f"{item['source_id']}: existing sidecar backdating flag invalid")
    if sidecar.get("content_type") != item.get("content_type_hint"):
        raise CaptureError(f"{item['source_id']}: existing sidecar content type mismatch")
    body = capture_path.read_bytes()
    if not body:
        raise CaptureError(f"{item['source_id']}: existing capture is empty")
    if item["content_type_hint"] == "application/pdf" and not body.startswith(b"%PDF-"):
        raise CaptureError(f"{item['source_id']}: existing PDF signature invalid")
    if item["content_type_hint"] == "text/html":
        lower = body[:2_000_000].lower()
        if b"<html" not in lower and b"<!doctype html" not in lower:
            raise CaptureError(f"{item['source_id']}: existing HTML marker missing")
        for marker in HTML_BLOCK_MARKERS:
            if marker in lower:
                raise CaptureError(f"{item['source_id']}: existing HTML contains challenge marker")
    return {
        "source_id": item["source_id"],
        "source_version_id": item["source_version_id"],
        "registered_source_locator": item["source_locator"],
        "capture_locator": sidecar["source_locator"],
        "capture_path": str(capture_path),
        "sidecar_path": str(sidecar_path),
        "capture_completed_at": sidecar["capture_completed_at"],
        "content_type": sidecar["content_type"],
        "byte_length": len(body),
        "artifact_sha256": hashlib.sha256(body).hexdigest(),
        "status": "RESUMED_EXISTING_VALID_PAIR",
    }


def launch_context(playwright: Any, *, private_root: Path, browser: str, headless: bool) -> tuple[Any, str]:
    channels = ("chrome", "msedge") if browser == "auto" else (browser,)
    failures: list[str] = []
    for channel in channels:
        profile = private_root / "browser-profile" / f"semiconductor-b026-{channel}"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                channel=channel,
                headless=headless,
                accept_downloads=False,
                ignore_https_errors=False,
            )
            return context, channel
        except Exception as exc:
            failures.append(f"{channel}: {exc}")
    raise CaptureError("unable to launch installed Chrome/Edge through Playwright; " + " | ".join(failures))


def is_target_closed_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return (
        "targetclosed" in text
        or "target page, context or browser has been closed" in text
        or "browser has been closed" in text
        or "context has been closed" in text
    )


def is_authorized_tsmc_browser_fallback_source(
    *,
    item: Mapping[str, Any],
    capture_locator: str,
) -> bool:
    identity = B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS.get(str(item.get("source_id") or ""))
    return bool(
        identity is not None
        and item.get("source_version_id") == identity[0]
        and item.get("source_locator") == identity[1]
        and item.get("content_type_hint") == "application/pdf"
        and capture_locator == identity[1]
    )


def capture_one(
    *,
    context: Any,
    browser_channel: str,
    item: Mapping[str, Any],
    capture_path: Path,
    sidecar_path: Path,
    capture_locator: str,
    redirect_policy: str,
    challenge_wait_seconds: int,
    navigation_timeout_seconds: int,
) -> dict[str, Any]:
    source_id = str(item["source_id"])
    locator = str(capture_locator)
    page = context.new_page()
    responses: list[Any] = []

    def on_response(response: Any) -> None:
        try:
            request = response.request
            if request.is_navigation_request() and request.frame == page.main_frame:
                responses.append(response)
        except Exception:
            return

    page.on("response", on_response)
    navigation_error: Exception | None = None
    is_pdf = str(item["content_type_hint"]) == "application/pdf"
    navigation_response: Any | None = None
    try:
        if is_pdf:
            print(f"PDF_NAV_BEGIN {source_id} -> {locator}", flush=True)
            main_response: Any | None = None
            try:
                main_response = page.goto(
                    locator,
                    wait_until="load",
                    timeout=max(1, navigation_timeout_seconds) * 1000,
                )
            except Exception as exc:
                navigation_error = exc
            finally:
                if main_response is not None and all(candidate is not main_response for candidate in responses):
                    responses.append(main_response)
                navigation_response = main_response
                response_status = getattr(main_response, "status", None)
                print(
                    f"PDF_NAV_COMPLETE {source_id} -> {locator} "
                    f"response_status={response_status} navigation_error={navigation_error!s}",
                    flush=True,
                )
        else:
            try:
                page.goto(locator, wait_until="commit", timeout=max(1, navigation_timeout_seconds) * 1000)
            except Exception as exc:
                navigation_error = exc

        deadline = time.monotonic() + max(0, challenge_wait_seconds)
        last_rejection: str | None = None
        seen: set[int] = set()
        while True:
            for response in reversed(responses):
                key = id(response)
                if key in seen:
                    continue
                seen.add(key)
                body_response = response
                api_response: Any | None = None
                request_chain: tuple[str, ...] | None = None
                raw_api_attempt: dict[str, Any] | None = None
                fallback_provenance: dict[str, Any] | None = None
                try:
                    if is_pdf:
                        print(f"PDF_RAW_REQUEST_BEGIN {source_id} -> {locator}", flush=True)
                        api_response, request_chain = fetch_pdf_response(
                            context=context,
                            exact_locator=locator,
                            policy=redirect_policy,
                            timeout_milliseconds=max(1, navigation_timeout_seconds) * 1000,
                        )
                        raw_api_attempt = {
                            "http_status": int(api_response.status),
                            "response_url": str(api_response.url),
                            "redirect_chain": list(request_chain),
                            "content_type": response_header_value(api_response, "content-type"),
                            "content_length": response_header_value(api_response, "content-length"),
                        }
                        if (
                            raw_api_attempt["http_status"] == 403
                            and is_authorized_tsmc_browser_fallback_source(
                                item=item,
                                capture_locator=locator,
                            )
                        ):
                            navigation_status = getattr(navigation_response, "status", None)
                            if navigation_response is None or navigation_status != 200:
                                raise CaptureError(
                                    f"{source_id}: authorized browser fallback requires HTTP 200 "
                                    f"navigation response, observed {navigation_status!r}"
                                )
                            body_response = navigation_response
                            navigation_chain = redirect_chain(navigation_response)
                            fallback_provenance = {
                                "primary_attempt": {
                                    "method": "playwright_request_context_get",
                                    "http_status": raw_api_attempt["http_status"],
                                    "response_url": raw_api_attempt["response_url"],
                                    "redirect_chain": raw_api_attempt["redirect_chain"],
                                    "content_type": raw_api_attempt["content_type"],
                                    "content_length": raw_api_attempt["content_length"],
                                },
                                "accepted_response": {
                                    "method": "playwright_main_navigation_response",
                                    "http_status": int(navigation_response.status),
                                    "response_url": str(navigation_response.url),
                                    "redirect_chain": list(navigation_chain),
                                },
                            }
                            dispose_api_response(api_response)
                            api_response = None
                            request_chain = None
                            print(
                                f"PDF_BROWSER_FALLBACK {source_id} -> {locator} "
                                "primary_api_status=403 navigation_status=200",
                                flush=True,
                            )
                        else:
                            body_response = api_response
                        print(
                            f"PDF_RAW_RESPONSE_COMPLETE {source_id} -> {locator} "
                            f"status={raw_api_attempt['http_status']} "
                            f"final_url={raw_api_attempt['response_url']} "
                            f"redirect_chain={raw_api_attempt['redirect_chain']!r} "
                            f"content_length={raw_api_attempt['content_length']!r}",
                            flush=True,
                        )
                        print(f"PDF_BODY_BEGIN {source_id} -> {locator}", flush=True)
                    body = bytes(body_response.body())
                    if is_pdf:
                        print(
                            f"PDF_BODY_COMPLETE {source_id} -> {locator} bytes={len(body)}",
                            flush=True,
                        )
                        print(f"PDF_VALIDATION_BEGIN {source_id} -> {locator}", flush=True)
                    try:
                        content_type, chain, final_url = validate_body(
                            item=item,
                            response=body_response,
                            body=body,
                            policy=redirect_policy,
                            effective_locator=locator,
                            redirect_chain_override=request_chain,
                        )
                    except Exception as exc:
                        if is_pdf:
                            def diagnostic_header(name: str) -> str:
                                value = response_header_value(body_response, name)
                                if value is None:
                                    return "<missing>"
                                text = str(value).replace("\r", "\\r").replace("\n", "\\n")
                                return text[:128]

                            print(
                                f"PDF_VALIDATION_REJECTED {source_id} -> {locator} "
                                f"response_status={getattr(body_response, 'status', None)!r} "
                                f"content_type={diagnostic_header('content-type')!r} "
                                f"content_length={diagnostic_header('content-length')!r} "
                                f"body_bytes={len(body)} prefix_hex={body[:16].hex()} "
                                f"reason={str(exc)[:240]!r}",
                                flush=True,
                            )
                        raise
                    response_status = int(body_response.status)
                    if is_pdf:
                        print(
                            f"PDF_VALIDATION_COMPLETE {source_id} -> {locator} "
                            f"content_type={content_type} status={response_status}",
                            flush=True,
                        )
                except Exception as exc:
                    if api_response is not None:
                        dispose_api_response(api_response)
                    if raw_api_attempt is not None:
                        last_rejection = (
                            f"{exc}; prior raw API request returned HTTP "
                            f"{raw_api_attempt['http_status']} at "
                            f"{raw_api_attempt['response_url']!r} and was not accepted"
                        )
                    else:
                        last_rejection = str(exc)
                    continue

                if api_response is not None:
                    dispose_api_response(api_response)
                captured_at = utc_timestamp()
                capture_path.parent.mkdir(parents=True, exist_ok=True)
                capture_path.write_bytes(body)
                sidecar = {
                    "schema_version": SIDECAR_SCHEMA,
                    "capture_intent_id": item["capture_intent_id"],
                    "source_id": item["source_id"],
                    "source_version_id": item["source_version_id"],
                    "source_locator": locator,
                    "capture_completed_at": captured_at,
                    "content_type": content_type,
                    "processing_disposition": "ELIGIBLE",
                    "historical_backdating_authorized": False,
                }
                write_json(sidecar_path, sidecar)
                receipt = {
                    "source_id": source_id,
                    "source_version_id": item["source_version_id"],
                    "registered_source_locator": item["source_locator"],
                    "capture_locator": locator,
                    "capture_path": str(capture_path),
                    "sidecar_path": str(sidecar_path),
                    "capture_completed_at": captured_at,
                    "content_type": content_type,
                    "http_status": response_status,
                    "byte_length": len(body),
                    "artifact_sha256": hashlib.sha256(body).hexdigest(),
                    "browser_channel": browser_channel,
                    "redirect_policy": redirect_policy,
                    "redirect_chain": list(chain),
                    "final_response_url": final_url,
                    "status": "CAPTURED",
                }
                if fallback_provenance is not None:
                    receipt["transport_provenance"] = fallback_provenance
                return receipt

            if time.monotonic() >= deadline:
                detail = last_rejection
                if detail is None and navigation_error is not None:
                    detail = f"{source_id}: navigation failed: {navigation_error}"
                if detail is None:
                    detail = f"{source_id}: no acceptable main-document response observed"
                raise CaptureError(detail)
            page.wait_for_timeout(500)
    finally:
        try:
            page.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="HYDRA semiconductor Batch026 private browser capture adapter")
    parser.add_argument("--authorized-public-acquisition", action="store_true")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--inbox-root", required=True)
    parser.add_argument("--browser", choices=("auto", "chrome", "msedge"), default="auto")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--redirect-policy", choices=("exact", "same-origin"), default="exact")
    parser.add_argument("--challenge-wait-seconds", type=int, default=180)
    parser.add_argument("--navigation-timeout-seconds", type=int, default=90)
    parser.add_argument("--browser-restart-retries", type=int, default=2)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    if not args.authorized_public_acquisition:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL")
        print("ERROR=explicit --authorized-public-acquisition is required")
        return 2

    repo_root = Path(args.repo_root).expanduser().resolve()
    private_root = assert_outside_repo(Path(args.private_root), repo_root, "PrivateRoot")
    inbox_root = assert_outside_repo(Path(args.inbox_root), repo_root, "InboxRoot")
    queue_doc = load_json(repo_root / QUEUE_RELATIVE_PATH)
    queue = validate_queue(queue_doc)
    blocked_items, eligible_items = partition_capture_queue(
        queue,
        blocked_source_ids=OPERATOR_BLOCKED_SOURCE_IDS,
    )
    blocked_source_id_set = set(OPERATOR_BLOCKED_SOURCE_IDS)
    leaked_source_ids = sorted(
        blocked_source_id_set & {str(item["source_id"]) for item in eligible_items}
    )
    if leaked_source_ids:
        raise CaptureError(
            f"operator-blocked source leaked into acquisition queue: {leaked_source_ids}"
        )
    remediation_doc = load_json(repo_root / LOCATOR_OVERLAY_RELATIVE_PATH)
    remediations = load_locator_remediations(remediation_doc)
    queue_ids = {item["source_id"] for item in queue}
    if not set(remediations).issubset(queue_ids):
        raise CaptureError("locator remediation references source outside Batch026 queue")
    inbox_root.mkdir(parents=True, exist_ok=True)

    journal_path = inbox_root / "HYDRA_CONSTRAINT_SEMI_B026_BROWSER_CAPTURE_JOURNAL_V001.json"
    if args.fresh:
        for item in eligible_items:
            capture_path = inbox_root / item["inbox_filename"]
            sidecar_path = Path(str(capture_path) + ".capture.json")
            if capture_path.exists():
                capture_path.unlink()
            if sidecar_path.exists():
                sidecar_path.unlink()
        if journal_path.exists():
            journal_path.unlink()

    entries: list[dict[str, Any]] = []
    for item in eligible_items:
        capture_path = inbox_root / item["inbox_filename"]
        sidecar_path = Path(str(capture_path) + ".capture.json")
        existing = validate_existing_pair(
            item=item,
            capture_path=capture_path,
            sidecar_path=sidecar_path,
            remediation=remediations.get(item["source_id"]),
        )
        if existing is not None:
            entries.append(existing)

    captured_by_id = {entry["source_id"]: entry for entry in entries}
    attempted_source_ids: list[str] = []
    failed_sources_by_id: dict[str, dict[str, str]] = {}
    blocked_sources = [
        {
            "ordinal": item["ordinal"],
            "source_id": item["source_id"],
            "status": BLOCKED_SOURCE_STATUS,
            "acquisition_attempted": False,
        }
        for item in blocked_items
    ]

    def write_journal() -> dict[str, Any]:
        ordered_entries = [
            captured_by_id[item["source_id"]]
            for item in eligible_items
            if item["source_id"] in captured_by_id
        ]
        failed_sources = [
            failed_sources_by_id[item["source_id"]]
            for item in eligible_items
            if item["source_id"] in failed_sources_by_id
        ]
        terminal_ids = set(captured_by_id) | set(failed_sources_by_id)
        pending_source_ids = [
            item["source_id"] for item in eligible_items if item["source_id"] not in terminal_ids
        ]
        accounting = {
            "total": len(queue),
            "blocked_by_operator": len(blocked_items),
            "eligible": len(eligible_items),
            "attempted": len(attempted_source_ids),
            "completed": len(ordered_entries),
            "failed": len(failed_sources),
            "pending": len(pending_source_ids),
        }
        journal = {
            "schema_version": JOURNAL_SCHEMA,
            "slice_id": EXPECTED_SLICE_ID,
            "queue_record_id": queue_doc["record_id"],
            "authoritative": False,
            "network_acquisition_authorized": True,
            "historical_backdating_authorized": False,
            "redirect_policy": args.redirect_policy,
            "expected_source_count": EXPECTED_SOURCE_COUNT,
            "entries": ordered_entries,
            "blocked_sources": blocked_sources,
            "attempted_source_ids": list(attempted_source_ids),
            "failed_sources": failed_sources,
            "pending_source_ids": pending_source_ids,
            "source_accounting": accounting,
            "complete": len(ordered_entries) == len(queue),
            "eligible_complete": len(ordered_entries) == len(eligible_items) and not failed_sources,
            "execution_complete": not pending_source_ids,
            "updated_at": utc_timestamp(),
        }
        write_json(journal_path, journal)
        return journal

    def print_accounting(journal: Mapping[str, Any]) -> None:
        accounting = journal["source_accounting"]
        print(f"TOTAL={accounting['total']}")
        print(f"BLOCKED_BY_OPERATOR={accounting['blocked_by_operator']}")
        print(f"ELIGIBLE={accounting['eligible']}")
        print(f"ATTEMPTED={accounting['attempted']}")
        print(f"COMPLETED={accounting['completed']}")
        print(f"FAILED={accounting['failed']}")
        print(f"PENDING={accounting['pending']}")

    journal = write_journal()
    print_accounting(journal)
    print("BLOCKED_SOURCE_IDS=" + ",".join(item["source_id"] for item in blocked_items))

    if not journal["source_accounting"]["pending"]:
        status = "PASS_WITH_OPERATOR_BLOCKS" if blocked_items else "PASS"
        print(f"HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE={status}")
        print(f"CAPTURED_OR_RESUMED={journal['source_accounting']['completed']}")
        print(f"JOURNAL={journal_path}")
        return 0 if journal["eligible_complete"] else 1

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise CaptureError(f"Playwright Python client unavailable: {exc}") from exc

    context = None
    with sync_playwright() as p:
        try:
            context, browser_channel = launch_context(
                p,
                private_root=private_root,
                browser=args.browser,
                headless=args.headless,
            )
            for item in eligible_items:
                source_id = item["source_id"]
                if source_id in captured_by_id:
                    print(f"RESUME_OK {item['ordinal']:03d}/041 {source_id}")
                    continue

                attempted_source_ids.append(source_id)
                journal = write_journal()
                failure_message: str | None = None
                context_unavailable = False
                restart_attempts = 0
                while True:
                    capture_path = inbox_root / item["inbox_filename"]
                    sidecar_path = Path(str(capture_path) + ".capture.json")
                    try:
                        remediation = remediations.get(source_id)
                        capture_locator = str(item["source_locator"])
                        if remediation is not None:
                            capture_locator = resolve_remediated_locator(
                                context=context,
                                item=item,
                                remediation=remediation,
                                navigation_timeout_seconds=args.navigation_timeout_seconds,
                            )
                            print(
                                f"LOCATOR_REMEDIATED {item['ordinal']:03d}/041 "
                                f"{source_id} -> {capture_locator}"
                            )
                        row = capture_one(
                            context=context,
                            browser_channel=browser_channel,
                            item=item,
                            capture_path=capture_path,
                            sidecar_path=sidecar_path,
                            capture_locator=capture_locator,
                            redirect_policy=args.redirect_policy,
                            challenge_wait_seconds=args.challenge_wait_seconds,
                            navigation_timeout_seconds=args.navigation_timeout_seconds,
                        )
                        captured_by_id[source_id] = row
                        print(
                            f"CAPTURE_OK {item['ordinal']:03d}/041 {source_id} "
                            f"bytes={row['byte_length']} sha256={row['artifact_sha256']}"
                        )
                        break
                    except Exception as exc:
                        if is_target_closed_error(exc) and restart_attempts < max(0, args.browser_restart_retries):
                            restart_attempts += 1
                            try:
                                context.close()
                            except Exception:
                                pass
                            try:
                                context, browser_channel = launch_context(
                                    p,
                                    private_root=private_root,
                                    browser=args.browser,
                                    headless=args.headless,
                                )
                            except Exception as restart_exc:
                                failure_message = (
                                    f"{source_id}: browser restart failed after target closure: {restart_exc}"
                                )
                                context_unavailable = True
                                break
                            print(f"BROWSER_RESTART retry={restart_attempts} source={source_id}")
                            continue
                        failure_message = f"{source_id}: capture failed: {exc}"
                        break

                if failure_message is not None:
                    failed_sources_by_id[source_id] = {
                        "source_id": source_id,
                        "status": "FAILED",
                        "error": failure_message,
                    }
                    print(f"CAPTURE_FAIL {item['ordinal']:03d}/041 {failure_message}")
                journal = write_journal()
                if context_unavailable:
                    break
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    journal = load_json(journal_path)
    print_accounting(journal)
    accounting = journal["source_accounting"]
    print(f"CAPTURED_OR_RESUMED={accounting['completed']}")
    print(f"FAILED_SOURCE_IDS={','.join(row['source_id'] for row in journal['failed_sources'])}")
    print(f"PENDING_SOURCE_IDS={','.join(journal['pending_source_ids'])}")
    print(f"JOURNAL={journal_path}")
    if accounting["failed"] or accounting["pending"]:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL")
        return 1

    status = "PASS_WITH_OPERATOR_BLOCKS" if blocked_items else "PASS"
    print(f"HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE={status}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
