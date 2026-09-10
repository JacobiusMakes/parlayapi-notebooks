from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from coverage_client import CoverageError, validate_key


class ParlayAPIProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        key = credentials.get("api_key")
        if not key:
            return  # Synthetic demo requires no credential and performs no request.
        try:
            validate_key(key)
        except CoverageError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from None
