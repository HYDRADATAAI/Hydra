from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = (
    ROOT
    / "tools"
    / "private"
    / "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py"
)
SPEC = importlib.util.spec_from_file_location("hydra_constraint_automated_browser_capture", TOOL)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


def source(source_id: str, url: str) -> dict:
    return {"source_id": source_id, "url": url}


def registry(rows: list[dict]) -> dict:
    return {"slice_id": capture.EXPECTED_SLICE_ID, "sources": rows}


def nine_sources() -> list[dict]:
    return [
        source(f"SRC-{index}", f"https://example.com/source-{index}.html")
        for index in range(9)
    ]


def test_registry_requires_exact_nine_unique_source_ids_and_locators() -> None:
    rows = nine_sources()
    assert len(capture.validate_registry(registry(rows))) == 9

    duplicate_id = nine_sources()
    duplicate_id[-1]["source_id"] = duplicate_id[0]["source_id"]
    with pytest.raises(capture.CaptureError, match="duplicate source identity"):
        capture.validate_registry(registry(duplicate_id))

    duplicate_locator = nine_sources()
    duplicate_locator[-1]["url"] = duplicate_locator[0]["url"]
    with pytest.raises(capture.CaptureError, match="duplicate exact source locator"):
        capture.validate_registry(registry(duplicate_locator))


def test_exact_html_main_document_is_accepted() -> None:
    locator = "https://example.com/source.html"
    body = b"<!doctype html><html><head><title>source</title></head><body>" + b"x" * 600 + b"</body></html>"
    observed = capture.validate_main_document(
        source_id="SRC-TEST",
        exact_locator=locator,
        response_url=locator,
        redirect_chain=[locator],
        status=200,
        observed_content_type="text/html; charset=utf-8",
        body=body,
    )
    assert observed == "text/html"


def test_redirect_or_wrong_url_fails_closed() -> None:
    locator = "https://example.com/source.html"
    body = b"<!doctype html><html><body>" + b"x" * 600 + b"</body></html>"
    with pytest.raises(capture.CaptureError, match="response URL drifted"):
        capture.validate_main_document(
            source_id="SRC-TEST",
            exact_locator=locator,
            response_url="https://mirror.example/source.html",
            redirect_chain=[locator, "https://mirror.example/source.html"],
            status=200,
            observed_content_type="text/html",
            body=body,
        )

    with pytest.raises(capture.CaptureError, match="redirect chain is not authorized"):
        capture.validate_main_document(
            source_id="SRC-TEST",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=["https://example.com/start", locator],
            status=200,
            observed_content_type="text/html",
            body=body,
        )


def test_challenge_page_fails_closed() -> None:
    locator = "https://example.com/source.html"
    body = (
        b"<!doctype html><html><head><title>Just a moment...</title></head>"
        b"<body>Enable JavaScript and cookies to continue"
        + b"x" * 600
        + b"</body></html>"
    )
    with pytest.raises(capture.CaptureError, match="challenge/error/interstitial marker"):
        capture.validate_main_document(
            source_id="SRC-TEST",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=[locator],
            status=200,
            observed_content_type="text/html",
            body=body,
        )


def test_pdf_requires_pdf_mime_and_signature() -> None:
    locator = "https://example.com/report.pdf"
    valid_pdf = b"%PDF-1.7\n" + b"x" * 2048
    assert (
        capture.validate_main_document(
            source_id="SRC-PDF",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=[locator],
            status=200,
            observed_content_type="application/pdf",
            body=valid_pdf,
        )
        == "application/pdf"
    )

    with pytest.raises(capture.CaptureError, match="lacks PDF signature"):
        capture.validate_main_document(
            source_id="SRC-PDF",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=[locator],
            status=200,
            observed_content_type="application/pdf",
            body=b"not-a-pdf" + b"x" * 2048,
        )


def test_capture_plan_never_supplies_available_at(tmp_path: Path) -> None:
    captured = []
    for index in range(9):
        captured.append(
            capture.CapturedDocument(
                source_id=f"SRC-{index}",
                source_locator=f"https://example.com/{index}.html",
                source_version_id=f"SV-SRC-{index}-20260926T000000Z-123456789abc",
                acquired_at="2026-09-26T20:00:00.000000Z",
                status=200,
                content_type="text/html",
                byte_length=1000,
                artifact_sha256="a" * 64,
                body_path=tmp_path / f"{index}.html",
                capture_method="PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT",
                browser_channel="chrome",
                redirect_chain=(f"https://example.com/{index}.html",),
            )
        )
    plan = capture._build_capture_plan(
        captured,
        release_id="REL-TEST",
        release_created_at="2026-09-26T20:00:01.000000Z",
    )
    assert plan["availability_mode"] == "ACQUISITION_TIME_CONSERVATIVE"
    assert len(plan["captures"]) == 9
    assert all("available_at" not in row for row in plan["captures"])
