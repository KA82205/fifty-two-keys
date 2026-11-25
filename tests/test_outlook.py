"""The forecasters' outlook, read from a made-up copy of the survey's table: only a later survey replaces it.

    python tests/test_outlook.py

The workbooks here are built in memory in the layout outlook.py expects (one sheet a series, a row a survey, columns 1 to 6
and A to D). They show that the reading rule does what it says. They do not show that the Philadelphia Fed's own file has
that layout: the hourly run's line "The outlook: ..." shows that, on the real file.
"""
import datetime, io, json, os, shutil, sys, tempfile

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import outlook as O                                     # noqa: E402
from test_engine import case, rerun                     # noqa: E402

TODAY = datetime.date(2027, 2, 14)


def workbook(when, gdp, gdp_year, jobs, jobs_year, cpi, cpi_year, u, u_year=(4.3, 4.2, 4.2), drop=None, scale=1.0):
    """A survey: growth by quarter (five figures) and for the next years, jobs a month the same way, inflation, unemployment."""
    import openpyxl
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    def sheet(name, quarters, years):
        ws = wb.create_sheet(name); ws.append(['YEAR', 'QUARTER'] + [f'{name}{i}' for i in range(1, 7)] + [f'{name}{c}' for c in 'ABCD'])
        ws.append([when[0] - 1, when[1]] + [1.0] * 6 + [1.0] * 4)                     # an older survey, which is not the one read
        ws.append([when[0], when[1]] + quarters + years)
    lv = [24000.0]
    for r in gdp:
        lv.append(lv[-1] * (1 + r / 100) ** 0.25)
    ya = [23900.0]
    for r in gdp_year:
        ya.append(ya[-1] * (1 + r / 100) if r is not None else None)
    sheet('RGDP', lv, (ya + [None] * 4)[:4])
    em = [160000.0 * scale]
    for j in jobs:
        em.append(em[-1] + 3 * j * scale)
    ea = [159500.0 * scale]
    for j in jobs_year:
        ea.append(ea[-1] + 12 * j * scale if j is not None else None)
    sheet('EMP', em, (ea + [None] * 4)[:4])
    sheet('CPI', [3.0] + cpi, (cpi_year + [None] * 4)[:4])
    sheet('UNEMP', [4.3] + u, (list(u_year) + [None] * 4)[:4])
    if drop:
        del wb[drop]
    b = io.BytesIO(); wb.save(b)
    return b.getvalue()


# the survey of November 2026 as it was entered by hand, and a made-up survey for February 2027
NOV = dict(when=(2026, 4), gdp=[2.3, 2.1, 2.2, 2.2, 2.1], gdp_year=[2.2, 2.1], jobs=[90, 65, 49, 51, 51], jobs_year=[55, 50], cpi=[4.0, 2.6, 2.4, 2.4, 2.4], cpi_year=[3.8, 2.4, 2.3],
           u=[4.2, 4.2, 4.2, 4.2, 4.2])
FEB = dict(when=(2027, 1), gdp=[1.4, 1.2, 1.6, 1.9, 2.0], gdp_year=[1.8], jobs=[30, 20, 40, 45, 60], jobs_year=[None], cpi=[3.1, 2.9, 2.7, 2.6, 2.5], cpi_year=[2.8, 2.4],
           u=[4.4, 4.6, 4.7, 4.7, 4.8], u_year=[4.6, 4.9])


def scratch():
    d = tempfile.mkdtemp(); path = os.path.join(d, 'outlook.json'); shutil.copy(os.path.join(HERE, 'data', 'outlook.json'), path)
    c = json.load(open(path)); c.update(outlook_survey='2026Q4', outlook_date='2026-11-16'); c.pop('outlook_entered', None)
    c['outlook'].update(gdp=[2.3, 2.1, 2.2, 2.2, 2.1, 2.1, 2.1], cpi_quarters=[4.0, 2.6, 2.4, 2.4, 2.4, 2.3, 2.3, 2.3], unemployment=4.2,
                        jobs_a_month=[90, 90, 65, 65, 65, 49, 49, 49, 51, 51, 51, 51, 51, 51, 50, 50, 50, 50, 50, 50])
    json.dump(c, open(path, 'w'), indent=1)
    return path


def test_the_same_survey_changes_nothing_and_the_rule_gives_what_was_entered():
    path = scratch(); before = open(path).read()
    state, words = O.refresh(TODAY, path, lambda: workbook(**NOV))
    assert state == 'same' and open(path).read() == before, (state, words)
    assert 'it would give' not in words, 'read by rule, the November survey gives the figures entered by hand: ' + words


def test_a_later_survey_replaces_the_part_it_gives_and_nothing_else():
    path = scratch(); old = json.load(open(path))
    state, words = O.refresh(TODAY, path, lambda: workbook(**FEB))
    new = json.load(open(path)); o, was = new['outlook'], old['outlook']
    assert state == 'new' and new['outlook_survey'] == '2027Q1' and new['outlook_date'] == str(TODAY) and new['outlook_entered'] == '2026-11-16'
    assert o['gdp'] == [2.3, 1.4, 1.2, 1.6, 1.9, 2.0, 1.8], o['gdp']                  # 2026 Q4 kept; five quarters from the survey; 2028 Q2 from its figure for 2028
    assert o['cpi_quarters'] == [4.0, 3.1, 2.9, 2.7, 2.6, 2.5, 2.4, 2.4], o['cpi_quarters']
    assert o['jobs_a_month'] == [90, 90] + [30] * 3 + [20] * 3 + [40] * 3 + [45] * 3 + [60] * 6, o['jobs_a_month']     # no figure for 2028: the last quarter is carried on
    assert o['unemployment'] == 4.9                                                   # the survey's figure for 2028: its five quarters stop at 2028 Q1
    reach = dict(FEB, when=(2027, 3), u=[4.4, 4.5, 4.6, 4.7, 4.75])                  # a survey that reaches 2028 Q2 gives that quarter's own figure
    path2 = scratch(); O.refresh(TODAY, path2, lambda: workbook(**reach)); assert json.load(open(path2))['outlook']['unemployment'] == 4.7
    for k in ('income', 'hourly_pay', 'spending', 'industrial_production', 'factory_jobs', 'oil', 'sentiment', 'population', 'recession_share'):
        assert o[k] == was[k], k
    assert new['politics'] == old['politics'] and new['settled'] == old['settled'] and 'typed on 2026-11-16 is kept here and not read' in new['outlook_note']
    again, _ = O.refresh(TODAY + datetime.timedelta(days=1), path, lambda: workbook(**FEB))
    assert again == 'same' and json.load(open(path)) == new, 'the same survey read twice is one change'


def test_a_survey_that_cannot_be_used_leaves_the_outlook_alone():
    def down():
        raise TimeoutError('timed out')
    for read, want in ((down, 'unreachable'), (lambda: b'<html>not a workbook</html>', 'unreadable'), (lambda: workbook(**FEB, drop='EMP'), 'unreadable'),
                       (lambda: workbook(**dict(FEB, jobs=[30000, 20000, 40000, 45000, 60000])), 'unreadable'),          # jobs in units, not thousands
                       (lambda: workbook(**dict(FEB, cpi=[3.1, None, 2.7, 2.6, 2.5])), 'unreadable')):                  # a quarter missing
        path = scratch(); before = open(path).read()
        state, words = O.refresh(TODAY, path, read)
        assert state == want and open(path).read() == before and 'the outlook in hand stays' in words, (state, words)


def test_a_new_survey_moves_the_chances_and_calls_nothing():
    """The whole way: a gloomier survey in February 2027 is read, the run-ahead is rerun, the open economy keys move and no key is called."""
    def read_it(dst):
        state, _ = O.refresh(datetime.date(2027, 3, 20), os.path.join(dst, 'data', 'outlook.json'), lambda: workbook(**FEB))
        assert state == 'new'
    pr, dst = case((2027, 2), '2027-03-20', keep=True)
    assert pr['outlook_from']['stale']
    pr2 = rerun(dst, edit=read_it)
    shutil.rmtree(os.path.dirname(dst))
    assert not pr2['outlook_from']['stale'] and 'Survey of Professional Forecasters, 2027 Q1' in pr2['outlook_from']['source']
    assert pr2['keys']['A01']['p'] < pr['keys']['A01']['p'] - 0.02 and pr2['keys']['B01']['p'] < pr['keys']['B01']['p'] - 0.05 and pr2['keys']['B04']['p'] < pr['keys']['B04']['p'] - 0.05
    assert pr2['index']['mean'] < pr['index']['mean']
    assert {i: (c['status'], c['value']) for i, c in pr2['calls'].items()} == {i: (c['status'], c['value']) for i, c in pr['calls'].items()}


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
