"""Research on the model itself. Writes research.json, which the page and research/audit.md draw on.

NOTHING HERE IS THE MODEL. The official model (build.py, locked in locked_keys.csv) is read and never changed. Every
alternative below is an experiment, reported so that the official model can be judged against it.

    python research.py
"""
import itertools, json, math, os, random, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import GROUPS, GROUP_NAMES, ALL, build      # noqa: E402
from test import TOOK_OFFICE                           # noqa: E402

rows, raw, _ = build()
YEARS = [r['year'] for r in rows]
WON = np.array([bool(TOOK_OFFICE[y]) for y in YEARS])
VOTE = np.array([float(r['inc_share']) for r in rows])
ID = [k[:3] for k in ALL]
X = np.array([[np.nan if r[k] is None else float(r[k]) for k in ALL] for r in rows])        # elections by keys; nan where a key has no answer
N = len(rows)


def index(M, groups=None):
    """The official count: the average over groups of the share of each group's answered keys that are yes."""
    groups = groups or [[ALL.index(k) for k in ks] for ks in GROUPS.values()]
    return np.array([np.mean([np.nanmean(row[g]) for g in groups if not np.all(np.isnan(row[g]))]) for row in M])


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


def tail(k, n, p):
    """The chance of k or more right out of n for a caller who is right with probability p each time."""
    return round(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)), 4)


def loo_line(cols, y):
    """Each election's vote estimated from a straight line (in one or more columns) fitted to the other elections."""
    cols = [np.asarray(c, float) for c in cols]; out = []
    for i in range(len(y)):
        m = np.arange(len(y)) != i
        b = np.linalg.lstsq(np.column_stack([np.ones(m.sum())] + [c[m] for c in cols]), y[m], rcond=None)[0]
        out.append(float(b[0] + sum(bj * c[i] for bj, c in zip(b[1:], cols))))
    return np.array(out)


out = {}
IX = index(X)
right = int(((IX > 0.5) == WON).sum())
assert right == 15

# ------------------------------------------------------------------ 1 how alike the keys are
C = np.full((len(ALL), len(ALL)), np.nan); both = np.zeros_like(C)
for i, j in itertools.product(range(len(ALL)), repeat=2):
    m = ~np.isnan(X[:, i]) & ~np.isnan(X[:, j]); both[i, j] = m.sum()
    if m.sum() >= 12 and X[m, i].std() > 0 and X[m, j].std() > 0:
        C[i, j] = np.corrcoef(X[m, i], X[m, j])[0, 1]
pairs = sorted(((round(float(C[i, j]), 2), ID[i], ID[j], int(both[i, j]), int((X[:, i] == X[:, j]).sum())) for i in range(len(ALL)) for j in range(i + 1, len(ALL)) if not np.isnan(C[i, j])), reverse=True)
gi = {g: [ALL.index(k) for k in ks] for g, ks in GROUPS.items()}
within = {g: round(float(np.nanmean([C[i, j] for i in gi[g] for j in gi[g] if i < j])), 2) for g in GROUPS}
between = round(float(np.nanmean([C[i, j] for a, b in itertools.combinations(GROUPS, 2) for i in gi[a] for j in gi[b]])), 2)
# how many unrelated keys the 52 are worth: (sum of eigenvalues)^2 / sum of squares, on the matrix with gaps set to zero.
# With 19 elections no set of keys can show more than 18 independent directions, so this is a ceiling as much as a finding.
Cz = np.where(np.isnan(C), 0, C); np.fill_diagonal(Cz, 1)
ev = np.clip(np.linalg.eigvalsh(Cz), 0, None)
eff = float(ev.sum() ** 2 / (ev ** 2).sum())
# clusters: keys that answer alike, joined while the average correlation between two clusters is 0.6 or more (average linkage)
clusters = [[i] for i in range(len(ALL))]
def link(a, b):
    v = [C[i, j] for i in a for j in b if not np.isnan(C[i, j])]
    return np.mean(v) if len(v) == len(a) * len(b) else -1
while True:
    best = max(((link(a, b), x, y) for x, a in enumerate(clusters) for y, b in enumerate(clusters) if x < y), default=(-1, 0, 0))
    if best[0] < 0.6:
        break
    clusters[best[1]] += clusters.pop(best[2])
clusters = sorted((sorted(c) for c in clusters), key=lambda c: (-len(c), c[0]))
weight = {ID[i]: round(1 / (len(GROUPS) * len(gi[g])), 4) for g in GROUPS for i in gi[g]}
out['alike'] = {
    'ids': ID, 'matrix': [[None if np.isnan(v) else round(float(v), 2) for v in row] for row in C],
    'top': [{'r': r, 'a': a, 'b': b, 'n': n, 'same': s} for r, a, b, n, s in pairs[:14]], 'opposed': [{'r': r, 'a': a, 'b': b, 'n': n} for r, a, b, n, _ in pairs[-5:]],
    'pairs_at_07': sum(1 for p in pairs if p[0] >= 0.7), 'pairs_at_05': sum(1 for p in pairs if p[0] >= 0.5), 'pairs': len(pairs),
    'within': within, 'between': between, 'effective_keys': round(eff, 1), 'ceiling': N - 1,
    'clusters': [[ID[i] for i in c] for c in clusters if len(c) > 1], 'singletons': sum(1 for c in clusters if len(c) == 1), 'n_clusters': len(clusters),
    'same_always': [[a, b, n] for r, a, b, n, same in pairs if same == n and n >= 12],
    'weight': weight, 'cluster_weight': [{'keys': [ID[i] for i in c], 'weight': round(sum(weight[ID[i]] for i in c), 3)} for c in clusters if len(c) > 1][:8],
    'answered': {str(y): int((~np.isnan(X[t])).sum()) for t, y in enumerate(YEARS)},
}

# ------------------------------------------------------------------ 2 simple rules, scored the same way (did the call match who took office?)
net = np.array([np.nan if v.get('approval_june') is None or v.get('disapproval_june') is None else v['approval_june'] - v['disapproval_june'] for v in raw])
gdp = np.array([np.nan if v.get('gdp_q2_growth') is None else v['gdp_q2_growth'] for v in raw])
first = X[:, ID.index('E02')]
def record(call, name, kind):
    ok = (call == WON)
    return {'name': name, 'kind': kind, 'right': int(ok.sum()), 'n': N, 'misses': [y for y, o in zip(YEARS, ok) if not o], 'interval': wilson(int(ok.sum()), N)}
base = [record(np.zeros(N, bool), 'The party in office always loses', 'no information'),
        record(np.ones(N, bool), 'The party in office always wins', 'no information'),
        record(first == 1, 'It wins after one term in office and loses after two or more', 'one fact'),
        record(net > 0, 'It wins if more approve of the president than disapprove in June', 'one figure'),
        record(gdp > 0, 'It wins if the economy grew in the second quarter', 'one figure')]
assert not np.isnan(net).any() and not np.isnan(gdp).any()
tfc = loo_line([net, gdp, first], VOTE)                  # approval, growth and first term together, each election left out (after Abramowitz)
base.append(record(tfc > 50, 'Approval, growth and first term in one equation, each election left out', 'fitted'))
keys_loo = loo_line([IX], VOTE)
base.append(record(IX > 0.5, 'Fifty-Two Keys', 'the model'))
out['baselines'] = base
out['vote'] = [{'name': n, 'mae': round(float(np.mean(np.abs(p - VOTE))), 2), 'side': int(((p > 50) == (VOTE > 50)).sum())}
               for n, p in (('Fifty-Two Keys, one line', keys_loo), ('Net approval alone', loo_line([net], VOTE)), ('Approval, growth and first term', tfc),
                            ('Always 50%', np.full(N, 50.0)), ('The average of the other elections', np.array([VOTE[np.arange(N) != i].mean() for i in range(N)])))]

# ------------------------------------------------------------------ 3 how much 19 elections can show
out['sample'] = {
    'right': right, 'n': N, 'interval': wilson(right, N),
    'by_chance': {'coin': tail(right, N, 0.5), 'always_loses': tail(right, N, 11 / 19), 'approval_rule': tail(right, N, base[3]['right'] / N)},
    'won': int(WON.sum()),
    # when two callers disagree: on how many elections does each beat the other (a sign test on the disagreements)
    'against_approval': {'keys_only': [y for y, a, b in zip(YEARS, (IX > 0.5) == WON, (net > 0) == WON) if a and not b], 'approval_only': [y for y, a, b in zip(YEARS, (IX > 0.5) == WON, (net > 0) == WON) if b and not a]},
    'against_always_loses': {'keys_only': [y for y, a, b in zip(YEARS, (IX > 0.5) == WON, ~WON) if a and not b], 'other_only': [y for y, a, b in zip(YEARS, (IX > 0.5) == WON, ~WON) if b and not a]},
}

# ------------------------------------------------------------------ 4 experiments (not the model)
exp = {}
cl = [np.array(c) for c in clusters]
one_vote = np.array([np.nanmean([np.nanmean(row[c]) for c in cl if not np.all(np.isnan(row[c]))]) for row in X])     # one concept, one vote: clusters of alike keys count once
exp['one_concept_one_vote'] = record(one_vote > 0.5, 'One vote for each cluster of alike keys', 'experiment')
flat = np.nanmean(X, axis=1)
exp['every_key_equal'] = record(flat > 0.5, 'Every key counts the same', 'experiment')
rule_only = [i for i, k in enumerate(ID) if k not in ('E03', 'E04')]                                                 # without the two keys that are Lichtman's own ratings
groups_ro = [[i for i in gi[g] if i in rule_only] for g in GROUPS]
exp['without_rated_keys'] = record(index(X, groups_ro) > 0.5, "Without the two keys taken from Lichtman's ratings", 'experiment')
# logistic curve through the 19 elections: the chance of winning at each count (a rough fit; see the audit)
def logit_fit(x, y, ridge=0.05):
    """A logistic curve by maximum likelihood (Newton's method), with a light penalty on the slope so that a resample in
    which the count splits winners from losers perfectly still gives a curve."""
    Z = np.column_stack([np.ones(len(x)), (x - 0.5) * 10]); b = np.zeros(2); pen = np.diag([0.0, ridge])
    for _ in range(60):
        p = 1 / (1 + np.exp(-Z @ b)); W = p * (1 - p)
        step = np.linalg.solve(Z.T @ (Z * W[:, None]) + pen, Z.T @ (y - p) - pen @ b)
        b = b + step
        if np.abs(step).max() < 1e-9:
            break
    return float(b[0]), float(b[1] * 10)
a, b = logit_fit(IX, WON.astype(float))
rnd = random.Random(52); fits = []
for _ in range(2000):
    pick = [rnd.randrange(N) for _ in range(N)]
    if 0 < WON[pick].sum() < N:
        fits.append(logit_fit(IX[pick], WON[pick].astype(float)))
curve = lambda a, b, x: 1 / (1 + math.exp(-(a + b * (x - 0.5))))
exp['win_curve'] = {'a': round(a, 3), 'b': round(b, 2), 'even_at': round(0.5 - a / b, 3), 'at': {f'{x:.2f}': [round(curve(a, b, x), 2)] + [round(float(np.percentile([curve(fa, fb, x) for fa, fb in fits], q)), 2) for q in (10, 90)]
                                                              for x in (0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80)}}
# the same curve laid over the 2028 run-ahead: the chance of winning, as against the share of runs above one half
run = json.load(open(os.path.join(HERE, 'projection_2028.json')))
over = lambda fa, fb: sum(h['share'] * curve(fa, fb, (h['lo'] + 2.5) / 100) for h in run['hist'])
exp['win_2028'] = {'chance': round(over(a, b), 3), 'range': [round(float(np.percentile([over(fa, fb) for fa, fb in fits], q)), 3) for q in (10, 90)], 'above_half': run['index']['above_half']}
out['experiments'] = exp

# ------------------------------------------------------------------ 5 the run-ahead method, tried on the past
# The 2028 run-ahead lays past 20-month stretches over today's figures. Here the same idea is tried at the same distance before
# each election from 1968: starting in October two years before, with stretches that do not overlap the 20 months being forecast,
# how often did the method's chances for the year-over-year keys match what happened? No forecasters' outlook exists for the past,
# so each series is carried at its own pace before the start; this tests the stretch method alone, not the full 2028 run.
import csv, datetime, statistics as st
import run_2028 as E
ym, H = E.ym, E.H
PACE = dict(E.PACE, jobs=36)


def path(t0):
    """How each series moved over the 20 months after t0, net of its own pace before, and that pace."""
    if t0 + H > max(E.P['pce']) or t0 - 36 < min(E.P['pce']):
        return None
    o, pace = {}, {}
    for k, months in PACE.items():
        pace[k] = 0.0 if months == 0 else math.log(E.P[k][t0] / E.P[k][t0 - months]) * 12 / months
        o[k] = [math.log(E.P[k][t0 + h] / E.P[k][t0]) - pace[k] * h / 12 for h in range(H + 1)]
    for k in E.MOVES:
        o[k] = [E.P[k][t0 + h] - E.P[k][t0] for h in range(H + 1)]
    return o, pace


def year_keys(t0, moves):
    """The year-over-year keys that need only monthly series, for an election whose run starts at t0, given how the series move."""
    lv = lambda k, h: PACE_AT[k] * h / 12 + moves[k][h]                                 # log level against t0
    u = lambda h: round(E.P['u'][t0] + moves['u'][h], 1)
    u3 = lambda h: (u(h) + u(h - 1) + u(h - 2)) / 3
    sp = lambda h: lv('rsp', h) + lv('cpi', h)
    spring = lambda k, a: sum(math.exp(lv(k, h)) for h in a) / 3
    back = math.log(E.P['cpi'][t0] / E.P['cpi'][t0 - 4])                                  # prices from the June before the start to the start
    return {'A03': lv('ip', 20) > lv('ip', 8), 'A05': u(20) < u(8), 'A06': lv('jobs', 20) > lv('jobs', 8), 'A07': lv('man', 20) > lv('man', 8),
            'A08': spring('claims', (18, 19, 20)) < spring('claims', (6, 7, 8)), 'A09': u3(20) - min(u3(h) for h in range(8, 20)) < 0.5,
            'A11': lv('rwage', 20) > lv('rwage', 8), 'A12': lv('cpi', 20) - lv('cpi', 8) < lv('cpi', 8) + back, 'A13': lv('roil', 20) < lv('roil', 8),
            'A14': sp(20) > sp(8), 'A15': sp(20) > sp(14), 'A16': moves['ics'][20] > moves['ics'][8], 'A17': spring('houst', (18, 19, 20)) > spring('houst', (6, 7, 8))}


starts = [t for t in range(ym(1962, 1), ym(2025, 2)) if (t % 12) % 3 == 0 and not (ym(2018, 7) <= t <= ym(2020, 1))]
paths = {t: path(t) for t in starts}
paths = {t: v for t, v in paths.items() if v}
gap = lambda t: E.P['u'][t] - E.normal_rate(t)
cases = []
for y in range(1968, 2028, 4):
    t0 = ym(y - 2, 10); real = path(t0)
    if not real:
        continue
    PACE_AT = real[1]
    actual = year_keys(t0, real[0])
    pool = [t for t in paths if abs(t - t0) > H and (t in E.REC) == (t0 in E.REC)]
    near = [t for t in pool if abs(gap(t) - gap(t0)) <= 1.0]                              # stretches that began with unemployment about as far from normal
    use = near if len(near) >= 20 else pool
    sims = [year_keys(t0, paths[t][0]) for t in use]
    for k in actual:
        cases.append({'year': y, 'key': k, 'p': sum(x[k] for x in sims) / len(sims), 'yes': bool(actual[k]), 'stretches': len(use)})
keys_v = sorted({c['key'] for c in cases})
rate = {k: {y: None for y in {c['year'] for c in cases}} for k in keys_v}
for k in keys_v:                                                                          # the plain record of each key in the other elections: the chance to beat
    cs = [c for c in cases if c['key'] == k]
    for c in cs:
        others = [x['yes'] for x in cs if x['year'] != c['year']]
        c['base'] = sum(others) / len(others)
brier = lambda field: float(np.mean([(c[field] - c['yes']) ** 2 for c in cases]))
bins = []
for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
    cs = [c for c in cases if lo <= c['p'] < hi]
    bins.append({'lo': lo, 'hi': min(hi, 1), 'n': len(cs), 'said': round(float(np.mean([c['p'] for c in cs])), 2) if cs else None, 'happened': round(float(np.mean([c['yes'] for c in cs])), 2) if cs else None})
out['engine'] = {
    'elections': sorted({c['year'] for c in cases}), 'keys': keys_v, 'n': len(cases), 'brier': round(brier('p'), 3), 'brier_base': round(brier('base'), 3),
    'brier_half': round(float(np.mean([(0.5 - c['yes']) ** 2 for c in cases])), 3), 'skill': round(1 - brier('p') / brier('base'), 3), 'bins': bins,
    'right_side': int(sum((c['p'] >= 0.5) == c['yes'] for c in cases)), 'base_right_side': int(sum((c['base'] >= 0.5) == c['yes'] for c in cases)),
    'by_key': [{'key': k, 'n': len(cs), 'yes': int(sum(c['yes'] for c in cs)), 'brier': round(float(np.mean([(c['p'] - c['yes']) ** 2 for c in cs])), 3),
                'brier_base': round(float(np.mean([(c['base'] - c['yes']) ** 2 for c in cs])), 3)} for k in keys_v for cs in [[c for c in cases if c['key'] == k]]],
    'by_year': [{'year': y, 'right_side': int(sum((c['p'] >= 0.5) == c['yes'] for c in cs)), 'n': len(cs), 'stretches': cs[0]['stretches']} for y in sorted({c['year'] for c in cases}) for cs in [[c for c in cases if c['year'] == y]]],
    # the stretches overlap, and an economy's keys move together, so the 195 cases are far fewer independent tests: at most one per election
    'independent_at_most': len({c['year'] for c in cases}),
    'blocks': {'stretches': run['stretches']['n'], 'with_recession': run['stretches']['with_recession'], 'four_year_blocks': run['range']['blocks'],
               'recessions': len({next(i for i, ((a, b), (c, d)) in enumerate(E.RECESSIONS) if ym(a, b) < t <= ym(c, d)) for s_ in E.stretches() if s_['recession'] for t in range(s_['t0'] + 1, s_['t0'] + H + 1) if t in E.REC})},
}

# ------------------------------------------------------------------ 6 how far approval has moved from the midterms to June of the election year
def day(sv):
    m, d, y = map(int, sv.split('/')); return datetime.date(y + (1900 if y >= 40 else 2000), m, d)
polls = {}
for r in csv.DictReader(open(os.path.join(HERE, 'data', 'course', 'approval.csv'), encoding='utf-8-sig')):
    try:
        polls.setdefault(day(r['election_date']).year, []).append((day(r['end_date']), float(r['approve']), float(r['disapprove'])))
    except (ValueError, KeyError):
        pass
moves = []
for y in sorted(polls):
    span = lambda a, b: [p for p in polls[y] if a <= p[0] <= b]
    then, june = span(datetime.date(y - 2, 10, 1), datetime.date(y - 2, 11, 30)), span(datetime.date(y, 6, 1), datetime.date(y, 6, 30)) or span(datetime.date(y, 5, 1), datetime.date(y, 5, 31))
    if then and june:
        moves.append({'year': y, 'then': round(st.mean(p[1] for p in then), 1), 'june': round(st.mean(p[1] for p in june), 1), 'then_dis': round(st.mean(p[2] for p in then), 1), 'june_dis': round(st.mean(p[2] for p in june), 1)})
now_a, now_d = run['approval']['approve'], run['approval']['disapprove']
ch = [m['june'] - m['then'] for m in moves]; chd = [m['june_dis'] - m['then_dis'] for m in moves]
out['approval'] = {'moves': moves, 'now': [now_a, now_d], 'needed': [round(50 - now_a, 1), round(now_d - 50, 1)],
                   'rose_by_needed': sum(1 for c in ch if c >= 50 - now_a), 'disapproval_fell_by_needed': sum(1 for c in chd if c <= 50 - now_d), 'n': len(moves),
                   'largest_rise': round(max(ch), 1), 'largest_fall_in_disapproval': round(min(chd), 1), 'median_change': round(st.median(ch), 1),
                   'spread': round(st.pstdev(ch), 1), 'set_by_hand': {'disapproval_below_half': run['keys']['C06']['p'], 'approval_at_50': run['keys']['C01']['p']}}      # no longer set by hand: the run-ahead's own chances (the name is kept for the page)

json.dump(out, open(os.path.join(HERE, 'research.json'), 'w'), separators=(',', ':'))
a_ = out['alike']
print(f"keys alike: {a_['pairs_at_07']} of {a_['pairs']} pairs at 0.7 or more, {a_['pairs_at_05']} at 0.5 or more; within groups {a_['within']}, between {a_['between']}")
print(f"  worth about {a_['effective_keys']} unrelated keys (no more than {a_['ceiling']} could show in 19 elections); {a_['n_clusters']} clusters, {a_['singletons']} of them single keys")
for c in a_['clusters'][:6]: print('  cluster', c)
for p in a_['top'][:10]: print('  ', p)
print('  answered keys by year', a_['answered'])
for b_ in base: print(f"  {b_['right']:2d}/19 {b_['interval']}  {b_['name']}  misses {b_['misses']}")
for v in out['vote']: print('  vote', v)
print('sample', out['sample'])
for k, v in exp.items():
    print(' exp', k, v if 'right' not in v else (v['right'], v['misses']))
e = out['engine']
print(f"run-ahead on the past: {e['n']} cases ({len(e['elections'])} elections x {len(e['keys'])} keys); Brier {e['brier']} against {e['brier_base']} for each key's plain record and {e['brier_half']} for 50-50; skill {e['skill']:+.1%}; right side {e['right_side']} against {e['base_right_side']}")
for b_ in e['bins']: print('   said', b_)
print('   by year', [(x['year'], x['right_side'], x['n'], x['stretches']) for x in e['by_year']])
print('   by key', [(x['key'], x['yes'], x['brier'], x['brier_base']) for x in e['by_key']])
print('   blocks', e['blocks'])
ap = out['approval']
print('approval', {k: v for k, v in ap.items() if k != 'moves'}); print('  ', [(m['year'], m['then'], m['june'], m['then_dis'], m['june_dis']) for m in ap['moves']])
