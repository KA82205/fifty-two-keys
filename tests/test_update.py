"""The weekly update: figures are checked before they are used, a bad one is held back, and the archive is never rewritten.

    python tests/test_update.py
"""
import copy, json, os, sys, tempfile

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, HERE)
import update                              # noqa: E402

RULE = update.MONTHLY['UNRATE']
GOOD = [('2026-08-01', 4.1), ('2026-09-01', 4.2), ('2026-10-01', 4.1)]


def held(fn):
    try:
        fn()
    except update.Held as err:
        return str(err)
    return None


def test_checks():
    check = lambda new, old=None, rule=RULE, name='UNRATE': held(lambda: update.check(name, new, old or {}, rule, 1))
    assert check(GOOD) is None and check(GOOD, dict(GOOD)) is None
    assert 'nothing was read' in check([])
    assert 'outside' in check(GOOD + [('2026-11-01', 41.0)]) or 'larger change' in check(GOOD + [('2026-11-01', 41.0)])       # a slipped decimal point
    assert 'larger change' in check(GOOD + [('2026-11-01', 7.0)])
    assert 'revision' in check(GOOD, {'2026-09-01': 5.1})                                         # a figure already held that now reads very differently
    assert 'out of order' in check(GOOD[::-1])
    assert 'well before' in check(GOOD[:1], dict(GOOD))                                           # a download that stops early
    assert check(GOOD[:2], dict(GOOD)) is None                                                    # one step behind is allowed (a first reading entered by hand)
    assert check([('2026-09-01', 159128.0), ('2026-10-01', 159293.0)], rule=update.MONTHLY['PAYEMS'], name='PAYEMS') is None
    assert 'outside' in check([('2026-10-01', 159.293)], rule=update.MONTHLY['PAYEMS'], name='PAYEMS')       # the same series in other units


def test_history_is_let_be_and_new_figures_are_not():
    """The quarterly table reaches back through 2020 and 2021. Those swings must not make the checks on new figures any
    looser: a wrong unit, a slipped decimal point or a corrupt value in a newly published quarter is held back, and so is a
    real move as large as 2020 until somebody has looked at it."""
    import csv
    rows = list(csv.DictReader(open(os.path.join(HERE, 'data', 'quarterly.csv'))))
    Q = update.QUARTERLY
    col = lambda c: sorted((r['observation_date'], float(r[c])) for r in rows)
    nxt = lambda d: f'{int(d[:4]) + (int(d[5:7]) + 3 > 12)}-{(int(d[5:7]) + 2) % 12 + 1:02d}-01'
    chk = lambda c, new, old: held(lambda: update.check(c, new, old, Q[c], 3))
    for c in Q:
        old = col(c); last_d, last_v = old[-1]; d = nxt(last_d); held_now = dict(old)
        growth = isinstance(Q[c][1], tuple)
        # the table as it stands, read again: accepted, 2020 and 2021 included
        assert chk(c, old, held_now) is None, c
        # the whole history lightly revised, as the statistical agencies do every year: accepted
        nudged = [(x, v + 0.3 if growth else v * 1.002) for x, v in old]
        assert chk(c, nudged, held_now) is None, c
        # an ordinary new quarter: accepted
        assert chk(c, old + [(d, last_v + 1.0 if growth else last_v * 1.004)], held_now) is None, c
        # a new quarter in the wrong units, with a slipped decimal point, a flipped sign, a zero, or not a number: all held back
        bad = [last_v + 25, last_v - 25, float('nan')] if growth else [last_v * 1000, last_v / 1000, last_v * 10, last_v / 10, -last_v, 0.0, last_v * 1.2, last_v * 0.85, float('nan')]
        if c == 'A067RL1Q156SBEA':
            bad = [last_v + 40, last_v - 40, float('nan')]
        for v in bad:
            assert chk(c, old + [(d, v)], held_now), (c, v)
        # history that comes back in other units, or re-based: held back, not swallowed as a revision
        for other in ([(x, v * 3) if abs(v) > 3 else (x, v) for x, v in old] if growth else [(x, v * 1.15) for x, v in old], [(x, v + 9 if growth else v * 1000) for x, v in old]):
            why = chk(c, other, held_now)
            assert why and ('revision' in why or 'outside' in why), (c, why)
    # a move as large as spring 2020 arriving as a NEW figure is held back, though the same figures sit in the table untouched
    g = col('A191RL1Q225SBEA'); i = [x for x, _ in g].index('2020-04-01')
    assert 'larger change' in chk('A191RL1Q225SBEA', g[:i + 1], dict(g[:i]))
    assert 'larger change' in chk('A191RL1Q225SBEA', g[:i + 2], dict(g[:i + 1]))
    # and a table read from nothing is held too: the first load of a table needs --trust
    assert chk('A191RL1Q225SBEA', g, {})
    # the monthly series and the state indexes follow the same rule
    for c, rule in list(update.MONTHLY.items()) + [('PAPHCI', update.STATE_RULE)]:
        v0 = {'UNRATE': 4.1, 'PAYEMS': 159293.0, 'MANEMP': 12700.0, 'CPIAUCSL': 330.0, 'INDPRO': 103.0, 'DPCERA3M086SBEA': 126.0, 'CES0600000008': 38.0, 'HOUST': 1350.0, 'UMCSENT': 55.0,
              'MCOILWTICO': 80.0, 'SP500': 7000.0, 'ICSA': 230000.0, 'PAPHCI': 150.0}[c]
        old = [('2026-08-01', v0), ('2026-09-01', v0)]
        assert held(lambda: update.check(c, old + [('2026-10-01', v0)], dict(old), rule, 1)) is None
        for v in (v0 * 1000, v0 / 1000, v0 * 100, v0 / 100, -v0, 0.0):
            assert held(lambda: update.check(c, old + [('2026-10-01', v)], dict(old), rule, 1)), (c, v)


def test_a_missing_value_is_not_a_zero():
    real = update.get
    try:
        update.get = lambda url, **k: 'observation_date,UNRATE\n2026-08-01,4.1\n2026-09-01,.\n2026-10-01,\n2026-11-01,4.3\n'
        assert update.fred('UNRATE', '2026-08-01') == [('2026-08-01', 4.1), ('2026-11-01', 4.3)]
        update.get = lambda url, **k: '<html>Service unavailable</html>'
        assert 'not a table' in held(lambda: update.fred('UNRATE', '2026-08-01'))
    finally:
        update.get = real


def test_a_failed_series_keeps_its_figures():
    real, path = update.fred, os.path.join(tempfile.mkdtemp(), 'm.csv')
    open(path, 'w').write('observation_date,UNRATE,PAYEMS\n2026-09-01,4.2,159128\n2026-10-01,4.1,159293\n')
    def fake(series, start, monthly_average=False):
        if series == 'UNRATE':
            return [('2026-09-01', 4.2), ('2026-10-01', 4.1), ('2026-11-01', 44.0)]              # a broken figure
        return [('2026-09-01', 159128.0), ('2026-10-01', 159301.0), ('2026-11-01', 159340.0)]    # a small revision and a new month
    try:
        update.fred = fake
        report = {'read': [], 'new': [], 'held': [], 'failed': []}
        import datetime
        update.refresh_table(path, {'UNRATE': update.MONTHLY['UNRATE'], 'PAYEMS': update.MONTHLY['PAYEMS']}, datetime.date(2026, 12, 7), set(), report, monthly=True)
    finally:
        update.fred = real
    assert open(path).read() == 'observation_date,UNRATE,PAYEMS\n2026-09-01,4.2,159128\n2026-10-01,4.1,159301\n2026-11-01,,159340\n', open(path).read()
    assert len(report['held']) == 1 and 'UNRATE' in report['held'][0] and report['read'] == ['PAYEMS']
    assert report['new'] == [{'series': 'PAYEMS', 'through': '2026-11', 'was': '2026-10'}]


def test_the_archive_is_written_once():
    pr = json.load(open(os.path.join(HERE, 'projection_2028.json')))
    import datetime
    t = datetime.datetime(2030, 1, 7, 12, 0, 0, tzinfo=datetime.timezone.utc)
    real = update.ARCHIVE
    try:
        update.ARCHIVE = tempfile.mkdtemp()
        first = update.archive(pr, {'held': []}, t)
        assert first == '2030-01-07T120000Z.json'
        kept = json.load(open(os.path.join(update.ARCHIVE, first)))
        assert kept['figures']['monthly'][0][0] == 'observation_date' and kept['assumptions']['settled'] and kept['model']['engine'] and kept['inputs']['locked_keys.csv']
        assert update.archive(pr, {'held': []}, t + datetime.timedelta(days=7)) is None, 'nothing changed, so nothing is archived'
        before = open(os.path.join(update.ARCHIVE, first)).read()
        later = copy.deepcopy(pr); k = sorted(later['keys'])[0]
        was = later['keys'][k]['p']; later['keys'][k]['p'] = 0.9 if was < 0.5 else 0.1
        second = update.archive(later, {'held': []}, t + datetime.timedelta(days=14))
        assert second and second != first and open(os.path.join(update.ARCHIVE, first)).read() == before
        try:
            update.archive(pr, {'held': []}, t + datetime.timedelta(days=14))                     # the same time stamp again
        except FileExistsError:
            pass
        else:
            raise AssertionError('an archive file was rewritten')
        index = json.load(open(os.path.join(update.ARCHIVE, 'index.json')))
        assert [e['file'] for e in index] == [first, second] and index[0]['changes'] == ['The first archived run.']
        assert any(k in line and 'now leans' in line for line in index[1]['changes']), index[1]['changes']
    finally:
        update.ARCHIVE = real


def test_changes_are_explained():
    old = {'keys': {'A05': {'p': 0.40, 'note': ''}, 'B04': {'p': 0.30, 'note': ''}, 'E05': {'p': 0.7, 'note': ''}}, 'data_through': {'monthly': 'October 2026', 'quarterly': '2026 Q3'}, 'engine': '1'}
    new = {'keys': {'A05': {'p': 0.56, 'note': ''}, 'B04': {'p': 0.0, 'note': 'It was 4.0% in January 2025 and 4.4% in June 2028.', 'landed': True}},
           'data_through': {'monthly': 'November 2026', 'quarterly': '2026 Q3'}, 'engine': '1'}
    got = update.changes(old, new, {'A05': 'Unemployment is lower than a year ago', 'B04': 'Unemployment is lower than when the term began', 'E05': 'The nominee won New Hampshire'})
    assert got[0] == 'Monthly figures now run through November 2026 (were October 2026).'
    assert 'E05 (The nominee won New Hampshire) was settled.' in got
    assert any(line.startswith('B04') and 'landed: no' in line for line in got) and any(line.startswith('A05') and 'now leans yes: 56%, from 40%' in line for line in got)


if __name__ == '__main__':
    test_checks(); test_history_is_let_be_and_new_figures_are_not(); test_a_missing_value_is_not_a_zero(); test_a_failed_series_keeps_its_figures(); test_the_archive_is_written_once(); test_changes_are_explained()
    print('ok (checks, held figures, the archive)')
