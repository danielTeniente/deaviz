"""Check that installed versions match the lock for this Python/platform."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    errors = []
    for line in (ROOT / "requirements-validation.lock").read_text().splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        requirement = Requirement(line.rstrip(" \\"))
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            errors.append(f"Missing: {requirement.name}")
            continue
        if installed not in requirement.specifier:
            errors.append(
                f"{requirement.name}: installed {installed}, expected {requirement.specifier}"
            )
    if errors:
        raise SystemExit(
            "Environment does not match validation lock:\n" + "\n".join(errors)
        )
    print("Installed versions match the validation lock.")


if __name__ == "__main__":
    main()
