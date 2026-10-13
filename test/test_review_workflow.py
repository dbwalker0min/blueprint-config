"""Exercise review enforcement in isolated pytest processes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.review_required


@pytest.fixture
def run_review_case(tmp_path):
    (tmp_path / "conftest.py").write_text(
        Path(__file__).with_name("conftest.py").read_text()
    )

    def run(source, *options):
        path = tmp_path / "test_example.py"
        path.write_text(source)
        environment = os.environ.copy()
        environment.pop("PYTEST_ADDOPTS", None)
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *options],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
        assert path.read_text() == source, "Running pytest must not change approvals"
        return result

    return run


@pytest.mark.reviewed(False)
@pytest.mark.parametrize(
    "marker", ["@pytest.mark.reviewed(True)", "@pytest.mark.reviewed(False)", ""]
)
@pytest.mark.parametrize("override", [False, True])
def test_review_status_and_override_preserve_test_execution(
    run_review_case, tmp_path, marker, override
):
    source = f"""
from pathlib import Path
import pytest
pytestmark = pytest.mark.review_required
{marker}
def test_behavior():
    Path("executed").write_text("yes")
    assert 2 + 2 == 4
"""
    result = run_review_case(source, *(["--allow-unreviewed"] if override else []))
    pending = "True" not in marker
    assert result.returncode == (1 if pending and not override else 0), result.stdout
    assert (tmp_path / "executed").read_text() == "yes"
    assert ("Pending human review" in result.stdout) is pending
    if override and pending:
        assert "No approvals changed" in result.stdout


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("override", [False, True])
def test_real_failure_is_preserved_with_pending_review(run_review_case, override):
    result = run_review_case(
        """
import pytest
@pytest.mark.reviewed(False)
def test_behavior():
    assert False, "REAL BEHAVIOR FAILURE"
""",
        *(["--allow-unreviewed"] if override else []),
    )
    assert result.returncode == 1
    assert "REAL BEHAVIOR FAILURE" in result.stdout
    assert "Pending human review" in result.stdout


@pytest.mark.reviewed(False)
@pytest.mark.parametrize(
    "marker",
    [
        '@pytest.mark.reviewed("False")',
        "@pytest.mark.reviewed()",
        "@pytest.mark.reviewed(True)\n@pytest.mark.reviewed(False)",
        "@pytest.mark.reviewed(approved=True)",
    ],
)
def test_malformed_review_markers_are_not_bypassed(run_review_case, marker):
    result = run_review_case(
        f"""
import pytest
{marker}
def test_behavior():
    pass
""",
        "--allow-unreviewed",
    )
    assert result.returncode == 4
    assert "use exactly one per-test" in result.stderr


@pytest.mark.reviewed(False)
def test_parameterized_reviews_and_selection(run_review_case):
    source = """
import pytest
@pytest.mark.reviewed(False)
@pytest.mark.parametrize("value", [1, 2])
def test_pending(value):
    assert value > 0
@pytest.mark.reviewed(True)
def test_approved():
    pass
"""
    result = run_review_case(source)
    assert result.returncode == 1
    assert "2 failed, 1 passed" in result.stdout
    result = run_review_case(source, "-k", "approved")
    assert result.returncode == 0
    assert "Pending human review" not in result.stdout


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("override", [False, True])
def test_skipping_does_not_approve_pending_review(run_review_case, override):
    result = run_review_case(
        """
import pytest
@pytest.mark.reviewed(False)
@pytest.mark.skip(reason="unavailable")
def test_behavior():
    pass
""",
        *(["--allow-unreviewed"] if override else []),
    )
    assert result.returncode == (0 if override else 1)
    assert "Pending human review" in result.stdout


@pytest.mark.reviewed(False)
def test_unmigrated_modules_are_not_assumed_reviewed_or_blocked(run_review_case):
    result = run_review_case("""
def test_existing():
    assert True
""")
    assert result.returncode == 0
    assert "Pending human review" not in result.stdout
