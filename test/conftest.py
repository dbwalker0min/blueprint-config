"""Human review tracking, initially required only by opted-in test modules."""

import pytest

_PENDING = pytest.StashKey[dict[str, str]]()


def pytest_addoption(parser):
    parser.addoption(
        "--allow-unreviewed",
        action="store_true",
        default=False,
        help="Run behavioral checks without failing for pending human review.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "reviewed(approved): per-test human approval, exactly True or False"
    )
    config.addinivalue_line(
        "markers", "review_required: require a reviewed marker on every test"
    )
    config.stash[_PENDING] = {}


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        markers = list(item.iter_markers("reviewed"))
        required = item.get_closest_marker("review_required") is not None
        if not markers:
            if required:
                config.stash[_PENDING][item.nodeid] = "missing @pytest.mark.reviewed"
            continue
        if (
            len(markers) != 1
            or markers[0] not in item.own_markers
            or len(markers[0].args) != 1
            or type(markers[0].args[0]) is not bool
            or markers[0].kwargs
        ):
            raise pytest.UsageError(
                f"{item.nodeid}: use exactly one per-test "
                "@pytest.mark.reviewed(True or False)"
            )
        if not markers[0].args[0]:
            config.stash[_PENDING][item.nodeid] = "@pytest.mark.reviewed(False)"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    reason = item.config.stash[_PENDING].get(item.nodeid)
    if reason and report.when == "call":
        message = f"Human review required: {reason}. Only the user approves review."
        report.sections.append(("Human review", message))
        # Preserve genuine failures/skips and always run the test body first.
        if report.passed and not item.config.getoption("--allow-unreviewed"):
            report.outcome = "failed"
            report.longrepr = message
    return report


def pytest_sessionfinish(session, exitstatus):
    # Selected skipped/xfail tests must not silently clear the review requirement.
    if (
        session.config.stash[_PENDING]
        and not session.config.getoption("--allow-unreviewed")
        and exitstatus == pytest.ExitCode.OK
    ):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    pending = config.stash[_PENDING]
    if not pending:
        return
    terminalreporter.section("Pending human review")
    for nodeid, reason in pending.items():
        terminalreporter.write_line(f"{nodeid}: {reason}")
    if config.getoption("--allow-unreviewed"):
        terminalreporter.write_line(
            "Review requirement bypassed; behavioral failures still fail. "
            "No approvals changed."
        )
    else:
        terminalreporter.write_line(
            "Review the tests and change their markers to reviewed(True). "
            "--allow-unreviewed bypasses only this review requirement."
        )
