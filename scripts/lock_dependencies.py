"""Regenerate locks, or verify them without modifying tracked files."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    args = parser.parse_args()
    if args.check and args.upgrade:
        parser.error("--check and --upgrade cannot be combined")
    with tempfile.TemporaryDirectory() as temporary:
        for name in ("runtime", "validation"):
            lock = ROOT / f"requirements-{name}.lock"
            output = Path(temporary) / lock.name if args.check else lock
            if args.check:
                shutil.copyfile(lock, output)
            command = [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "compile",
                f"requirements-{name}.in",
                "--python-version",
                "3.10",
                "--universal",
                "--generate-hashes",
                "--no-header",
                "--quiet",
                "--output-file",
                str(output),
            ]
            if name == "validation":
                command += ["--constraint", "requirements-runtime.lock"]
            if args.upgrade:
                command.append("--upgrade")
            subprocess.run(command, cwd=ROOT, check=True)
            if args.check and output.read_text() != lock.read_text():
                raise SystemExit(
                    f"{lock.name} is stale. Run python scripts/lock_dependencies.py and review the diff."
                )
    print(
        "Dependency locks verified."
        if args.check
        else "Dependency locks updated; review and run validation."
    )


if __name__ == "__main__":
    main()
