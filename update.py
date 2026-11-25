"""The update. It is run every hour: it reads what could have changed, checks it, and reruns the 2028 run-ahead only if a
figure the run-ahead reads is new.

    python update.py                 read, check, and if anything is new: run, archive, build
    python update.py --force         read every source and run, whether or not anything is new
    python update.py --offline       no reading: run, archive and build from the figures already here
    python update.py --trust UNRATE  accept a series even though it failed a check (after looking at it)

What it reads, and when
    VoteHub (api.votehub.com)    polls of presidential approval: on every run
    Philadelphia Fed             the Survey of Professional Forecasters' table of median forecasts, for the outlook
                                 (outlook.py): with the economic series. Only a later survey replaces the outlook
    FRED (fred.stlouisfed.org)   twelve monthly series, five quarterly series, the latest S&P 500 and oil price, and the
                                 Philadelphia Fed's coincident index for each of the 50 states: when a release could have
                                 come out (economy_due below), and on the first run of every day

When it runs the model again
    After reading, every file the run-ahead reads is fingerprinted and compared with the fingerprints of the last run
    (data/fingerprint.json). If none differs and the day is the same, the run stops there: nothing is recalculated and
    nothing is saved. The first run of each day always goes through, so the page's date and its 30-day windows keep up.

The rules it keeps
    A figure that fails a check is not used. The last good figure stays, the run says so, and the run ends as failed
    so that somebody looks: at once when a figure is first held back, and then once a day until it is settled. A source
    that cannot be reached is tried again on the next run and reported once a day if it stays out of reach.
    Nothing is ever filled in, and a key with missing figures stays open: it never becomes "no".
    Every run whose projection differs from the last one kept is written to archive/ under its own time stamp, with the
    figures, assumptions and versions behind it. Archive files are never rewritten.
"""
import csv, datetime, hashlib, io, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outlook as OUT                                  # noqa: E402
import facts as FACTS                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
ARCHIVE = os.path.join(HERE, 'archive')
FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
FRED_API = 'https://api.stlouisfed.org/fred/series/observations'
VOTEHUB = 'https://api.votehub.com/polls?poll_type=approval&subject=donald-trump'
AGENT = {'User-Agent': 'fifty-two-keys/1.0 (update)'}
FIRST = '2025-12-01'                                   # the first month kept in data/latest_monthly.csv
ET = ZoneInfo('America/New_York')
# When the economic series are read. The statistical agencies publish at 8:30 and 10:00 in the morning, Eastern time, on
# working days, and FRED carries a new figure within the hour. The other hours are there in case a release is late, falls
# on another day, or a morning run did not start.
RELEASE_HOURS = (8, 9, 10, 11)                         # Monday to Friday
FALLBACK_HOURS = (14, 20)                              # every day
OUT_OF_REACH_DAYS = 2                                  # a source not read for this many days is reported on the day's first run

# series: (lowest and highest believable value, the largest believable change in a NEW figure from the one before it, the
# largest believable REVISION to a figure already held). Changes are fractions unless marked 'points'.
#   - Every figure read, new or old, must lie inside the range.
#   - A figure for a date not held before must not differ from the figure before it by more than the second limit.
#   - A figure already held must not have moved by more than the third limit. It is not compared with its neighbours again:
#     the swings of 2020 and 2021 are in the tables already, and what matters for them is that they have not changed much.
# So the limits on new figures can be tight without tripping over history. They are there to catch a broken download or a
# changed unit, not to judge the economy: a real move as large as spring 2020 would be held back too, and let in with --trust
# after somebody has looked at it.
MONTHLY = {
    'UNRATE': ((2, 16), ('points', 2.0), ('points', 0.4)),            'PAYEMS': ((120000, 200000), 0.03, 0.01),
    'MANEMP': ((9000, 16000), 0.05, 0.02),                             'CPIAUCSL': ((250, 500), 0.03, 0.01),
    'INDPRO': ((70, 140), 0.08, 0.04),                                 'DPCERA3M086SBEA': ((90, 180), 0.06, 0.03),
    'CES0600000008': ((25, 60), 0.04, 0.02),                           'HOUST': ((400, 2500), 0.45, 0.15),
    'UMCSENT': ((30, 115), ('points', 20), ('points', 6)),             'MCOILWTICO': ((10, 250), 0.6, 0.02),
    'SP500': ((2000, 20000), 0.35, 0.01),                              'ICSA': ((120000, 7000000), 2.0, 0.08),
}
AVERAGED = ('SP500', 'ICSA')                           # daily and weekly series, averaged by month: only finished months are kept
QUARTERLY = {
    # growth rates, annualised. The ranges take in 2020 and 2021 (output -28 and +35; income +59), which are held already.
    'A191RL1Q225SBEA': ((-40, 40), ('points', 12), ('points', 4)),    'A067RL1Q156SBEA': ((-40, 65), ('points', 30), ('points', 6)),
    # levels: people in thousands, dollars per person. A new quarter sits within a few percent of the one before, so a figure
    # in other units (millions, or dollars in place of thousands) cannot pass.
    'B230RC0Q173SBEA': ((320000, 370000), 0.005, 0.005),               'A939RX0Q048SBEA': ((55000, 90000), 0.03, 0.03),
    'A229RX0Q048SBEA': ((40000, 70000), 0.04, 0.04),
}
DAILY = {'sp500': ('SP500', (2000, 20000), 0.30), 'oil': ('DCOILWTICO', (10, 250), 0.45)}
# the Philadelphia Fed's coincident index for each state (FRED series ALPHCI to WYPHCI). These indexes are re-estimated, so past months move.
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
          'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
STATE_RULE = ((40, 500), 0.06, 0.12)


class Held(Exception):
    """A figure that failed a check. It is not used."""


DOWN = {}                                              # hosts that did not answer in this run: they are not asked again
THIRD, SEATS = FACTS.refresh_third, FACTS.refresh_seats   # the tests put files in their place
SURVEY = OUT.fetch                                     # how the Survey of Professional Forecasters is read (the tests put a file in its place)


def get(url, tries=3, wait=2.0, timeout=20):
    """Read a URL. A server error or a timeout is tried again; a request the server rejects (HTTP 4xx) is not. A host that
    fails to answer twice in a row is left alone for the rest of the run, so one dead source cannot hold the run up."""
    host = urllib.parse.urlsplit(url).netloc
    if DOWN.get(host, 0) >= 2:
        raise ConnectionError(f'{host} did not answer earlier in this run')
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
                text = r.read().decode('utf-8-sig')
            DOWN[host] = 0
            return text
        except urllib.error.HTTPError as err:
            if (err.code < 500 and err.code != 429) or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt == tries - 1:
                DOWN[host] = DOWN.get(host, 0) + 1
                raise
        time.sleep(wait * 2 ** attempt)


def fred(series, start, monthly_average=False):
    """[(YYYY-MM-DD, value)] for one FRED series. A missing value ('.' or blank) is left out, never read as zero.
    With a key in FRED_API_KEY the series is read from FRED's API; without one, from the download link behind its charts."""
    key = os.environ.get('FRED_API_KEY', '').strip()
    if key:
        q = {'series_id': series, 'api_key': key, 'file_type': 'json', 'observation_start': start}
        if monthly_average:
            q.update(frequency='m', aggregation_method='avg')
        obs = json.loads(get(FRED_API + '?' + urllib.parse.urlencode(q)))['observations']
        pairs = [(o['date'], o['value']) for o in obs]
    else:
        url = f'{FRED}?id={series}&cosd={start}' + ('&fq=Monthly&fam=avg' if monthly_average else '')
        rows = list(csv.reader(io.StringIO(get(url))))
        if not rows or len(rows[0]) != 2 or rows[0][1].strip() != series:
            raise Held(f'{series}: the download is not a table of this series (first line: {rows[0] if rows else "empty"})')
        pairs = [(r[0], r[1]) for r in rows[1:] if len(r) == 2]
    out = []
    for d, v in pairs:
        if v.strip() not in ('', '.'):
            datetime.date.fromisoformat(d); out.append((d, float(v)))
    return out


def moved(a, b, limit):
    """Is the change from a to b larger than the limit? The limit is a fraction, or ('points', n) for an absolute change."""
    return abs(b - a) > limit[1] if isinstance(limit, tuple) else abs(b / a - 1) > limit


def check(series, new, held, rule, step_months):
    """Check a freshly read series against its limits and against the figures already held. Raises Held with the reason.
    See the note above MONTHLY for the three limits and what each is applied to."""
    (low, high), step, revision = rule
    if not new:
        raise Held(f'{series}: nothing was read')
    dates = [d for d, _ in new]
    if dates != sorted(set(dates)):
        raise Held(f'{series}: the dates are out of order or repeated')
    months = lambda a, b: (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7]))
    before = None
    for d, v in new:
        if v != v or not low <= v <= high:                                  # v != v: not a number
            raise Held(f'{series}: {v:g} for {d[:7]} is outside {low:g} to {high:g}')
        if d in held:
            if moved(held[d], v, revision):
                raise Held(f'{series}: {d[:7]} was {held[d]:g} and now reads {v:g}, a larger revision than this series gets')
        elif before is not None and months(before[0], d) <= 3 * step_months:
            gap = max(1, round(months(before[0], d) / step_months))          # a figure after a missing month or two may have moved that much more
            limit = ('points', step[1] * gap) if isinstance(step, tuple) else step * gap
            if moved(before[1], v, limit):
                raise Held(f'{series}: {before[1]:g} in {before[0][:7]} to {v:g} in {d[:7]} is a larger change than a new figure of this series makes')
        before = (d, v)
    if held and months(max(dates), max(held)) > step_months:               # one step behind is allowed: a first reading entered by hand
        raise Held(f'{series}: the download stops at {max(dates)[:7]}, well before the figures already held ({max(held)[:7]})')


def table(path):
    rows = list(csv.DictReader(open(path)))
    return rows, [c for c in rows[0] if c != 'observation_date']


def refresh_table(path, rules, today, trust, report, monthly):
    """Update one CSV of FRED series, column by column. A column that fails its check keeps the figures it had."""
    rows, cols = table(path)
    held = {c: {r['observation_date']: float(r[c]) for r in rows if r[c] != ''} for c in cols}
    step = 1 if monthly else 3
    this_month = today.strftime('%Y-%m-01')
    for c in cols:
        try:
            new = fred(c, FIRST if monthly else rows[0]['observation_date'], monthly and c in AVERAGED)
            if monthly and c in AVERAGED:
                new = [(d, v) for d, v in new if d < this_month]            # the month in progress is not a monthly average yet
            if c not in trust:
                check(c, new, held[c], rules[c], step)
            before = max(held[c]) if held[c] else None
            held[c].update(new)
            report['read'].append(c)
            if before is None or max(held[c]) > before:
                report['new'].append({'series': c, 'through': max(held[c])[:7], 'was': before and before[:7]})
        except Held as err:
            report['held'].append(str(err))
        except Exception as err:                                            # noqa: BLE001  the network fails in many ways
            report['failed'].append(f'{c}: could not be read ({type(err).__name__}: {err})')
    dates = sorted({d for c in cols for d in held[c]})
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['observation_date'] + cols)
        for d in dates:
            w.writerow([d] + [('' if d not in held[c] else str(int(held[c][d])) if float(held[c][d]).is_integer() else repr(held[c][d])) for c in cols])


def refresh_prices(latest, today, trust, report):
    for name, (series, (low, high), jump) in DAILY.items():
        try:
            rows = fred(series, str(today - datetime.timedelta(days=45)))
            if not rows:
                raise Held(f'{series}: no price in the last 45 days')
            d, v = rows[-1]
            was = latest[name]['value']
            if series not in trust and (not low <= v <= high or abs(v / was - 1) > jump):
                raise Held(f'{series}: {v:g} on {d} against {was:g} held is not a believable price')
            if d >= latest[name]['date']:
                latest[name] = {'date': d, 'value': v}
            report['read'].append(series)
        except Held as err:
            report['held'].append(str(err))
        except Exception as err:                                            # noqa: BLE001
            report['failed'].append(f'{series}: could not be read ({type(err).__name__}: {err})')


def refresh_states(path, trust, report):
    """The state indexes, month by month for this term. A state that fails its check keeps the months it had."""
    held = {}
    for r in csv.DictReader(open(path)):
        if r['index'] != '':
            held.setdefault(r['state'], {})[r['month']] = float(r['index'])
    first = min(m for d in held.values() for m in d)
    before, bad = max(min(max(d) for d in held.values()), first), []
    for st in STATES:
        try:
            new = fred(st + 'PHCI', first + '-01')
            if 'states' not in trust:
                check(st + 'PHCI', new, {m + '-01': v for m, v in held[st].items()}, STATE_RULE, 1)
            held[st].update({d[:7]: v for d, v in new})
        except Held as err:
            bad.append(str(err))
        except Exception as err:                                            # noqa: BLE001
            bad.append(f'{st}PHCI: could not be read ({type(err).__name__}: {err})')
        time.sleep(0.15)
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['state', 'month', 'index'])
        for st in STATES:
            for m in sorted(held[st]):
                w.writerow([st, m, f'{held[st][m]:.2f}'])
    if bad:
        report['failed' if all('could not be read' in b for b in bad) else 'held'].append(f'state indexes: {len(bad)} of {len(STATES)} states not updated; the first: {bad[0]}')
    else:
        report['read'].append('state indexes')
    through = min(max(d) for d in held.values())                            # the last month that every state has
    if through > before:
        report['new'].append({'series': 'state indexes', 'through': through, 'was': before})


def trim(p):
    a = {str(x.get('choice', '')).lower(): x.get('pct') for x in p.get('answers') or []}
    return {'id': p.get('id'), 'pollster': p.get('pollster'), 'start': p.get('start_date'), 'end': p.get('end_date'), 'population': p.get('population'),
            'n': p.get('sample_size'), 'approve': a.get('approve'), 'disapprove': a.get('disapprove'), 'internal': bool(p.get('internal')), 'url': p.get('url')}


def refresh_polls(path, today, trust, report):
    held = json.load(open(path))
    try:
        data = json.loads(get(VOTEHUB))
        raw = data['polls'] if isinstance(data, dict) else data
        polls = [trim(p) for p in raw if p.get('poll_type') == 'approval' and p.get('subject') == 'Donald Trump']
        good = []
        for p in polls:                                                     # a poll that cannot be read is left out and counted, not guessed
            try:
                datetime.date.fromisoformat(p['end'])
                assert p['pollster'] and 0 <= p['approve'] <= 100 and 0 <= p['disapprove'] <= 100 and p['approve'] + p['disapprove'] <= 101
                good.append(p)
            except Exception:                                               # noqa: BLE001
                pass
        if 'polls' not in trust:
            if len(good) < 0.9 * len([p for p in held['polls'] if p['approve'] is not None]):
                raise Held(f'approval polls: {len(good)} readable polls, far fewer than the {len(held["polls"])} already held')
            if not any(p['population'] == 'a' for p in good):
                raise Held('approval polls: none of all adults')
        good.sort(key=lambda p: (p['end'], str(p['id'])))
        seen = {p['id'] for p in held['polls']}
        added = [p for p in good if p['id'] not in seen]
        json.dump({'source': held['source'], 'fetched': str(today), 'polls': good}, open(path, 'w'), separators=(',', ':'))
        report['read'].append('approval polls')
        if added:
            report['new'].append({'series': 'approval polls', 'added': len(added), 'of_all_adults': sum(1 for p in added if p['population'] == 'a')})
    except Held as err:
        report['held'].append(str(err))
    except Exception as err:                                                # noqa: BLE001
        report['failed'].append(f'approval polls: could not be read ({type(err).__name__}: {err})')


# ---------------------------------------------------------------------------------------------------------------- the archive
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]


INPUTS = ['data/latest_monthly.csv', 'data/quarterly.csv', 'data/latest.json', 'data/approval_polls.json', 'data/state_index_this_term.csv', 'data/outlook.json', 'data/third_candidates.json', 'locked_keys.csv',
          'run_2028.py', 'build.py', 'calls.py', 'data/congress_seats.csv', 'data/nh_primaries.csv']


def vote(index):
    line = json.load(open(os.path.join(HERE, 'results.json')))['sure']['line']
    return round(line[0] + line[1] * index, 1)


def summary(pr):
    """The headline figures of one run."""
    return {'as_of': pr['as_of'], 'mean': pr['index']['mean'], 'median': pr['index']['median'], 'p25': pr['index']['p25'], 'p75': pr['index']['p75'],
            'above_half': pr['index']['above_half'], 'in_favor': pr['likely']['in_favor'], 'likely': pr['likely']['index'], 'vote': vote(pr['likely']['index']),
            'landed': sorted(k for k, v in pr['keys'].items() if v.get('landed')), 'open': len([k for k, v in pr['keys'].items() if not v.get('landed')])}


def changes(old, new, text):
    """What changed between two runs, in sentences. `text` gives each key's wording."""
    out = []
    lean = lambda p: 'yes' if p >= 0.5 else 'no'
    pct = lambda p: f'{100 * p:.0f}%'
    a, b = old.get('data_through') or {}, new.get('data_through') or {}
    if a.get('monthly') != b.get('monthly') and a.get('monthly'):
        out.append(f"Monthly figures now run through {b['monthly']} (were {a['monthly']}).")
    if a.get('quarterly') != b.get('quarterly') and a.get('quarterly'):
        out.append(f"Quarterly figures now run through {b['quarterly']} (were {a['quarterly']}).")
    if old.get('engine') and old.get('engine') != new.get('engine'):
        out.append(f"The run-ahead method changed (version {old['engine']} to {new['engine']}); see the change log.")
    oa, na = {k: v for k, v in (old.get('outlook') or {}).items()}, {k: v for k, v in (new.get('outlook') or {}).items()}
    drop = ('sp500_now', 'housing_starts', 'claims')
    diff = sorted(k for k in set(oa) | set(na) if k not in drop and oa.get(k) != na.get(k))
    if diff and oa:
        out.append('The outlook was revised: ' + ', '.join(d.replace('_', ' ') for d in diff) + '.')
    if (old.get('politics') or {}) != (new.get('politics') or {}) and old.get('politics'):
        out.append('The odds for the nomination and approval keys were revised.')
    ok, nk = old['keys'], new['keys']
    gone = sorted(k for k in ok if k not in nk)
    for k in gone:
        out.append(f"{k} ({text.get(k, k)}) was settled.")
    oc, nc = old.get('calls') or {}, new.get('calls') or {}
    for k in sorted(nc):                                 # the calls: a key held, a call revised before the close, a call made final
        a, b = oc.get(k), nc[k]
        if not a:
            continue
        if b['status'] == 'held' and a['status'] != 'held':
            out.append(f"{k} ({text.get(k, k)}) is held: {b.get('why', '')}")
        elif a['status'] == 'held' and b['status'] != 'held':
            out.append(f"{k} ({text.get(k, k)}) is no longer held.")
        elif a.get('value') is not None and b.get('value') is not None and a['value'] != b['value']:
            out.append(f"{k} ({text.get(k, k)}) was corrected to {'yes' if b['value'] else 'no'} on revised figures. {b.get('evidence', '')}")
        elif b.get('final') and not a.get('final'):
            out.append(f"{k} ({text.get(k, k)}) is final: {'yes' if b['value'] else 'no'}.")
    if (new.get('outlook_from') or {}).get('stale') and not (old.get('outlook_from') or {}).get('stale'):
        out.append('A newer survey of forecasters should be out; the outlook entered is the older one.')
    for k in sorted(nk):
        if nk[k].get('landed') and not (ok.get(k) or {}).get('landed'):
            out.append(f"{k} ({text.get(k, k)}) landed: {'yes' if nk[k]['p'] >= 0.5 else 'no'}. {nk[k]['note']}")
    flips = [k for k in sorted(nk) if k in ok and lean(ok[k]['p']) != lean(nk[k]['p']) and not nk[k].get('landed')]
    for k in flips:
        out.append(f"{k} ({text.get(k, k)}) now leans {lean(nk[k]['p'])}: {pct(nk[k]['p'])}, from {pct(ok[k]['p'])}.")
    big = sorted((k for k in nk if k in ok and k not in flips and not nk[k].get('landed') and abs(nk[k]['p'] - ok[k]['p']) >= 0.05), key=lambda k: -abs(nk[k]['p'] - ok[k]['p']))
    for k in big[:6]:
        out.append(f"{k} ({text.get(k, k)}): {pct(ok[k]['p'])} to {pct(nk[k]['p'])}.")
    return out


def differs(old, new):
    """Does projection `new` say something `old` did not? The headline figures, any key that landed or changed its lean, any
    key whose odds moved by a point or more, the months the figures run through, the method and the assumptions. A price
    that ticked without moving any of these is not a different projection."""
    head = lambda pr: {k: v for k, v in summary(pr).items() if k != 'as_of'}
    if head(old) != head(new): return True
    if any(old.get(k) != new.get(k) for k in ('engine', 'outlook', 'politics', 'recession_share')): return True
    through = lambda pr: {k: v for k, v in (pr.get('data_through') or {}).items() if k != 'prices'}
    if through(old) != through(new): return True
    a, b = old['keys'], new['keys']
    if set(a) != set(b): return True
    call = lambda pr: {k: (c['status'], c.get('value'), c.get('final')) for k, c in (pr.get('calls') or {}).items()}
    if old.get('calls') and call(old) != call(new): return True
    if (old.get('outlook_from') or {}).get('stale') != (new.get('outlook_from') or {}).get('stale') and old.get('outlook_from'): return True
    return any(bool(a[k].get('landed')) != bool(b[k].get('landed')) or (a[k]['p'] >= 0.5) != (b[k]['p'] >= 0.5) or abs(a[k]['p'] - b[k]['p']) >= 0.01 for k in b)


def archive(pr, report, made, commit=''):
    """Write this run to the archive under its own time stamp, unless it says nothing the last one kept did not."""
    os.makedirs(ARCHIVE, exist_ok=True)
    index_path = os.path.join(ARCHIVE, 'index.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else []
    inputs = {p: sha(os.path.join(HERE, p)) for p in INPUTS}
    if index:
        last = json.load(open(os.path.join(ARCHIVE, index[-1]['file'])))
        if not differs(last['projection'], pr):
            return None
    sys.path.insert(0, HERE)
    from make_page import TEXT
    text = {k: v[0] for k, v in TEXT.items()}
    why = changes(json.load(open(os.path.join(ARCHIVE, index[-1]['file'])))['projection'], pr, text) if index else ['The first archived run.']
    name = made.strftime('%Y-%m-%dT%H%M%SZ') + '.json'
    # the figures themselves, as used: the two tables of national series and the prices. (The 50 state indexes and the list of
    # polls are too long to repeat here; their fingerprints are in `inputs` and the files are in the commit that follows this run.)
    figures = {'monthly': list(csv.reader(open(os.path.join(D, 'latest_monthly.csv')))), 'quarterly': list(csv.reader(open(os.path.join(D, 'quarterly.csv'))))[-12:],
               'quarterly_columns': next(csv.reader(open(os.path.join(D, 'quarterly.csv')))), 'prices': json.load(open(os.path.join(D, 'latest.json'))),
               'approval': pr.get('approval'), 'states': pr.get('states')}
    entry = {'made': made.strftime('%Y-%m-%dT%H:%M:%SZ'), 'model': {'keys': inputs['locked_keys.csv'], 'engine': pr.get('engine')}, 'commit': commit, 'inputs': inputs,
             'figures': figures, 'assumptions': json.load(open(os.path.join(D, 'outlook.json'))), 'checks': report, 'changes': why, 'projection': pr}
    with open(os.path.join(ARCHIVE, name), 'x') as f:                        # 'x': an archive file is written once and never again
        json.dump(entry, f, indent=1)
    index.append(dict(summary(pr), file=name, made=entry['made'], engine=pr.get('engine'), changes=why))
    json.dump(index, open(index_path, 'w'), indent=1)
    return name


def economy_due(now, new_day, force=False):
    """Are the economic series read on this run? `now` is the time in the East. Polls are read on every run."""
    return bool(force or new_day or (now.weekday() < 5 and now.hour in RELEASE_HOURS) or now.hour in FALLBACK_HOURS)


POLLS = 'approval polls'
of_polls = lambda line: line.startswith(POLLS)


def fingerprint(day, held):
    """A short hash of every file the run-ahead reads, the day, and the series being held back. The date a file was fetched
    is left out of it, so reading the same figures again changes nothing."""
    h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
    fp = {'day': str(day), 'held back': h(sorted(held))}
    for p in INPUTS:
        full = os.path.join(HERE, p)
        if not os.path.exists(full): fp[p] = ''; continue
        if p.endswith(('latest.json', 'approval_polls.json', 'third_candidates.json')):
            x = json.load(open(full)); x.pop('as_of', None); x.pop('fetched', None); fp[p] = h(x)
        else:
            fp[p] = sha(full)
    return fp


def alarm(held, held_before, read_on, today, new_day, force=False, keys_held=(), keys_held_before=(), stale=False):
    """Should this run end as failed, so that somebody looks? Returns the reason, or None.
    A figure held back: on the run that first holds it, then on the first run of each day until it is settled.
    A key held (its evidence is late, or an entry and the rule disagree): the same.
    A source out of reach: on the first run of the day, once it has not been read for OUT_OF_REACH_DAYS days.
    The outlook is older than the latest survey of forecasters: on the first run of each Monday.
    A run asked for by hand reports any of them."""
    if held and (set(held) - set(held_before) or new_day or force):
        return 'Some figures failed a check and were not used; the page was rebuilt with the last good ones. See the warnings above.'
    if keys_held and (set(keys_held) - set(keys_held_before) or new_day or force):
        return f"Held: {', '.join(sorted(keys_held))}. The evidence for these keys is late or in dispute; they keep their chance and are not counted as no. See KEYS.md for what each needs."
    if stale and ((new_day and today.weekday() == 0) or force):
        return 'A newer Survey of Professional Forecasters should be out and has not been read (outlook.py; see the line that starts "The outlook:" above). The run ahead uses the older one until it is.'
    day = datetime.date.fromisoformat
    lost = [k for k in ('economy', 'polls') if read_on.get(k) and (today - day(read_on[k])).days >= OUT_OF_REACH_DAYS]
    if lost and (new_day or force):
        return f"Not read for {OUT_OF_REACH_DAYS} days or more: {', '.join(lost)}. The page shows the last figures read."
    return None


def out(key, value):
    """A result for the workflow that started the run."""
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write(f'{key}={value}\n')


def feed():
    """The part of docs/keys.json that other sites read."""
    try:
        k = json.load(open(os.path.join(HERE, 'docs', 'keys.json')))
        return [k.get('likely'), k.get('mean'), k.get('sd'), k.get('settled'), k.get('calls'), k.get('index_dist')]
    except Exception:                                                       # noqa: BLE001
        return None


def main(argv):
    offline = '--offline' in argv
    trust = set(argv[argv.index('--trust') + 1].replace(',', ' ').split()) if '--trust' in argv and len(argv) > argv.index('--trust') + 1 else set()
    force = '--force' in argv or bool(trust)
    made = datetime.datetime.now(datetime.timezone.utc)
    now = made.astimezone(ET); today = now.date()
    latest_path, log_path, fp_path = os.path.join(D, 'latest.json'), os.path.join(D, 'update_log.json'), os.path.join(D, 'fingerprint.json')
    latest = json.load(open(latest_path))
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    new_day = latest.get('as_of', '') < str(today)
    report = {'read': [], 'new': [], 'held': [], 'failed': [], 'trusted': sorted(trust)}
    economy = not offline and economy_due(now, new_day, force)
    read_on = dict(log.get('read_on') or {})
    if not offline:
        say = lambda what: print(f"{what}: {len(report['read'])} read, {len(report['held'])} held back, {len(report['failed'])} not reached", flush=True)
        if economy:
            print('FRED is read ' + ('through its API, with a key' if os.environ.get('FRED_API_KEY', '').strip() else 'through its download links, without a key'), flush=True)
            refresh_table(os.path.join(D, 'latest_monthly.csv'), MONTHLY, today, trust, report, monthly=True); say('monthly series')
            refresh_table(os.path.join(D, 'quarterly.csv'), QUARTERLY, today, trust, report, monthly=False); say('quarterly series')
            refresh_prices(latest, today, trust, report); say('prices')
            refresh_states(os.path.join(D, 'state_index_this_term.csv'), trust, report); say('state indexes')
            state, words = OUT.refresh(today, os.path.join(D, 'outlook.json'), SURVEY)          # the forecasters' outlook: replaced only by a later survey
            print('The outlook: ' + words, flush=True); report['outlook'] = {'state': state, 'said': words}
            if state == 'new': report['new'].append({'series': "the forecasters' outlook", 'through': json.load(open(os.path.join(D, 'outlook.json')))['outlook_survey']})
            if state != 'new' and state != 'same': print('::warning::' + words)
            state, words = SEATS(today); print('Seats in Congress: ' + words, flush=True)            # counted once, in the January a new Congress meets
            if state == 'new': report['new'].append({'series': 'seats in the new Congress'})
            if state == 'unreachable': print('::warning::' + words)
            if not report['failed']: read_on['economy'] = str(today)
        else:
            print(f"The economic series are not read at this hour ({now:%A %H:%M} Eastern); they were last read {log.get('economy_read', 'at the last full run')}.", flush=True)
        n = len(report['failed'])
        refresh_polls(os.path.join(D, 'approval_polls.json'), today, trust, report); say('approval polls')
        state, words = THIRD(today); print('Third candidates: ' + words, flush=True)      # polls that name a third candidate (key E03): on every run
        if state == 'new': report['new'].append({'series': 'polls naming a third candidate'})
        if state == 'unreachable': print('::warning::' + words)
        if len(report['failed']) == n: read_on['polls'] = str(today)
        latest['as_of'] = str(today)
        json.dump(latest, open(latest_path, 'w'), indent=1)
    if not economy:                                    # what was held back or out of reach on the last reading of the economy still is
        for kind in ('held', 'failed'):
            report[kind] = [m for m in log.get(kind, []) if not of_polls(m)] + report[kind]
    for line in report['held'] + report['failed']:
        print('::warning::' + line)
    print(f"read {len(report['read'])} sources; new figures: {json.dumps(report['new'])}")
    held = sorted({m.split(':')[0] for m in report['held']})
    fp = fingerprint(today, held); old = json.load(open(fp_path)) if os.path.exists(fp_path) else {}
    what = [k for k in fp if fp[k] != old.get(k)]
    if not what and not force and not offline:
        print(f"Nothing new since the run of {log.get('made', 'before')}: nothing is recalculated."); out('changed', 'false')
        return 0
    print('New: ' + (', '.join(what) if what else 'nothing (the run was asked for)'))
    before = feed()
    run = lambda script: subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE, check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, KEYS_HELD=' '.join(held)))
    run('run_2028.py')
    pr = json.load(open(os.path.join(HERE, 'projection_2028.json')))
    name = archive(pr, report, made, os.environ.get('GITHUB_SHA', ''))
    print('archived as ' + name if name else 'the projection says nothing new: not added to the archive')
    run('make_page.py')
    first_held = sorted(set(held) - set(log.get('held_names') or []))
    keys_held = sorted(k for k, c in (pr.get('calls') or {}).items() if c['status'] == 'held')
    if not offline:                                    # a run without reading says nothing about the sources
        json.dump(dict(report, made=made.strftime('%Y-%m-%dT%H:%M:%SZ'), economy_read=made.strftime('%Y-%m-%dT%H:%M:%SZ') if economy else log.get('economy_read'),
                       read_on=read_on, held_names=held, keys_held=keys_held), open(log_path, 'w'), indent=1)
    json.dump(fp, open(fp_path, 'w'), indent=1)
    news = [n_['series'] for n_ in report['new']]
    out('changed', 'true'); out('feed', 'true' if feed() != before else 'false')
    out('what', ', '.join(news) if news else ('a figure held back' if first_held else 'the day' if what == ['day'] else 'revised figures'))
    why = alarm(held, log.get('held_names') or [], read_on, today, new_day, force, keys_held, log.get('keys_held') or [], (pr.get('outlook_from') or {}).get('stale', False))
    if why:
        print('::error::' + why); out('alert', 'true')
    return 1 if why else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
