"""Rebuild synthetic fixtures using the existing lab; requires its marimo runtime."""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = "0.1.0"


def load_lab():
    path = HERE.parents[1] / "integrations/hamilton-comparability/lab_adapter.py"
    spec = importlib.util.spec_from_file_location("reality_check_lab_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_lab()


def build():
    lab = load_lab()
    questions, answers = [], []

    def add(qid, title, claim, evidence, label, explanation):
        questions.append({"id": qid, "title": title, "claim": claim, "evidence": evidence})
        answers.append({"id": qid, "label": label, "explanation": explanation})

    scope = {"book": "Fictional Book A", "event": "fictional-event-001", "market": "spread"}
    contract = (
        "Synthetic contract only: a complete snapshot authoritatively replaces all active quote IDs "
        "within exactly its declared scope at its source revision. A partial snapshot makes no "
        "statement about omitted IDs. Higher source revision wins regardless of arrival order. "
        "Snapshots attest only their own source revision. An omitted ID in a later partial "
        "snapshot has unknown current activity; do not carry earlier activity forward as proof. "
        "All captured observations are supplied, but their source coverage may be incomplete. "
        "Active means active in this synthetic contract state, not any real sportsbook."
    )
    add("ORC-01", "An empty partial page", "Quote q-17 is inactive at revision 102.",
        {"contract": contract, "previous": {"scope": scope, "source_revision": 101,
         "complete": True, "active_quote_ids": ["q-17"]},
         "next": {"scope": scope, "source_revision": 102, "complete": False, "active_quote_ids": []}},
        "insufficient_evidence", "The newer page is partial. Its omission neither proves withdrawal nor current activity.")
    add("ORC-02", "A complete replacement", "Quote q-17 is inactive in the local contract state at revision 102.",
        {"contract": contract, "previous": {"scope": scope, "source_revision": 101,
         "complete": True, "active_quote_ids": ["q-17"]},
         "next": {"scope": scope, "source_revision": 102, "complete": True, "active_quote_ids": []}},
        "supported", "Only the explicit complete, newer, same-scope replacement contract establishes this local absence. This is no claim about an actual API's withdrawal semantics.")
    event_contract = ("Synthetic event contract: quote q-17 starts inactive at revision 200. "
                      "restore sets it active and remove sets it inactive. The greatest source revision "
                      "determines current state; arrival order has no authority. All events through revision 202 are provided.")
    events = [{"operation": "restore", "source_revision": 202, "arrival": 1},
              {"operation": "remove", "source_revision": 201, "arrival": 2}]
    add("ORC-03", "A late removal", "After both arrivals, q-17 is inactive because the removal arrived last.",
        {"contract": event_contract, "events": events}, "contradicted",
        "Restore revision 202 wins over removal revision 201. Arrival order cannot overrule the newer source state.")
    add("ORC-04", "The heartbeat looks fresh", "Quote q-17 was verified by its source within the last two minutes.",
        {"fictional_now_minute": 720, "book": "Fictional Book A", "book_heartbeat_minute": 720,
         "quote": {"id": "q-17", "retrieved_minute": 720, "source_minute": None},
         "contract": "A book heartbeat only confirms its process is running. It does not certify any quote's age."},
        "insufficient_evidence", "A book heartbeat and retrieval clock do not supply a per-quote source verification time.")

    def comparison(scenario="matching"):
        left, candidates = lab.synthetic_records(scenario)
        return {"record_a": left, "candidates_b": candidates, "now_minute": 720,
                "maximum_age_minutes": 5, "maximum_source_gap_minutes": 2,
                "contract": "Use the existing odds-comparability teaching lab checks: event, market, named outcome, line for spread/total, period, settlement, valid American prices, source age and source-time gap. All required fields must be supplied. Passing these checks is only comparability under this toy contract."}

    evidence = comparison()
    evidence["context"] = "Fictional MLB-style doubleheader; these are not real MLB teams, fixtures or records."
    evidence["record_a"]["event"] = "North vs South, doubleheader game 1"
    evidence["candidates_b"][0]["event"] = "North vs South, doubleheader game 2"
    add("ORC-05", "Same teams, second game", "These two records refer to the same event.", evidence,
        "contradicted", "The same fictional teams play two games. Explicit game 1 and game 2 identities differ.")

    evidence = comparison()
    for record in (evidence["record_a"], evidence["candidates_b"][0]):
        record.update(market="total", outcome="Fictional Batter A home runs over", point=0.5,
                      period="full game", settlement="all plate appearances in the declared game")
    evidence["candidates_b"][0]["point"] = 1.5
    add("ORC-06", "A home-run alternate", "The over 0.5 and over 1.5 home-run records are the same betting contract.",
        evidence, "contradicted", "Over 0.5 and over 1.5 require different home-run counts. An alternate line is not the standard line.")
    add("ORC-07", "A different period", "The two records cover the same period.", comparison("period"),
        "contradicted", "Full game and first half are explicitly different periods.")
    add("ORC-08", "An unstated settlement rule", "These two records have matching settlement rules.",
        comparison("unknown_rules"), "insufficient_evidence",
        "One settlement rule is null. Missing information cannot establish either agreement or a known disagreement.")
    add("ORC-09", "Fetched now, source time absent", "Both records satisfy the five-minute source-age limit.",
        comparison("unknown_time"), "insufficient_evidence",
        "Record B lacks a source timestamp. Its current retrieval timestamp cannot establish source age.")
    add("ORC-10", "Matching declared contracts", "These records pass all supplied toy comparability checks.",
        comparison(), "supported", "All required contract fields match, both prices are valid, and supplied source ages and gap meet the stated limits. This does not establish profit or execution availability.")
    evidence = comparison()
    evidence["record_a"]["source_minute"] = 715
    evidence["candidates_b"][0]["source_minute"] = 717
    add("ORC-11", "At the inclusive limits", "Both records satisfy the five-minute age and two-minute source-gap limits.",
        evidence, "supported", "At minute 720, source ages are 5 and 3 minutes, and the gap is 2 minutes. The teaching lab accepts equality at both limits.")
    add("ORC-12", "The source order restores activity", "After both arrivals, q-17 is active in the local contract state.",
        {"contract": event_contract, "events": events}, "supported",
        "Source revision 202 is the greatest supplied revision and explicitly restores q-17. The late older removal cannot change that state.")

    return {
        "dataset_name": "Odds Reality Check", "dataset_version": VERSION, "synthetic_only": True,
        "notice": "All fixtures, books, athletes, events, clocks and contracts are fictional. No API calls, real sportsbook data, customer records, model results, profit claims or coverage certification. This is an open educational challenge, not a held-out scientific benchmark or vendor ranking.",
        "instructions": "For each claim, choose supported when the supplied evidence establishes it, contradicted when supplied evidence establishes its opposite, or insufficient_evidence when neither is established. Use only the explicit synthetic contract. Do not infer actual API or sportsbook guarantees. Questions are independent.",
        "allowed_labels": ["supported", "contradicted", "insufficient_evidence"], "questions": questions,
    }, {"dataset_version": VERSION, "answers": answers}


if __name__ == "__main__":
    questions, answers = build()
    for filename, payload in (("questions.json", questions), ("answer-key.json", answers)):
        (HERE / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
