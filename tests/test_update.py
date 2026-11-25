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
    test_checks(); test_a_missing_value_is_not_a_zero(); test_a_failed_series_keeps_its_figures(); test_the_archive_is_written_once(); test_changes_are_explained()
    print('ok (checks, held figures, the archive)')
