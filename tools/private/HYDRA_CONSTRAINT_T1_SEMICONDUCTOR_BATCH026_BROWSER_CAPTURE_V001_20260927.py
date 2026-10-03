from __future__ import annotations

import argparse
import base64
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
TSMC_BROWSER_403_FALLBACK_SOURCE_IDS = (
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
)
EXPECTED_TSMC_BROWSER_403_FALLBACK_SOURCE_COUNT = 4
TSMC_LOCATOR_REMEDIATION_KIND = "TSMC_OFFICIAL_LOCATOR_CORRECTION"
TSMC_LOCATOR_REMEDIATIONS: dict[str, dict[str, Any]] = {
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17": {
        "remediation_kind": TSMC_LOCATOR_REMEDIATION_KIND,
        "requested_locator": (
            "https://investor.tsmc.com/schinese/encrypt/files/encrypt_file/reports/"
            "2025-04/7630274eecc1197a4e3ea6a415f44a47204fe10a/"
            "TSMC%201Q25%20Transcript.pdf"
        ),
        "effective_locator": (
            "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
            "2025-04/7630274eecc1197a4e3ea6a415f44a47204fe10a/"
            "TSMC%201Q25%20Transcript.pdf"
        ),
        "authority_page": "https://investor.tsmc.com/english/quarterly-results/2025/q1",
        "document_title": "TSMC Q1 2025 Earnings Call",
        "publication_date": "2025-04-17",
    },
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20": {
        "remediation_kind": TSMC_LOCATOR_REMEDIATION_KIND,
        "requested_locator": (
            "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
            "2023-07/7ec677062ca442e429b632ccd6d4f31ad53b1ce7/"
            "TSMC%202Q23%20Transcript.pdf"
        ),
        "effective_locator": (
            "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
            "2023-07/7ec677062ca442e429b632ccd6d4f31ad53b1ce7/"
            "TSMC%202Q23%20Transcript.pdf"
        ),
        "authority_page": "https://investor.tsmc.com/english/quarterly-results/2023/q2",
        "document_title": "Q2 2023 Taiwan Semiconductor Manufacturing Co Ltd Earnings Call",
        "publication_date": "2023-07-20",
    },
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK": {
        "remediation_kind": TSMC_LOCATOR_REMEDIATION_KIND,
        "requested_locator": (
            "https://investor.tsmc.com/sites/ir/annual-report/2025/"
            "2025%20Annual%20Report.E.pdf"
        ),
        "effective_locator": (
            "https://investor.tsmc.com/sites/ir/annual-report/2025/"
            "2025%20TSMC%20Annual%20Report.E.pdf"
        ),
        "authority_page": "https://investor.tsmc.com/static/annualReports/2025/english/index.html",
        "document_title": "TSMC 2025 Annual Report",
        "publication_date": None,
    },
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16": {
        "remediation_kind": TSMC_LOCATOR_REMEDIATION_KIND,
        "requested_locator": (
            "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
            "2026-07/57b65edbfe6e480e74abe202be983ecbde79e934/"
            "TSMC%202Q26%20Transcript.pdf"
        ),
        "effective_locator": (
            "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
            "2026-08/3e494f0c14dd0890f897aa044415e21d93486cc4/"
            "TSMC%202Q26%20Transcript.pdf"
        ),
        "authority_page": "https://investor.tsmc.com/english/quarterly-results/2026/q2",
        "document_title": "Q2 2026 Taiwan Semiconductor Manufacturing Co Ltd Earnings Call",
        "publication_date": "2026-07-16",
    },
}
BLOCKED_SOURCE_STATUS = "BLOCKED_BY_OPERATOR"
SIDECAR_SCHEMA = "hydra-semiconductor-private-capture-sidecar/v1"
JOURNAL_SCHEMA = "hydra-constraint-semiconductor-batch026-browser-capture-journal/v1"

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


def validate_tsmc_locator_remediation(
    *,
    item: Mapping[str, Any],
    remediation: Mapping[str, Any],
) -> str:
    source_id = str(item.get("source_id") or "")
    expected = TSMC_LOCATOR_REMEDIATIONS.get(source_id)
    if source_id not in TSMC_BROWSER_403_FALLBACK_SOURCE_IDS or expected is None:
        raise CaptureError(f"{source_id}: source is not authorized for TSMC locator remediation")

    for field in ("requested_locator", "effective_locator", "authority_page"):
        value = remediation.get(field)
        parsed = urlparse(str(value or ""))
        if parsed.scheme.lower() != "https" or normalize_host(str(value or "")) != "investor.tsmc.com":
            raise CaptureError(f"{source_id}: TSMC locator remediation {field} is not on the approved official host")
    if dict(remediation) != expected:
        raise CaptureError(f"{source_id}: TSMC locator correction is not in the exact authorized mapping")
    if item.get("source_locator") != expected["requested_locator"]:
        raise CaptureError(f"{source_id}: registered TSMC source locator mismatch")
    if item.get("title") != expected["document_title"]:
        raise CaptureError(f"{source_id}: TSMC locator correction would change document identity")
    if item.get("publication_date") != expected["publication_date"]:
        raise CaptureError(f"{source_id}: TSMC locator correction would change publication date")
    return str(expected["effective_locator"])


def resolve_tsmc_effective_locator(
    *,
    item: Mapping[str, Any],
    remediation: Mapping[str, Any],
) -> str:
    return validate_tsmc_locator_remediation(item=item, remediation=remediation)


def locator_resolution_provenance(
    *,
    item: Mapping[str, Any],
    effective_locator: str,
    remediation: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if remediation is None:
        return None
    resolved = validate_tsmc_locator_remediation(item=item, remediation=remediation)
    if effective_locator != resolved:
        raise CaptureError(f"{item['source_id']}: effective locator differs from its verified TSMC correction")
    return {
        "requested_locator": remediation["requested_locator"],
        "effective_locator": remediation["effective_locator"],
        "authority_page": remediation["authority_page"],
        "document_title": remediation["document_title"],
        "publication_date": remediation["publication_date"],
    }


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
    if remediation.get("remediation_kind") == TSMC_LOCATOR_REMEDIATION_KIND:
        effective_locator = validate_tsmc_locator_remediation(item=item, remediation=remediation)
        if locator != effective_locator:
            raise CaptureError(f"{item['source_id']}: capture locator differs from verified TSMC locator correction")
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
        reject_forbidden_capture_request(current_url)
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
        try:
            reject_forbidden_capture_request(next_url)
        except Exception:
            dispose_api_response(response)
            raise
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
    result = {
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
    if remediation is not None and remediation.get("remediation_kind") == TSMC_LOCATOR_REMEDIATION_KIND:
        result["locator_resolution"] = locator_resolution_provenance(
            item=item,
            effective_locator=sidecar["source_locator"],
            remediation=remediation,
        )
    return result


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


def capture_browser_pdf_response_after_403(
    *,
    context: Any,
    page: Any,
    exact_locator: str,
    policy: str,
    timeout_milliseconds: int,
) -> tuple[Any, bytes, dict[str, Any]]:
    create_cdp_session = getattr(context, "new_cdp_session", None)
    if not callable(create_cdp_session):
        raise CaptureError("Chromium response-stage capture is unavailable for the authorized TSMC fallback")
    try:
        cdp = create_cdp_session(page)
    except Exception as exc:
        raise CaptureError(f"unable to start TSMC response-stage capture: {exc}") from exc

    captured: list[dict[str, Any]] = []

    def response_headers(raw_headers: Any) -> dict[str, str]:
        if not isinstance(raw_headers, list):
            return {}
        selected: dict[str, str] = {}
        for header in raw_headers:
            if not isinstance(header, Mapping):
                continue
            name = str(header.get("name") or "").lower()
            if name in {"content-type", "content-length", "content-disposition", "location"}:
                selected[name] = str(header.get("value") or "")[:300]
        return selected

    def on_request_paused(event: Mapping[str, Any]) -> None:
        request = event.get("request")
        request_url = str(request.get("url") or "") if isinstance(request, Mapping) else ""
        if request_url == exact_locator:
            row: dict[str, Any] = {
                "url": request_url,
                "http_status": int(event.get("responseStatusCode") or 0),
                "headers": response_headers(event.get("responseHeaders")),
            }
            if row["http_status"] == 200:
                try:
                    response_body = cdp.send("Fetch.getResponseBody", {"requestId": event["requestId"]})
                    encoded_body = str(response_body.get("body") or "")
                    row["body"] = (
                        base64.b64decode(encoded_body)
                        if response_body.get("base64Encoded") is True
                        else encoded_body.encode("utf-8")
                    )
                except Exception as exc:
                    row["body_error"] = f"{type(exc).__name__}: {exc}"[:240]
            captured.append(row)
        try:
            cdp.send("Fetch.continueRequest", {"requestId": event["requestId"]})
        except Exception:
            pass

    try:
        cdp.on("Fetch.requestPaused", on_request_paused)
        cdp.send(
            "Fetch.enable",
            {"patterns": [{"urlPattern": exact_locator, "requestStage": "Response"}]},
        )
        navigation_response = page.goto(
            exact_locator,
            wait_until="load",
            timeout=max(1, int(timeout_milliseconds)),
        )
        if navigation_response is None:
            raise CaptureError("authorized TSMC browser retry did not produce a navigation response")
        chain = redirect_chain(navigation_response)
        validate_redirects(
            exact_locator=exact_locator,
            response_url=str(navigation_response.url),
            chain=chain,
            policy=policy,
        )
        if int(navigation_response.status) != 200:
            raise CaptureError(
                f"authorized TSMC browser retry requires HTTP 200, observed {navigation_response.status}"
            )
        matching = [
            row for row in captured
            if row.get("url") == str(navigation_response.url)
            and row.get("http_status") == int(navigation_response.status)
        ]
        if not matching:
            raise CaptureError("no exact HTTP 200 TSMC response-stage body was captured")
        captured_response = matching[-1]
        body = captured_response.get("body")
        if not isinstance(body, bytes):
            reason = captured_response.get("body_error") or "response-stage body is unavailable"
            raise CaptureError(f"TSMC response-stage body was not captured: {reason}")
        declared_length = captured_response.get("headers", {}).get("content-length")
        if declared_length:
            try:
                expected_length = int(declared_length)
            except ValueError as exc:
                raise CaptureError("TSMC response-stage Content-Length is invalid") from exc
            if expected_length != len(body):
                raise CaptureError(
                    "TSMC response-stage body length does not match Content-Length "
                    f"({len(body)} != {expected_length})"
                )
        evidence = {
            "transport": "CHROMIUM_FETCH_RESPONSE_STAGE",
            "http_status": int(navigation_response.status),
            "response_url": str(navigation_response.url),
            "content_type": response_header_value(navigation_response, "content-type"),
            "content_length": declared_length,
            "redirect_chain": list(chain),
            "byte_length": len(body),
            "artifact_sha256": hashlib.sha256(body).hexdigest(),
            "signature_hex": body[:16].hex(),
        }
        return navigation_response, body, evidence
    finally:
        try:
            cdp.send("Fetch.disable")
        except Exception:
            pass
        try:
            cdp.detach()
        except Exception:
            pass


def reject_quarantined_capture_item(item: Mapping[str, Any], capture_locator: str) -> None:
    """Fail closed for quarantined row identities before capture side effects."""
    tools_dir = Path(__file__).resolve().parents[1]
    tools_dir_text = str(tools_dir)
    if tools_dir_text not in sys.path:
        sys.path.insert(0, tools_dir_text)
    from constraint_source_quarantine import QuarantinePolicyError, reject_quarantined_capture_item as enforce_quarantine

    repo_root = Path(__file__).resolve().parents[2]
    try:
        enforce_quarantine(repo_root, item, capture_locator, operation="browser capture")
    except QuarantinePolicyError as exc:
        raise CaptureError(str(exc)) from exc


def reject_forbidden_capture_request(locator: str) -> None:
    """Apply the shared provider and browser-authority policy to each request URL."""
    tools_dir = Path(__file__).resolve().parents[1]
    tools_dir_text = str(tools_dir)
    if tools_dir_text not in sys.path:
        sys.path.insert(0, tools_dir_text)
    from constraint_source_quarantine import QuarantinePolicyError, reject_forbidden_capture_locator

    try:
        reject_forbidden_capture_locator(locator, operation="browser capture request")
    except QuarantinePolicyError as exc:
        raise CaptureError(str(exc)) from exc


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
    locator_remediation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_id = str(item["source_id"])
    reject_quarantined_capture_item(item, capture_locator)
    locator = str(capture_locator)
    locator_resolution = locator_resolution_provenance(
        item=item,
        effective_locator=locator,
        remediation=locator_remediation,
    )
    page = context.new_page()
    responses: list[Any] = []
    blocked_provider_urls: list[str] = []
    fallback_retry_active = False

    def guard_provider_request(route: Any) -> None:
        request_url = str(getattr(getattr(route, "request", None), "url", ""))
        try:
            reject_forbidden_capture_request(request_url)
        except CaptureError:
            blocked_provider_urls.append(request_url)
            route.abort("blockedbyclient")
            return
        route.continue_()

    if not callable(getattr(page, "route", None)):
        try:
            page.close()
        except Exception:
            pass
        raise CaptureError("browser page does not support pre-request provider routing")
    try:
        page.route("**/*", guard_provider_request)
    except Exception as exc:
        try:
            page.close()
        except Exception:
            pass
        raise CaptureError(f"unable to install pre-request provider guard: {exc}") from exc

    def on_response(response: Any) -> None:
        try:
            if fallback_retry_active:
                return
            request = response.request
            if request.is_navigation_request() and request.frame == page.main_frame:
                responses.append(response)
        except Exception:
            return

    page.on("response", on_response)
    navigation_error: Exception | None = None
    is_pdf = str(item["content_type_hint"]) == "application/pdf"
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
                response_status = getattr(main_response, "status", None)
                print(
                    f"PDF_NAV_COMPLETE {source_id} -> {locator} "
                    f"response_status={response_status} navigation_error={navigation_error!s}",
                    flush=True,
                )
            if blocked_provider_urls:
                raise CaptureError(
                    "SUPERSEDED_BY_BATCH030_QUARANTINE: blocked forbidden provider request before dispatch: "
                    f"{blocked_provider_urls[-1]}"
                )
        else:
            try:
                page.goto(locator, wait_until="commit", timeout=max(1, navigation_timeout_seconds) * 1000)
            except Exception as exc:
                navigation_error = exc
            if blocked_provider_urls:
                raise CaptureError(
                    "SUPERSEDED_BY_BATCH030_QUARANTINE: blocked forbidden provider request before dispatch: "
                    f"{blocked_provider_urls[-1]}"
                )

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
                body_override: bytes | None = None
                fallback_used = False
                fallback_prior_attempt: dict[str, Any] | None = None
                browser_fallback_evidence: dict[str, Any] | None = None
                try:
                    if is_pdf:
                        print(f"PDF_RAW_REQUEST_BEGIN {source_id} -> {locator}", flush=True)
                        api_response, request_chain = fetch_pdf_response(
                            context=context,
                            exact_locator=locator,
                            policy=redirect_policy,
                            timeout_milliseconds=max(1, navigation_timeout_seconds) * 1000,
                        )
                        body_response = api_response
                        print(
                            f"PDF_RAW_RESPONSE_COMPLETE {source_id} -> {locator} "
                            f"status={body_response.status} final_url={body_response.url} "
                            f"redirect_chain={list(request_chain)!r} "
                            f"content_length={response_header_value(body_response, 'content-length')!r}",
                            flush=True,
                        )
                        raw_api_status = int(body_response.status)
                        if (
                            raw_api_status == 403
                            and source_id in TSMC_BROWSER_403_FALLBACK_SOURCE_IDS
                        ):
                            fallback_prior_attempt = {
                                "transport": "PLAYWRIGHT_API_REQUEST",
                                "http_status": raw_api_status,
                                "final_response_url": str(api_response.url),
                                "redirect_chain": list(request_chain),
                                "accepted": False,
                                "reason": "HTTP_403_AUTHORIZED_TSMC_BROWSER_NAVIGATION_FALLBACK",
                            }
                            browser_status = int(getattr(response, "status", 0))
                            if browser_status != 200:
                                raise CaptureError(
                                    f"{source_id}: authorized browser fallback requires "
                                    f"HTTP 200 navigation response, observed {browser_status}"
                                )
                            browser_chain = redirect_chain(response)
                            validate_redirects(
                                exact_locator=locator,
                                response_url=str(response.url),
                                chain=browser_chain,
                                policy=redirect_policy,
                            )
                            browser_fallback_evidence = {
                                "initial_navigation_status": browser_status,
                                "initial_navigation_url": str(response.url),
                                "initial_navigation_content_type": response_header_value(response, "content-type"),
                                "initial_navigation_content_length": response_header_value(response, "content-length"),
                                "initial_navigation_redirect_chain": list(browser_chain),
                            }
                            print(
                                f"PDF_BROWSER_403_FALLBACK_BEGIN {source_id} -> {locator} "
                                f"api_status={raw_api_status} browser_status={browser_status} "
                                f"browser_url={response.url}",
                                flush=True,
                            )
                            fallback_retry_active = True
                            try:
                                body_response, body_override, response_stage_evidence = (
                                    capture_browser_pdf_response_after_403(
                                        context=context,
                                        page=page,
                                        exact_locator=locator,
                                        policy=redirect_policy,
                                        timeout_milliseconds=max(1, navigation_timeout_seconds) * 1000,
                                    )
                                )
                            finally:
                                fallback_retry_active = False
                            browser_fallback_evidence["validated_navigation_response"] = response_stage_evidence
                            request_chain = tuple(response_stage_evidence["redirect_chain"])
                            fallback_used = True
                        print(f"PDF_BODY_BEGIN {source_id} -> {locator}", flush=True)
                    body = body_override if body_override is not None else bytes(body_response.body())
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
                    if fallback_prior_attempt is not None:
                        last_rejection = (
                            f"{exc}; prior raw API request returned HTTP "
                            f"{fallback_prior_attempt['http_status']} at "
                            f"{fallback_prior_attempt['final_response_url']!r} and was not accepted"
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
                result = {
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
                if locator_resolution is not None:
                    result["locator_resolution"] = locator_resolution
                if fallback_used:
                    result["capture_transport"] = "BROWSER_NAVIGATION_RESPONSE_FALLBACK"
                    result["prior_failed_acquisition_attempt"] = fallback_prior_attempt
                    result["browser_response_stage_evidence"] = browser_fallback_evidence
                return result

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
    sys.path.insert(0, str(repo_root / "tools"))
    from constraint_source_quarantine import QuarantinePolicyError, reject_retired_batch026
    try:
        reject_retired_batch026(repo_root, queue, operation="browser capture")
    except QuarantinePolicyError as exc:
        raise CaptureError(str(exc)) from exc
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
    if set(TSMC_LOCATOR_REMEDIATIONS) != set(TSMC_BROWSER_403_FALLBACK_SOURCE_IDS):
        raise CaptureError("TSMC locator remediation allowlist must match the exact four fallback sources")
    if set(remediations) & set(TSMC_LOCATOR_REMEDIATIONS):
        raise CaptureError("Micron and TSMC locator remediation sets must remain disjoint")
    for item in queue:
        tsmc_remediation = TSMC_LOCATOR_REMEDIATIONS.get(str(item["source_id"]))
        if tsmc_remediation is not None:
            validate_tsmc_locator_remediation(item=item, remediation=tsmc_remediation)
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
            remediation=(
                TSMC_LOCATOR_REMEDIATIONS.get(item["source_id"])
                or remediations.get(item["source_id"])
            ),
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
                        micron_remediation = remediations.get(source_id)
                        tsmc_remediation = TSMC_LOCATOR_REMEDIATIONS.get(source_id)
                        remediation = tsmc_remediation or micron_remediation
                        capture_locator = str(item["source_locator"])
                        if tsmc_remediation is not None:
                            capture_locator = resolve_tsmc_effective_locator(
                                item=item,
                                remediation=tsmc_remediation,
                            )
                            print(
                                f"LOCATOR_REMEDIATED {item['ordinal']:03d}/041 "
                                f"{source_id} -> {capture_locator}"
                            )
                        elif micron_remediation is not None:
                            capture_locator = resolve_remediated_locator(
                                context=context,
                                item=item,
                                remediation=micron_remediation,
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
                            locator_remediation=tsmc_remediation,
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
