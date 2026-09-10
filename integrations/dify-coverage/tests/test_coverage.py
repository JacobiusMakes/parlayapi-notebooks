from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import httpx
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))
import coverage_client as c
from provider.parlayapi import ParlayAPIProvider
from tools.props_coverage import PropsCoverageTool
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
ROW = dict(
    event_id="fictional",
    player="DO NOT RETURN THIS FIGHTER",
    line=None,
    sport_key="mma_mixed_martial_arts",
    bookmaker="fanduel",
    market_key="method_of_victory_ko_tko",
    over_price=123,
    under_price=None,
    last_observed="2029-12-31T23:59:50Z",
    last_update="2029-12-31T23:50:00Z",
)
PARAMS = dict(
    mode="live",
    sport="mma_mixed_martial_arts",
    bookmaker="fanduel",
    market="method_of_victory",
)


def mocked_http(monkeypatch, handler):
    original = httpx.Client
    seen = []

    def record(request):
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(
        c.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(record), **kwargs),
    )
    return seen


def test_actual_sdk_demo_never_calls_network(monkeypatch):
    monkeypatch.setattr(
        c, "request_json", lambda *a, **kw: pytest.fail("demo performed request")
    )
    message = list(PropsCoverageTool.from_credentials({}).invoke({"mode": "demo"}))[0]
    result = message.message.json_object
    assert result["synthetic"] is True and result["observed_selection_count"] == 1
    assert "Fictional Fighter" not in json.dumps(result)


def test_private_summary_does_not_return_odds_names_or_key():
    result = c.summarize(
        [ROW],
        {"x-result-has-more": "false"},
        PARAMS["sport"],
        PARAMS["bookmaker"],
        PARAMS["market"],
        NOW,
    )
    assert result["observation_age_seconds"]["oldest"] == 10
    assert result["write_age_seconds"]["oldest"] == 600
    assert result["observed_market_counts"] == {"method_of_victory_ko_tko": 1}
    text = json.dumps(result)
    assert ROW["player"] not in text and "over_price" not in text and "123" not in text


@pytest.mark.parametrize(
    "headers,rows,status",
    [
        ({}, [], "inconclusive"),
        ({"x-result-has-more": "false"}, [], "not_observed"),
        ({"x-result-has-more": "true"}, [ROW], "partial"),
        (
            {"x-result-has-more": "false", "x-result-truncated": "true"},
            [ROW],
            "partial",
        ),
    ],
)
def test_incomplete_never_becomes_absent_or_full(headers, rows, status):
    assert (
        c.summarize(
            rows, headers, PARAMS["sport"], PARAMS["bookmaker"], PARAMS["market"], NOW
        )["status"]
        == status
    )


@pytest.mark.parametrize(
    "change",
    [
        {"bookmaker": "draftkings"},
        {"sport_key": "baseball_mlb"},
        {"market_key": "method_of_victory_ko_tko_dq"},
    ],
)
def test_exact_filters_reject_other_semantics(change):
    row = dict(ROW, **change)
    with pytest.raises(c.CoverageError):
        c.summarize(
            [row], {}, PARAMS["sport"], "fanduel", "method_of_victory_ko_tko", NOW
        )


def test_duplicates_rejected():
    with pytest.raises(c.CoverageError):
        c.summarize([ROW, ROW], {}, PARAMS["sport"], "fanduel", PARAMS["market"], NOW)


@pytest.mark.parametrize(
    "value",
    [
        "../secret",
        "https://evil.test",
        "fanduel,draftkings",
        "x?apiKey=secret",
        "FANDUEL",
    ],
)
def test_url_injection_rejected_without_request(monkeypatch, value):
    monkeypatch.setattr(
        c, "request_json", lambda *a, **kw: pytest.fail("bad input sent")
    )
    with pytest.raises(c.CoverageError):
        c.check_coverage(dict(PARAMS, bookmaker=value), "secret")


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500])
def test_http_errors_are_redacted_and_not_retried(monkeypatch, status):
    seen = mocked_http(
        monkeypatch,
        lambda request: httpx.Response(
            status,
            json={"detail": "LEAK_KEY"},
            headers={"location": "https://evil.test"},
        ),
    )
    with pytest.raises(c.CoverageError) as exc:
        c.check_coverage(PARAMS, "LEAK_KEY")
    assert "LEAK_KEY" not in str(exc.value) and len(seen) == 1
    assert seen[0].url.host == "parlay-api.com"
    assert "LEAK_KEY" not in str(seen[0].url)
    assert seen[0].headers["X-API-Key"] == "LEAK_KEY"


def test_actual_sdk_live_tool_uses_safe_result(monkeypatch):
    mocked_http(
        monkeypatch,
        lambda request: httpx.Response(
            200, json=[ROW], headers={"x-result-has-more": "false"}
        ),
    )
    result = list(
        PropsCoverageTool.from_credentials({"api_key": "PRIVATE_KEY"}).invoke(PARAMS)
    )[0].message.json_object
    assert result["observed_selection_count"] == 1 and ROW["player"] not in json.dumps(
        result
    )


@pytest.mark.parametrize(
    "body,valid",
    [
        ({"valid": True}, True),
        ({"valid": False, "reason": "LEAK"}, False),
        ({"valid": "true"}, False),
    ],
)
def test_actual_provider_validation_requires_boolean_true(monkeypatch, body, valid):
    seen = mocked_http(monkeypatch, lambda request: httpx.Response(200, json=body))
    provider = ParlayAPIProvider()
    if valid:
        provider.validate_credentials({"api_key": "PRIVATE_KEY"})
    else:
        with pytest.raises(ToolProviderCredentialValidationError) as exc:
            provider.validate_credentials({"api_key": "PRIVATE_KEY"})
        assert "LEAK" not in str(exc.value)
    assert seen[0].url.path == "/v1/meta/api-key-check"


def test_provider_empty_key_permits_only_demo(monkeypatch):
    monkeypatch.setattr(c, "request_json", lambda *a, **kw: pytest.fail("request"))
    ParlayAPIProvider().validate_credentials({})


def test_byte_cap_rejects_response(monkeypatch):
    mocked_http(
        monkeypatch,
        lambda request: httpx.Response(200, content=b"x" * (c.MAX_BYTES + 1)),
    )
    with pytest.raises(c.CoverageError):
        c.check_coverage(PARAMS, "PRIVATE_KEY")


def test_schema_validates_with_real_sdk(monkeypatch):
    from dify_plugin.core.entities.plugin.setup import PluginConfiguration
    from dify_plugin.entities.tool import ToolConfiguration, ToolProviderConfiguration

    monkeypatch.chdir(Path(__file__).resolve().parents[1] / "plugin")
    PluginConfiguration.model_validate(
        yaml.safe_load(Path("manifest.yaml").read_text())
    )
    ToolConfiguration.model_validate(
        yaml.safe_load(Path("tools/props_coverage.yaml").read_text())
    )
    ToolProviderConfiguration.model_validate(
        yaml.safe_load(Path("provider/parlayapi.yaml").read_text())
    )


@pytest.mark.parametrize("value", ["unknown", "TRUE", "", "0"])
def test_malformed_truncation_is_inconclusive(value):
    result = c.summarize(
        [],
        {"x-result-has-more": "false", "x-result-truncated": value},
        PARAMS["sport"],
        PARAMS["bookmaker"],
        PARAMS["market"],
        NOW,
    )
    assert result["status"] == "inconclusive"
