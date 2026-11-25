"""The 2028 run-ahead, run on made-up future figures: keys land when their figures are published, and only then.

    python tests/test_engine.py

Each case copies the repository to a temporary folder, extends the figures there with invented months (a fixed random walk,
not a forecast), and runs run_2028.py with fewer runs. Nothing in the repository itself is touched.
"""
import csv, datetime, json, os, random, shutil, subprocess, sys, tempfile

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ECONOMY = {f'{g}{i:02d}' for g, n in (('A', 17), ('B', 14)) for i in range(1, n + 1)}       # every economy key but the two scored from state indexes
STATE_KEYS = {'A18', 'B15'}
APPROVAL = {f'C{i:02d}' for i in range(1, 7)}


def case(last_month, as_of, drop=None, no_polls_in=(), states=True):
    """Run the run-ahead on figures invented through last_month (year, month). Returns the projection."""
    dst = os.path.join(tempfile.mkdtemp(), 'repo')
    shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns('.git', '__pycache__', 'archive', 'docs', 'fonts'))
    rnd, D = random.Random(7), os.path.join(dst, 'data')
    path = os.path.join(D, 'latest_monthly.csv'); rows = list(csv.reader(open(path))); head = rows[0]
    rows = [r for r in rows if all(r[1:4])]                                                    # drop a month that holds only a first reading
    v = {h: float(rows[-1][i] or rows[-2][i]) for i, h in enumerate(head) if i}
    rows[-1] = [x or f'{v[h] * 1.0018:.3f}' for x, h in zip(rows[-1], head)]                    # the one figure still to come for the last month
    step = dict(PAYEMS=55, CPIAUCSL=0.002, INDPRO=0.001, DPCERA3M086SBEA=0.0018, CES0600000008=0.0031, UMCSENT=0.4, MCOILWTICO=-0.012, SP500=0.006)
    y, m = int(rows[-1][0][:4]), int(rows[-1][0][5:7])
    while True:
        m += 1
        if m == 13:
            y, m = y + 1, 1
        if (y, m) > last_month:
            break
        row = [f'{y}-{m:02d}-01']
        for h in head[1:]:
            if h == 'PAYEMS': v[h] += step[h] + rnd.gauss(0, 30)
            elif h == 'UMCSENT': v[h] += step[h] + rnd.gauss(0, 1.5)
            elif h == 'UNRATE': v[h] = round(v[h] + rnd.choice([-0.1, 0, 0, 0.1]), 1)
            else: v[h] *= 1 + step.get(h, 0) + rnd.gauss(0, 0.03 if h in ('SP500', 'MCOILWTICO', 'HOUST', 'ICSA') else 0.003)
            row.append('' if drop == (h, y, m) else f'{v[h]:.3f}')
        rows.append(row)
    csv.writer(open(path, 'w', newline=''), lineterminator='\n').writerows(rows)
    path = os.path.join(D, 'quarterly.csv'); rows = list(csv.reader(open(path))); q = [float(x) for x in rows[-1][1:]]
    y, m = int(rows[-1][0][:4]), int(rows[-1][0][5:7])
    while True:
        m += 3
        if m > 12:
            y, m = y + 1, 1
        if (y, m + 2) > last_month:
            break
        g, i = 2.1 + rnd.gauss(0, 0.8), 2.0 + rnd.gauss(0, 1.0)
        q = [g, i, q[2] * 1.000625, q[3] * (1 + g / 100) ** 0.25 / 1.000625, q[4] * (1 + i / 100) ** 0.25 / 1.000625]
        rows.append([f'{y}-{m:02d}-01', f'{g:.1f}', f'{i:.1f}', f'{q[2]:.0f}', f'{q[3]:.0f}', f'{q[4]:.0f}'])
    csv.writer(open(path, 'w', newline=''), lineterminator='\n').writerows(rows)
    path = os.path.join(D, 'state_index_this_term.csv'); rows = list(csv.reader(open(path))); by = {}
    for st, mo, ix in rows[1:]:
        if ix:
            by.setdefault(st, {})[mo] = float(ix)
    for st, ser in by.items() if states else ():
        mo = max(ser); y, m, x = int(mo[:4]), int(mo[5:7]), ser[mo]
        while True:
            m += 1
            if m == 13:
                y, m = y + 1, 1
            if (y, m) > last_month:
                break
            x *= 1 + rnd.gauss(0.0012, 0.002); ser[f'{y}-{m:02d}'] = x
    csv.writer(open(path, 'w', newline=''), lineterminator='\n').writerows([rows[0]] + [[st, mo, f'{by[st][mo]:.2f}'] for st in by for mo in sorted(by[st])])
    path = os.path.join(D, 'approval_polls.json'); P = json.load(open(path))
    d, a = datetime.date(2026, 11, 20), 33.0
    end = datetime.date.fromisoformat(as_of)
    while d + datetime.timedelta(days=5) <= end:
        d += datetime.timedelta(days=5); a += rnd.gauss(0.05, 0.4)
        if (d.year, d.month) in no_polls_in:
            continue
        for who in ('Made-up Poll A', 'Made-up Poll B'):
            P['polls'].append({'id': f'{who}{d}', 'pollster': who, 'start': str(d), 'end': str(d), 'population': 'a', 'n': 1000, 'approve': round(a + rnd.gauss(0, 1), 1),
                               'disapprove': round(96 - a + rnd.gauss(0, 1), 1), 'internal': False, 'url': ''})
    json.dump(P, open(path, 'w'))
    json.dump({'as_of': as_of, 'sp500': {'date': as_of, 'value': v['SP500'] * 1.01}, 'oil': {'date': as_of, 'value': v['MCOILWTICO'] * 0.99}}, open(os.path.join(D, 'latest.json'), 'w'))
    r = subprocess.run([sys.executable, 'run_2028.py'], cwd=dst, capture_output=True, text=True, env=dict(os.environ, KEYS_RUNS='20000'))
    assert r.returncode == 0, r.stderr[-1500:]
    out = json.load(open(os.path.join(dst, 'projection_2028.json')))
    shutil.rmtree(os.path.dirname(dst))
    return out


def landed(pr):
    return {k for k, x in pr['keys'].items() if x['landed']}


def test_today():
    pr = json.load(open(os.path.join(HERE, 'projection_2028.json')))
    settled = json.load(open(os.path.join(HERE, 'data', 'outlook.json')))['settled']
    assert len(pr['keys']) + len(settled) == 52 and not set(pr['keys']) & set(settled)
    assert all(0 <= x['p'] <= 1 and x['note'] for x in pr['keys'].values())
    assert all(x['p'] in (0, 1) for k, x in pr['keys'].items() if x['landed'])
    assert pr['groups']['D']['mean'] == sum(settled[k]['value'] for k in settled if k[0] == 'D') / 6
    lo, hi = pr['range']['above_half']
    assert 0 <= lo <= pr['index']['above_half'] <= hi <= 1


def test_nothing_lands_early():
    pr = case((2027, 6), '2027-07-20')
    assert not landed(pr) and pr['data_through'] == {'monthly': 'June 2027', 'quarterly': '2027 Q2', 'prices': '2027-07-20'}
    pr = case((2028, 5), '2028-06-25')
    assert not landed(pr), 'with May 2028 as the last month, no key has its June figures'
    assert 0 < pr['keys']['A01']['p'] < 1 and 0 < pr['keys']['C03']['p'] < 1


def test_keys_land_when_june_2028_is_published():
    pr = case((2028, 6), '2028-08-05')
    assert landed(pr) == ECONOMY | APPROVAL | STATE_KEYS, sorted((ECONOMY | APPROVAL | STATE_KEYS) ^ landed(pr))
    assert all(pr['keys'][k]['p'] in (0, 1) for k in ECONOMY | APPROVAL | STATE_KEYS)
    assert 'electoral votes' in pr['keys']['A18']['note'] and 'four years earlier' in pr['keys']['B15']['note']
    pr = case((2028, 6), '2028-08-05', states=False)
    assert landed(pr) == ECONOMY | APPROVAL, 'the two state keys wait for the state indexes: they are scored by states.py, not by a stand-in'
    assert not pr['keys']['A18']['landed'] and not pr['keys']['B15']['landed']


def test_a_hole_in_the_figures_keeps_the_key_open():
    """One month of unemployment missing in 2027: the three keys that read unemployment stay open, and are not scored as no."""
    pr = case((2028, 6), '2028-08-05', drop=('UNRATE', 2027, 9))
    still_open = {'A05', 'A09', 'B04'}
    assert landed(pr) == (ECONOMY | APPROVAL | STATE_KEYS) - still_open, sorted(((ECONOMY | APPROVAL | STATE_KEYS) - still_open) ^ landed(pr))
    assert all(not pr['keys'][k]['landed'] for k in still_open)
    assert any(0 < pr['keys'][k]['p'] < 1 for k in still_open), 'an open key keeps a chance; it is not forced to no'


def test_no_june_polls_no_approval_keys():
    pr = case((2028, 6), '2028-08-05', no_polls_in=((2028, 5), (2028, 6)))        # June polls, or May's if there are none, are what the keys read
    assert not landed(pr) & APPROVAL and landed(pr) == ECONOMY | STATE_KEYS
    assert 0 < pr['keys']['C03']['p'] < 1


if __name__ == '__main__':
    test_today(); test_nothing_lands_early(); test_keys_land_when_june_2028_is_published(); test_a_hole_in_the_figures_keeps_the_key_open(); test_no_june_polls_no_approval_keys()
    print('ok (the run-ahead: keys land when their figures are published, and only then)')
