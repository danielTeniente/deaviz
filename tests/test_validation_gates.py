"""Verify that the lint baseline fails closed for changed and new findings."""

import pytest

from scripts.check_lint import check

FINDING = {
    "path": "views/example.py",
    "code": "F821",
    "message": "Undefined name",
    "source": "missing()",
}


def test_exact_existing_finding_is_allowed():
    check([FINDING], [FINDING])


@pytest.mark.parametrize(
    "actual,baseline",
    [
        ([FINDING], []),
        ([], [FINDING]),
        ([FINDING, FINDING], [FINDING]),
        ([dict(FINDING, source="another_missing()")], [FINDING]),
    ],
)
def test_new_changed_duplicate_or_fixed_findings_require_action(actual, baseline):
    with pytest.raises(ValueError):
        check(actual, baseline)
