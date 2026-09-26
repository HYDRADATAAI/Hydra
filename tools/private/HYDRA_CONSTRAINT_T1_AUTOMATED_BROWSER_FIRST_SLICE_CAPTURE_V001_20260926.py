from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_SLICE_ID = "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1"
EXPECTED_SOURCE_COUNT = 9
REGISTRY_RELATIVE_PATH = Path(
    "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
)
MATERIALIZER_SRC_RELATIVE_PATH = Path("constraint-t1-raw-artifact-store/src")
ATTESTATION_VALIDATOR_RELATIVE_PATH = Path("tools/validate_constraint_t1_first_slice_attestation.py")
REPLAY_BUILDER_RELATIVE_PATH = Path("tools/build_constraint_t1_first_slice_replay_lineage.py")
POST_CAPTURE_STATUS_BUILDER_RELATIVE_PATH = Path("tools/build_constraint_t1_post_capture_public_status.py")

HTML_BLOCK_MARKERS = (
    b"attention required! | cloudflare",
    b"just a moment...",
    b"enable javascript and cookies to continue",
    b"checking your browser",
    b"verify you are human",
    b"cf-chl-",
    b"cloudflare ray id",
    b"request blocked",
)
SOURCE_TEXT_MARKERS: dict[str, bytes] = {
    "SRC-LBNL-QUEUED-UP-2025": b"queued up: 2025 edition",
    "SRC-FERC-ORDER-2023-FACT-SHEET": (
        b"fact sheet | improvements to generator interconnection procedures and agreements"
    ),
    "SRC-PJM-2025-YEAR-IN-REVIEW-2026-01-08": (
        b"2025 year in review: planning prepares for burgeoning electricity demand"
    ),
}


class CaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapturedDocument:
    source_id: str
    source_locator: str
    source_version_id: str
    acquired_at: str
    status: int
    content_type: str
    byte_length: int
    artifact_sha256: str
    body_path: Path
    capture_method: str
    browser_channel: str
    redirect_chain: tuple[str, ...]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def assert_outside_repo(path: str | Path, repo_root: str | Path, label: str) -> Path:
    candidate = _resolved(path)
    repo = _resolved(repo_root)
    try:
        candidate.relative_to(repo)
    except ValueError:
        return candidate
    raise CaptureError(f"{label} must remain outside the public repository: {candidate}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CaptureError(f"unable to read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CaptureError(f"top-level JSON object required: {path}")
    return value


def validate_registry(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    if registry.get("slice_id") != EXPECTED_SLICE_ID:
        raise CaptureError(f"unexpected registry slice_id: {registry.get('slice_id')!r}")
    sources = registry.get("sources")
    if not isinstance(sources, list) or len(sources) != EXPECTED_SOURCE_COUNT:
        raise CaptureError(f"authoritative registry must contain exactly {EXPECTED_SOURCE_COUNT} sources")

    normalized: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    locators: set[str] = set()
    for index, raw in enumerate(sources):
        if not isinstance(raw, Mapping):
            raise CaptureError(f"registry.sources[{index}] must be an object")
        source_id = raw.get("source_id")
        locator = raw.get("url")
        if not isinstance(source_id, str) or not source_id:
            raise CaptureError(f"registry.sources[{index}].source_id required")
        if source_id in source_ids:
            raise CaptureError(f"duplicate source identity: {source_id}")
        if not isinstance(locator, str) or not locator.startswith("https://"):
            raise CaptureError(f"{source_id}: exact HTTPS source locator required")
        if locator in locators:
            raise CaptureError(f"duplicate exact source locator: {locator}")
        source_ids.add(source_id)
        locators.add(locator)
        normalized.append(dict(raw))
    return normalized


def expected_content_type(locator: str) -> str:
    return "application/pdf" if locator.lower().endswith(".pdf") else "text/html"


def validate_main_document(
    *,
    source_id: str,
    exact_locator: str,
    response_url: str,
    redirect_chain: Sequence[str],
    status: int,
    observed_content_type: str | None,
    body: bytes,
) -> str:
    if response_url != exact_locator:
        raise CaptureError(
            f"{source_id}: main-document response URL drifted from exact registered locator: "
            f"{response_url!r}"
        )
    if list(redirect_chain) != [exact_locator]:
        raise CaptureError(
            f"{source_id}: redirect chain is not authorized for exact-source capture: "
            f"{list(redirect_chain)!r}"
        )
    if status != 200:
        raise CaptureError(f"{source_id}: HTTP status {status} is not acceptable")

    expected = expected_content_type(exact_locator)
    observed = (observed_content_type or "").strip().lower()
    if not observed.startswith(expected):
        raise CaptureError(
            f"{source_id}: unexpected content type {observed_content_type!r}; "
            f"expected prefix {expected!r}"
        )
    if not body:
        raise CaptureError(f"{source_id}: empty main-document body")

    if expected == "application/pdf":
        if len(body) < 1024:
            raise CaptureError(f"{source_id}: suspiciously small PDF body ({len(body)} bytes)")
        if not body.startswith(b"%PDF-"):
            raise CaptureError(f"{source_id}: application/pdf body lacks PDF signature")
    else:
        if len(body) < 512:
            raise CaptureError(f"{source_id}: suspiciously small HTML body ({len(body)} bytes)")
        lower = body[:2_000_000].lower()
        if b"<html" not in lower and b"<!doctype html" not in lower:
            raise CaptureError(f"{source_id}: text/html body does not contain an HTML document marker")
        for marker in HTML_BLOCK_MARKERS:
            if marker in lower:
                raise CaptureError(
                    f"{source_id}: challenge/error/interstitial marker present: "
                    f"{marker.decode('ascii', errors='replace')}"
                )
        source_marker = SOURCE_TEXT_MARKERS.get(source_id)
        if source_marker is not None and source_marker not in lower:
            raise CaptureError(
                f"{source_id}: main-document body is missing the expected exact-source marker"
            )
    return expected


def _redirect_chain(response: Any) -> tuple[str, ...]:
    request = response.request
    chain: list[str] = []
    while request is not None:
        chain.append(str(request.url))
        request = request.redirected_from
    chain.reverse()
    return tuple(chain)


def _launch_persistent_context(playwright: Any, *, private_root: Path, browser: str, headless: bool) -> tuple[Any, str]:
    channels = ("chrome", "msedge") if browser == "auto" else (browser,)
    failures: list[str] = []
    for channel in channels:
        profile = private_root / "browser-profile" / channel
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
    raise CaptureError(
        "unable to launch installed Chrome/Edge through Playwright; "
        + " | ".join(failures)
    )


def _body_from_response(response: Any) -> bytes:
    try:
        value = response.body()
    except Exception as exc:
        raise CaptureError(f"unable to read browser main-document response body: {exc}") from exc
    if not isinstance(value, (bytes, bytearray)):
        raise CaptureError("browser response body was not bytes")
    return bytes(value)


def capture_source(
    *,
    context: Any,
    browser_channel: str,
    source: Mapping[str, Any],
    capture_dir: Path,
    challenge_wait_seconds: int,
    navigation_timeout_seconds: int,
) -> CapturedDocument:
    source_id = str(source["source_id"])
    locator = str(source["url"])
    expected = expected_content_type(locator)
    suffix = ".pdf" if expected == "application/pdf" else ".html"
    body_path = capture_dir / f"{source_id}{suffix}"

    page = context.new_page()
    document_responses: list[Any] = []

    def on_response(response: Any) -> None:
        try:
            request = response.request
            if request.is_navigation_request() and request.frame == page.main_frame:
                document_responses.append(response)
        except Exception:
            return

    page.on("response", on_response)
    navigation_error: Exception | None = None
    try:
        try:
            page.goto(
                locator,
                wait_until="commit",
                timeout=max(1, navigation_timeout_seconds) * 1000,
            )
        except Exception as exc:
            navigation_error = exc

        deadline = time.monotonic() + max(0, challenge_wait_seconds)
        last_rejection: str | None = None
        seen_response_ids: set[int] = set()
        while True:
            for response in reversed(document_responses):
                response_key = id(response)
                if response_key in seen_response_ids:
                    continue
                seen_response_ids.add(response_key)
                try:
                    body = _body_from_response(response)
                    content_type = response.header_value("content-type")
                    chain = _redirect_chain(response)
                    normalized_content_type = validate_main_document(
                        source_id=source_id,
                        exact_locator=locator,
                        response_url=str(response.url),
                        redirect_chain=chain,
                        status=int(response.status),
                        observed_content_type=content_type,
                        body=body,
                    )
                except CaptureError as exc:
                    last_rejection = str(exc)
                    continue
                except Exception as exc:
                    last_rejection = f"{source_id}: response inspection failed: {exc}"
                    continue

                acquired_at = utc_timestamp()
                digest = hashlib.sha256(body).hexdigest()
                version_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                source_version_id = f"SV-{source_id}-{version_stamp}-{digest[:12]}"
                body_path.write_bytes(body)
                return CapturedDocument(
                    source_id=source_id,
                    source_locator=locator,
                    source_version_id=source_version_id,
                    acquired_at=acquired_at,
                    status=int(response.status),
                    content_type=normalized_content_type,
                    byte_length=len(body),
                    artifact_sha256=digest,
                    body_path=body_path,
                    capture_method="PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT",
                    browser_channel=browser_channel,
                    redirect_chain=chain,
                )

            if time.monotonic() >= deadline:
                detail = last_rejection
                if detail is None and navigation_error is not None:
                    detail = f"{source_id}: navigation failed: {navigation_error}"
                if detail is None:
                    detail = f"{source_id}: no acceptable main-document response was observed"
                raise CaptureError(detail)
            page.wait_for_timeout(500)
    finally:
        try:
            page.close()
        except Exception:
            pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_checked(command: list[str], *, env: Mapping[str, str] | None = None, label: str) -> None:
    completed = subprocess.run(command, env=dict(env) if env is not None else None, check=False)
    if completed.returncode != 0:
        raise CaptureError(f"{label} failed with exit code {completed.returncode}")


def _build_capture_plan(captures: Sequence[CapturedDocument], *, release_id: str, release_created_at: str) -> dict[str, Any]:
    return {
        "schema_version": "hydra-constraint-first-slice-local-capture-plan/v1",
        "slice_id": EXPECTED_SLICE_ID,
        "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
        "release_id": release_id,
        "release_created_at": release_created_at,
        "captures": [
            {
                "source_id": row.source_id,
                "source_version_id": row.source_version_id,
                "input_file": str(row.body_path),
                "content_type": row.content_type,
                "source_locator": row.source_locator,
                "acquired_at": row.acquired_at,
                "processing_disposition": "ELIGIBLE",
            }
            for row in captures
        ],
    }


def _validate_post_outputs(attestation_path: Path, replay_path: Path) -> None:
    attestation = _load_json(attestation_path)
    if attestation.get("materialized_source_count") != EXPECTED_SOURCE_COUNT:
        raise CaptureError("sanitized attestation source count is not 9")
    if attestation.get("all_registry_sources_materialized") is not True:
        raise CaptureError("sanitized attestation does not cover all registered sources")
    if attestation.get("historical_availability_backdated") is not False:
        raise CaptureError("sanitized attestation reports historical availability backdating")

    replay = _load_json(replay_path)
    if replay.get("source_count") != EXPECTED_SOURCE_COUNT:
        raise CaptureError("replay-lineage source count is not 9")
    if replay.get("ordinary_source_version_hash_lineage_complete") is not True:
        raise CaptureError("source-version hash lineage is incomplete")
    if replay.get("strict_historical_replay_ready") is not False:
        raise CaptureError("strict historical replay was improperly promoted")
    if replay.get("historical_availability_backdated") is not False:
        raise CaptureError("replay-lineage reports historical availability backdating")


def run(args: argparse.Namespace) -> int:
    repo_root = _resolved(args.repo_root)
    private_root = assert_outside_repo(args.private_root, repo_root, "PrivateRoot")
    raw_root = assert_outside_repo(private_root / "raw", repo_root, "PrivateRawRoot")
    staging_root = assert_outside_repo(private_root / "capture-staging", repo_root, "PrivateStagingRoot")
    metadata_root = assert_outside_repo(private_root / "metadata", repo_root, "PrivateMetadataRoot")

    registry_path = repo_root / REGISTRY_RELATIVE_PATH
    materializer_src = repo_root / MATERIALIZER_SRC_RELATIVE_PATH
    attestation_validator = repo_root / ATTESTATION_VALIDATOR_RELATIVE_PATH
    replay_builder = repo_root / REPLAY_BUILDER_RELATIVE_PATH
    for label, path in (
        ("authoritative source registry", registry_path),
        ("authoritative T1 materializer source", materializer_src),
        ("sanitized attestation validator", attestation_validator),
        ("deterministic replay-lineage builder", replay_builder),
    ):
        if not path.exists():
            raise CaptureError(f"{label} not found: {path}")

    sources = validate_registry(_load_json(registry_path))
    raw_root.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)

    run_stamp = safe_timestamp()
    capture_dir = staging_root / run_stamp
    capture_dir.mkdir(parents=True, exist_ok=False)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise CaptureError(
            "Playwright is not installed in this Python runtime. "
            "Use the committed PowerShell launcher, which bootstraps Playwright into the private root."
        ) from exc

    captures: list[CapturedDocument] = []
    browser_channel = ""
    with sync_playwright() as playwright:
        context, browser_channel = _launch_persistent_context(
            playwright,
            private_root=private_root,
            browser=args.browser,
            headless=args.headless,
        )
        try:
            for source in sources:
                row = capture_source(
                    context=context,
                    browser_channel=browser_channel,
                    source=source,
                    capture_dir=capture_dir,
                    challenge_wait_seconds=args.challenge_wait_seconds,
                    navigation_timeout_seconds=args.navigation_timeout_seconds,
                )
                captures.append(row)
                print(
                    f"CAPTURE_OK {row.source_id} status={row.status} "
                    f"bytes={row.byte_length} sha256={row.artifact_sha256}"
                )
        finally:
            context.close()

    if len(captures) != EXPECTED_SOURCE_COUNT:
        raise CaptureError(
            f"capture count drifted: expected {EXPECTED_SOURCE_COUNT}, observed {len(captures)}"
        )

    capture_manifest = {
        "schema_version": "hydra-constraint-automated-browser-capture-manifest/v1",
        "slice_id": EXPECTED_SLICE_ID,
        "capture_method": "PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT",
        "browser_channel": browser_channel,
        "raw_bodies_published_to_git": False,
        "challenge_bypass_attempted": False,
        "cookie_export_or_theft_performed": False,
        "rendered_dom_used_as_source_body": False,
        "sources": [
            {
                "source_id": row.source_id,
                "source_locator": row.source_locator,
                "source_version_id": row.source_version_id,
                "acquired_at": row.acquired_at,
                "http_status": row.status,
                "content_type": row.content_type,
                "byte_length": row.byte_length,
                "artifact_sha256": row.artifact_sha256,
                "capture_method": row.capture_method,
                "browser_channel": row.browser_channel,
                "redirect_chain": list(row.redirect_chain),
            }
            for row in captures
        ],
    }
    capture_manifest_path = metadata_root / (
        f"HYDRA_CONSTRAINT_FIRST_SLICE_AUTOMATED_BROWSER_CAPTURE_MANIFEST_{run_stamp}.json"
    )
    _write_json(capture_manifest_path, capture_manifest)

    release_created_at = utc_timestamp()
    release_id = f"REL-AIDC-FIRST-SLICE-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    capture_plan = _build_capture_plan(
        captures,
        release_id=release_id,
        release_created_at=release_created_at,
    )
    plan_path = metadata_root / f"HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_CAPTURE_PLAN_{run_stamp}.json"
    attestation_path = metadata_root / (
        f"HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_MATERIALIZATION_ATTESTATION_{run_stamp}.json"
    )
    replay_path = metadata_root / (
        f"HYDRA_CONSTRAINT_FIRST_SLICE_REPLAY_LINEAGE_PACKET_{run_stamp}.json"
    )
    _write_json(plan_path, capture_plan)

    env = os.environ.copy()
    previous_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(materializer_src)
        if not previous_pythonpath
        else str(materializer_src) + os.pathsep + previous_pythonpath
    )

    _run_checked(
        [
            sys.executable,
            "-m",
            "hydra_constraint_t1_raw.first_slice_cli",
            "--registry",
            str(registry_path),
            "--capture-plan",
            str(plan_path),
            "--private-root",
            str(raw_root),
            "--public-repo-root",
            str(repo_root),
            "--attestation-output",
            str(attestation_path),
        ],
        env=env,
        label="authoritative private T1 materializer",
    )
    _run_checked(
        [
            sys.executable,
            str(attestation_validator),
            "--attestation",
            str(attestation_path),
            "--registry",
            str(registry_path),
        ],
        env=env,
        label="sanitized materialization attestation validation",
    )
    _run_checked(
        [
            sys.executable,
            str(replay_builder),
            "--attestation",
            str(attestation_path),
            "--registry",
            str(registry_path),
            "--output",
            str(replay_path),
        ],
        env=env,
        label="deterministic replay-lineage builder",
    )
    _validate_post_outputs(attestation_path, replay_path)

    print(f"SOURCE_CAPTURE={EXPECTED_SOURCE_COUNT}/{EXPECTED_SOURCE_COUNT}")
    print("PRIVATE_MATERIALIZATION=PASS")
    print("ATTESTATION=PASS")
    print("SOURCE_VERSION_HASH_LINEAGE=PASS")
    print("REPLAY_LINEAGE=PASS")
    print("STRICT_HISTORICAL_REPLAY=BLOCKED")
    print("NATIVE_T5_T6_ADMISSION=BLOCKED")
    print("RAW_SOURCE_PUBLICATION=NO")
    return 0


def build_parser() -> argparse.ArgumentParser:
    default_repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Capture the authoritative HYDRA Constraint first-slice registry with an installed "
            "Chrome/Edge browser, then invoke the existing T1 materializer, attestation validator, "
            "and deterministic replay-lineage builder."
        )
    )
    parser.add_argument("--repo-root", default=str(default_repo))
    parser.add_argument("--private-root", default=r"D:\HYDRA\_PRIVATE\constraint")
    parser.add_argument("--browser", choices=("auto", "chrome", "msedge"), default="auto")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--challenge-wait-seconds", type=int, default=180)
    parser.add_argument("--navigation-timeout-seconds", type=int, default=90)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except CaptureError as exc:
        print("HYDRA_CONSTRAINT_AUTOMATED_BROWSER_SOURCE_CAPTURE=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
