"""2028, run ahead: where the open keys are likely to land. Writes projection_2028.json.

THIS IS NOT THE MODEL. The model scores each key by its rule once the June 2028 figures exist. This file estimates,
from the figures published so far, how likely each open key is to go the party's way, and from that where the count
may end up. Nothing here changes a key, a group or a rule, and nothing here was checked against an election result.
update.py reruns it whenever a figure it reads has changed.

How the economy keys are run (33 keys)
  1 Start from the figures published so far (FRED) and the outlook forecasters hold (data/outlook.json).
  2 Take every stretch of 20 months since 1964 that began, like October 2026, with unemployment at or below its
    normal rate and no recession under way. Measure how each series moved in that stretch against its own pace over
    the three years before (or, for prices, oil, stocks, housing, claims and sentiment, simply how it moved).
  3 Lay each stretch over the outlook, so the middle of the stretches that had no recession sits on the outlook,
    and score all 33 keys on the result. One stretch gives one complete set of keys, so keys that move together in
    real life move together here: a recession hits all of them at once.
  4 Stretches that ran into a recession are weighted to 30% of the total. History alone gives more and forecasters
    give less.
  5 As new months are published they replace the run. Each series follows its published figures as far as they go,
    and only the months still ahead are run, from the latest figure, on what the same stretches did over those same
    months. Once a key's June 2028 figures are out nothing is left to run, and the key has landed.
  Three series are handled apart. Unemployment is put halfway between the forecasters' flat path and its drift in the
  past stretches, and never below 3.4%. Payroll jobs follow the outlook and unemployment, because past job booms came
  with a fast-growing workforce. The two state keys use a stand-in for the state indexes fitted on 1980 to 2024.

How the other keys are run (11 keys)
  The six approval keys: from today's reading, approval takes a step to each date the keys compare, sized by how far it
  has moved between the midterm and June of the election year in the terms since 1950 (or by its month-to-month moves in
  this term, if those are larger). No trend is assumed. In half of the runs with a recession every step goes down. A
  reading that has been taken is used as it is, and the keys land once the June 2028 polls are in.
  The third-candidate key: how often the key was yes in the record, moved halfway toward what the polls say once three
  pollsters have named a third candidate in the last 90 days; scored by rule on the June 2028 polls (facts.py).
  The four nomination keys: how often each was yes in the record (record_rates below), until each is settled. No odds
  are entered by hand; the ones entered in November 2026 stay in data/outlook.json for the record and are not read.
"""
import csv, datetime, json, math, os, random, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
sys.path.insert(0, HERE)
from build import GROUPS, ALL                         # noqa: E402
import states as SK                                   # noqa: E402
import calls as CALL                                  # noqa: E402

CFG = json.load(open(os.path.join(D, 'outlook.json')))          # the outlook and the odds: entered by hand, with what each rests on in the README
LATEST = json.load(open(os.path.join(D, 'latest.json')))        # the date of the run and the latest daily prices: written by update.py
OUTLOOK, POLITICS = CFG['outlook'], CFG['politics']
TODAY = datetime.date.fromisoformat(LATEST['as_of'])
AS_OF = f"{TODAY:%B} {TODAY.day}, {TODAY.year}"
ym = lambda y, m: y * 12 + (m - 1)
START, H = ym(2026, 10), 20                           # the run starts from October 2026; June 2028 is 20 months on
QEND = [2, 5, 8, 11, 14, 17, 20]                      # quarter ends from December 2026 to June 2028
Q0 = 2026 * 4 + 3                                     # 2026 Q4, the first quarter of the run
RUNS, SEED = int(os.environ.get('KEYS_RUNS', 200000)), 2028     # KEYS_RUNS: fewer runs, for the tests only
ENGINE = '2026.11e'                                   # the version of this run-ahead method; a change to the method changes it, new data do not
# what the three "approval is rising" keys (C03, C04, C05) did in each election since 1952; years without the president on the ticket count double
CYCLES = {1952: (1, 0, 1), 1956: (1, 1, 0), 1960: (0, 1, 0), 1964: (1, 1, 0), 1968: (0, 0, 0), 1972: (1, 1, 1), 1976: (0, 0, 0), 1980: (1, 0, 0),
          1984: (1, 1, 1), 1988: (0, 0, 0), 1992: (0, 0, 0), 1996: (1, 1, 1), 2000: (1, 0, 0), 2004: (0, 0, 0), 2008: (0, 0, 0), 2012: (1, 1, 1),
          2016: (1, 1, 1), 2020: (0, 0, 0), 2024: (0, 0, 0)}
OPEN_SEAT = {1952, 1960, 1968, 1988, 2000, 2008, 2016}
ENTERED = CFG['settled']                              # entered with what each rests on: the midterms, the term limit, and later the nominations

RECESSIONS = [((1960, 4), (1961, 2)), ((1969, 12), (1970, 11)), ((1973, 11), (1975, 3)), ((1980, 1), (1980, 7)), ((1981, 7), (1982, 11)),
              ((1990, 7), (1991, 3)), ((2001, 3), (2001, 11)), ((2007, 12), (2009, 6)), ((2020, 2), (2020, 4))]
REC = {t for (a, b), (c, d) in RECESSIONS for t in range(ym(a, b) + 1, ym(c, d) + 1)}       # the months after each peak, through the trough
# the unemployment rate the Congressional Budget Office treats as normal, approximate anchor years
NORMAL = [(1960, 5.5), (1970, 5.9), (1978, 6.2), (1990, 5.9), (2000, 5.0), (2008, 4.9), (2012, 5.0), (2019, 4.5), (2026, 4.3)]

MD = {'UNRATE': ('u', 'UNRATE'), 'PAYEMS': ('jobs', 'PAYEMS'), 'MANEMP': ('man', 'MANEMP'), 'CPIAUCSL': ('cpi', 'CPIAUCSL'), 'INDPRO': ('ip', 'INDPRO'),
      'DPCERA3M086SBEA': ('pce', 'DPCERA3M086SBEA'), 'CES0600000008': ('wage', 'CES0600000008'), 'OILPRICEx': ('oil', 'MCOILWTICO'),
      'S&P 500': ('sp', 'SP500'), 'UMCSENTx': ('ics', 'UMCSENT'), 'HOUST': ('houst', 'HOUST'), 'CLAIMSx': ('claims', 'ICSA')}
PACE = {'man': 36, 'ip': 36, 'pce': 36, 'rwage': 36, 'cpi': 24, 'roil': 0, 'rsp': 0, 'houst': 0, 'claims': 0}     # months of its own pace taken out
MOVES = ['u', 'ics']


def load_monthly():
    rows = list(csv.reader(open(os.path.join(D, 'fred_md_2026-09.csv')))); head = rows[0]
    P = {s: {} for s, _ in MD.values()}
    for r in rows[2:]:
        if r and '/' in r[0]:
            mo, _, yr = r[0].split('/')
            for name, (s, _) in MD.items():
                x = r[head.index(name)]
                if x != '':
                    P[s][ym(int(yr), int(mo))] = float(x)
    for r in csv.DictReader(open(os.path.join(D, 'latest_monthly.csv'))):
        y, m, _ = r['observation_date'].split('-')
        if ym(int(y), int(m)) > ym(TODAY.year, TODAY.month):       # a month that has not begun on the day of the run is not a figure
            continue
        for name, (s, col) in MD.items():
            if r[col] != '':
                P[s][ym(int(y), int(m))] = float(r[col])
    for s, d in P.items():                                # October 2025 was not collected; sentiment was quarterly before 1978
        for t in [t for t in d if t > START + H]:
            del d[t]
        ts = sorted(t for t in d if t <= START)
        for a, b in zip(ts, ts[1:]):
            for t in range(a + 1, b):
                w = (t - a) / (b - a)
                d[t] = d[a] + w * (d[b] - d[a]) if s in MOVES else d[a] * (d[b] / d[a]) ** w
    for name, top in (('rwage', 'wage'), ('roil', 'oil'), ('rsp', 'sp')):
        P[name] = {t: P[top][t] / P['cpi'][t] for t in P[top] if t in P['cpi']}
    return P


def load_quarterly():
    Q, level = {}, {}
    for r in csv.DictReader(open(os.path.join(D, 'course', 'fred_econ.csv'))):
        g, i = r['GDP_growth_quarterly'], r['RDPI_growth_quarterly']
        Q[int(r['year']) * 4 + int(r['quarter']) - 1] = {'gdp': None if g in ('', 'NA') else float(g), 'rdpi': None if i in ('', 'NA') else float(i)}
    for r in csv.DictReader(open(os.path.join(D, 'quarterly.csv'))):
        y, m, _ = r['observation_date'].split('-'); q = int(y) * 4 + (int(m) - 1) // 3
        if ym(int(y), int(m)) + 2 >= ym(TODAY.year, TODAY.month):    # a quarter that has not ended on the day of the run is not a figure
            continue
        Q[q] = {'gdp': float(r['A191RL1Q225SBEA']), 'rdpi': float(r['A067RL1Q156SBEA'])}
        level[(int(y), (int(m) - 1) // 3 + 1)] = {'pop': float(r['B230RC0Q173SBEA']), 'gdp_pc': float(r['A939RX0Q048SBEA']), 'rdpi_pc': float(r['A229RX0Q048SBEA'])}
    return Q, level


P = load_monthly()
QS, LEVEL = load_quarterly()
avg = lambda xs: sum(xs) / len(xs)
m3 = lambda s, y, months: avg([P[s][ym(y, m)] for m in months])


def baselines():
    """The parts of the outlook no forecaster's survey gives, taken from the figures themselves and not typed in: each
    growth rate is the series' own pace over the last two years, oil and consumer sentiment stay where they last stood
    (for both, "no change" is the plainest forecast there is), and the population grows as it did over the last year.
    They move by themselves as new figures are published. The share of runs with a recession is set in run()."""
    last = lambda s: max(P[s]); pace = lambda s, months=24: round(100 * ((P[s][last(s)] / P[s][last(s) - months]) ** (12 / months) - 1), 1)
    qs = sorted(QS)[-8:]; lv = sorted(LEVEL)
    out = {'hourly_pay': pace('wage'), 'spending': pace('pce'), 'industrial_production': pace('ip'), 'factory_jobs': pace('man'),
           'income': [round(avg([QS[q]['rdpi'] for q in qs]), 1)] * 7, 'population': round(100 * (LEVEL[lv[-1]]['pop'] / LEVEL[lv[-5]]['pop'] - 1), 2),
           'oil': [[1, round(P['oil'][last('oil')], 1)], [20, round(P['oil'][last('oil')], 1)]], 'sentiment': [[1, round(P['ics'][last('ics')], 1)], [20, round(P['ics'][last('ics')], 1)]]}
    return out


def record_rates(path=None):
    """The chances of the third-candidate key and the four nomination keys, counted from the record (keys_table.csv) and
    not typed in. Each is the share of past elections in which the key was yes, with half a yes and half a no added
    to the count, so that a handful of elections never gives a chance of 0 or 100%.
      E05 and E04   the party in office: counted over the elections in which the sitting president did not run, as in
                    2028. E04 is counted apart for the years the nominee won New Hampshire and the years he did not.
      E07           the other party's primary is its own affair whoever holds the White House: counted over every election.
      E06           compares the two primaries, so it is counted apart for each combination of E05 and E07, over every election.
      E03           counted over every election.
    Returns the rates and the counts behind them."""
    rows = list(csv.DictReader(open(path or os.path.join(HERE, 'keys_table.csv'))))
    col = lambda r, key: int(r[next(c for c in r if c.startswith(key + '_') and not c.endswith('_if_nominee'))])
    rate = lambda rs, key: (sum(col(r, key) for r in rs) + 0.5) / (len(rs) + 1)
    count = lambda rs, key: [sum(col(r, key) for r in rs), len(rs)]
    open_ = [r for r in rows if col(r, 'E01') == 0]
    won, lost = [r for r in open_ if col(r, 'E05')], [r for r in open_ if not col(r, 'E05')]
    cell = lambda a, b: [r for r in rows if col(r, 'E05') == a and col(r, 'E07') == b]
    return {'no_third_candidate': rate(rows, 'E03'), 'nominee_wins_nh': rate(open_, 'E05'), 'two_thirds_if_won': rate(won, 'E04'), 'two_thirds_if_lost': rate(lost, 'E04'),
            'challenger_loses_nh': rate(rows, 'E07'), 'stronger': {f'{a}{b}': rate(cell(a, b), 'E06') for a in (1, 0) for b in (1, 0)},
            'counts': {'elections': len(rows), 'president_not_running': len(open_), 'no_third_candidate': count(rows, 'E03'), 'nominee_wins_nh': count(open_, 'E05'), 'two_thirds_if_won': count(won, 'E04'),
                       'two_thirds_if_lost': count(lost, 'E04'), 'challenger_loses_nh': count(rows, 'E07'), 'stronger': {f'{a}{b}': count(cell(a, b), 'E06') for a in (1, 0) for b in (1, 0)}}}


ENTERED_POLITICS = dict(POLITICS)                      # as typed in November 2026, kept for the record
POLITICS = dict(record_rates(), slump_in_recession=POLITICS['slump_in_recession'])
ENTERED_OUTLOOK = {k: OUTLOOK[k] for k in ('hourly_pay', 'spending', 'industrial_production', 'factory_jobs', 'income', 'population', 'oil', 'sentiment', 'recession_share')}      # as typed in November 2026, kept for the record
OUTLOOK.update(baselines())
BASE = dict(
    jobs_jan21=P['jobs'][ym(2021, 1)], jobs_jan25=P['jobs'][ym(2025, 1)], ip_jan21=P['ip'][ym(2021, 1)], ip_jan25=P['ip'][ym(2025, 1)],
    pce_jan21=P['pce'][ym(2021, 1)], pce_jan25=P['pce'][ym(2025, 1)], man_jan25=P['man'][ym(2025, 1)], wage_jan25=P['wage'][ym(2025, 1)],
    cpi_jan21=P['cpi'][ym(2021, 1)], cpi_jan25=P['cpi'][ym(2025, 1)], cpi_jun26=P['cpi'][ym(2026, 6)], oil_jan25=P['oil'][ym(2025, 1)],
    sp_jan25=P['sp'][ym(2025, 1)], ics_jan25=P['ics'][ym(2025, 1)], u_jan25=P['u'][ym(2025, 1)],
    claims_q1_25=m3('claims', 2025, (1, 2, 3)), houst_q1_25=m3('houst', 2025, (1, 2, 3)),
    pop_21q1=LEVEL[(2021, 1)]['pop'], pop_25q1=LEVEL[(2025, 1)]['pop'], pop_26q3=LEVEL[(2026, 3)]['pop'])
G = {k: LEVEL[q]['gdp_pc'] for k, q in (('q16', (2016, 4)), ('q20', (2020, 4)), ('q24', (2024, 4)), ('now', (2026, 3)))}
R = {k: LEVEL[q]['rdpi_pc'] for k, q in (('q20', (2020, 4)), ('q24', (2024, 4)), ('now', (2026, 3)))}
BAR = dict(gdp=(100 * ((G['q24'] / G['q20']) ** 0.25 - 1) + 100 * ((G['q20'] / G['q16']) ** 0.25 - 1)) / 2, rdpi=100 * ((R['q24'] / R['q20']) ** 0.25 - 1))
POP_Q = (1 + OUTLOOK['population'] / 100) ** 0.25

# How far the published figures reach. K: months past October 2026 for each monthly series (spending runs a month behind).
# KQ: quarters from 2026 Q4 (so -1 while 2026 Q3 is the latest). MONTH_NOW: the month the latest daily prices fall in.
def reach(s):
    k = -1 if START not in P[s] else 0                # spending runs a month behind the rest
    while k < H and START + k + 1 in P[s]:
        k += 1
    return k


K = {s: reach(s) for s in ('u', 'jobs', 'man', 'cpi', 'ip', 'wage', 'pce', 'houst', 'claims', 'oil', 'ics', 'sp')}
QKEY = lambda q: ((Q0 + q) // 4, (Q0 + q) % 4 + 1)
KQ = min(6, max(y * 4 + q - 1 for y, q in LEVEL) - Q0)
MONTH_NOW = min(H, ym(TODAY.year, TODAY.month) - START)
# the latest price of oil and of the S&P 500, and the month it stands for: today's price until that month's average is published
ANCHOR = {s: (MONTH_NOW, LATEST[name]['value']) if MONTH_NOW > K[s] else (K[s], P[s][START + K[s]]) for s, name in (('oil', 'oil'), ('sp', 'sp500'))}
# the month from which each series is still run rather than read
AT = dict({s: max(K[s], 0) for s in ('cpi', 'man', 'ip', 'pce', 'houst', 'claims', 'u', 'ics')}, rwage=max(min(K['wage'], K['cpi']), 0), roil=ANCHOR['oil'][0])
# what each economy key waits for: it has landed when these are published through June 2028 (the two state keys are scored from the state indexes)
NEEDS = {'A01': ['gdp'], 'A02': ['gdp'], 'A03': ['ip'], 'A04': ['pce', 'gdp'], 'A05': ['u'], 'A06': ['jobs'], 'A07': ['man'], 'A08': ['claims'], 'A09': ['u'],
         'A10': ['gdp'], 'A11': ['wage', 'cpi'], 'A12': ['cpi'], 'A13': ['oil', 'cpi'], 'A14': ['sp'], 'A15': ['sp'], 'A16': ['ics'], 'A17': ['houst'],
         'B01': ['gdp'], 'B02': ['ip'], 'B03': ['pce', 'gdp'], 'B04': ['u'], 'B05': ['jobs'], 'B06': ['man'], 'B07': ['claims'], 'B08': ['gdp'],
         'B09': ['wage', 'cpi'], 'B10': ['cpi'], 'B11': ['oil', 'cpi'], 'B12': ['sp', 'cpi'], 'B13': ['ics'], 'B14': ['houst']}
published = lambda name: KQ >= 6 if name == 'gdp' else K[name] >= H
LANDED = {k for k, needs in NEEDS.items() if all(published(n) for n in needs)}
POP28 = LEVEL[QKEY(KQ)]['pop'] * POP_Q ** (6 - KQ)             # the population in 2028 Q2


def normal_rate(t):
    y = t / 12
    for (a, va), (b, vb) in zip(NORMAL, NORMAL[1:]):
        if a <= y <= b:
            return va + (vb - va) * (y - a) / (b - a)
    return NORMAL[-1][1]


def stretch(t0):
    """What happened over the 20 months after month t0, as moves from t0 (growth series net of their own pace before it)."""
    if t0 + H > START - 1:                                # the stretches are history: all of them ended before the run began, so new months never change the set
        return None
    out = {'t0': t0, 'recession': any(t in REC for t in range(t0 + 1, t0 + H + 1))}
    for s, months in PACE.items():
        pace = 0.0 if months == 0 else math.log(P[s][t0] / P[s][t0 - months]) * 12 / months
        out[s] = [0.0] + [math.log(P[s][t0 + h] / P[s][t0]) - pace * h / 12 for h in range(1, H + 1)]
    for s in MOVES:
        out[s] = [0.0] + [P[s][t0 + h] - P[s][t0] for h in range(1, H + 1)]
    q0 = (t0 // 12) * 4 + (t0 % 12) // 3                      # the quarter that begins with t0, the counterpart of 2026 Q4
    for s in ('gdp', 'rdpi'):
        past = [QS[q][s] for q in range(q0 - 12, q0) if q in QS and QS[q][s] is not None]
        ahead = [QS.get(q, {}).get(s) for q in range(q0, q0 + 7)]
        if len(past) < 12 or any(x is None for x in ahead):
            return None
        out[s] = [x - avg(past) for x in ahead]
    return out


def stretches(gap=0.3):
    res = []
    for t0 in range(ym(1964, 1), START):
        if (t0 % 12) % 3 or t0 in REC or P['u'][t0] - normal_rate(t0) > gap:        # a quarter's first month, like October; no recession; low unemployment
            continue
        if ym(2018, 7) <= t0 <= ym(2020, 1):                                          # the 2020 shutdown is left out: it was not a business cycle
            continue
        s = stretch(t0)
        if s:
            res.append(s)
    return res


def interp(points, h):
    for (a, va), (b, vb) in zip(points, points[1:]):
        if a <= h <= b:
            return va + (vb - va) * (h - a) / (b - a)
    return points[-1][1]


def outlook_paths():
    """Each series from October 2026 to June 2028: its published figures as far as they go, then the forecasters' path from the latest one."""
    A = lambda s, h: P[s][START + h]
    path = lambda points: (lambda h: interp(points, max(h, points[0][0])))
    o = {}
    k, flat = K['u'], OUTLOOK['unemployment']
    o['u'] = ([A('u', h) for h in range(k + 1)] + [(A('u', k) + flat) / 2] + [flat] * H)[:H + 1]
    j = [A('jobs', h) for h in range(K['jobs'] + 1)]
    for g in OUTLOOK['jobs_a_month'][K['jobs']:]:
        j.append(j[-1] + g)
    o['jobs'] = j
    grow = lambda s, rate: [A(s, h) if h <= K[s] else A(s, K[s]) * (1 + rate / 100) ** ((h - K[s]) / 12) for h in range(H + 1)]
    o['man'], o['ip'], o['wage'] = grow('man', OUTLOOK['factory_jobs']), grow('ip', OUTLOOK['industrial_production']), grow('wage', OUTLOOK['hourly_pay'])
    o['pce'] = grow('pce', OUTLOOK['spending'])
    qa = [m3('cpi', 2026, (7, 8, 9))]                                                # the survey gives quarterly averages, from 2026 Q4
    for r in OUTLOOK['cpi_quarters']:
        qa.append(qa[-1] * (1 + r / 100) ** 0.25)
    c0 = P['cpi'][START]
    nd = (3 * qa[1] - c0) / 2                                                        # November and December 2026, given October
    pts = [(0, c0), (1, nd), (2, nd)] + [(1 + 3 * (q - 1), qa[q]) for q in range(2, 9)]      # quarterly averages sit on the middle month
    first = [math.exp(interp([(a, math.log(v)) for a, v in pts], h)) for h in range(H + 1)]
    k = K['cpi']
    o['cpi'] = first if k == 0 else [A('cpi', h) if h <= k else A('cpi', k) * first[h] / first[k] for h in range(H + 1)]
    # oil and sentiment: the latest figure, carried along the shape of the outlook (oil by the same percentage, sentiment by the same number of points)
    c, k, (a, v) = path(OUTLOOK['oil']), K['oil'], ANCHOR['oil']
    o['oil'] = [A('oil', h) if h <= k else v * c(h) / c(a) if h >= a else math.exp(interp([(k, math.log(A('oil', k))), (a, math.log(v))], h)) for h in range(H + 1)]
    c, k = path(OUTLOOK['sentiment']), K['ics']
    o['ics'] = [A('ics', h) if h <= k else A('ics', k) + c(h) - c(k) for h in range(H + 1)]
    for s, span in (('houst', 6), ('claims', 3)):                                    # held at their recent level: the average of the last six and three months
        level = avg([A(s, K[s] - i) for i in range(span)])
        o[s] = [A(s, h) if h <= K[s] else level for h in range(H + 1)]
    return o


O = outlook_paths()


def middle(S):
    """The middle of the stretches that had no recession. Forecasters' outlooks describe that case, so it is laid on the outlook."""
    calm = [s for s in S if not s['recession']]
    med = {k: [st.median(s[k][h] for s in calm) for h in range(H + 1)] for k in list(PACE) + MOVES if k != 'rsp'}
    med.update({k: [st.median(s[k][q] for s in calm) for q in range(7)] for k in ('gdp', 'rdpi')})
    return med


def economy_keys(s, med, rnd):
    def d(k, h):                                          # how this stretch moved from the latest published month on, against the middle stretch
        a = AT[k]
        return 0.0 if h <= a else (s[k][h] - med[k][h]) - (s[k][a] - med[k][a])
    cpi = [O['cpi'][h] * math.exp(d('cpi', h)) for h in range(H + 1)]
    lv = {k: [O[k][h] * math.exp(d(k, h)) for h in range(H + 1)] for k in ('man', 'ip', 'pce', 'houst', 'claims')}
    rw = [O['wage'][h] / O['cpi'][h] * math.exp(d('rwage', h)) for h in range(H + 1)]
    ro = [O['oil'][h] / O['cpi'][h] * math.exp(d('roil', h)) for h in range(H + 1)]
    a, v = ANCHOR['sp']
    sp = [P['sp'][START + h] if h <= K['sp'] else v if h <= a else v * math.exp(s['rsp'][h] - s['rsp'][a]) * cpi[h] / cpi[a] for h in range(H + 1)]
    k = K['u']                                            # halfway between the outlook and the drift of past stretches; not below 3.4%
    ur = [O['u'][h] if h <= k else max(3.4, 0.5 * (O['u'][h] + d('u', h)) + 0.5 * (O['u'][k] + s['u'][h] - s['u'][k])) for h in range(H + 1)]
    u = [round(x, 1) for x in ur]
    lf = rnd.gauss(0, 0.004)                                                          # the workforce may grow a little faster or slower than expected
    k = K['jobs']
    jobs = [O['jobs'][h] if h <= k else O['jobs'][h] * (1 - 0.0104 * (ur[h] - O['u'][h]) + lf * (h - k) / 12) for h in range(H + 1)]
    ics = [O['ics'][h] if h <= K['ics'] else round(min(110, max(40, O['ics'][h] + d('ics', h))), 1) for h in range(H + 1)]
    g = [QS[Q0 + q]['gdp'] if q <= KQ else OUTLOOK['gdp'][q] + s['gdp'][q] - med['gdp'][q] for q in range(7)]
    r = [QS[Q0 + q]['rdpi'] if q <= KQ else OUTLOOK['income'][q] + s['rdpi'][q] - med['rdpi'][q] for q in range(7)]
    per = lambda rates, name: [LEVEL[QKEY(q)][name] / LEVEL[QKEY(q - 1)][name] if q <= KQ else (1 + x / 100) ** 0.25 / POP_Q for q, x in enumerate(rates)]
    gpc, rpc = per(g, 'gdp_pc'), per(r, 'rdpi_pc')
    spring = lambda xs, hs: avg([xs[h] for h in hs])
    u3 = lambda h: (u[h] + u[h - 1] + u[h - 2]) / 3
    ann = lambda ratio, months: 100 * (ratio ** (12 / months) - 1)
    pop28 = POP28
    w = [0.55 ** (15 - q) for q in range(9, 15)]
    wavg = lambda xs: sum(a * b for a, b in zip(w, xs)) / sum(w)
    # a stand-in for the electoral-vote-weighted state measure, fitted on the twelve elections from 1980 (see README)
    states = 0.165 + 0.016 * wavg(g[1:]) - 1.344 * wavg([(ur[QEND[i + 1]] - ur[QEND[i]]) / 3 for i in range(6)]) + rnd.gauss(0, 0.025)
    term = lambda now, start: 100 * ((now / start) ** (4 / 14) - 1)
    k = {
        'A01': g[6] > 0, 'A02': math.prod(gpc[3:]) > 1, 'A03': lv['ip'][20] > lv['ip'][8],
        'A04': lv['pce'][20] / lv['pce'][8] / POP_Q ** 4 > 1, 'A05': u[20] < u[8], 'A06': jobs[20] > jobs[8], 'A07': lv['man'][20] > lv['man'][8],
        'A08': spring(lv['claims'], (18, 19, 20)) < spring(lv['claims'], (6, 7, 8)), 'A09': u3(20) - min(u3(h) for h in range(8, 20)) < 0.5,
        'A10': math.prod(rpc[3:]) > 1, 'A11': rw[20] > rw[8], 'A12': cpi[20] / cpi[8] < cpi[8] / BASE['cpi_jun26'], 'A13': ro[20] < ro[8],
        'A14': sp[20] > sp[8], 'A15': sp[20] > sp[14], 'A16': ics[20] > ics[8],
        'A17': spring(lv['houst'], (18, 19, 20)) > spring(lv['houst'], (6, 7, 8)), 'A18': states > 0,
        'B01': term(G['now'] * math.prod(gpc), G['q24']) >= BAR['gdp'],
        'B02': ann(lv['ip'][20] / BASE['ip_jan25'], 41) > ann(BASE['ip_jan25'] / BASE['ip_jan21'], 48),
        'B03': ann((lv['pce'][20] / pop28) / (BASE['pce_jan25'] / BASE['pop_25q1']), 41) > ann((BASE['pce_jan25'] / BASE['pop_25q1']) / (BASE['pce_jan21'] / BASE['pop_21q1']), 48),
        'B04': u[20] < BASE['u_jan25'], 'B05': ann(jobs[20] / BASE['jobs_jan25'], 41) > ann(BASE['jobs_jan25'] / BASE['jobs_jan21'], 48),
        'B06': lv['man'][20] > BASE['man_jan25'], 'B07': spring(lv['claims'], (18, 19, 20)) < BASE['claims_q1_25'],
        'B08': term(R['now'] * math.prod(rpc), R['q24']) > BAR['rdpi'], 'B09': rw[20] > BASE['wage_jan25'] / BASE['cpi_jan25'],
        'B10': ann(cpi[20] / BASE['cpi_jan25'], 41) < ann(BASE['cpi_jan25'] / BASE['cpi_jan21'], 48), 'B11': ro[20] < BASE['oil_jan25'] / BASE['cpi_jan25'],
        'B12': sp[20] / cpi[20] > BASE['sp_jan25'] / BASE['cpi_jan25'], 'B13': ics[20] > BASE['ics_jan25'],
        'B14': spring(lv['houst'], (18, 19, 20)) > BASE['houst_q1_25'], 'B15': states > 0.154,
    }
    return k


def third_chance():
    """The chance that no third candidate reaches 10% in the June 2028 polls. With no reading it is how often none did in
    the record (record_rates). With one (three or more pollsters naming a third candidate in the last 90 days, facts.py) it is
    halfway between those odds and what the reading says, which is held loosely: the further June is, the more such
    support has room to fade or to grow."""
    now = (THIRD or {}).get('now') or {}
    if now.get('reading') is None:
        return POLITICS['no_third_candidate']
    months = max(0.0, (datetime.date(CALL.CYCLE['year'], 6, 15) - TODAY).days / 30.44); sd = 3 + 0.25 * months
    says = 0.5 * (1 + math.erf((10 - now['reading']) / sd / math.sqrt(2)))
    return 0.5 * POLITICS['no_third_candidate'] + 0.5 * says


def other_keys(rnd, recession):
    # approval: from today's reading it takes a step to each date the keys compare, of the size it has moved month to month
    # in this term, with no trend assumed either way. A reading that has been taken is used as it is. In half of the runs
    # with a recession every step goes down. Disapproval moves by as much the other way.
    a0, d0, step = APPROVAL['approve'], APPROVAL['disapprove'], APPROVAL['step']; y = CALL.CYCLE['year']
    down = recession and rnd.random() < POLITICS['slump_in_recession']
    cur, at, seen = a0, TODAY, {}
    for name, when in (('june27', datetime.date(y - 1, 6, 15)), ('jan28', datetime.date(y, 1, 15)), ('june28', datetime.date(y, 6, 15))):
        if APPROVAL.get(name) and name != 'june28':
            seen[name] = APPROVAL[name]['approve']; continue
        months = max(0.0, (when - max(at, TODAY)).days / 30.44); z = rnd.gauss(0, 1)
        if name == 'june28': months = max(months, 0.5)          # until the June polls are in, today's reading is not June's: half a month's step stays open
        cur += step * math.sqrt(months) * (-abs(z) if down else z); at = max(when, TODAY); seen[name] = cur
    j = seen['june28']; dis = d0 - (j - a0); mid = (APPROVAL.get('midterm') or {}).get('approve', a0)
    won = rnd.random() < POLITICS['nominee_wins_nh']; other_lost = rnd.random() < POLITICS['challenger_loses_nh']
    stronger = rnd.random() < POLITICS['stronger'][f'{int(won)}{int(other_lost)}']
    return {'C01': j >= 50, 'C02': j > dis, 'C03': j > seen['june27'], 'C04': j > mid, 'C05': j > seen['jan28'], 'C06': dis < 50,
            'E03': rnd.random() < THIRD_P,
            'E04': rnd.random() < (POLITICS['two_thirds_if_won'] if won else POLITICS['two_thirds_if_lost']), 'E05': won, 'E06': stronger, 'E07': other_lost}


def run(runs=RUNS, seed=SEED, share=None, gap=0.3):
    S = stretches(gap); med = middle(S); rnd = random.Random(seed)
    econ = [economy_keys(s, med, rnd) for s in S]
    # a recession in the months still ahead, in stretches like this one: the record's own share is used, so it falls by itself
    # as the months left run out. `share` overrides it only for the what-if lines.
    rec = [any(t in REC for t in range(s['t0'] + max(MONTH_NOW, 0) + 1, s['t0'] + H + 1)) for s in S]; seen = avg(rec)
    share = seen if share is None else share
    w = [1.0] * len(S) if seen in (0, 1) else [share / seen if r else (1 - share) / (1 - seen) for r in rec]
    size = {g: len(ks) for g, ks in GROUPS.items()}
    tally, index, by_group, calm_index = {}, [], {g: [] for g in GROUPS}, []
    yes_rec, n_rec = {}, 0
    yes_above, hits, draws, sums = {}, [0] * len(S), [0] * len(S), [0.0] * len(S)      # for the keys that matter most, and for the range of the estimate
    for i in rnd.choices(range(len(S)), weights=w, k=runs):
        k = dict(econ[i]); k.update(other_keys(rnd, rec[i])); k.update(FIXED)
        sh = {g: sum(v for a, v in k.items() if a[0] == g) / size[g] for g in GROUPS}
        ix = avg(list(sh.values())); above = ix > 0.5
        for a, b in k.items():
            tally[a] = tally.get(a, 0) + b
            if b and above:
                yes_above[a] = yes_above.get(a, 0) + 1
            if b and rec[i]:
                yes_rec[a] = yes_rec.get(a, 0) + 1
        n_rec += rec[i]
        for g in GROUPS:
            by_group[g].append(sh[g])
        index.append(ix); draws[i] += 1; hits[i] += above; sums[i] += ix
        if not rec[i]:
            calm_index.append(ix)
    n_above = sum(hits)
    # for each key: the share of runs above one half when it is yes, and when it is no
    split = {a: (yes_above.get(a, 0) / tally[a] if tally[a] else None, (n_above - yes_above.get(a, 0)) / (runs - tally[a]) if runs - tally[a] else None) for a in tally}
    per = [{'t0': s['t0'], 'recession': r, 'above': hits[i] / draws[i] if draws[i] else None, 'mean': sums[i] / draws[i] if draws[i] else None} for i, (s, r) in enumerate(zip(S, rec))]
    return dict(share=share, p={a: tally[a] / runs for a in sorted(tally)}, index=index, by_group=by_group, calm=calm_index, stretches=len(S), with_recession=sum(rec),
                first=S[0]['t0'] // 12, last=S[-1]['t0'] // 12, split=split, per=per, copy=dict({a: econ[0][a] for a in LANDED}, **approval_keys()),
                p_rec={a: yes_rec.get(a, 0) / n_rec for a in tally} if n_rec else {}, p_calm={a: (tally[a] - yes_rec.get(a, 0)) / (runs - n_rec) for a in tally} if runs > n_rec else {})


def spread(per, share, rnd, reps=4000, years=4):
    """How far the headline figures could move with a different draw of history. The 20-month stretches overlap, so they are
    resampled in blocks of four calendar years, and the recession share is drawn between 20% and 40% rather than held at one value.
    Returns the middle 80% of the share of runs above one half, and of the average count."""
    blocks = {}
    for x in per:
        if x['above'] is not None:
            blocks.setdefault((x['t0'] // 12) // years, []).append(x)
    names, out = sorted(blocks), []
    for _ in range(reps):
        pick = [x for b in rnd.choices(names, k=len(names)) for x in blocks[b]]
        r, c = [x for x in pick if x['recession']], [x for x in pick if not x['recession']]
        if not pick:
            continue
        if not r or not c:                               # late in the run no stretch has a recession still ahead: there is nothing to weigh
            out.append((avg([x['above'] for x in pick]), avg([x['mean'] for x in pick]))); continue
        sh = min(0.95, max(0.02, rnd.uniform(share - 0.10, share + 0.10)))
        out.append((sh * avg([x['above'] for x in r]) + (1 - sh) * avg([x['above'] for x in c]), sh * avg([x['mean'] for x in r]) + (1 - sh) * avg([x['mean'] for x in c])))
    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))]
    return {'above_half': [round(q([a for a, _ in out], .1), 3), round(q([a for a, _ in out], .9), 3)], 'mean': [round(q([m for _, m in out], .1), 3), round(q([m for _, m in out], .9), 3)],
            'blocks': len(names), 'block_years': years}


def approval():
    """Approval of the president among all adults, and the readings the six approval keys compare.

    One reading is the average over pollsters of each pollster's own average, from the polls of all adults that finished
    in the window (no campaign or party internals). Polls come from VoteHub (data/approval_polls.json, refreshed by update.py).
    """
    polls = [p for p in json.load(open(os.path.join(D, 'approval_polls.json')))['polls']
             if p['population'] == 'a' and not p.get('internal') and p['approve'] is not None and p['disapprove'] is not None and p['end'] <= str(TODAY)]

    def reading(lo, hi):
        by = {}
        for p in polls:
            if str(lo) <= p['end'] <= str(hi):
                by.setdefault(p['pollster'], []).append(p)
        if not by:
            return None
        side = lambda k: round(avg([avg([p[k] for p in ps]) for ps in by.values()]), 1)
        return {'approve': side('approve'), 'disapprove': side('disapprove'), 'pollsters': len(by), 'polls': sum(map(len, by.values())), 'from': str(lo), 'to': str(hi)}
    day = datetime.timedelta(days=1)
    month = lambda y, m: reading(datetime.date(y, m, 1), datetime.date(y + m // 12, m % 12 + 1, 1) - day)
    now = next((r for r in (reading(TODAY - n * day, TODAY) for n in (29, 59, 89)) if r), None)      # the last 30 days; 60 or 90 if no poll finished in them
    if now is None:
        raise SystemExit('no poll of all adults in the last 90 days: the approval keys cannot be read')
    out = dict(now, year_ago=month(TODAY.year - 1, TODAY.month), midterm=reading('2026-10-01', '2026-11-30'), june27=month(2027, 6),
               jan28=month(2028, 1) or month(2027, 12), june28=month(2028, 6) or month(2028, 5))
    # the June 2028 polls are in a week after the month ends, if every reading the keys compare exists
    out['in'] = TODAY >= datetime.date.fromisoformat(CALL.CYCLE['approval_in']) and all(out[k] for k in ('june28', 'june27', 'jan28', 'midterm'))
    # how far approval has moved from one month to the next in this term: the size of step the run-ahead lets it take
    months = [r['approve'] for r in (month(y, m) for y in range(2025, TODAY.year + 1) for m in range(1, 13) if datetime.date(y, m, 1) <= TODAY.replace(day=1)) if r]
    steps = [b - a for a, b in zip(months, months[1:])]
    term = round(st.pstdev(steps), 2) if len(steps) >= 6 else None
    # and how far it moved between the midterm and June of the election year in the nineteen terms since 1950 (research.json):
    # that spread, spread evenly over the months between, is the larger of the two and the one used
    try:
        past = json.load(open(os.path.join(HERE, 'research.json')))['approval']['moves']
        record = round(math.sqrt(sum((m['june'] - m['then']) ** 2 for m in past) / len(past)) / math.sqrt(19.5), 2)
    except (FileNotFoundError, KeyError, ZeroDivisionError):
        record = None
    out['step'] = max([x for x in (term, record) if x] or [1.5])
    out['step_from'] = {'this_term': term, 'months': len(steps), 'past_terms': record}
    return out


APPROVAL = approval()
THIRD = json.load(open(os.path.join(D, 'third_candidates.json'))) if os.path.exists(os.path.join(D, 'third_candidates.json')) else None      # facts.py
THIRD_P = third_chance()


def approval_keys():
    """The six approval keys, by their rules, once the June 2028 polls are in. Until then they are open, never false by default."""
    a = APPROVAL
    if not a['in']:
        return {}
    j, dis = a['june28']['approve'], a['june28']['disapprove']
    return {'C01': j >= 50, 'C02': j > dis, 'C03': j > a['june27']['approve'], 'C04': j > a['midterm']['approve'], 'C05': j > a['jan28']['approve'], 'C06': dis < 50}


def state_figures():
    """The two state keys. Until the state indexes run through June 2028 this gives only where the states stand so far
    (a reading, used in the notes); once they do, it scores A18 and B15 by the model's own rule in states.py."""
    idx = {}
    for r in csv.DictReader(open(os.path.join(D, 'state_index_this_term.csv'))):
        if r['index'] != '' and r['month'] <= f'{TODAY:%Y-%m}':             # a month that has not begun on the day of the run is not a figure
            idx.setdefault(r['state'], {})[r['month']] = float(r['index'])
    idx['DC'] = {m: (x + idx['VA'][m]) / 2 for m, x in idx['MD'].items() if m in idx['VA']}
    ev, W = SK.electoral_votes(), SK.measures()
    now, last = SK.so_far()
    out = {'through': min(last, f'{TODAY:%Y-%m}'), 'growing': sum(1 for x in now if now[x] > 0), 'growing_ev': sum(ev[2028][x] for x in now if now[x] > 0),
           'faster_ev': sum(ev[2028][x] for x in now if now[x] > W[(x, 2024)]), 'keys': {}}
    ends = SK.quarter_ends(2028)[0]
    if len(idx) == 51 and all(e in idx[x] for x in idx for e in ends):
        for x in idx:
            W[(x, 2028)] = SK.weighted_growth(idx[x], 2028)
        a18, b15, fig = SK.state_keys(2028, W, ev)
        out['keys'] = {'A18': bool(a18), 'B15': bool(b15)}; out['final'] = fig
    return out


STATES = state_figures()

# Every key's state today, by the model's own rules on the figures published so far (calls.py). A key that is provisional or
# settled is the same in every run. A key that is held keeps its last entry if it has one; otherwise it stays open.
CALLS = CALL.evaluate(TODAY, P, QS, LEVEL, APPROVAL, STATES, ENTERED, LANDED, CALL.read_history(os.path.join(D, 'key_calls.csv')), set(os.environ.get('KEYS_HELD', '').split()), third=THIRD)
FIXED = {k: bool(c['value']) for k, c in CALLS.items() if c['status'] in ('provisional', 'settled')}
FIXED.update({k: c['last'] for k, c in CALLS.items() if 'last' in c and k[0] in 'DE'})
FIXED.update({k: bool(v['value']) for k, v in ENTERED.items() if k not in FIXED})
SETTLED = {k: v for k, v in FIXED.items() if k[0] in 'DE'}       # called on events: these leave the list of keys the run-ahead reports on
_none = [k for k in ('D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'E01', 'E02') if k not in FIXED]
if _none:
    raise SystemExit('no evidence entered for ' + ', '.join(_none) + ': these keys have no chance to run, and a missing key is not a no')


def notes():
    """Where each open key stands on the latest figures, in a sentence."""
    last = {s: START + K[s] for s in K}                                               # the latest published month of each series
    now = {s: P[s][last[s]] for s in K}
    name = lambda t: f"{datetime.date(t // 12, t % 12 + 1, 1):%B %Y}"
    yr = lambda s, back=0: 100 * (P[s][last[s] - back] / P[s][last[s] - back - 12] - 1)
    ann = lambda ratio, months: 100 * (ratio ** (12 / months) - 1)
    up = lambda x, a='above', b='below': a if x >= 0 else b
    lq, nq = QKEY(KQ), 8 + KQ                                                         # the latest quarter, and how many quarters of the term it closes
    term_gdp, term_inc = 100 * ((LEVEL[lq]['gdp_pc'] / G['q24']) ** (4 / nq) - 1), 100 * ((LEVEL[lq]['rdpi_pc'] / R['q24']) ** (4 / nq) - 1)
    inc_year = 100 * (LEVEL[lq]['rdpi_pc'] / LEVEL[(lq[0] - 1, lq[1])]['rdpi_pc'] - 1)
    sp_now, oil_now, oil_at = ANCHOR['sp'][1], ANCHOR['oil'][1], ANCHOR['oil'][0]
    sp_real = 100 * ((sp_now / now['cpi']) / (BASE['sp_jan25'] / BASE['cpi_jan25']) - 1)
    oil_then = BASE['oil_jan25'] * now['cpi'] / BASE['cpi_jan25']
    oil_28 = O['oil'][H] / O['cpi'][H] - BASE['oil_jan25'] / BASE['cpi_jan25']        # the outlook for mid-2028 against the start of the term, after inflation
    pce_need = 100 * (((1 + ann((BASE['pce_jan25'] / BASE['pop_25q1']) / (BASE['pce_jan21'] / BASE['pop_21q1']), 48) / 100) ** (41 / 12)
                       * BASE['pce_jan25'] * (POP28 / BASE['pop_25q1']) / now['pce']) ** (12 / max(1, START + H - last['pce'])) - 1)
    starts = lambda back=0: avg([P['houst'][last['houst'] - back - i] for i in range(6)])
    claims = lambda back=0: avg([P['claims'][last['claims'] - back - i] for i in range(3)])
    u3 = lambda t: avg([P['u'][t - i] for i in range(3)])
    signal = u3(last['u']) - min(u3(last['u'] - i) for i in range(1, 13))
    cpi_back = 1 if last['cpi'] - 12 == ym(2025, 10) else 0                           # October 2025 was not collected
    months = lambda s: last[s] - ym(2025, 1)
    jobs_ahead = avg(OUTLOOK['jobs_a_month'][max(8, K['jobs']):]) if K['jobs'] < H else 0
    man6 = 1000 * (now['man'] - P['man'][last['man'] - 6])
    a = APPROVAL
    c = POLITICS['counts']
    n = {
        'A01': f"Forecasters expect growth of about {OUTLOOK['gdp'][6]}% a year in spring 2028. It was {QS[Q0 + KQ]['gdp']}% in the latest quarter.",
        'A02': f"Forecast growth is about {avg(OUTLOOK['gdp'][3:]):.0f}% a year, and the population is growing about {OUTLOOK['population']}%.",
        'A03': f"{up(yr('ip'), 'Up', 'Down')} {abs(yr('ip')):.1f}% in the past year.",
        'A04': f"Real spending is up {yr('pce'):.1f}% in the past year, {up(yr('pce') - OUTLOOK['population'], 'ahead of', 'behind')} the population.",
        'A05': f"It is {now['u']}% now. Forecasters expect about {OUTLOOK['unemployment']}% through 2028, and a tie counts as no.",
        'A06': f"Forecasters expect about {5 * round(jobs_ahead / 5):.0f},000 new jobs a month, a slow pace that a weak year could turn negative.",
        'A07': f"Factory jobs have {up(man6, 'risen', 'fallen')} {abs(man6):,.0f} in the past six months.",
        'A08': f"Claims are about {claims() / 1000:.0f},000 a week, {up(claims() - claims(12))} the {claims(12) / 1000:.0f},000 of a year earlier.",
        'A09': f"The signal is at {max(0, signal):.2f} now. It takes 0.50, a rise of about half a point in unemployment.",
        'A10': f"{up(inc_year, 'Up', 'Down')} {abs(inc_year):.1f}% in the past year.",
        'A11': f"Pay is rising {yr('wage'):.1f}% a year, and forecasters expect inflation of about {st.median(OUTLOOK['cpi_quarters'][1:])}%.",
        'A12': f"Inflation is {yr('cpi', cpi_back):.1f}% now." + (" This year's oil shock lifts the mid-2027 figure that mid-2028 is compared with." if last['cpi'] < ym(2027, 6) else ''),
        'A13': (f"About ${oil_now:.0f} a barrel now. Futures and forecasts point to about ${O['oil'][8]:.0f} in mid-2027 and ${O['oil'][20]:.0f} in mid-2028." if oil_at < 8 else
                f"About ${oil_now:.0f} a barrel now. It averaged ${O['oil'][8]:.0f} in June 2027."),
        'A14': "The S&P 500 was higher than a year before in about seven years of ten, and lower in recessions.",
        'A15': "Higher than six months before in about two years of three.",
        'A16': f"The index is {now['ics']}" + (", near its record low, which leaves room to recover." if now['ics'] < 55 else '.'),
        'A17': f"Starts are running near {starts() / 1000:.2f} million a year, against {starts(12) / 1000:.2f} million a year earlier.",
        'A18': f"State economies are growing in {STATES['growing']} of 51 now. This key has failed only in sharp downturns (1980, 2020).",
        'B01': f"So far this term: {term_gdp:.2f}% a year. The bar, the average of the last two terms, is {BAR['gdp']:.2f}%.",
        'B02': f"{up(now['ip'] - BASE['ip_jan25'], 'Up', 'Down')} {abs(100 * (now['ip'] / BASE['ip_jan25'] - 1)):.1f}% since January 2025, against {ann(BASE['ip_jan25'] / BASE['ip_jan21'], 48):.1f}% a year last term.",
        'B03': f"It would take real spending growth of {pce_need:.1f}% a year from here.",
        'B04': f"It was {BASE['u_jan25']}% in January 2025 and is {now['u']}% now.",
        'B05': f"Out of reach: jobs grew {ann(BASE['jobs_jan25'] / BASE['jobs_jan21'], 48):.1f}% a year last term and {ann(now['jobs'] / BASE['jobs_jan25'], months('jobs')):.1f}% a year so far in this one.",
        'B06': f"{now['man'] / 1000:.2f} million now against {BASE['man_jan25'] / 1000:.2f} million in January 2025.",
        'B07': f"About {claims() / 1000:.0f},000 a week now against {BASE['claims_q1_25'] / 1000:.0f},000 at the start of the term.",
        'B08': f"So far this term: {term_inc:.1f}% a year. Last term: {BAR['rdpi']:.1f}%.",
        'B09': f"Pay after inflation is {abs(100 * ((now['wage'] / now['cpi']) / (BASE['wage_jan25'] / BASE['cpi_jan25']) - 1)):.1f}% {up(now['wage'] / now['cpi'] - BASE['wage_jan25'] / BASE['cpi_jan25'])} its January 2025 level.",
        'B10': f"Inflation has averaged {ann(now['cpi'] / BASE['cpi_jan25'], months('cpi')):.1f}% a year this term against {ann(BASE['cpi_jan25'] / BASE['cpi_jan21'], 48):.1f}% last term.",
        'B11': f"Oil is about ${oil_now:.0f} now. January 2025's price is ${oil_then:.0f} in today's dollars, and forecasts have oil {up(oil_28)} that by 2028.",
        'B12': f"The S&P 500 is {abs(sp_real):.0f}% {up(sp_real)} its start-of-term level, after inflation.",
        'B13': f"The index is {now['ics']}. It was {BASE['ics_jan25']} in January 2025.",
        'B14': f"Starts average {starts() / 1000:.2f} million against {BASE['houst_q1_25'] / 1000:.2f} million at the start of the term.",
        'B15': f"So far this term, growth is above its 2024 pace in states holding {STATES['faster_ev']:.0f} electoral votes.",
        'C01': f"{a['approve']:.0f}% approve now, in polls of all adults from the past month ({a['pollsters']} pollsters).",
        'C02': f"{a['approve']:.0f}% approve and {a['disapprove']:.0f}% disapprove now.",
        'C03': f"{a['approve']:.0f}% approve now" + (f" against {a['year_ago']['approve']:.0f}% a year ago" if a['year_ago'] else '') + (f". The key compares June 2028 with June 2027 ({a['june27']['approve']:.0f}%)." if a.get('june27') else ". Neither June reading the key compares exists yet, so it is close to a coin toss."),
        'C04': f"Approval averaged {a['midterm']['approve']:.0f}% in the polls around the midterms and is {a['approve']:.0f}% now. It has moved about {a['step']} points a month in this term.",
        'C05': (f"{a['jan28']['approve']:.0f}% approved in January 2028; {a['approve']:.0f}% do now." if a.get('jan28') else "Neither reading the key compares exists yet, so it is close to a coin toss."),
        'C06': f"{a['disapprove']:.0f}% disapprove now.",
        'E03': f"No third candidate reached 10% by June in {c['no_third_candidate'][0]} of the {c['no_third_candidate'][1]} elections on record.",
        'E04': f"In the {c['president_not_running']} elections since 1952 in which the sitting president did not run, his party's nominee won two-thirds of the delegates in {c['two_thirds_if_won'][0] + c['two_thirds_if_lost'][0]}.",
        'E05': f"In those {c['president_not_running']} elections the party's nominee won the New Hampshire primary in {c['nominee_wins_nh'][0]}.",
        'E06': f"The party's nominee did better in New Hampshire than the challenger did in {sum(v[0] for v in c['stronger'].values())} of {c['elections']} elections.",
        'E07': f"The challenger lost the New Hampshire primary in {c['challenger_loses_nh'][0]} of {c['elections']} elections.",
    }
    for k in ('E03', 'E04', 'E05', 'E06', 'E07'):                                    # no odds are entered: the chance is the record's, until the key is settled
        n[k] += ' The chance shown is that share, with half a yes and half a no added to the count.' if k != 'E06' else ' The chance shown is counted apart for each way the two primaries can fall.'
    # a key that has landed says what settled it
    if STATES['keys']:
        f = STATES['final']
        n.update({'A18': f"State economies were growing in {f['states_growing_n']} of 51, holding {f['states_growing_ev']:.0f} of 538 electoral votes.",
                  'B15': f"Growth was faster than four years earlier in {f['states_better_n']} of 51 states, holding {f['states_better_ev']:.0f} of 538 electoral votes."})
    if a['in']:
        j, dis = a['june28']['approve'], a['june28']['disapprove']
        n.update({'C01': f"{j:.0f}% approved in the June 2028 polls.", 'C02': f"{j:.0f}% approved and {dis:.0f}% disapproved in the June 2028 polls.",
                  'C03': f"{j:.0f}% approved in June 2028 against {a['june27']['approve']:.0f}% a year earlier.", 'C04': f"{j:.0f}% approved in June 2028 against {a['midterm']['approve']:.0f}% at the midterms.",
                  'C05': f"{j:.0f}% approved in June 2028 against {a['jan28']['approve']:.0f}% in January.", 'C06': f"{dis:.0f}% disapproved in the June 2028 polls."})
    return n


def main():
    full = {k[:3]: k for k in ALL}
    Rn = run()
    OUTLOOK['recession_share'] = round(Rn['share'], 3)          # the record's own share for the months still ahead (run())
    ix = sorted(Rn['index']); n = len(ix)
    q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
    above = sum(1 for x in ix if x > 0.5) / n
    size = {g: len(ks) for g, ks in GROUPS.items()}
    likely = {a: Rn['p'][a] >= 0.5 for a in Rn['p']}
    note = notes()
    landed = {a for a, c in CALLS.items() if a[0] in 'ABC' and c['status'] in ('provisional', 'settled')}     # scored on published figures: the same in every run
    count = {s: sum(1 for c in CALLS.values() if c['status'] == s) for s in ('settled', 'provisional', 'unresolved', 'held')}
    closes = datetime.date.fromisoformat(CALL.CYCLE['closes'])
    month = lambda t: f"{datetime.date(t // 12, t % 12 + 1, 1):%B %Y}"
    vintage = datetime.date.fromisoformat(CFG['outlook_date'])
    due = next(datetime.date(y, m, 25) for y in (vintage.year, vintage.year + 1) for m in (2, 5, 8, 11) if datetime.date(y, m, 1) > vintage)   # the survey comes out in the middle of these months
    dist = {}
    for x in ix:
        dist[round(x, 2)] = dist.get(round(x, 2), 0) + 1
    lk = {g: sum(v for a, v in likely.items() if a[0] == g) for g in GROUPS}
    out = {
        'as_of': AS_OF, 'date': str(TODAY), 'runs': RUNS, 'stretches': {'n': Rn['stretches'], 'with_recession': Rn['with_recession'], 'first': Rn['first'], 'last': Rn['last']},
        'recession_share': OUTLOOK['recession_share'],
        'index': {'mean': round(avg(ix), 3), 'median': round(q(ix, .5), 3), 'p5': round(q(ix, .05), 3), 'p25': round(q(ix, .25), 3), 'p75': round(q(ix, .75), 3),
                  'p95': round(q(ix, .95), 3), 'above_half': round(above, 3), 'p10': round(q(ix, .10), 3), 'p90': round(q(ix, .90), 3),
                  'sd': round(st.pstdev(ix), 3), 'expected_in_favor': round(sum(Rn['p'].values()), 2)},
        # the whole spread of the count over the runs, to the nearest hundredth: [count, share of runs]
        'index_dist': [[v, round(c / n, 5)] for v, c in sorted(dist.items())],
        'calm': {'mean': round(avg(Rn['calm']), 3), 'above_half': round(sum(1 for x in Rn['calm'] if x > 0.5) / len(Rn['calm']), 3)},
        'hist': [{'lo': b, 'share': round(sum(1 for x in ix if b <= 100 * x < b + 5) / n, 4)} for b in range(0, 100, 5)],
        'groups': {g: {'mean': round(avg(v), 3), 'p10': round(q(sorted(v), .1), 3), 'p90': round(q(sorted(v), .9), 3), 'likely': lk[g], 'n': size[g]} for g, v in Rn['by_group'].items()},
        'likely': {'in_favor': sum(likely.values()), 'index': round(avg([lk[g] / size[g] for g in GROUPS]), 3)},
        'keys': {a: {'p': round(v, 3), 'p_calm': round(Rn['p_calm'].get(a, v), 3), 'p_recession': round(Rn['p_rec'].get(a, v), 3), 'note': note[a], 'landed': a in landed,
                     'status': CALLS[a]['status']}
                 for a, v in Rn['p'].items() if a not in SETTLED},
        # every key's state: called on evidence, scored on figures that can still be revised, open, or held (calls.py)
        'calls': {a: {k: v for k, v in c.items() if v not in ('', None) or k == 'value'} for a, c in CALLS.items()},
        'count': dict(count, final=sum(1 for c in CALLS.values() if c['final']), closes=str(closes), closed=TODAY >= closes,
                      called=sum(1 for c in CALLS.values() if c['value'] is not None), in_favor=sum(1 for c in CALLS.values() if c['value'])),
        'horizon': {'target': 'June 2028', 'months_left': max(0, H - max(K['u'], 0)), 'quarters_left': 6 - KQ, 'days_to_close': max(0, (closes - TODAY).days)},
        'through': dict({col: month(START + K[s]) for s, col in MD.values() if K[s] >= 0}, quarterly=f"{QKEY(KQ)[0]} Q{QKEY(KQ)[1]}", states=STATES['through'],
                        approval_polls=APPROVAL['to']),
        'odds_entered': 'not entered: counted from the record',
        'outlook_from': {'date': str(vintage), 'source': CFG['outlook_note'], 'next_survey_by': str(due), 'stale': TODAY > due and min(K['u'], K['cpi']) < H},
        'copy_differs': sorted(a for a, v in Rn['copy'].items() if a in FIXED and bool(v) != FIXED[a]),
        'outlook': {k: v for k, v in OUTLOOK.items()}, 'politics': POLITICS, 'politics_as_entered_in_november_2026': ENTERED_POLITICS,
        'range': spread(Rn['per'], OUTLOOK['recession_share'], random.Random(SEED + 1)),
        'decisive': sorted(({'id': a, 'p': round(Rn['p'][a], 3), 'if_yes': round(y, 3), 'if_no': round(n, 3)} for a, (y, n) in Rn['split'].items()
                            if a not in SETTLED and y is not None and n is not None), key=lambda d: d['if_no'] - d['if_yes']),
        'engine': ENGINE,
        'outlook_baselines': {'from_the_figures': baselines(), 'as_entered_in_november_2026': ENTERED_OUTLOOK, 'recession_share_from': 'the share of like stretches since 1964 in which a recession began in the months still ahead'},
        'approval_step': {'points_a_month': APPROVAL['step'], 'measured': APPROVAL['step_from'], 'from': f"{APPROVAL['approve']}% approve, {APPROVAL['disapprove']}% disapprove"},
        'third_candidates': {'chance_none_reaches_10': round(THIRD_P, 3), 'reading': ((THIRD or {}).get('now') or {}).get('reading'), 'pollsters': ((THIRD or {}).get('now') or {}).get('pollsters', 0), 'odds_entered': POLITICS['no_third_candidate'], 'from_the_record': POLITICS['no_third_candidate']},
        'approval': {k: APPROVAL[k] for k in ('approve', 'disapprove', 'pollsters', 'polls', 'from', 'to', 'year_ago', 'midterm')},
        'states': {k: STATES[k] for k in ('through', 'growing', 'growing_ev', 'faster_ev')},
        'data_through': {'monthly': f"{datetime.date((START + K['u']) // 12, (START + K['u']) % 12 + 1, 1):%B %Y}", 'quarterly': f"{QKEY(KQ)[0]} Q{QKEY(KQ)[1]}",
                         'prices': LATEST['sp500']['date']},
    }
    assert all(out['keys'][a]['p'] in (0, 1) for a in landed), 'a key that has landed is the same in every run'
    assert all(out['keys'][a]['p'] == CALLS[a]['value'] for a in landed), 'and it is what the rule gives on the published figures'
    if all(c['value'] is not None for c in CALLS.values()):          # nothing is left open: the count is what the rules give, not a projection
        final = CALL.index({a: c['value'] for a, c in CALLS.items()})
        assert min(ix) == max(ix) and abs(ix[0] - final) < 1e-12, 'with every key called, every run gives the count the rules give'
        out['observed'] = {'index': round(final, 4), 'in_favor': sum(c['value'] for c in CALLS.values()), 'final': all(c['final'] for c in CALLS.values())}
    elif TODAY > datetime.date.fromisoformat(CALL.CYCLE['last_day']):  # the last day has passed with keys still open
        # Nothing is re-weighted. Every group keeps all of its keys and its fifth of the count, and the line stays at one half.
        # The count is given as the lowest and the highest it could be (each open key counted against the party, then for it),
        # and the keys make a call only if both ends fall on the same side of one half.
        got = {a: c['value'] for a, c in CALLS.items()}; lo = CALL.index({a: bool(v) for a, v in got.items()}); hi = CALL.index({a: (True if v is None else bool(v)) for a, v in got.items()})
        out['observed'] = {'index': None, 'lowest': round(lo, 4), 'highest': round(hi, 4), 'call': ('in favor' if lo > 0.5 else 'against' if hi <= 0.5 else None), 'in_favor': sum(bool(v) for v in got.values()),
                           'final': True, 'left_open': sorted(a for a, v in got.items() if v is None),
                           'note': 'These keys had no evidence by the last day. They are counted neither way: the count is somewhere between the two figures, and there is a call only if both are on the same side of one half.'}
    assert set(out['keys']) | set(SETTLED) == set(full) and all(out['keys'][a]['note'] for a in out['keys'])
    # how far the answer moves when the main assumptions do
    vary = []
    def also(label, **kw):
        r = run(runs=min(60000, RUNS), **kw); v = r['index']
        vary.append({'what': label, 'mean': round(avg(v), 3), 'above_half': round(sum(1 for x in v if x > 0.5) / len(v), 3)})
    also('recession in 20% of runs', share=0.20); also('recession in 40% of runs', share=0.40)
    keep = dict(POLITICS)                              # the nomination keys: every chance a quarter of the way to no, then to yes, then as typed in November 2026
    lean = lambda to: {k: (v + 0.25 * (to - v)) for k, v in keep.items() if isinstance(v, float) and k != 'slump_in_recession'}
    for to, label in ((0.0, 'a rougher nomination season'), (1.0, 'a smoother nomination season')):
        POLITICS.update(lean(to)); POLITICS['stronger'] = {k: v + 0.25 * (to - v) for k, v in keep['stronger'].items()}; also(label); POLITICS.update(keep)
    e = ENTERED_POLITICS; lost = 1 - (e['dem_on_ballot'] * e['dem_nominee_wins_nh'] + (1 - e['dem_on_ballot']) * e['dem_write_in_win'])
    POLITICS.update(no_third_candidate=e['no_third_candidate'], nominee_wins_nh=e['nominee_wins_nh'], two_thirds_if_won=e['two_thirds_if_won'], two_thirds_if_lost=e['two_thirds_if_lost'], challenger_loses_nh=lost)
    also('the nomination odds as typed in November 2026'); POLITICS.update(keep)
    step = APPROVAL['step']                                # approval moving half as much, or twice as much, from month to month as it has in this term
    APPROVAL['step'] = step / 2; also('approval moving half as much each month'); APPROVAL['step'] = step * 2; also('approval moving twice as much each month'); APPROVAL['step'] = step
    out['if'] = vary
    json.dump(out, open(os.path.join(HERE, 'projection_2028.json'), 'w'), indent=1)
    for row in CALL.record(CALLS, TODAY, os.path.join(D, 'key_calls.csv')):
        print(f"  the record: {row['key']} {row['status']}" + (f", {'yes' if row['value'] == '1' else 'no'}" if row['value'] else '') + (' (final)' if row['final'] == '1' else ''))

    print(f"2028, run ahead, as of {AS_OF}: {RUNS:,} runs over {Rn['stretches']} stretches of history ({Rn['first']} to {Rn['last']}; {Rn['with_recession']} ran into a recession, weighted to {OUTLOOK['recession_share']:.0%})")
    print(f"  share of keys in the Republicans' favor: mean {out['index']['mean']:.1%}, middle {out['index']['median']:.1%}; half of runs between {out['index']['p25']:.1%} and {out['index']['p75']:.1%}; "
          f"nine in ten between {out['index']['p5']:.1%} and {out['index']['p95']:.1%}")
    print(f"  above one half (the keys would say the Republicans win): {above:.1%} of runs | without a recession: {out['calm']['above_half']:.1%}")
    print(f"  if every open key goes the likelier way: {out['likely']['in_favor']} of 52 in favor, {out['likely']['index']:.1%} by group")
    for g, v in out['groups'].items():
        print(f"  {g}  expected {v['mean']:.0%}  (one run in ten below {v['p10']:.0%}, one in ten above {v['p90']:.0%})")
    for a in sorted(out['keys']):
        print(f"  {a}  {out['keys'][a]['p']:5.0%}  {out['keys'][a]['note']}")
    for v in vary:
        print(f"  if {v['what']:45s} mean {v['mean']:.1%}  above half {v['above_half']:.1%}")


if __name__ == '__main__':
    main()
