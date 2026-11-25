"""Two kinds of evidence the keys need that are not economic series: seats in Congress, and polls that name a third candidate.

Seats (keys D01, D02, D03, D05, D06)
    Read from the public list of sitting members kept at github.com/unitedstates/congress-legislators, in the January a new
    Congress meets. The House count is of the voting members of the fifty states whose term began that January; the list
    is used only once at least 430 of them are on it, so a half-updated list is never counted. The Senate count is of all
    one hundred. An independent is counted with the party he or she sits with. The line is added to
    data/congress_seats.csv with its source, and never changed afterwards.

Third candidates (key E03: no third candidate at 10% or more in the June polls)
    Read from PollResults.org's list of presidential polls (CC BY 4.0, the list The Margin and Tipping Point also read; this
    file reads the list itself and nothing either of those sites makes of it).
      Which polls     national polls of the general election whose last day in the field is in the window, published by
                      the cutoff, with at least one question that names a candidate who is neither party's
      A third candidate   an answer filed under a party other than the two, with a name. "Someone else", "another
                      candidate", "don't know" and "would not vote" are not candidates and are not counted for one
      One poll        the best-placed third candidate in each question that names one; the mean of those questions
                      (a poll that asks three pairings counts once)
      One pollster    the mean of its polls in the window
      The reading     the mean over pollsters. Undecided voters are left where the poll left them
      Enough          at least three pollsters. Fewer is no reading: the key stays open. A poll that names no third
                      candidate says nothing about one, and is not counted as zero
    The 10% line is the key's own and is not touched here.

    python facts.py            read both sources and say what they give, changing nothing
"""
import csv, datetime, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
MEMBERS = 'https://raw.githubusercontent.com/unitedstates/congress-legislators/gh-pages/legislators-current.json'
POLLS = 'https://api.pollresults.org/v1.0/politics/results/president'
AGENT = {'User-Agent': 'fifty-two-keys/1.0 (facts)'}
STATES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
NOT_A_CANDIDATE = ('someone else', 'somebody else', 'another candidate', 'other', 'others', "don't know", 'dont know', 'not sure', 'undecided', 'unsure', 'would not vote', "wouldn't vote", 'will not vote',
                   'none', 'neither', 'refused', 'no opinion', 'third party', 'third-party candidate', 'independent candidate', 'generic')
ENOUGH = 3


def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
        return r.read().decode('utf-8-sig')


# ---------------------------------------------------------------------------------------------------------------- seats
def seats(members, year):
    """Seats by party in the Congress that met in January of `year`, from the list of sitting members, or None if the list
    is not that Congress's yet. {'house_d', 'house_r', 'senate_d', 'senate_r', 'house_new'}"""
    side = lambda t: {'Democrat': 'd', 'Republican': 'r'}.get(t.get('caucus') or t.get('party'))
    last = [m['terms'][-1] for m in members if m.get('terms')]
    house = [t for t in last if t['type'] == 'rep' and t.get('state') in STATES]; senate = [t for t in last if t['type'] == 'sen']
    fresh = sum(1 for t in house if t['start'][:7] == f'{year}-01')
    if fresh < 430 or len(senate) < 98:
        return None
    c = lambda ts, s: sum(1 for t in ts if side(t) == s)
    return {'house_d': c(house, 'd'), 'house_r': c(house, 'r'), 'senate_d': c(senate, 'd'), 'senate_r': c(senate, 'r'), 'house_new': fresh}


def refresh_seats(today, path=None, read=lambda: json.loads(get(MEMBERS))):
    """In the January and February after an election, add the new Congress's line to data/congress_seats.csv once the list of
    members is that Congress's. Returns (state, words): 'new', 'same' (nothing to do), 'early' or 'unreachable'."""
    path = path or os.path.join(D, 'congress_seats.csv')
    rows = list(csv.DictReader(open(path))); year = today.year
    if year % 2 == 0 or not (datetime.date(year, 1, 3) <= today <= datetime.date(year, 2, 28)) or any(int(r['start_year']) == year for r in rows):
        return 'same', 'no new Congress to count'
    try:
        s = seats(read(), year)
    except Exception as err:                            # noqa: BLE001
        return 'unreachable', f'the list of members of Congress was not reached ({type(err).__name__}: {str(err)[:80]})'
    if s is None:
        return 'early', f'the list of members is not yet that of the Congress that met in January {year}'
    if not (400 <= s['house_d'] + s['house_r'] <= 435 and 98 <= s['senate_d'] + s['senate_r'] <= 100):
        return 'unreachable', f"the list of members gives counts that cannot be right: {s}"
    line = {'congress': int(rows[-1]['congress']) + (year - int(rows[-1]['start_year'])) // 2, 'start_year': year, 'senate_d': s['senate_d'], 'senate_r': s['senate_r'], 'house_d': s['house_d'], 'house_r': s['house_r'],
            'note': f"counted on {today} from github.com/unitedstates/congress-legislators; independents with the party they sit with; {435 - s['house_d'] - s['house_r']} House seats vacant or other"}
    with open(path, 'a', newline='') as f:
        csv.DictWriter(f, list(rows[0].keys()), lineterminator='\n').writerow(line)
    return 'new', f"the Congress that met in January {year}: House {s['house_d']} Democrats, {s['house_r']} Republicans; Senate {s['senate_d']} to {s['senate_r']}"


# ------------------------------------------------------------------------------------------------------ third candidates
def day(s):
    """The feed writes dates as 6/14/28; some rows carry a time after it."""
    m, d, y = (s or '').split(' ')[0].split('/')
    return datetime.date(2000 + int(y) if int(y) < 100 else int(y), int(m), int(d))


def third_in(question):
    """The best-placed named third candidate in one question: (name, percent), or None if the question names none."""
    best = None
    for a in question.get('answers') or []:
        name = (a.get('candidateName') or '').strip(); party = (a.get('party') or '').upper()
        low = name.lower()
        if party in ('DEM', 'REP', 'NONE', '') or not name or low in NOT_A_CANDIDATE or set(low.replace('-', ' ').split()) & {'generic', 'someone', 'somebody', 'candidate', 'party', 'other', 'another', 'else', 'undecided'} or a.get('pct') is None:
            continue
        if best is None or float(a['pct']) > best[1]:
            best = (name, float(a['pct']))
    return best


def third_reading(records, lo, hi, published_by=None, cycle='2028'):
    """The reading for polls that finished between lo and hi (see the top of this file). Always returns the polls it found;
    'reading' is None unless at least ENOUGH pollsters named a third candidate."""
    polls = []
    for r in records:
        try:
            end = day(r.get('endDate'))
            made = day(r.get('createdAt')) if r.get('createdAt') else end
        except (ValueError, AttributeError):
            continue
        if str(r.get('cycle') or cycle) != cycle or (r.get('state') or 'US') != 'US' or not (lo <= end <= hi) or (published_by and made > published_by):
            continue
        got = [t for t in (third_in(q) for q in r.get('questions') or [] if str(q.get('stage') or '').lower() == 'general') if t]
        if got:
            top = max(got, key=lambda t: t[1])
            polls.append({'id': r.get('pollId'), 'pollster': r.get('pollster') or r.get('displayName'), 'end': str(end), 'questions': len(got), 'share': round(sum(t[1] for t in got) / len(got), 2),
                          'best': top[0], 'best_share': top[1], 'url': r.get('url') if str(r.get('url') or '').startswith('http') else None})
    seen = {}
    for p in polls:                                     # the same poll listed twice counts once
        seen[(p['pollster'], p['end'], p['share'])] = p
    polls = sorted(seen.values(), key=lambda p: (p['end'], p['pollster'] or ''))
    by = {}
    for p in polls:
        by.setdefault(p['pollster'], []).append(p['share'])
    means = [sum(v) / len(v) for v in by.values()]
    return {'from': str(lo), 'to': str(hi), 'published_by': str(published_by) if published_by else None, 'pollsters': len(by), 'polls': polls,
            'reading': round(sum(means) / len(means), 2) if len(by) >= ENOUGH else None}


def fetch_polls(read=get, max_pages=40):
    out, seen, cursor = [], set(), None
    for _ in range(max_pages):
        page = json.loads(read(POLLS + '?limit=100' + (f'&cursor={urllib.parse.quote(cursor)}' if cursor else '')))
        new = [r for r in page.get('results', []) if r.get('pollId') not in seen]
        seen.update(r.get('pollId') for r in new); out.extend(new); cursor = page.get('cursor')
        if not cursor or not new:
            break
    return out


def refresh_third(today, path=None, read=None, year=2028):
    """Read the poll list and write data/third_candidates.json: the reading for the last 90 days, and the June reading once
    June has begun. A source that does not answer leaves the file as it is. Returns (state, words)."""
    path = path or os.path.join(D, 'third_candidates.json')
    try:
        records = (read or fetch_polls)()
    except Exception as err:                            # noqa: BLE001
        return 'unreachable', f'the list of presidential polls was not reached ({type(err).__name__}: {str(err)[:80]}); the last reading stays'
    one = datetime.timedelta(days=1)
    out = {'source': 'PollResults.org, presidential polls (CC BY 4.0)', 'rule': 'facts.py', 'enough_pollsters': ENOUGH,
           'now': third_reading(records, today - 89 * one, today),
           'june': third_reading(records, datetime.date(year, 6, 1), datetime.date(year, 6, 30), datetime.date(year, 7, 7)) if today >= datetime.date(year, 6, 1) else None}
    old = json.load(open(path)) if os.path.exists(path) else {}
    same = {k: old.get(k) for k in ('now', 'june')} == {k: out[k] for k in ('now', 'june')}
    json.dump(dict(out, fetched=str(today)), open(path, 'w'), indent=1)
    n = out['now']
    return ('same' if same else 'new'), (f"third candidates, last 90 days: {n['pollsters']} pollsters named one" + (f", reading {n['reading']}%" if n['reading'] is not None else ', too few for a reading'))


if __name__ == '__main__':
    members = json.loads(get(MEMBERS)); print('members listed:', len(members), '| the Congress of January 2025:', seats(members, 2025))
    recs = fetch_polls(); r = third_reading(recs, datetime.date.today() - datetime.timedelta(days=89), datetime.date.today())
    print(len(recs), 'polls listed |', {k: v for k, v in r.items() if k != 'polls'}); [print('  ', p) for p in r['polls'][:8]]
