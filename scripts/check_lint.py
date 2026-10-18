"""Block new lint findings and require removal of fixed baseline entries."""

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(item: dict) -> tuple:
    return tuple(item[key] for key in ("path", "code", "message", "source"))


def check(actual: list[dict], baseline: list[dict]) -> None:
    new = Counter(map(fingerprint, actual)) - Counter(map(fingerprint, baseline))
    stale = Counter(map(fingerprint, baseline)) - Counter(map(fingerprint, actual))
    if new or stale:
        raise ValueError(
            f"New lint findings: {dict(new)}; stale baseline entries: {dict(stale)}"
        )


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", ".", "--output-format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise SystemExit(result.stderr)
    findings = []
    for item in json.loads(result.stdout):
        path = Path(item["filename"])
        findings.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "code": item["code"],
                "message": item["message"],
                "source": path.read_text(encoding="utf-8-sig")
                .splitlines()[item["location"]["row"] - 1]
                .strip(),
            }
        )
    baseline = json.loads((ROOT / "scripts/lint-baseline.json").read_text())
    check(findings, baseline)
    print(f"Lint passed with {len(baseline)} explicitly recorded existing finding(s).")
    for item in baseline:
        print(f"KNOWN: {item['path']}: {item['code']} {item['message']}")


if __name__ == "__main__":
    main()
