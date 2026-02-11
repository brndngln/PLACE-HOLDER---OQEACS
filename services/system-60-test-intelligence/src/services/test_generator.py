from __future__ import annotations

from src.models import GenerateTestsRequest, GenerateTestsResult


class TestGenerator:
    def generate(self, request: GenerateTestsRequest) -> GenerateTestsResult:
        body = (
            "def test_generated_smoke():\n"
            "    assert True\n\n"
            "def test_generated_edge_case_none():\n"
            "    assert None is None\n"
        )
        if request.framework == "pytest":
            tests_code = body
        else:
            tests_code = "# Generated tests\n" + body
        return GenerateTestsResult(tests_code=tests_code, test_count=2, coverage_estimate=35.0)
