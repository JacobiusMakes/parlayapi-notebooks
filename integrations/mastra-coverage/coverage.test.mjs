import assert from 'node:assert/strict';
import test from 'node:test';
import { BOOKS, gateSummary, privateSummary, summarizePayload } from './coverage.mjs';
import { coverageWorkflow } from './workflow.mjs';

function fictionalPayload() {
  // Validator-only numeric sentinels, never an illustrative market or demo output.
  return [{ id: 'synthetic-event', sport_key: 'soccer_epl', home_team: 'Fictional Home', away_team: 'Fictional Away',
    bookmakers: [{ key: 'pinnacle', markets: [{ key: 'h2h', outcomes: [
      { name: 'Fictional Home', price: 2 }, { name: 'Fictional Away', price: 2 }, { name: 'Draw', price: 2 },
    ] }] }] }];
}

test('real Mastra runtime: offline ignores credentials and network, returns only aggregate metadata', async () => {
  const previousFetch = globalThis.fetch;
  const previousKey = process.env.PARLAY_API_KEY;
  globalThis.fetch = () => { throw new Error('Network forbidden'); };
  process.env.PARLAY_API_KEY = 'secret-sentinel';
  try {
    const run = await coverageWorkflow.createRun();
    const result = await run.start({ inputData: {} });
    assert.equal(result.status, 'success');
    assert.equal(result.result.synthetic, true);
    assert.equal(result.result.complete, 2);
    assert.equal(result.result.incomplete, 2);
    assert.equal(result.result.shapeCheckPassed, false);
    assert.doesNotMatch(JSON.stringify(result), /secret-sentinel|price|Fictional Home/);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousKey === undefined) delete process.env.PARLAY_API_KEY;
    else process.env.PARLAY_API_KEY = previousKey;
  }
});

test('complete three-way supplied group passes without exposing names, IDs or prices', () => {
  const summary = gateSummary(summarizePayload(fictionalPayload()));
  assert.equal(summary.complete, 1);
  assert.equal(summary.shapeCheckPassed, false);
  assert.deepEqual(summary.missingRequestedBooks, ["draftkings", "fanduel"]);
  assert.doesNotMatch(JSON.stringify(summary), /synthetic-event|Fictional|price/);
});

for (const [label, mutate] of [
  ['missing Draw', outcomes => outcomes.pop()],
  ['null Draw price', outcomes => { outcomes[2].price = null; }],
  ['string price', outcomes => { outcomes[2].price = '2'; }],
  ['nonfinite price', outcomes => { outcomes[2].price = Infinity; }],
  ['invalid decimal', outcomes => { outcomes[2].price = 1; }],
  ['duplicate outcome', outcomes => outcomes.push({ ...outcomes[2] })],
  ['unrecognized outcome', outcomes => { outcomes[2].name = 'Tie-ish'; }],
  ['spread point', outcomes => { outcomes[0].point = 0; }],
]) {
  test(`${label} prevents downstream processing`, () => {
    const payload = fictionalPayload();
    mutate(payload[0].bookmakers[0].markets[0].outcomes);
    const summary = gateSummary(summarizePayload(payload));
    assert.equal(summary.complete, 0);
    assert.equal(summary.incomplete, 1);
    assert.equal(summary.shapeCheckPassed, false);
  });
}

test('duplicate moneyline markets cannot count the first complete one as safe', () => {
  const payload = fictionalPayload();
  payload[0].bookmakers[0].markets.push(payload[0].bookmakers[0].markets[0]);
  assert.equal(gateSummary(summarizePayload(payload)).shapeCheckPassed, false);
});

test('shape check requires every requested book and fails when a supplied book lacks h2h', () => {
  const payload = fictionalPayload();
  const book = payload[0].bookmakers[0];
  payload[0].bookmakers = BOOKS.map(key => ({ ...structuredClone(book), key }));
  assert.equal(gateSummary(summarizePayload(payload)).shapeCheckPassed, true);
  payload[0].bookmakers[1].markets = [];
  const summary = gateSummary(summarizePayload(payload));
  assert.equal(summary.shapeCheckPassed, false);
  assert.equal(summary.groupsWithoutH2h, 1);
  assert.deepEqual(summary.missingRequestedBooks, ['draftkings']);
});

test('wrong sport, unknown book and duplicate event fail closed', () => {
  for (const mutate of [
    p => { p[0].sport_key = 'basketball_nba'; },
    p => { p[0].bookmakers[0].key = 'arbitrary private text'; },
    p => p.push(p[0]),
  ]) {
    const payload = fictionalPayload();
    mutate(payload);
    assert.throws(() => summarizePayload(payload));
  }
});

test('empty scoped response stops, without claiming absent sportsbook coverage', () => {
  assert.equal(gateSummary(summarizePayload([])).decision, 'stop');
});

test('derived team-label groups are skipped separately, not called missing outcomes', () => {
  const payload = fictionalPayload();
  payload[0].home_team += ' Corners';
  const summary = gateSummary(summarizePayload(payload));
  assert.equal(summary.skippedDerivedGroups, 1);
  assert.equal(summary.complete, 0);
  assert.equal(summary.incomplete, 0);
  assert.equal(summary.decision, 'stop');
  assert.equal(summary.shapeCheckPassed, false);
});

test('explicit live uses one fixed-origin scoped request and strips private data before Mastra', async () => {
  let calls = 0;
  const transport = async (url, options) => {
    calls += 1;
    assert.equal(url.origin, 'https://parlay-api.com');
    assert.equal(url.pathname, '/v1/sports/soccer_epl/odds');
    assert.equal(url.searchParams.get('bookmakers'), BOOKS.join(','));
    assert.equal(url.searchParams.get('oddsFormat'), 'decimal');
    assert.equal(url.searchParams.get('regions'), 'global');
    assert.equal(options.headers['X-API-Key'], 'secret-sentinel');
    assert.equal(options.redirect, 'error');
    assert.ok(options.signal instanceof AbortSignal);
    return Response.json(fictionalPayload());
  };
  const previousFetch = globalThis.fetch;
  const previousKey = process.env.PARLAY_API_KEY;
  globalThis.fetch = transport;
  process.env.PARLAY_API_KEY = 'secret-sentinel';
  try {
    const result = await (await coverageWorkflow.createRun()).start({ inputData: { live: true } });
    assert.equal(result.status, 'success');
    assert.equal(result.result.shapeCheckPassed, false);
    assert.deepEqual(result.result.missingRequestedBooks, ["draftkings", "fanduel"]);
    assert.equal(result.result.synthetic, false);
    assert.equal(calls, 1);
    assert.doesNotMatch(JSON.stringify(result), /secret-sentinel|Fictional|synthetic-event|price/);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousKey === undefined) delete process.env.PARLAY_API_KEY;
    else process.env.PARLAY_API_KEY = previousKey;
  }
});

test('missing key makes zero calls; transport errors remain fixed and do not retry', async () => {
  let calls = 0;
  const fail = async () => { calls += 1; throw new Error('secret-sentinel'); };
  assert.equal((await privateSummary(true, fail, '')).status, 'error');
  assert.equal(calls, 0);
  const result = await privateSummary(true, fail, 'test-only-key');
  assert.equal(result.status, 'error');
  assert.equal(calls, 1);
  assert.doesNotMatch(JSON.stringify(result), /secret-sentinel/);
});

test('partial, oversized, invalid and HTTP failure bodies are withheld', async () => {
  for (const response of [
    Response.json(fictionalPayload(), { headers: { 'x-result-has-more': 'true' } }),
    Response.json(fictionalPayload(), { headers: { 'x-result-truncated': 'unknown' } }),
    new Response('x'.repeat(2 * 1024 * 1024 + 1)),
    new Response('secret-sentinel'),
    new Response('secret-sentinel', { status: 429 }),
    Response.json(fictionalPayload(), { headers: { 'content-length': '3000000' } }),
  ]) {
    const result = await privateSummary(true, async () => response, 'test-only-key');
    assert.ok(['incomplete_response', 'error'].includes(result.status));
    assert.deepEqual(result.groups, []);
    assert.doesNotMatch(JSON.stringify(result), /secret-sentinel/);
    assert.equal(response.body.locked, true);
  }
});
