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
from urllib.parse import urlparse

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


def validate_body(
    *,
    item: Mapping[str, Any],
    response: Any,
    body: bytes,
    policy: str,
    effective_locator: str,
) -> tuple[str, tuple[str, ...], str]:
    source_id = str(item["source_id"])
    locator = effective_locator
    expected = str(item["content_type_hint"])
    chain = redirect_chain(response)
    final_url = str(response.url)
    validate_redirects(exact_locator=locator, response_url=final_url, chain=chain, policy=policy)

    if int(response.status) != 200:
        raise CaptureError(f"{source_id}: HTTP status {response.status} is not acceptable")
    if not body:
        raise CaptureError(f"{source_id}: empty main-document body")

    observed = (response.header_value("content-type") or "").strip().lower()
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
    locator = str(item["source_locator"])
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
    try:
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
                try:
                    body = bytes(response.body())
                    content_type, chain, final_url = validate_body(
                        item=item,
                        response=response,
                        body=body,
                        policy=redirect_policy,
                        effective_locator=locator,
                    )
                except Exception as exc:
                    last_rejection = str(exc)
                    continue

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
                return {
                    "source_id": source_id,
                    "source_version_id": item["source_version_id"],
                    "registered_source_locator": item["source_locator"],
                    "capture_locator": locator,
                    "capture_path": str(capture_path),
                    "sidecar_path": str(sidecar_path),
                    "capture_completed_at": captured_at,
                    "content_type": content_type,
                    "http_status": int(response.status),
                    "byte_length": len(body),
                    "artifact_sha256": hashlib.sha256(body).hexdigest(),
                    "browser_channel": browser_channel,
                    "redirect_policy": redirect_policy,
                    "redirect_chain": list(chain),
                    "final_response_url": final_url,
                    "status": "CAPTURED",
                }

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
    remediation_doc = load_json(repo_root / LOCATOR_OVERLAY_RELATIVE_PATH)
    remediations = load_locator_remediations(remediation_doc)
    queue_ids = {item["source_id"] for item in queue}
    if not set(remediations).issubset(queue_ids):
        raise CaptureError("locator remediation references source outside Batch026 queue")
    inbox_root.mkdir(parents=True, exist_ok=True)

    journal_path = inbox_root / "HYDRA_CONSTRAINT_SEMI_B026_BROWSER_CAPTURE_JOURNAL_V001.json"
    if args.fresh:
        for item in queue:
            capture_path = inbox_root / item["inbox_filename"]
            sidecar_path = Path(str(capture_path) + ".capture.json")
            if capture_path.exists():
                capture_path.unlink()
            if sidecar_path.exists():
                sidecar_path.unlink()
        if journal_path.exists():
            journal_path.unlink()

    entries: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for item in queue:
        capture_path = inbox_root / item["inbox_filename"]
        sidecar_path = Path(str(capture_path) + ".capture.json")
        existing = validate_existing_pair(
            item=item,
            capture_path=capture_path,
            sidecar_path=sidecar_path,
            remediation=remediations.get(item["source_id"]),
        )
        if existing is None:
            pending.append(item)
        else:
            entries.append(existing)

    journal = {
        "schema_version": JOURNAL_SCHEMA,
        "slice_id": EXPECTED_SLICE_ID,
        "queue_record_id": queue_doc["record_id"],
        "authoritative": False,
        "network_acquisition_authorized": True,
        "historical_backdating_authorized": False,
        "redirect_policy": args.redirect_policy,
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "entries": entries,
        "complete": len(pending) == 0,
    }
    write_json(journal_path, journal)

    if not pending:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=PASS")
        print("CAPTURED_OR_RESUMED=41")
        print("PENDING=0")
        print(f"JOURNAL={journal_path}")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise CaptureError(f"Playwright Python client unavailable: {exc}") from exc

    with sync_playwright() as p:
        context = None
        browser_channel = ""
        try:
            context, browser_channel = launch_context(
                p,
                private_root=private_root,
                browser=args.browser,
                headless=args.headless,
            )
            captured_by_id = {entry["source_id"]: entry for entry in entries}
            for item in queue:
                if item["source_id"] in captured_by_id:
                    print(f"RESUME_OK {item['ordinal']:03d}/041 {item['source_id']}")
                    continue

                attempts = 0
                while True:
                    capture_path = inbox_root / item["inbox_filename"]
                    sidecar_path = Path(str(capture_path) + ".capture.json")
                    try:
                        remediation = remediations.get(item["source_id"])
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
                                f"{item['source_id']} -> {capture_locator}"
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
                        captured_by_id[item["source_id"]] = row
                        print(
                            f"CAPTURE_OK {item['ordinal']:03d}/041 {item['source_id']} "
                            f"bytes={row['byte_length']} sha256={row['artifact_sha256']}"
                        )
                        break
                    except Exception as exc:
                        if is_target_closed_error(exc) and attempts < max(0, args.browser_restart_retries):
                            attempts += 1
                            try:
                                context.close()
                            except Exception:
                                pass
                            context, browser_channel = launch_context(
                                p,
                                private_root=private_root,
                                browser=args.browser,
                                headless=args.headless,
                            )
                            print(f"BROWSER_RESTART retry={attempts} source={item['source_id']}")
                            continue
                        raise CaptureError(f"{item['source_id']}: capture failed: {exc}") from exc

                ordered_entries = [
                    captured_by_id[q["source_id"]]
                    for q in queue
                    if q["source_id"] in captured_by_id
                ]
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
                    "complete": len(ordered_entries) == EXPECTED_SOURCE_COUNT,
                    "updated_at": utc_timestamp(),
                }
                write_json(journal_path, journal)
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    final_entries = load_json(journal_path).get("entries", [])
    if len(final_entries) != EXPECTED_SOURCE_COUNT:
        raise CaptureError(f"capture incomplete after runner exit: {len(final_entries)}/{EXPECTED_SOURCE_COUNT}")

    print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=PASS")
    print("CAPTURED_OR_RESUMED=41")
    print("PENDING=0")
    print(f"JOURNAL={journal_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
