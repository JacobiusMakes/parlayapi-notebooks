# Odds Reality Check: media brief

A betting-data answer can look convincing while referring to the wrong game, a different market, or a quote whose status is unknown.

**Odds Reality Check** is an open, fictional challenge from the ParlayAPI team. Its twelve cases ask whether a specific claim is supported, contradicted, or not established by the supplied evidence. A browser exercise and local scorer let developers and readers inspect mistakes and reveal explanations.

[Get the challenge and scoring instructions](../labs/odds-reality-check/README.md).

## The story

Sports-data integration involves more than fetching a number. A standard home-run market and an alternate threshold describe different contracts. Two games between the same teams may be a doubleheader. A quote missing from a partial update has not necessarily been withdrawn.

These details matter when developers build comparison tools and when AI assistants interpret the results. The challenge turns those distinctions into concrete examples a reader can inspect. It also includes cases where the evidence does support a conclusion: refusing every question is not the objective.

Three possible editorial angles:

- **Sports technology:** Can a betting app distinguish a missing quote from a withdrawn one?
- **AI and developer tools:** An HTTP success and valid JSON do not establish that an agent's conclusion follows.
- **Data literacy:** Same teams, different game. Same player, different threshold. How a plausible comparison changes when one detail changes.

## What is available

- Twelve fictional cases with an explicit claim and the evidence needed to evaluate it.
- A separate answer key with reasons, so readers can challenge the interpretation.
- A browser quiz with twelve evidence cards, explicit scoring, explanations and a downloadable result.
- A local Python scoring tool and an answer template.
- Scores that include class-level results and unsupported positive claims, with missing answers accounted for.
- Explicitly synthetic baseline submissions that illustrate the scoring method.
- Reused comparison logic from the existing [interactive data-quality lesson](../labs/odds-comparability/README.md).

The question export and scoring path needs no ParlayAPI account, API key or external model service. The code and fictional fixtures can be inspected independently. Consult the challenge README for exact runtime and optional reference-check dependencies.

## What has not been measured

This is a small educational challenge, not a held-out research benchmark, a scientific estimate of model reliability, or a ranking of commercial AI products. Public cases and answers can be memorized. A perfect result does not certify a betting app, an API, production coverage, settlement correctness or profitability.

We have not run a comparative study of named AI providers. The included baselines are scripted examples, not observed model results. The cases contain no actual customer messages, sportsbook feed or historical odds archive.

## Reproduce or cover it

Use the version of the dataset you tested and retain its hash, the full response and the scorer output. If evaluating an AI system, record the model/version, full prompt, tool access, date and number of attempts. Do not present a selectively chosen run as general performance. Keep API keys and private data out of published examples.

The MIT licence covers this repository's software and fictional materials. It does not grant rights to ParlayAPI's live data. API data access and use remain governed separately.

## About ParlayAPI

ParlayAPI provides sports odds and player-prop data through API and agent-oriented tools. Coverage depends on the sport, sportsbook, market and delivery route. Its public notebooks teach private analysis and data handling, with fictional examples available before connecting an account.

[Product documentation](https://parlay-api.com/docs) · [Official MCP repository](https://github.com/JacobiusMakes/parlay-api-mcp) · [Current plans](https://parlay-api.com/pricing)

Media inquiries: **outreach@parlay-api.com**. Customer support: **support@parlay-api.com**.

Astra is the AI assistant helping the ParlayAPI team create and review this material and coordinate outreach. A human founder interview can be discussed separately. No founder quotation or interview booking is supplied by this brief.
