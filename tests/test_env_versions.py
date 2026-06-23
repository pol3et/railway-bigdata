from pathlib import Path
import tomllib

import pandas
import pyarrow
import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]

PANDAS_MIN = (2, 2)
PANDAS_MAX_MAJOR = 4
PYARROW_MIN_MAJOR = 15
PYARROW_MAX_MAJOR = 25
PINNED_PANDAS = "3.0.3"
PINNED_PYARROW = "24.0.0"


def _leading_int(value: str) -> int:
    digits = []
    for char in value:
        if not char.isdigit():
            break
        digits.append(char)
    if not digits:
        raise AssertionError(f"Version segment {value!r} does not start with a number")
    return int("".join(digits))


def _major_minor(version: str) -> tuple[int, int]:
    parts = version.split(".")
    if len(parts) < 2:
        raise AssertionError(f"Version {version!r} does not include major.minor")
    return _leading_int(parts[0]), _leading_int(parts[1])


def _major(version: str) -> int:
    return _leading_int(version.split(".", 1)[0])


def _major_in_window(major: int, lower_inclusive: int, upper_exclusive: int) -> bool:
    return lower_inclusive <= major < upper_exclusive


def _pandas_in_window(version: str) -> bool:
    major, minor = _major_minor(version)
    return (major, minor) >= PANDAS_MIN and major < PANDAS_MAX_MAJOR


def _dependency_spec(dependencies: list[str], name: str) -> str:
    prefix = f"{name}"
    for dependency in dependencies:
        if dependency == prefix or dependency.startswith(f"{prefix}>") or dependency.startswith(f"{prefix}="):
            return dependency
    raise AssertionError(f"{name!r} is missing from project dependencies")


def test_pandas_version_is_inside_validated_window():
    assert _pandas_in_window(pandas.__version__), (
        f"Installed pandas {pandas.__version__} is outside the validated range "
        f">={PANDAS_MIN[0]}.{PANDAS_MIN[1]},<{PANDAS_MAX_MAJOR}"
    )


def test_pyarrow_version_is_inside_validated_window():
    observed = _major(pyarrow.__version__)

    assert _major_in_window(observed, PYARROW_MIN_MAJOR, PYARROW_MAX_MAJOR), (
        f"Installed pyarrow {pyarrow.__version__} is outside the validated range "
        f">={PYARROW_MIN_MAJOR},<{PYARROW_MAX_MAJOR}"
    )


def test_guard_windows_match_pyproject_dependency_bounds():
    with (ROOT / "pyproject.toml").open("rb") as fh:
        project = tomllib.load(fh)["project"]

    dependencies = project["dependencies"]

    assert project["requires-python"] == ">=3.12,<3.15"
    assert _dependency_spec(dependencies, "pandas") == (
        f"pandas>={PANDAS_MIN[0]}.{PANDAS_MIN[1]},<{PANDAS_MAX_MAJOR}"
    )
    assert _dependency_spec(dependencies, "pyarrow") == (
        f"pyarrow>={PYARROW_MIN_MAJOR},<{PYARROW_MAX_MAJOR}"
    )


def test_constraints_lock_pins_validated_stack():
    constraints_path = ROOT / "constraints.txt"

    assert constraints_path.exists(), "constraints.txt must be committed at the repo root"

    pins = {
        line.strip()
        for line in constraints_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert f"pandas=={PINNED_PANDAS}" in pins
    assert f"pyarrow=={PINNED_PYARROW}" in pins


def test_version_window_helpers_reject_out_of_window_values():
    assert _pandas_in_window("2.2.0")
    assert _pandas_in_window("3.0.3")
    assert not _pandas_in_window("2.1.9")
    assert not _pandas_in_window("4.0.0")
    assert _major_in_window(15, PYARROW_MIN_MAJOR, PYARROW_MAX_MAJOR)
    assert _major_in_window(24, PYARROW_MIN_MAJOR, PYARROW_MAX_MAJOR)
    assert not _major_in_window(14, PYARROW_MIN_MAJOR, PYARROW_MAX_MAJOR)
    assert not _major_in_window(25, PYARROW_MIN_MAJOR, PYARROW_MAX_MAJOR)
