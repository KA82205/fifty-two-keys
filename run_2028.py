"""2028, run ahead: where the 44 open keys are likely to land. Writes projection_2028.json.

THIS IS NOT THE MODEL. The model scores each key by its rule once the June 2028 figures exist. This file estimates,
on November 22, 2026, how likely each open key is to go the party's way, and from that where the count may end up.
Nothing here changes a key, a group or a rule, and nothing here was checked against an election result.

How the economy keys are run (33 keys)
  1 Start from the latest figures (FRED, November 22, 2026) and the outlook forecasters hold today (OUTLOOK below).
  2 Take every stretch of 20 months since 1964 that began, like now, with unemployment at or below its normal rate
    and no recession under way. Measure how each series moved in that stretch against its own pace over the three
    years before (or, for prices, oil, stocks, housing, claims and sentiment, simply how it moved).
  3 Lay each stretch over today's outlook, so the middle of the stretches that had no recession sits on the outlook,
    and score all 33 keys on the result. One stretch gives one complete set of keys, so keys that move together in
    real life move together here: a recession hits all of them at once.
  4 Stretches that ran into a recession are weighted to 30% of the total. History alone gives more and forecasters
    give less.
  Three series are handled apart. Unemployment is put halfway between the forecasters' flat path and its drift in the
  past stretches, and never below 3.4%. Payroll jobs follow the outlook and unemployment, because past job booms came
  with a fast-growing workforce. The two state keys use a stand-in for the state indexes fitted on 1980 to 2024.

How the other keys are run (11 keys): by the odds in POLITICS below, set from polls and from how these keys went in
the 19 elections since 1952. They are judgment, and the README lists what each rests on.
"""
import csv, json, math, os, random, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
sys.path.insert(0, HERE)
from build import GROUPS, ALL                         # noqa: E402

AS_OF = 'November 22, 2026'
ym = lambda y, m: y * 12 + (m - 1)
NOW, H = ym(2026, 10), 20                             # October 2026 is the last month of data; June 2028 is 20 months on
QEND = [2, 5, 8, 11, 14, 17, 20]                      # quarter ends from December 2026 to June 2028
RUNS, SEED = 200000, 2028

# ------------------------------------------------------------------ the outlook, and what it rests on
OUTLOOK = {
    'recession_share': 0.30,      # stretches that ran into a recession: 33% in history; forecasters put the risk of a falling quarter near 20%
    'unemployment': 4.2,          # Survey of Professional Forecasters (Nov. 16, 2026): 4.2 to 4.3 through 2028; Federal Reserve (Sept.): 4.1
    'jobs_a_month': [90, 90, 65, 65, 65, 49, 49, 49, 51, 51, 51, 51, 51, 51, 50, 50, 50, 50, 50, 50],     # the same survey, thousands
    'gdp': [2.3, 2.1, 2.2, 2.2, 2.1, 2.1, 2.1],     # the same survey, annual rates, 2026 Q4 to 2028 Q2
    'income': [2.0] * 7,          # real disposable income: no survey; a little under GDP, as it has run this term
    'cpi_quarters': [4.0, 2.6, 2.4, 2.4, 2.4, 2.3, 2.3, 2.3],     # the same survey, annual rates, 2026 Q4 on
    'population': 0.25,           # percent a year, the pace of the past year
    'industrial_production': 1.0, 'spending': 2.2, 'hourly_pay': 3.8, 'factory_jobs': 0.0,     # percent a year
    'oil': [(1, 84.0), (8, 80.0), (14, 72.0), (20, 70.0)],     # dollars: now; June and December 2027; June 2028. Futures, the EIA's November outlook
    'sentiment': [(1, 51.5), (8, 57.0), (20, 60.0)],            # the November reading, then a partial recovery as the oil shock fades
    'housing_starts': 1300.0, 'claims': 205000.0,                # held at their recent levels
    'sp500_now': 6910.39,         # close of November 20, 2026
}
POLITICS = {
    'surge': 0.03,                # disapproval falls below half by June 2028 (it is 60% now)
    'net_given_surge': 0.6, 'fifty_given_net': 0.7,
    'slump_in_recession': 0.5,    # in a recession, half the time none of the three "approval is rising" keys holds
    'no_third_candidate': 0.88,   # a third candidate reached 10% in June polls in 4 of 19 elections; none is near it now
    'nominee_wins_nh': 0.68,      # Republican nominees won New Hampshire in 8 of 11 open contests; Vance leads there, the race is level nationally
    'two_thirds_if_won': 0.82, 'two_thirds_if_lost': 0.60,
    'dem_on_ballot': 0.85,        # New Hampshire and the Democratic National Committee are in dispute over the date
    'dem_nominee_wins_nh': 0.42,  # Democratic nominees won New Hampshire in 4 of 10 open contests
    'dem_write_in_win': 0.10,
}
# what the three "approval is rising" keys (C03, C04, C05) did in each election since 1952; years without the president on the ticket count double
CYCLES = {1952: (1, 0, 1), 1956: (1, 1, 0), 1960: (0, 1, 0), 1964: (1, 1, 0), 1968: (0, 0, 0), 1972: (1, 1, 1), 1976: (0, 0, 0), 1980: (1, 0, 0),
          1984: (1, 1, 1), 1988: (0, 0, 0), 1992: (0, 0, 0), 1996: (1, 1, 1), 2000: (1, 0, 0), 2004: (0, 0, 0), 2008: (0, 0, 0), 2012: (1, 1, 1),
          2016: (1, 1, 1), 2020: (0, 0, 0), 2024: (0, 0, 0)}
OPEN_SEAT = {1952, 1960, 1968, 1988, 2000, 2008, 2016}
SETTLED = {'D01': 0, 'D02': 0, 'D03': 0, 'D04': 0, 'D05': 0, 'D06': 0, 'E01': 0, 'E02': 1}
POLLS = dict(approve=37.9, disapprove=59.8, approve_midterm=38.5, rubio=35.4, vance=34.0, nh_vance=39.0, nh_rubio=27.3)     # RealClearPolitics averages, Nov. 21, 2026

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
    for r in csv.DictReader(open(os.path.join(D, 'latest_monthly_2026-11.csv'))):
        y, m, _ = r['observation_date'].split('-')
        for name, (s, col) in MD.items():
            if r[col] != '':
                P[s][ym(int(y), int(m))] = float(r[col])
    for s, d in P.items():                                # October 2025 was not collected; sentiment was quarterly before 1978
        ts = sorted(d)
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
    for r in csv.DictReader(open(os.path.join(D, 'quarterly_2016-2026.csv'))):
        y, m, _ = r['observation_date'].split('-'); q = int(y) * 4 + (int(m) - 1) // 3
        Q[q] = {'gdp': float(r['A191RL1Q225SBEA']), 'rdpi': float(r['A067RL1Q156SBEA'])}
        level[(int(y), (int(m) - 1) // 3 + 1)] = {'pop': float(r['B230RC0Q173SBEA']), 'gdp_pc': float(r['A939RX0Q048SBEA']), 'rdpi_pc': float(r['A229RX0Q048SBEA'])}
    return Q, level


P = load_monthly()
QS, LEVEL = load_quarterly()
avg = lambda xs: sum(xs) / len(xs)
m3 = lambda s, y, months: avg([P[s][ym(y, m)] for m in months])
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


def normal_rate(t):
    y = t / 12
    for (a, va), (b, vb) in zip(NORMAL, NORMAL[1:]):
        if a <= y <= b:
            return va + (vb - va) * (y - a) / (b - a)
    return NORMAL[-1][1]


def stretch(t0):
    """What happened over the 20 months after month t0, as moves from t0 (growth series net of their own pace before it)."""
    if t0 + H > max(P['pce']):
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
    for t0 in range(ym(1964, 1), NOW):
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
    o, last = {}, {s: P[s][NOW] for s in ('u', 'jobs', 'man', 'cpi', 'ip', 'wage')}
    o['u'] = [last['u'], (last['u'] + OUTLOOK['unemployment']) / 2] + [OUTLOOK['unemployment']] * (H - 1)
    j = [last['jobs']]
    for g in OUTLOOK['jobs_a_month']:
        j.append(j[-1] + g)
    o['jobs'] = j
    grow = lambda x0, rate, lead=0: [x0 * (1 + rate / 100) ** ((h + lead) / 12) for h in range(H + 1)]
    o['man'], o['ip'], o['wage'] = grow(last['man'], OUTLOOK['factory_jobs']), grow(last['ip'], OUTLOOK['industrial_production']), grow(last['wage'], OUTLOOK['hourly_pay'])
    o['pce'] = grow(P['pce'][NOW - 1], OUTLOOK['spending'], 1)                       # spending is known to September
    qa = [m3('cpi', 2026, (7, 8, 9))]
    for r in OUTLOOK['cpi_quarters']:
        qa.append(qa[-1] * (1 + r / 100) ** 0.25)
    nd = (3 * qa[1] - last['cpi']) / 2                                               # November and December, given October
    pts = [(0, last['cpi']), (1, nd), (2, nd)] + [(1 + 3 * (k - 1), qa[k]) for k in range(2, 9)]      # quarterly averages sit on the middle month
    o['cpi'] = [math.exp(interp([(a, math.log(v)) for a, v in pts], h)) for h in range(H + 1)]
    o['oil'] = [P['oil'][NOW]] + [interp(OUTLOOK['oil'], h) for h in range(1, H + 1)]
    o['ics'] = [P['ics'][NOW]] + [interp(OUTLOOK['sentiment'], h) for h in range(1, H + 1)]
    o['houst'], o['claims'] = [OUTLOOK['housing_starts']] * (H + 1), [OUTLOOK['claims']] * (H + 1)
    return o


O = outlook_paths()


def middle(S):
    """The middle of the stretches that had no recession. Forecasters' outlooks describe that case, so it is laid on the outlook."""
    calm = [s for s in S if not s['recession']]
    med = {k: [st.median(s[k][h] for s in calm) for h in range(H + 1)] for k in list(PACE) + MOVES if k != 'rsp'}
    med.update({k: [st.median(s[k][q] for s in calm) for q in range(7)] for k in ('gdp', 'rdpi')})
    return med


def economy_keys(s, med, rnd):
    d = lambda k, h: s[k][h] - med[k][h]
    cpi = [O['cpi'][h] * math.exp(d('cpi', h)) for h in range(H + 1)]
    lv = {k: [O[k][h] * math.exp(d(k, h)) for h in range(H + 1)] for k in ('man', 'ip', 'pce', 'houst', 'claims')}
    rw = [O['wage'][h] / O['cpi'][h] * math.exp(d('rwage', h)) for h in range(H + 1)]
    ro = [None] + [O['oil'][h] / O['cpi'][h] * math.exp(d('roil', h) - d('roil', 1)) for h in range(1, H + 1)]
    sp = [None] + [OUTLOOK['sp500_now'] * math.exp(s['rsp'][h] - s['rsp'][1]) * cpi[h] / cpi[1] for h in range(1, H + 1)]
    ur = [max(3.4, 0.5 * (O['u'][h] + d('u', h)) + 0.5 * (O['u'][0] + s['u'][h])) for h in range(H + 1)]      # halfway; not below 3.4%
    u = [round(x, 1) for x in ur]
    lf = rnd.gauss(0, 0.004)                                                          # the workforce may grow a little faster or slower than expected
    jobs = [O['jobs'][h] * (1 - 0.0104 * (ur[h] - O['u'][h]) + lf * h / 12) for h in range(H + 1)]
    ics = [None] + [round(min(110, max(40, O['ics'][h] + d('ics', h) - d('ics', 1))), 1) for h in range(1, H + 1)]
    g = [OUTLOOK['gdp'][q] + s['gdp'][q] - med['gdp'][q] for q in range(7)]
    r = [OUTLOOK['income'][q] + s['rdpi'][q] - med['rdpi'][q] for q in range(7)]
    per = lambda rates: [(1 + x / 100) ** 0.25 / POP_Q for x in rates]
    gpc, rpc = per(g), per(r)
    spring = lambda xs, hs: avg([xs[h] for h in hs])
    u3 = lambda h: (u[h] + u[h - 1] + u[h - 2]) / 3
    ann = lambda ratio, months: 100 * (ratio ** (12 / months) - 1)
    pop28 = BASE['pop_26q3'] * POP_Q ** 7
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


def other_keys(rnd, recession):
    pool = [c for y, c in CYCLES.items() for _ in range(2 if y in OPEN_SEAT else 1)]
    c3, c4, c5 = (0, 0, 0) if recession and rnd.random() < POLITICS['slump_in_recession'] else rnd.choice(pool)
    surge = (not recession) and rnd.random() < POLITICS['surge']
    net = surge and rnd.random() < POLITICS['net_given_surge']; fifty = net and rnd.random() < POLITICS['fifty_given_net']
    if surge:
        c3 = c4 = c5 = 1
    won = rnd.random() < POLITICS['nominee_wins_nh']
    cut = lambda mu, sd, lo, hi: min(hi, max(lo, rnd.gauss(mu, sd)))
    rep = cut(47, 8, 30, 70) if won else cut(33, 8, 10, 45)                           # the Republican nominee's share of the New Hampshire vote
    if rnd.random() < POLITICS['dem_on_ballot']:
        dwon = rnd.random() < POLITICS['dem_nominee_wins_nh']; dem = cut(33, 6, 24, 55) if dwon else cut(22, 10, 3, 34)
    else:
        dwon = rnd.random() < POLITICS['dem_write_in_win']; dem = cut(45, 8, 30, 65) if dwon else cut(5, 3, 0, 15)
    return {'C01': fifty, 'C02': net, 'C03': bool(c3), 'C04': bool(c4), 'C05': bool(c5), 'C06': surge,
            'E03': rnd.random() < POLITICS['no_third_candidate'],
            'E04': rnd.random() < (POLITICS['two_thirds_if_won'] if won else POLITICS['two_thirds_if_lost']), 'E05': won, 'E06': rep > dem, 'E07': not dwon}


def run(runs=RUNS, seed=SEED, share=None, gap=0.3):
    share = OUTLOOK['recession_share'] if share is None else share
    S = stretches(gap); med = middle(S); rnd = random.Random(seed)
    econ = [economy_keys(s, med, rnd) for s in S]
    rec = [s['recession'] for s in S]; seen = avg(rec)
    w = [share / seen if r else (1 - share) / (1 - seen) for r in rec]
    size = {g: len(ks) for g, ks in GROUPS.items()}
    tally, index, by_group, calm_index = {}, [], {g: [] for g in GROUPS}, []
    for i in rnd.choices(range(len(S)), weights=w, k=runs):
        k = dict(econ[i]); k.update(other_keys(rnd, rec[i])); k.update({a: bool(b) for a, b in SETTLED.items()})
        for a, b in k.items():
            tally[a] = tally.get(a, 0) + b
        sh = {g: sum(v for a, v in k.items() if a[0] == g) / size[g] for g in GROUPS}
        for g in GROUPS:
            by_group[g].append(sh[g])
        index.append(avg(list(sh.values())))
        if not rec[i]:
            calm_index.append(index[-1])
    return dict(p={a: tally[a] / runs for a in sorted(tally)}, index=index, by_group=by_group, calm=calm_index, stretches=len(S), with_recession=sum(rec),
                first=S[0]['t0'] // 12, last=S[-1]['t0'] // 12)


def notes():
    """Where each open key stands today, in a sentence."""
    now = {s: P[s][NOW] for s in P if NOW in P[s]}
    yr = lambda s, t=NOW: 100 * (P[s][t] / P[s][t - 12] - 1)
    ann = lambda ratio, months: 100 * (ratio ** (12 / months) - 1)
    term_gdp, term_inc = 100 * ((G['now'] / G['q24']) ** (4 / 7) - 1), 100 * ((R['now'] / R['q24']) ** (4 / 7) - 1)
    sp_real = 100 * ((OUTLOOK['sp500_now'] / now['cpi']) / (BASE['sp_jan25'] / BASE['cpi_jan25']) - 1)
    oil_then = BASE['oil_jan25'] * now['cpi'] / BASE['cpi_jan25']
    pce_need = 100 * (((1 + ann((BASE['pce_jan25'] / BASE['pop_25q1']) / (BASE['pce_jan21'] / BASE['pop_21q1']), 48) / 100) ** (41 / 12)
                       * BASE['pce_jan25'] * (BASE['pop_26q3'] * POP_Q ** 7 / BASE['pop_25q1']) / P['pce'][NOW - 1]) ** (12 / 21) - 1)
    starts = avg([P['houst'][NOW - i] for i in range(6)])
    claims = avg([P['claims'][NOW - i] for i in range(3)])
    oil = OUTLOOK['oil']
    n = {
        'A01': f"Forecasters expect growth of about {OUTLOOK['gdp'][6]}% a year in spring 2028. It was 3.4% last quarter.",
        'A02': f"Forecast growth is about 2% a year, and the population is growing about {OUTLOOK['population']}%.",
        'A03': f"Up {yr('ip'):.1f}% in the past year.",
        'A04': f"Real spending is up {yr('pce', NOW - 1):.1f}% in the past year, ahead of the population.",
        'A05': f"It is {now['u']}% now. Forecasters expect about {OUTLOOK['unemployment']}% through 2028, and a tie counts as no.",
        'A06': "Forecasters expect about 50,000 new jobs a month, a slow pace that a weak year could turn negative.",
        'A07': f"Factory jobs have risen {1000 * (now['man'] - P['man'][ym(2025, 12)]):,.0f} since December after falling through 2025.",
        'A08': f"Claims are about {claims / 1000:.0f},000 a week, already low.",
        'A09': "No signal now. It would take a rise of about half a point in unemployment.",
        'A10': f"Up {100 * (R['now'] / LEVEL[(2025, 3)]['rdpi_pc'] - 1):.1f}% in the past year, held back by the jump in prices.",
        'A11': f"Pay is rising {yr('wage'):.1f}% a year and inflation is forecast to slow to about 2.4%.",
        'A12': f"Inflation is {yr('cpi', NOW - 1):.1f}% now. This year's oil shock lifts the mid-2027 figure that mid-2028 is compared with.",
        'A13': f"About ${oil[0][1]:.0f} a barrel now. Futures and forecasts point to about ${oil[1][1]:.0f} in mid-2027 and ${oil[3][1]:.0f} in mid-2028.",
        'A14': "The S&P 500 was higher than a year before in about seven years of ten, and lower in recessions.",
        'A15': "Higher than six months before in about two years of three.",
        'A16': f"The index is {OUTLOOK['sentiment'][0][1]}, near its record low, which leaves room to recover.",
        'A17': f"Starts are running near {starts / 1000:.2f} million a year, with borrowing costs high.",
        'A18': "State economies are growing in 49 of 51 now. This key has failed only in sharp downturns (1980, 2020).",
        'B01': f"So far this term: {term_gdp:.2f}% a year. The bar, the average of the last two terms, is {BAR['gdp']:.2f}%.",
        'B02': f"Up {100 * (now['ip'] / BASE['ip_jan25'] - 1):.1f}% since January 2025, against {ann(BASE['ip_jan25'] / BASE['ip_jan21'], 48):.1f}% a year last term.",
        'B03': f"It would take real spending growth of {pce_need:.1f}% a year from here.",
        'B04': f"It was {BASE['u_jan25']}% in January 2025 and is {now['u']}% now.",
        'B05': f"Out of reach: jobs grew {ann(BASE['jobs_jan25'] / BASE['jobs_jan21'], 48):.1f}% a year last term and {ann(now['jobs'] / BASE['jobs_jan25'], 21):.1f}% a year so far in this one.",
        'B06': f"{now['man'] / 1000:.2f} million now against {BASE['man_jan25'] / 1000:.2f} million in January 2025.",
        'B07': f"About {claims / 1000:.0f},000 a week now against {BASE['claims_q1_25'] / 1000:.0f},000 at the start of the term.",
        'B08': f"So far this term: {term_inc:.1f}% a year. Last term: {BAR['rdpi']:.1f}%.",
        'B09': f"Pay after inflation is {100 * ((now['wage'] / now['cpi']) / (BASE['wage_jan25'] / BASE['cpi_jan25']) - 1):.1f}% above its January 2025 level.",
        'B10': f"Inflation has averaged {ann(now['cpi'] / BASE['cpi_jan25'], 21):.1f}% a year this term against {ann(BASE['cpi_jan25'] / BASE['cpi_jan21'], 48):.1f}% last term.",
        'B11': f"Oil is about ${oil[0][1]:.0f} now. January 2025's price is ${oil_then:.0f} in today's dollars, and forecasts have oil below that by 2028.",
        'B12': f"After November's fall the S&P 500 is {sp_real:.0f}% above its start-of-term level, after inflation.",
        'B13': f"The index is {OUTLOOK['sentiment'][0][1]}. It was {BASE['ics_jan25']} in January 2025.",
        'B14': f"Starts average {starts / 1000:.2f} million against {BASE['houst_q1_25'] / 1000:.2f} million at the start of the term.",
        'B15': "So far this term, growth is above its 2024 pace in states holding 414 electoral votes.",
        'C01': f"{POLLS['approve']:.0f}% approve now, in the RealClearPolitics average.",
        'C02': f"{POLLS['approve']:.0f}% approve and {POLLS['disapprove']:.0f}% disapprove now.",
        'C03': "Approval has fallen in each year of this term. It rose in the last year for 3 of the 7 presidents who were not running again.",
        'C04': f"Approval averaged {POLLS['approve_midterm']}% around the midterms, its low for the term. It was higher by June in 8 of 19 cycles.",
        'C05': "It rose from January to June of the election year in 6 of 19 cycles.",
        'C06': f"{POLLS['disapprove']:.0f}% disapprove now.",
        'E03': "No third candidate is polling near 10%. One reached it by June in 4 of the 19 elections.",
        'E04': f"Rubio ({POLLS['rubio']:.0f}%) and Vance ({POLLS['vance']:.0f}%) are level in national polls, which points to a real contest.",
        'E05': f"Vance leads Rubio in New Hampshire polls, {POLLS['nh_vance']:.0f}% to {POLLS['nh_rubio']:.0f}%, and the nomination is open.",
        'E06': "Two candidates dominate the Republican race, and the Democratic field is split five ways.",
        'E07': "The Democratic field is split, and New Hampshire is in dispute with the national party over its date.",
    }
    return n


def main():
    full = {k[:3]: k for k in ALL}
    Rn = run()
    ix = sorted(Rn['index']); n = len(ix)
    q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
    above = sum(1 for x in ix if x > 0.5) / n
    size = {g: len(ks) for g, ks in GROUPS.items()}
    likely = {a: Rn['p'][a] >= 0.5 for a in Rn['p']}
    lk = {g: sum(v for a, v in likely.items() if a[0] == g) for g in GROUPS}
    out = {
        'as_of': AS_OF, 'runs': RUNS, 'stretches': {'n': Rn['stretches'], 'with_recession': Rn['with_recession'], 'first': Rn['first'], 'last': Rn['last']},
        'recession_share': OUTLOOK['recession_share'],
        'index': {'mean': round(avg(ix), 3), 'median': round(q(ix, .5), 3), 'p5': round(q(ix, .05), 3), 'p25': round(q(ix, .25), 3), 'p75': round(q(ix, .75), 3),
                  'p95': round(q(ix, .95), 3), 'above_half': round(above, 3)},
        'calm': {'mean': round(avg(Rn['calm']), 3), 'above_half': round(sum(1 for x in Rn['calm'] if x > 0.5) / len(Rn['calm']), 3)},
        'hist': [{'lo': b, 'share': round(sum(1 for x in ix if b <= 100 * x < b + 5) / n, 4)} for b in range(0, 100, 5)],
        'groups': {g: {'mean': round(avg(v), 3), 'p10': round(q(sorted(v), .1), 3), 'p90': round(q(sorted(v), .9), 3), 'likely': lk[g], 'n': size[g]} for g, v in Rn['by_group'].items()},
        'likely': {'in_favor': sum(likely.values()), 'index': round(avg([lk[g] / size[g] for g in GROUPS]), 3)},
        'keys': {a: {'p': round(v, 3), 'note': notes().get(a, '')} for a, v in Rn['p'].items() if a not in SETTLED},
        'outlook': {k: v for k, v in OUTLOOK.items()}, 'politics': POLITICS, 'polls': POLLS,
    }
    assert set(out['keys']) | set(SETTLED) == set(full) and all(out['keys'][a]['note'] for a in out['keys'])
    # how far the answer moves when the main assumptions do
    vary = []
    def also(label, **kw):
        r = run(runs=60000, **kw); v = r['index']
        vary.append({'what': label, 'mean': round(avg(v), 3), 'above_half': round(sum(1 for x in v if x > 0.5) / len(v), 3)})
    also('recession in 20% of runs', share=0.20); also('recession in 40% of runs', share=0.40)
    keep = dict(POLITICS)
    POLITICS.update(nominee_wins_nh=0.55, two_thirds_if_won=0.7, two_thirds_if_lost=0.4, no_third_candidate=0.8, dem_nominee_wins_nh=0.5); also('a rougher nomination season')
    POLITICS.update(keep); POLITICS.update(nominee_wins_nh=0.8, two_thirds_if_won=0.9, two_thirds_if_lost=0.7, no_third_candidate=0.93, dem_nominee_wins_nh=0.35); also('a smoother nomination season')
    POLITICS.update(keep); POLITICS.update(surge=0.0); also('no chance that disapproval falls below half')
    POLITICS.update(keep); POLITICS.update(surge=0.08); also('an 8% chance that it does')
    POLITICS.update(keep)
    out['if'] = vary
    json.dump(out, open(os.path.join(HERE, 'projection_2028.json'), 'w'), indent=1)

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
