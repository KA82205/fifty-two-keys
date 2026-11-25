"""The calls, from today to the day the count is closed, on made-up future figures and a clock set by hand.

    python tests/test_calls.py

Every case runs in a copy of the repository in a temporary folder (tests/test_engine.py makes it). Nothing here touches the
repository's own figures, record or projection, and nothing here says anything about what will happen: the future months are
a fixed random walk.
"""
import csv, json, os, shutil, sys

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import build as B, calls as C                           # noqa: E402
from test_engine import case, rerun                     # noqa: E402

ECON = {i for i in C.IDS if i[0] in 'AB'}
POLL = {i for i in C.IDS if i[0] == 'C'}
LATE = ['E03', 'E04', 'E05', 'E06', 'E07']
FAST = '3000'


def status(pr, s):
    return {i for i, c in pr['calls'].items() if c['status'] == s}


def csv_edit(name, change):
    def edit(dst):
        path = os.path.join(dst, 'data', name); rows = list(csv.reader(open(path))); change(rows)
        csv.writer(open(path, 'w', newline=''), lineterminator='\n').writerows(rows)
    return edit


def enter(**keys):
    """Enter evidence for keys, as it is entered by hand: in the settled block of data/outlook.json."""
    def edit(dst):
        path = os.path.join(dst, 'data', 'outlook.json'); c = json.load(open(path))
        c['settled'].update({k: {'value': v, 'why': 'Made up for the test.'} for k, v in keys.items()}); json.dump(c, open(path, 'w'))
    return edit


def both(*edits):
    return lambda dst: [e(dst) for e in edits]


NH = csv_edit('nh_primaries.csv', lambda rows: rows.append(['2028', 'Made-up R', '41', '1', 'Made-up R', 'Made-up D', '33', '0']))
SEATS = csv_edit('congress_seats.csv', lambda rows: rows.append(['120', '2027', '56', '44', '257', '178', 'made up for the test']))


def record(dst):
    return C.read_history(os.path.join(dst, 'data', 'key_calls.csv'))


def test_the_list_has_every_key_and_matches_the_rules():
    rows = C.registry()
    assert [r['id'] for r in rows] == C.IDS and len(rows) == 52 and [r['key'] for r in rows] == B.ALL
    need = ('question', 'rule', 'depends_on', 'compares', 'sign', 'with', 'a_tie_counts_as', 'scored_by', 'sources', 'window_closes', 'earliest_call', 'count_closes', 'revisions',
            'called_yes', 'called_no', 'stays_open', 'checked', 'checks', 'if_missing', 'fallback', 'automatic', 'by_hand', 'remedy')
    for r in rows:
        assert all(r.get(k) for k in need), (r['id'], [k for k in need if not r.get(k)])
        assert all(s['series'] and s['published_by'] and s['units'] and s['comes_out'] and s['licence'] for s in r['sources']), r['id']
        assert r['sign'] in ('>', '<', '>=', 'is', 'is not')
    # ties: the model's convention is that a tie is no unless the rule says "at least" or "did not lose"
    yes = {r['id'] for r in rows if r['a_tie_counts_as'] == 'yes'}
    assert yes == {'B01', 'C01', 'D03', 'D05', 'D06', 'E04'}, yes
    # every economy series the list names is one update.py reads and checks
    import update as U
    read = set(U.MONTHLY) | set(U.QUARTERLY) | {'SP500', 'ICSA', 'MCOILWTICO'}
    named = {x for r in rows if r['group'] in 'AB' and r['id'] not in ('A18', 'B15') for s in r['sources'] for x in s['series']}
    assert named <= read, named - read
    on_disk = json.load(open(os.path.join(HERE, 'data', 'key_registry.json')))['keys']
    assert on_disk == json.loads(json.dumps(rows)), 'data/key_registry.json is out of date: run python calls.py'
    assert sum(r['automatic'] == 'yes' for r in rows) == 41 and {r['id'] for r in rows if r['automatic'] != 'yes'} == {'D01', 'D02', 'D03', 'D05', 'D06', 'E01', 'E03', 'E04', 'E05', 'E06', 'E07'}


def test_today():
    pr = json.load(open(os.path.join(HERE, 'projection_2028.json')))
    assert set(pr['calls']) == set(C.IDS)
    n = pr['count']
    assert n['settled'] + n['provisional'] + n['unresolved'] + n['held'] == 52 and n['held'] == 0 and n['provisional'] == 0
    assert status(pr, 'settled') == {'D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'E01', 'E02'}
    assert all(pr['calls'][i]['evidence'] for i in status(pr, 'settled')) and all(pr['calls'][i]['why'] for i in status(pr, 'unresolved'))
    assert 'observed' not in pr, 'with keys open the count is a projection, and is not called observed'
    assert abs(sum(s for _, s in pr['index_dist']) - 1) < 1e-3 and abs(sum(v * s for v, s in pr['index_dist']) - pr['index']['mean']) < 0.004
    assert abs(pr['index']['expected_in_favor'] - (sum(k['p'] for k in pr['keys'].values()) + n['in_favor'])) < 0.05
    last = {}
    for r in C.read_history():
        last[r['key']] = r
    assert set(last) == status(pr, 'settled') and all((last[i]['value'] == '1') == pr['calls'][i]['value'] for i in last), 'the record agrees with the calls'


def test_from_now_to_the_close():
    """The same made-up future, read on seven days. A key moves only when its own evidence exists."""
    # summer 2027: a year of new figures, and nothing can be called
    pr = case((2027, 6), '2027-07-20', runs=FAST)
    assert status(pr, 'settled') == {'D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'E01', 'E02'} and not status(pr, 'provisional') and not status(pr, 'held')
    assert pr['horizon']['months_left'] == 12 and pr['horizon']['quarters_left'] == 4 and pr['outlook_from']['stale'], 'eight months of new figures, and an outlook two surveys old'
    # leap day 2028
    pr = case((2028, 1), '2028-02-29', runs=FAST)
    assert not status(pr, 'provisional') and pr['horizon']['months_left'] == 5 and pr['through']['UNRATE'] == 'January 2028'
    # June 25, 2028: May is the last month out. June has not ended; nothing is scored on it
    pr = case((2028, 5), '2028-06-25', runs=FAST)
    assert not status(pr, 'provisional') and pr['horizon']['months_left'] == 1 and all(0 <= k['p'] <= 1 for k in pr['keys'].values())
    # July 20: the June monthly figures are out, second-quarter GDP is not. Monthly keys are scored, not final; GDP keys stay open
    pr, dst = case((2028, 6), '2028-07-20', last_quarter=(2028, 1), states=False, keep=True, runs=FAST)
    waits_gdp = {'A01', 'A02', 'A04', 'A10', 'B01', 'B03', 'B08'}
    assert status(pr, 'provisional') == (ECON - waits_gdp - {'A18', 'B15'}) | POLL, sorted(status(pr, 'provisional') ^ ((ECON - waits_gdp - {'A18', 'B15'}) | POLL))
    assert all(not pr['calls'][i]['final'] for i in status(pr, 'provisional')) and all(pr['keys'][i]['p'] in (0, 1) for i in status(pr, 'provisional'))
    assert all(0 < pr['keys'][i]['p'] < 1 for i in ('A01', 'B01')) and pr['horizon']['months_left'] == 0 and pr['horizon']['quarters_left'] == 1
    assert status(pr, 'held') == set(LATE), 'the nomination keys should have been entered by July 15: they are held, not scored as no'
    assert all(0 < pr['keys'][i]['p'] < 1 for i in LATE) and 'observed' not in pr
    n = len(record(dst))
    assert rerun(dst, runs=FAST)['calls'] == pr['calls'] and len(record(dst)) == n, 'the same day again: the same calls, and nothing added to the record'
    # a figure is revised before the close: the key is scored again, and the record keeps both
    flip = 'no' if pr['calls']['A05']['value'] else 'yes'
    def revise(rows):
        col = rows[0].index('UNRATE'); june27 = next(r for r in rows if r[0] == '2027-06-01'); june28 = next(r for r in rows if r[0] == '2028-06-01')
        june28[col] = f"{float(june27[col]) + (0.3 if flip == 'no' else -0.3):.1f}"
    pr2 = rerun(dst, '2028-07-25', csv_edit('latest_monthly.csv', revise), runs=FAST)
    assert pr2['calls']['A05']['value'] == (flip == 'yes') and pr2['calls']['A05']['status'] == 'provisional'
    assert [r['value'] for r in record(dst) if r['key'] == 'A05'] == (['1', '0'] if flip == 'no' else ['0', '1'])
    shutil.rmtree(os.path.dirname(dst))


def test_the_close_and_after():
    pr, dst = case((2028, 6), '2028-08-05', keep=True, runs=FAST)
    assert status(pr, 'settled') >= ECON | POLL and all(pr['calls'][i]['final'] for i in ECON | POLL) and pr['count']['closed']
    assert status(pr, 'held') == set(LATE) and 'observed' not in pr, 'five keys have no evidence: the count is not called complete, and no key is counted as no for want of it'
    assert all(0 < pr['keys'][i]['p'] < 1 for i in LATE)
    was = pr['calls']['A06']
    # a revision after the close is noted and does not change the call
    def revise(rows):
        col = rows[0].index('PAYEMS'); june27 = next(r for r in rows if r[0] == '2027-06-01'); june28 = next(r for r in rows if r[0] == '2028-06-01')
        june28[col] = f"{float(june27[col]) * (0.99 if was['value'] else 1.01):.0f}"
    pr2 = rerun(dst, '2028-09-10', csv_edit('latest_monthly.csv', revise), runs=FAST)
    assert pr2['calls']['A06']['value'] == was['value'] and pr2['calls']['A06']['final'] and 'revised_since' in pr2['calls']['A06'] and pr2['keys']['A06']['p'] == float(was['value'])
    # the nomination keys and the seat counts are entered: every key is called, and every run gives the count the rules give
    pr3 = rerun(dst, '2028-09-11', both(enter(E03=1, E04=0), NH, SEATS), runs=FAST)
    assert not status(pr3, 'held') and not status(pr3, 'unresolved') and pr3['count']['settled'] == 52 and pr3['count']['final'] == 52
    values = {i: c['value'] for i, c in pr3['calls'].items()}
    assert pr3['observed'] == {'index': round(C.index(values), 4), 'in_favor': sum(values.values()), 'final': True}
    assert pr3['index']['mean'] == pr3['index']['p5'] == pr3['index']['p95'] == round(C.index(values), 3) and len(pr3['index_dist']) == 1
    assert (values['E05'], values['E06'], values['E07']) == (True, True, True) and pr3['calls']['D02']['basis'] == 'rule'
    assert pr3['keys'].keys() == (ECON | POLL), 'the keys called on events leave the run-ahead list'
    # once final, a call is not undone by a later entry
    pr4 = rerun(dst, '2028-09-12', enter(D02=1), runs=FAST)
    assert pr4['calls']['D02'] == dict(pr3['calls']['D02'], revised_since=pr4['calls']['D02'].get('revised_since')) and 'stands' in pr4['calls']['D02']['revised_since'] and pr4['observed'] == pr3['observed']
    shutil.rmtree(os.path.dirname(dst))
    # before that, an entry that the seat counts contradict is held: the run goes on with the call the key had, and says so
    pr5 = case((2027, 6), '2027-07-20', edit=both(enter(D02=1), SEATS), runs=FAST)
    c = pr5['calls']['D02']
    assert c['status'] == 'held' and 'disagree' in c['basis'] and c['value'] is None and c['last'] is False and pr5['count']['held'] == 1
    assert pr5['groups']['D']['mean'] == 0 and pr5['calls']['D01']['basis'] == 'rule' and pr5['calls']['D01']['final']


def test_ties_missing_figures_and_the_other_party():
    """The rules at their edges, through the same function that scores 1952 to 2024."""
    pr, dst = case((2028, 6), '2028-07-20', keep=True, runs=FAST)
    def ties(rows):
        h = rows[0]; row = lambda day: next(r for r in rows if r[0] == day)
        row('2028-06-01')[h.index('UNRATE')] = row('2027-06-01')[h.index('UNRATE')]                 # A05: lower than a year ago? A tie is no
        row('2028-06-01')[h.index('PAYEMS')] = row('2027-06-01')[h.index('PAYEMS')]                 # A06: more jobs? A tie is no
        row('2028-06-01')[h.index('UMCSENT')] = row('2027-06-01')[h.index('UMCSENT')]               # A16
    def polls(dst):
        path = os.path.join(dst, 'data', 'approval_polls.json'); P = json.load(open(path))
        P['polls'] = [p for p in P['polls'] if not ('2028-05-01' <= p['end'] <= '2028-06-30')]
        P['polls'].append({'id': 'tie', 'pollster': 'Made-up Poll A', 'start': '2028-06-10', 'end': '2028-06-12', 'population': 'a', 'n': 1000, 'approve': 50.0, 'disapprove': 50.0, 'internal': False, 'url': ''})
        json.dump(P, open(path, 'w'))
    pr = rerun(dst, edit=both(csv_edit('latest_monthly.csv', ties), polls), runs=FAST)
    c = pr['calls']
    assert (c['A05']['value'], c['A06']['value'], c['A16']['value']) == (False, False, False), 'a tie is no where the rule asks for an improvement'
    assert c['C01']['value'] is True and c['C02']['value'] is False and c['C06']['value'] is False, 'exactly 50%: at least half approve, not more than disapprove, and not fewer than half disapprove'
    # a figure held back by the checks: the keys that read it are held, with a chance, whatever the file says
    pr = rerun(dst, runs=FAST, held='UNRATE', edit=csv_edit('latest_monthly.csv', lambda rows: next(r for r in rows if r[0] == '2028-06-01').__setitem__(rows[0].index('UNRATE'), '')))
    assert {'A05', 'A09', 'B04'} <= status(pr, 'held') and all('held back' in pr['calls'][i]['why'] for i in ('A05', 'A09', 'B04')) and any(0 < pr['keys'][i]['p'] < 1 for i in ('A05', 'A09', 'B04'))
    # a row dated after the day of the run is not read
    pr = rerun(dst, '2028-05-20', runs=FAST)
    assert pr['through']['PAYEMS'] == 'May 2028' and not status(pr, 'provisional'), 'on May 20 the file may hold June: it is not read'
    shutil.rmtree(os.path.dirname(dst))
    # the other party in office: the same seat counts, read the other way (in this process, on the real files)
    import run_2028 as R
    keep = dict(C.CYCLE)
    try:
        for party, house in (('R', False), ('D', True)):
            C.CYCLE['party'] = party
            d, have = C.figures(R.P, R.QS, R.LEVEL, R.APPROVAL, {})
            d['seats'][2027] = {'house_d': '257', 'house_r': '178', 'senate_d': '50', 'senate_r': '50'}
            k, _, _ = B.score_year(d, 2028)
            assert k['D02_holds_house'] is house and k['D03_holds_senate'] is True, 'a tied Senate is held by the party of the vice president'
            assert k['E02_first_term_party'] is (party == 'R') and k['D04_prev_majority'] is False
    finally:
        C.CYCLE.clear(); C.CYCLE.update(keep)


def test_the_page_and_the_feed_are_built_at_every_stage():
    """The page is written from the run at four points of the same made-up future. Its sentences follow the figures: no stage
    stops the build, a projected count is never shown as a count of calls, and the feed carries every key's state."""
    import subprocess
    def page(dst):
        if not os.path.exists(os.path.join(dst, 'fonts')):
            shutil.copytree(os.path.join(HERE, 'fonts'), os.path.join(dst, 'fonts'))
        r = subprocess.run([sys.executable, 'make_page.py'], cwd=dst, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        return open(os.path.join(dst, 'docs', 'index.html')).read(), json.load(open(os.path.join(dst, 'docs', 'keys.json')))
    pr, dst = case((2027, 6), '2027-07-20', keep=True, runs=FAST)
    html, feed = page(dst); shutil.rmtree(os.path.dirname(dst))
    assert feed['count']['settled'] == 8 and feed['settled'] == 8 and feed['observed'] is None and len(feed['calls']) == 52 and feed['format'] == 2
    assert abs(sum(s for _, s in feed['index_dist']) - 1) < 1e-3 and set(feed['chances']) == set(pr['keys'])
    pr, dst = case((2028, 6), '2028-07-20', last_quarter=(2028, 1), keep=True, runs=FAST)
    html, feed = page(dst); shutil.rmtree(os.path.dirname(dst))
    assert feed['count']['provisional'] == len(status(pr, 'provisional')) > 20 and feed['count']['held'] == 5 and feed['observed'] is None
    assert feed['settled'] == 8 + feed['count']['provisional'], 'the old field counts every key with a call, as it always has'
    pr, dst = case((2028, 6), '2028-08-05', keep=True, runs=FAST)
    html, feed = page(dst)
    assert feed['count']['closed'] and feed['observed'] is None and '"observed":null' in html.replace(' ', '')
    pr = rerun(dst, '2028-09-11', both(enter(E03=1, E04=0), NH, SEATS), runs=FAST)
    html, feed = page(dst); shutil.rmtree(os.path.dirname(dst))
    assert feed['observed'] == pr['observed'] and feed['observed']['final'] and feed['chances'].keys() == (ECON | POLL) and all(v in (0, 1) for v in feed['chances'].values())
    assert '"observed":{' in html.replace(' ', '') and feed['mean'] == feed['median'] == round(pr['observed']['index'], 3)


def test_the_two_copies_of_the_rules_agree():
    """run_2028.py scores the economy and approval keys inside each run; build.score_year scores them for the record. On
    three more made-up futures, with every figure published, the two give the same answer for every key."""
    for seed in (11, 23, 42):
        pr = case((2028, 6), '2028-08-05', seed=seed, runs=FAST)
        assert pr['copy_differs'] == [] and status(pr, 'settled') >= ECON | POLL, (seed, pr['copy_differs'])


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
