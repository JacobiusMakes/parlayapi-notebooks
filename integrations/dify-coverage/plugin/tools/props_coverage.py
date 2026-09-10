from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from coverage_client import CoverageError, check_coverage


class PropsCoverageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        try:
            result = check_coverage(
                tool_parameters, self.runtime.credentials.get("api_key", "")
            )
        except CoverageError as exc:
            result = {
                "status": "error",
                "message": str(exc),
                "coverage_verified": False,
            }
        yield self.create_json_message(result)
