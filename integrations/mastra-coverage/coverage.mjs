export const SPORT = 'soccer_epl';
export const BOOKS = ['pinnacle', 'draftkings', 'fanduel'];
const MAX_BYTES = 2 * 1024 * 1024;

function empty(status, synthetic) {
  return { status, synthetic, scope: SPORT, groups: [], missingRequestedBooks: [...BOOKS], groupsWithoutH2h: 0, skippedDerivedGroups: 0 };
}

export function summarizeGroups(groups, synthetic, requestedBooks = BOOKS) {
  const totals = new Map();
  for (const group of groups) {
    const counts = totals.get(group.bookmaker) ?? { bookmaker: group.bookmaker, complete: 0, incomplete: 0 };
    const roles = group.roles;
    const complete = group.valid && roles.length === 3 && new Set(roles).size === 3
      && ['home', 'away', 'draw'].every(role => roles.includes(role));
    counts[complete ? 'complete' : 'incomplete'] += 1;
    totals.set(group.bookmaker, counts);
  }
  return { status: groups.length ? 'observed' : 'empty', synthetic, scope: SPORT, groups: [...totals.values()],
    missingRequestedBooks: requestedBooks.filter(book => !totals.has(book)), groupsWithoutH2h: 0, skippedDerivedGroups: 0 };
}

export function syntheticSummary() {
  // Fictional presence metadata only. There are no sample odds or API observations.
  return summarizeGroups([
    { bookmaker: 'synthetic_book_a', roles: ['home', 'away', 'draw'], valid: true },
    { bookmaker: 'synthetic_book_a', roles: ['home', 'away'], valid: true },
    { bookmaker: 'synthetic_book_b', roles: ['home', 'away', 'draw'], valid: true },
    { bookmaker: 'synthetic_book_b', roles: ['home', 'draw', 'draw'], valid: true },
  ], true, ['synthetic_book_a', 'synthetic_book_b']);
}

export function summarizePayload(payload) {
  if (!Array.isArray(payload) || payload.length > 500) throw new Error('Invalid payload');
  const groups = [];
  let groupsWithoutH2h = 0;
  let skippedDerivedGroups = 0;
  const eventIds = new Set();
  for (const event of payload) {
    if (!event || event.sport_key !== SPORT || typeof event.id !== 'string' || !event.id
      || eventIds.has(event.id) || typeof event.home_team !== 'string' || !event.home_team
      || typeof event.away_team !== 'string' || !event.away_team
      || event.home_team === event.away_team || !Array.isArray(event.bookmakers)) throw new Error('Invalid event');
    eventIds.add(event.id);
    const books = new Set();
    for (const book of event.bookmakers) {
      if (!book || !BOOKS.includes(book.key) || books.has(book.key) || !Array.isArray(book.markets)) throw new Error('Invalid bookmaker');
      books.add(book.key);
      const markets = book.markets.filter(market => market?.key === 'h2h');
      if (/corners|bookings|cards/i.test(event.home_team + ' ' + event.away_team)) {
        skippedDerivedGroups += 1;
        continue;
      }
      if (!markets.length) {
        groupsWithoutH2h += 1;
        continue;
      }
      const market = markets[0];
      if (!Array.isArray(market.outcomes)) throw new Error('Invalid outcomes');
      const roles = [];
      let valid = markets.length === 1;
      for (const outcome of market.outcomes) {
        if (!outcome || typeof outcome.name !== 'string') throw new Error('Invalid outcome');
        const role = outcome.name === event.home_team ? 'home'
          : outcome.name === event.away_team ? 'away'
            : outcome.name.toLowerCase() === 'draw' ? 'draw' : 'unknown';
        roles.push(role);
        valid &&= Number.isFinite(outcome.price) && outcome.price > 1 && outcome.point == null;
      }
      groups.push({ bookmaker: book.key, roles, valid });
    }
  }
  return { ...summarizeGroups(groups, false), groupsWithoutH2h, skippedDerivedGroups };
}

export async function privateSummary(live = false, fetcher = fetch, key = process.env.PARLAY_API_KEY) {
  if (!live) return syntheticSummary();
  if (typeof key !== 'string' || !key.trim() || /[\r\n]/.test(key)) return empty('error', false);
  let reader;
  try {
    const url = new URL(`https://parlay-api.com/v1/sports/${SPORT}/odds`);
    url.search = new URLSearchParams({ regions: 'global', bookmakers: BOOKS.join(','), markets: 'h2h', oddsFormat: 'decimal', include: 'slim' });
    const response = await fetcher(url, {
      headers: { 'X-API-Key': key }, redirect: 'error', signal: AbortSignal.timeout(15000),
    });
    reader = response.body?.getReader();
    if (response.status !== 200 || !reader) return empty('error', false);
    const hasMore = response.headers.get('x-result-has-more');
    const truncated = response.headers.get('x-result-truncated');
    if ((hasMore !== null && hasMore !== 'false') || (truncated !== null && truncated !== 'false')) return empty('incomplete_response', false);
    if (Number(response.headers.get('content-length')) > MAX_BYTES) return empty('error', false);
    const chunks = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) return empty('error', false);
      chunks.push(value);
    }
    return summarizePayload(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  } catch {
    return empty('error', false);
  } finally {
    try { await reader?.cancel(); } catch { /* No transport details leave the private boundary. */ }
  }
}

export function gateSummary(summary) {
  const complete = summary.groups.reduce((sum, group) => sum + group.complete, 0);
  const incomplete = summary.groups.reduce((sum, group) => sum + group.incomplete, 0);
  const decision = summary.status !== 'observed' ? 'stop'
    : incomplete > 0 || summary.groupsWithoutH2h > 0 || summary.missingRequestedBooks.length > 0
      ? 'review_incomplete_groups' : complete > 0 ? 'supplied_shapes_complete' : 'stop';
  return { ...summary, decision, complete, incomplete, shapeCheckPassed: decision === 'supplied_shapes_complete' };
}
