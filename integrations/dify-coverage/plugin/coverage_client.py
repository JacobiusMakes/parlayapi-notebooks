"""Bounded own-key diagnostics; no source rows or credentials leave this module."""

from collections import Counter
from datetime import datetime, timezone
import json
import math
import re
import time
import httpx

BASE = "https://parlay-api.com"
MAX_BYTES = 1_000_000
LIMIT = 500
SLUG = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


class CoverageError(Exception):
    pass


def request_json(path, key, params=None):
    if (
        not isinstance(key, str)
        or not key.strip()
        or len(key) > 512
        or any(ord(c) < 33 or ord(c) > 126 for c in key)
    ):
        raise CoverageError("A valid ParlayAPI key is required for live mode.")
    try:
        with httpx.Client(
            timeout=10.0, follow_redirects=False, trust_env=False
        ) as client:
            with client.stream(
                "GET",
                BASE + path,
                params=params,
                headers={"X-API-Key": key, "Accept-Encoding": "identity"},
            ) as response:
                if response.status_code in (401, 403):
                    raise CoverageError(
                        "API access was denied. Check your key and account access."
                    )
                if response.status_code == 429:
                    raise CoverageError(
                        "API rate limit reached. Retry later; no automatic retry was sent."
                    )
                if response.status_code != 200:
                    raise CoverageError(
                        "The API request did not succeed. No coverage conclusion is available."
                    )
                if (
                    response.headers.get("content-encoding", "identity").lower()
                    != "identity"
                ):
                    raise CoverageError(
                        "Unexpected response encoding. No coverage conclusion is available."
                    )
                body = bytearray()
                deadline = time.monotonic() + 10
                for chunk in response.iter_bytes():
                    if (
                        time.monotonic() > deadline
                        or len(body) + len(chunk) > MAX_BYTES
                    ):
                        raise CoverageError(
                            "The bounded response limit was reached. No coverage conclusion is available."
                        )
                    body.extend(chunk)
                return json.loads(body), dict(response.headers)
    except CoverageError:
        raise
    except (httpx.HTTPError, ValueError, TypeError):
        raise CoverageError(
            "The API response could not be read. No coverage conclusion is available."
        ) from None


def validate_key(key):
    body, _ = request_json("/v1/meta/api-key-check", key)
    if not isinstance(body, dict) or body.get("valid") is not True:
        raise CoverageError(
            "The API key is unavailable, inactive or has no credit headroom."
        )


def summarize(rows, headers, sport, book, market, now=None, synthetic=False):
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise CoverageError(
            "Unexpected API response shape; no coverage conclusion is available."
        )
    now = now or datetime.now(timezone.utc)
    counts, observed_ages, write_ages = Counter(), [], []
    identities = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("bookmaker") != book
            or row.get("sport_key") != sport
        ):
            raise CoverageError(
                "Response did not match the requested sport and bookmaker."
            )
        key = row.get("market_key")
        if (
            not isinstance(key, str)
            or not SLUG.fullmatch(key)
            or not (
                key == market
                or (
                    market == "method_of_victory"
                    and key.startswith("method_of_victory_")
                )
            )
        ):
            raise CoverageError("Response did not match the requested market.")
        identity = tuple(
            row.get(k) for k in ("event_id", "player", "market_key", "line")
        )
        if not isinstance(row.get("event_id"), str) or not isinstance(
            row.get("player"), str
        ):
            raise CoverageError("Response is missing selection identity.")
        try:
            if identity in identities:
                raise CoverageError(
                    "Duplicate selections found; no complete coverage conclusion is available."
                )
            identities.add(identity)
        except TypeError:
            raise CoverageError("Unexpected selection identity.") from None
        counts[key] += 1
        for field, ages in (
            ("last_observed", observed_ages),
            ("last_update", write_ages),
        ):
            value = row.get(field)
            if not isinstance(value, str):
                continue
            try:
                instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if instant.tzinfo is None:
                    continue
                age = (now - instant).total_seconds()
                if math.isfinite(age) and age >= -5:
                    ages.append(round(max(0, age), 1))
            except ValueError:
                continue
    has_more = headers.get("x-result-has-more")
    truncated = headers.get("x-result-truncated") not in (None, "false")
    incomplete = truncated or has_more != "false"
    status = "observed" if rows else "not_observed"
    if incomplete:
        status = "partial" if rows else "inconclusive"
    return {
        "synthetic": synthetic,
        "status": status,
        "sport": sport,
        "bookmaker": book,
        "requested_market": market,
        "observed_selection_count": len(rows),
        "observed_market_counts": dict(counts),
        "response_incomplete_or_unknown": incomplete,
        "observation_age_seconds": {
            "known_rows": len(observed_ages),
            "oldest": max(observed_ages, default=None),
        },
        "write_age_seconds": {
            "known_rows": len(write_ages),
            "oldest": max(write_ages, default=None),
        },
        "notes": [
            "A bounded observation is not proof of full sportsbook coverage or future availability.",
            "Observation time does not establish when a price changed.",
            "KO/TKO and KO/TKO/DQ have different settlement scope.",
            "No live prices, participant names or source rows are returned.",
        ],
    }


def check_coverage(parameters, key):
    mode = parameters.get("mode", "demo")
    if mode == "demo":
        now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        rows = [
            dict(
                event_id="fictional-event",
                player="Fictional Fighter",
                line=None,
                bookmaker="fanduel",
                sport_key="mma_mixed_martial_arts",
                market_key="method_of_victory_ko_tko",
                last_observed="2030-01-01T00:00:00Z",
            )
        ]
        return summarize(
            rows,
            {"x-result-has-more": "false"},
            "mma_mixed_martial_arts",
            "fanduel",
            "method_of_victory",
            now,
            True,
        )
    if mode != "live":
        raise CoverageError("Mode must be demo or live.")
    sport, book, market = (parameters.get(k) for k in ("sport", "bookmaker", "market"))
    if not all(isinstance(v, str) and SLUG.fullmatch(v) for v in (sport, book, market)):
        raise CoverageError(
            "Sport, bookmaker and market must be individual lowercase API keys."
        )
    rows, headers = request_json(
        "/v1/sports/" + sport + "/props",
        key,
        {
            "bookmakers": book,
            "markets": market,
            "oddsFormat": "american",
            "limit": LIMIT,
        },
    )
    return summarize(rows, headers, sport, book, market)
