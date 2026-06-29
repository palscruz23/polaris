from collections.abc import Sequence

from app.evaluations.prod_cases import (
    PROD_CASES,
    PROD_SUITE_DESCRIPTION,
    PROD_SUITE_NAME,
)
from app.evaluations.smoke_cases import (
    SMOKE_CASES,
    SMOKE_SUITE_DESCRIPTION,
    SMOKE_SUITE_NAME,
)
from app.services.evaluation_service import EvalCaseDefinition


BUILT_IN_SUITES: dict[
    str,
    tuple[str, Sequence[EvalCaseDefinition]],
] = {
    SMOKE_SUITE_NAME: (SMOKE_SUITE_DESCRIPTION, SMOKE_CASES),
    PROD_SUITE_NAME: (PROD_SUITE_DESCRIPTION, PROD_CASES),
}

NIGHTLY_SUITE_NAMES = (SMOKE_SUITE_NAME, PROD_SUITE_NAME)
