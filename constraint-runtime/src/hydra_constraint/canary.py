from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse
import hashlib
import json
import urllib.error
import urllib.request

from .runtime import unresolved_admission


@dataclass(frozen=True)
class CanarySpec:
    name: str
    url: str
    required_markers: List[str]
    enabled: bool = True
    timeout_seconds: float = 20.0
    max_bytes: int = 2_000_000


@dataclass(frozen=True)
class CanaryResponse:
    status: int
    final_url: str
    headers: Dict[str, str]
    body: bytes


@dataclass
class CanaryResult:
    name: str
    url: str
    enabled: bool
    status: str
    http_status: Optional[int]
    final_url: Optional[str]
    content_type: Optional[str]
    bytes_read: int
    sha256: Optional[str]
    required_markers: List[str]
    missing_markers: List[str]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CanaryTransport:
    def fetch(self, spec: CanarySpec, user_agent: str) -> CanaryResponse:
        req = urllib.request.Request(
            spec.url,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=spec.timeout_seconds) as response:
                body = response.read(spec.max_bytes + 1)
                if len(body) > spec.max_bytes:
                    raise ValueError(f"response exceeds max_bytes={spec.max_bytes}")
                return CanaryResponse(
                    status=int(response.status),
                    final_url=response.geturl(),
                    headers={k.lower(): v for k, v in response.headers.items()},
                    body=body,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read(spec.max_bytes + 1) if hasattr(exc, "read") else b""
            return CanaryResponse(
                status=int(exc.code),
                final_url=getattr(exc, "url", spec.url),
                headers={k.lower(): v for k, v in exc.headers.items()} if exc.headers else {},
                body=body,
            )


class CanaryRunner:
    def __init__(
        self,
        transport: Optional[CanaryTransport] = None,
        *,
        user_agent: str = "HYDRA-Constraint-Canary/0.18 (+https://github.com/HYDRADATAAI/Hydra)",
    ):
        self.transport = transport or CanaryTransport()
        self.user_agent = user_agent

    def run_one(self, spec: CanarySpec) -> CanaryResult:
        if not spec.enabled:
            return CanaryResult(
                name=spec.name,
                url=spec.url,
                enabled=False,
                status="DISABLED",
                http_status=None,
                final_url=None,
                content_type=None,
                bytes_read=0,
                sha256=None,
                required_markers=spec.required_markers,
                missing_markers=[],
            )
        try:
            response = self.transport.fetch(spec, self.user_agent)
        except Exception as exc:
            return CanaryResult(
                name=spec.name,
                url=spec.url,
                enabled=True,
                status="FAIL",
                http_status=None,
                final_url=None,
                content_type=None,
                bytes_read=0,
                sha256=None,
                required_markers=spec.required_markers,
                missing_markers=list(spec.required_markers),
                error=str(exc),
            )

        text = response.body.decode("utf-8", "replace")
        missing = [marker for marker in spec.required_markers if marker.lower() not in text.lower()]
        passed = response.status == 200 and not missing
        return CanaryResult(
            name=spec.name,
            url=spec.url,
            enabled=True,
            status="PASS" if passed else "FAIL",
            http_status=response.status,
            final_url=response.final_url,
            content_type=response.headers.get("content-type"),
            bytes_read=len(response.body),
            sha256=hashlib.sha256(response.body).hexdigest(),
            required_markers=spec.required_markers,
            missing_markers=missing,
            error=None if passed else ("marker mismatch" if missing else f"HTTP {response.status}"),
        )

    def run(self, specs: List[CanarySpec]) -> Dict[str, Any]:
        results = [self.run_one(spec) for spec in specs]
        enabled = [r for r in results if r.enabled]
        return {
            "schema_version": "hydra-constraint-live-canary-report/v1",
            "read_only": True,
            "ledger_mutation": False,
            "automatic_trading_action": False,
            "status": "PASS" if enabled and all(r.status == "PASS" for r in enabled) else "FAIL",
            "status_scope": "CURRENT_FETCH_AND_MARKERS_ONLY",
            "admission": unresolved_admission(),
            "enabled_sources": len(enabled),
            "passed_sources": sum(r.status == "PASS" for r in enabled),
            "results": [r.to_dict() for r in results],
        }


def load_specs(path: str | Path) -> List[CanarySpec]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("read_only") is not True:
        raise ValueError("live canary config must declare read_only=true")
    if payload.get("ledger_mutation") is not False:
        raise ValueError("live canary config must declare ledger_mutation=false")
    if payload.get("automatic_trading_action") is not False:
        raise ValueError("live canary config must declare automatic_trading_action=false")
    return [CanarySpec(**item) for item in payload["sources"]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HYDRA Constraint read-only live source canaries.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = CanaryRunner().run(load_specs(args.config))
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
