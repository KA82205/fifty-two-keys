"""The weekly update: fetch the latest figures, check them, rerun the 2028 run-ahead, archive it, rebuild the page.

    python update.py                 fetch, check, run, archive, build
    python update.py --offline       no fetching: run, archive and build from the figures already here
    python update.py --trust UNRATE  accept a series even though it failed a check (after looking at it)

What it reads
    FRED (fred.stlouisfed.org)   twelve monthly series, five quarterly series, the latest S&P 500 and oil price,
                                 and the Philadelphia Fed's coincident index for each of the 50 states
    VoteHub (api.votehub.com)    polls of presidential approval

The rules it keeps
    A figure that fails a check is not used. The last good figure stays, the run says so, and the run ends as failed
    so that somebody looks. Nothing is ever filled in, and a key with missing figures stays open: it never becomes "no".
    Every run that changes anything is written to archive/ under its own time stamp, with the figures, assumptions and
    versions behind it. Archive files are never rewritten.
"""
import csv, datetime, hashlib, io, json, os, subprocess, sys, time, urllib.error, urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
ARCHIVE = os.path.join(HERE, 'archive')
FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
VOTEHUB = 'https://api.votehub.com/polls?poll_type=approval&subject=donald-trump'
AGENT = {'User-Agent': 'fifty-two-keys/1.0 (weekly update)'}
FIRST = '2025-12-01'                                   # the first month kept in data/latest_monthly.csv

# series: (lowest and highest believable value, the largest believable change from one month or quarter to the next, the
# largest believable revision to a figure already held). Changes are fractions unless marked 'points'. The limits are wide:
# they are there to catch a broken download or a changed unit, not to judge the economy. A figure outside them is held back.
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
    'A191RL1Q225SBEA': ((-40, 40), ('points', 45), ('points', 4)),    'A067RL1Q156SBEA': ((-40, 60), ('points', 60), ('points', 6)),
    'B230RC0Q173SBEA': ((330000, 370000), 0.005, 0.005),               'A939RX0Q048SBEA': ((60000, 90000), 0.12, 0.03),
    'A229RX0Q048SBEA': ((45000, 70000), 0.15, 0.04),
}
DAILY = {'sp500': ('SP500', (2000, 20000), 0.30), 'oil': ('DCOILWTICO', (10, 250), 0.45)}
# the Philadelphia Fed's coincident index for each state (FRED series ALPHCI to WYPHCI). These indexes are re-estimated, so past months move.
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
          'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
STATE_RULE = ((40, 500), 0.06, 0.12)


class Held(Exception):
    """A figure that failed a check. It is not used."""


def get(url, tries=4, wait=4.0):
    """Read a URL. A server error or a timeout is tried again; a request the server rejects (HTTP 4xx) is not."""
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=45) as r:
                return r.read().decode('utf-8-sig')
        except urllib.error.HTTPError as err:
            if (err.code < 500 and err.code != 429) or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == tries - 1:
                raise
        time.sleep(wait * 2 ** attempt)


def fred(series, start, monthly_average=False):
    """[(YYYY-MM-DD, value)] for one FRED series. A missing value ('.' or blank) is left out, never read as zero."""
    url = f'{FRED}?id={series}&cosd={start}' + ('&fq=Monthly&fam=avg' if monthly_average else '')
    rows = list(csv.reader(io.StringIO(get(url))))
    if not rows or len(rows[0]) != 2 or rows[0][1].strip() != series:
        raise Held(f'{series}: the download is not a table of this series (first line: {rows[0] if rows else "empty"})')
    out = []
    for r in rows[1:]:
        if len(r) == 2 and r[1].strip() not in ('', '.'):
            datetime.date.fromisoformat(r[0]); out.append((r[0], float(r[1])))
    return out


def moved(a, b, limit):
    """Is the change from a to b larger than the limit? The limit is a fraction, or ('points', n) for an absolute change."""
    return abs(b - a) > limit[1] if isinstance(limit, tuple) else abs(b / a - 1) > limit


def check(series, new, held, rule, step_months):
    """Check a freshly read series against its limits and against the figures already held. Raises Held with the reason."""
    (low, high), step, revision = rule
    if not new:
        raise Held(f'{series}: nothing was read')
    dates = [d for d, _ in new]
    if dates != sorted(set(dates)):
        raise Held(f'{series}: the dates are out of order or repeated')
    for (d0, v0), (d1, v1) in zip(new, new[1:]):
        y0, m0, y1, m1 = int(d0[:4]), int(d0[5:7]), int(d1[:4]), int(d1[5:7])
        gap = (y1 * 12 + m1) - (y0 * 12 + m0)
        if gap == step_months and moved(v0, v1, step):
            raise Held(f'{series}: {v0:g} in {d0[:7]} to {v1:g} in {d1[:7]} is a larger change than this series makes')
    for d, v in new:
        if not low <= v <= high:
            raise Held(f'{series}: {v:g} for {d[:7]} is outside {low:g} to {high:g}')
        if d in held and moved(held[d], v, revision):
            raise Held(f'{series}: {d[:7]} was {held[d]:g} and now reads {v:g}, a larger revision than this series gets')
    behind = lambda a, b: (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7]))
    if held and behind(max(dates), max(held)) > step_months:               # one step behind is allowed: a first reading entered by hand
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


INPUTS = ['data/latest_monthly.csv', 'data/quarterly.csv', 'data/latest.json', 'data/approval_polls.json', 'data/state_index_this_term.csv', 'data/outlook.json', 'locked_keys.csv',
          'run_2028.py', 'build.py']


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


def archive(pr, report, made, commit=''):
    """Write this run to the archive under its own time stamp, unless nothing in it differs from the last one kept."""
    os.makedirs(ARCHIVE, exist_ok=True)
    index_path = os.path.join(ARCHIVE, 'index.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else []
    inputs = {p: sha(os.path.join(HERE, p)) for p in INPUTS}
    body = {k: v for k, v in pr.items() if k != 'as_of'}
    if index:
        last = json.load(open(os.path.join(ARCHIVE, index[-1]['file'])))
        if {k: v for k, v in last['projection'].items() if k != 'as_of'} == body and last['inputs'] == inputs:
            return None
    sys.path.insert(0, HERE)
    from make_page import TEXT
    text = {k: v[0] for k, v in TEXT.items()}
    why = changes(json.load(open(os.path.join(ARCHIVE, index[-1]['file'])))['projection'], pr, text) if index else ['The first archived run.']
    name = made.strftime('%Y-%m-%dT%H%M%SZ') + '.json'
    entry = {'made': made.strftime('%Y-%m-%dT%H:%M:%SZ'), 'model': {'keys': inputs['locked_keys.csv'], 'engine': pr.get('engine')}, 'commit': commit, 'inputs': inputs,
             'assumptions': json.load(open(os.path.join(D, 'outlook.json'))), 'checks': report, 'changes': why, 'projection': pr}
    with open(os.path.join(ARCHIVE, name), 'x') as f:                        # 'x': an archive file is written once and never again
        json.dump(entry, f, indent=1)
    index.append(dict(summary(pr), file=name, made=entry['made'], engine=pr.get('engine'), changes=why))
    json.dump(index, open(index_path, 'w'), indent=1)
    return name


def main(argv):
    offline = '--offline' in argv
    trust = set(argv[argv.index('--trust') + 1].replace(',', ' ').split()) if '--trust' in argv and len(argv) > argv.index('--trust') + 1 else set()
    made = datetime.datetime.now(datetime.timezone.utc)
    today = made.astimezone(ZoneInfo('America/New_York')).date()
    report = {'read': [], 'new': [], 'held': [], 'failed': [], 'trusted': sorted(trust)}
    latest_path = os.path.join(D, 'latest.json')
    latest = json.load(open(latest_path))
    if not offline:
        refresh_table(os.path.join(D, 'latest_monthly.csv'), MONTHLY, today, trust, report, monthly=True)
        refresh_table(os.path.join(D, 'quarterly.csv'), QUARTERLY, today, trust, report, monthly=False)
        refresh_prices(latest, today, trust, report)
        refresh_states(os.path.join(D, 'state_index_this_term.csv'), trust, report)
        refresh_polls(os.path.join(D, 'approval_polls.json'), today, trust, report)
        latest['as_of'] = str(today)
        json.dump(latest, open(latest_path, 'w'), indent=1)
    for line in report['held'] + report['failed']:
        print('::warning::' + line)
    print(f"read {len(report['read'])} sources; new figures: {json.dumps(report['new'])}")
    run = lambda script: subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    run('run_2028.py')
    pr = json.load(open(os.path.join(HERE, 'projection_2028.json')))
    name = archive(pr, report, made, os.environ.get('GITHUB_SHA', ''))
    print('archived as ' + name if name else 'nothing changed since the last archived run')
    run('make_page.py')
    json.dump(dict(report, made=made.strftime('%Y-%m-%dT%H:%M:%SZ')), open(os.path.join(D, 'update_log.json'), 'w'), indent=1)
    if report['held'] or report['failed']:
        print('::error::Some figures were not updated; the page was rebuilt with the last good ones. See the warnings above.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
