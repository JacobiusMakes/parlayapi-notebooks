import copy
from datetime import datetime, timezone
import io
import json
import unittest
from unittest.mock import patch

import ufc_methods as recipe

NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


class CoverageTests(unittest.TestCase):
    def test_distinct_methods_without_price_output(self):
        summary = recipe.summarize(recipe.demo(NOW), now=NOW)
        self.assertEqual(len(summary), 3)
        self.assertEqual(
            {r["method"] for r in summary},
            {
                "method_of_victory_ko_tko",
                "method_of_victory_ko_tko_dq",
                "method_of_victory_submission",
            },
        )
        self.assertTrue(all(r["oldest_observation_seconds"] == 12 for r in summary))
        self.assertNotIn("price", json.dumps(summary))

    def test_shape_identity_and_clock_failures(self):
        for payload in ({"data": []}, [None]):
            with self.assertRaises(ValueError):
                recipe.summarize(payload, now=NOW)
        for field, value in [
            ("last_observed", "bad"),
            ("last_observed", "2026-09-09T11:59:00"),
            ("last_observed", "2027-01-01T00:00:00Z"),
            ("commence_time", None),
            ("player", ""),
            ("player", "  "),
            ("home_team", None),
            ("game_date", "2020-01-01"),
        ]:
            payload = recipe.demo(NOW)
            payload[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                recipe.summarize(payload, now=NOW)

    def test_label_mismatches_are_counted_without_alias_guessing(self):
        for player, home in [
            ("Edgar Chairez", "Édgar Cháirez"),
            ("Unrelated Fighter", "Example Fighter A"),
        ]:
            payload = recipe.demo(NOW)
            payload[0]["player"] = player
            payload[0]["home_team"] = home
            untouched = copy.deepcopy(payload)
            summary = recipe.summarize(payload, now=NOW)
            flagged = next(r for r in summary if r["bookmaker"] == "fanduel")
            self.assertEqual(flagged["selections"], 1)
            self.assertEqual(flagged["fighter_label_mismatches"], 1)
            self.assertEqual(payload, untouched)
            self.assertEqual(recipe.summarize(payload[:1], now=NOW, player=home), [])

    def test_duplicates_and_exact_local_filters(self):
        payload = recipe.demo(NOW)
        with self.assertRaises(ValueError):
            recipe.summarize(payload + [copy.deepcopy(payload[0])], now=NOW)
        self.assertEqual(
            recipe.summarize(payload, now=NOW, player="example fighter a"), []
        )
        self.assertEqual(recipe.summarize(payload, now=NOW, day=NOW.date()), [])
        self.assertEqual(
            len(recipe.summarize(payload, now=NOW, player="Example Fighter A")), 3
        )

    def test_truncated_unknown_header_and_body_bound(self):
        class Response:
            status = 200

            def __init__(self, more, body):
                self.more, self.body = more, io.BytesIO(body)

            def getheader(self, key):
                return self.more if key == "x-result-has-more" else "application/json"

            def read1(self, size):
                return self.body.read(size)

        class Connection:
            sock = None

            def __init__(self, response):
                self.response, self.calls, self.closed = response, [], False

            def request(self, *args, **kwargs):
                self.calls.append((args, kwargs))

            def getresponse(self):
                return self.response

            def close(self):
                self.closed = True

        for more, body in [
            ("true", b"[]"),
            (None, b"[]"),
            ("false", b"x" * (recipe.MAX_BYTES + 1)),
        ]:
            connection = Connection(Response(more, body))
            with (
                patch.object(
                    recipe.http.client, "HTTPSConnection", return_value=connection
                ),
                self.assertRaises(ValueError),
            ):
                recipe.fetch("private-test-key")
            self.assertTrue(connection.closed)
            self.assertEqual(len(connection.calls), 1)
        connection = Connection(Response("false", b"[]"))
        with patch.object(
            recipe.http.client, "HTTPSConnection", return_value=connection
        ) as factory:
            self.assertEqual(recipe.fetch("private-test-key"), [])
            factory.assert_called_once_with("parlay-api.com", timeout=15)
        args, kwargs = connection.calls[0]
        self.assertNotIn("private-test-key", args[1])
        self.assertEqual(kwargs["headers"]["X-API-Key"], "private-test-key")


if __name__ == "__main__":
    unittest.main()
