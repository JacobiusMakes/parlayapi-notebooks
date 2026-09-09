#!/usr/bin/env python3
"""Private, single-request UFC method coverage check. Standard library only."""

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import http.client
import json
import os
import sys
import time
from urllib.parse import urlencode

HOST = "parlay-api.com"
PATH = "/v1/sports/mma_mixed_martial_arts/props"
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 15
BOOKS = ("fanduel", "draftkings", "novig")
METHODS = {
    "method_of_victory_decision",
    "method_of_victory_submission",
    "method_of_victory_ko_tko",
    "method_of_victory_ko_tko_dq",
}


def fetch(key):
    if not key or any(ord(c) < 32 or ord(c) > 126 for c in key):
        raise ValueError("Set PARLAY_API_KEY to your own API key.")
    query = urlencode(
        dict(
            bookmakers=",".join(BOOKS),
            markets="method_of_victory",
            oddsFormat="american",
            limit=500,
        )
    )
    connection = http.client.HTTPSConnection(HOST, timeout=TIMEOUT)
    deadline = time.monotonic() + TIMEOUT
    try:
        connection.request(
            "GET",
            PATH + "?" + query,
            headers={"X-API-Key": key, "Accept": "application/json"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(
                f"API returned HTTP {response.status}; no redirect or retry attempted."
            )
        if (response.getheader("x-result-has-more") or "").lower() != "false":
            raise ValueError(
                "Incomplete or unconfirmed result set. Refusing coverage counts."
            )
        if "application/json" not in (response.getheader("Content-Type") or "").lower():
            raise ValueError("Expected JSON response.")
        chunks, total = [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("Response exceeded the 15-second read budget.")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("Response exceeds 2 MiB.")
            chunks.append(chunk)
        return json.loads(b"".join(chunks))
    finally:
        connection.close()


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Missing observation or commencement timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Malformed timestamp.") from None
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def summarize(payload, *, now=None, player=None, day=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, list):
        raise ValueError("Expected the API props list.")
    groups = defaultdict(list)
    mismatches = defaultdict(int)
    identities = set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Expected a prop object.")
        book, method = row.get("bookmaker"), row.get("market_key")
        if book not in BOOKS or method not in METHODS:
            raise ValueError("Unexpected bookmaker or method in scoped response.")
        if (book == "fanduel" and method == "method_of_victory_ko_tko_dq") or (
            book != "fanduel" and method == "method_of_victory_ko_tko"
        ):
            raise ValueError(
                "Unexpected method settlement semantics for this sportsbook."
            )
        fighter = row.get("player")
        if any(
            not isinstance(row.get(field), str) or not row[field].strip()
            for field in ("player", "home_team", "away_team")
        ):
            raise ValueError("Missing fighter or event label.")
        mismatch = fighter not in (row["home_team"], row["away_team"])
        kickoff = instant(row.get("commence_time"))
        observed = instant(row.get("last_observed"))
        if row.get("last_update_type") != "collector_observation":
            raise ValueError("Expected an explicit collector observation clock.")
        age = (now - observed).total_seconds()
        if age < 0:
            raise ValueError("Observation clock is ahead of this computer.")
        if row.get("game_date") != kickoff.date().isoformat():
            raise ValueError("Event date does not match commencement.")
        identity = (book, row.get("event_id"), fighter, method)
        if (
            not isinstance(row.get("event_id"), str)
            or not row["event_id"]
            or identity in identities
        ):
            raise ValueError("Missing or duplicate selection identity.")
        identities.add(identity)
        if (
            kickoff <= now
            or (player is not None and fighter != player)
            or (day is not None and kickoff.date() != day)
        ):
            continue
        groups[(book, method)].append(age)
        mismatches[(book, method)] += int(mismatch)
    return [
        {
            "bookmaker": book,
            "method": method,
            "selections": len(ages),
            "fighter_label_mismatches": mismatches[(book, method)],
            "youngest_observation_seconds": round(min(ages), 1),
            "oldest_observation_seconds": round(max(ages), 1),
        }
        for (book, method), ages in sorted(groups.items())
    ]


def demo(now):
    """Fabricated identities and clocks only. No live payload or quoted odds."""
    kickoff = (now + timedelta(days=3)).replace(microsecond=0)
    return [
        dict(
            bookmaker=book,
            market_key=method,
            player="Example Fighter A",
            home_team="Example Fighter A",
            away_team="Example Fighter B",
            event_id="synthetic-example",
            commence_time=kickoff.isoformat(),
            game_date=kickoff.date().isoformat(),
            last_observed=(now - timedelta(seconds=12)).isoformat(),
            last_update_type="collector_observation",
        )
        for book, method in [
            ("fanduel", "method_of_victory_ko_tko"),
            ("draftkings", "method_of_victory_ko_tko_dq"),
            ("novig", "method_of_victory_submission"),
        ]
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Synthetic local examples; no network or key used.",
    )
    parser.add_argument(
        "--player", help="Exact case-sensitive fighter name; filters locally."
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="UTC event date YYYY-MM-DD; filters locally.",
    )
    args = parser.parse_args()
    try:
        now = datetime.now(timezone.utc)
        payload = (
            demo(now) if args.demo else fetch(os.environ.get("PARLAY_API_KEY", ""))
        )
        summary = summarize(
            payload, now=datetime.now(timezone.utc), player=args.player, day=args.date
        )
        print(
            json.dumps(
                {
                    "mode": "synthetic demo"
                    if args.demo
                    else "private account request",
                    "coverage": summary,
                    "note": "Empty counts do not prove a sportsbook has no markets. Fighter label mismatches need manual identity checks before comparisons; labels are never normalized or merged.",
                },
                indent=2,
            )
        )
        return 0
    except (ValueError, OSError, http.client.HTTPException):
        # Never print server bodies, headers, keys, URLs, or exception text.
        print(
            "Coverage check failed. Check your key/access, connection, result completeness and response timestamps. No retry performed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
