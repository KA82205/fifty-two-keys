"""Fifty-Two Keys: tests. Reads keys_table.csv (build.py).

The model (declared before running)
  elections   every election with at least two-thirds of the keys available and at least half of every group
  index       the mean of the five group shares (share of a group's available keys that are true)
  the call    index above one half: the party in office wins the election, meaning the Electoral College.
              At one half or below it loses. Nothing is fitted, and nothing overrides the count.

Checks for overfitting (none of them changes the model)
  Nothing is fitted, so the model cannot overfit through weights or cut-offs. It can only do so through choices
  made after seeing results. The checks below look for that, and for a record that hangs on a few keys.
  tried       three changes made after the results were in, and taken out for that reason: what each would have
              scored, and which calls it changes
  picked      would choosing among those versions by their record on earlier elections have helped later on?
  regroup     every way to split three keys off one group into a group of their own
  one key     the record with any one key left out, and the calls that one key going the other way would change
  ratings     the record without the keys that use Lichtman's own ratings for the past
  one group   the record with each group left out
  halves      the record with a random half of the keys

Kept for the record; not part of the model and not on the page
  vote        a share of the national vote: the average of two straight lines fitted to OTHER elections only
              (the party's two-party share on the index, and on the president's June net approval)
  states      every state moves from its previous result by the forecast national swing; electoral votes follow
  tests       each election left out in turn; and each election from 1980 on from earlier elections only
  state step  the adjustment for each state's own economy is declared, with its decision rule, in states.py
"""
import csv, itertools, json, math, os, random, shutil, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                    # noqa: E402
from build import GROUPS, GROUP_NAMES, ALL, IF_NOMINEE   # noqa: E402
import states as S                                    # noqa: E402

# Tried and removed: two override rules ("deal-breakers"). If either key was false the call was "loses", whatever
# the count. They made the record 18 of 19 on paper and were taken out again on November 22, 2026: the count decides.
TRIED_DEAL_BREAKERS = ['C06_disapproval_under_50', 'E05_office_won_primary']
# Keys whose past values are Lichtman's own ratings and not a rule (B01 only where the data do not reach back).
HIS_RATINGS = ['E03_no_third_party', 'E04_no_contest']
HIS_RATING_B01 = [1952, 1956]

# The Primary Model's record as its own site states it (primarymodel.com, read November 2026): in hindsight it
# calls every election from 1952 to 1992 except 1960; its forecasts made in advance, from 1996, missed 2000, 2020, 2024.
PRIMARY_MODEL_MISSES = [1960, 2000, 2020, 2024]

TOOK_OFFICE = {1952: 0, 1956: 1, 1960: 0, 1964: 1, 1968: 0, 1972: 1, 1976: 0, 1980: 0, 1984: 1, 1988: 1, 1992: 0, 1996: 1,
               2000: 0, 2004: 1, 2008: 0, 2012: 1, 2016: 0, 2020: 0, 2024: 0}      # did the party in office keep the White House


BANDS = [(0, 0.4, 'clear loss'), (0.4, 0.5, 'likely loss'), (0.5, 0.6, 'toss-up'), (0.6, 0.7, 'lean win'), (0.7, 1.01, 'clear win')]


def load():
    gallup = {int(r['year']): float(r['june_net_approval']) for r in csv.DictReader(open(os.path.join(HERE, 'data', 'june_net_approval_gallup.csv')))}
    rows = []
    for r in csv.DictReader(open(os.path.join(HERE, 'keys_table.csv'))):
        x = {'year': int(r['year']), 'party': r['inc_party'], 'y': float(r['inc_share'])}
        for k in ALL + IF_NOMINEE:
            x[k] = None if r[k] == '' else int(r[k])
        ok = sum(x[k] is not None for k in ALL) / len(ALL) >= 2 / 3 and all(sum(x[k] is not None for k in ks) / len(ks) >= 0.5 for ks in GROUPS.values())
        x['net'] = gallup[x['year']]
        if ok:
            rows.append(x)
    return rows


def share(r, keys):
    v = [r[k] for k in keys if r[k] is not None]
    return sum(v) / len(v) if v else 0.5


def index(r, groups=GROUPS):
    return st.mean(share(r, ks) for ks in groups.values())


def ols(X, y):
    X1 = np.column_stack([np.ones(len(X)), np.asarray(X, float)])
    return np.linalg.lstsq(X1, np.asarray(y, float), rcond=None)[0]


def line_on(f):
    def m(train, r):
        b = ols([[f(t)] for t in train], [t['y'] for t in train])
        return float(b[0] + b[1] * f(r))
    return m


def average(*ms):
    return lambda train, r: st.mean(m(train, r) for m in ms)


def loo(rows, m):
    return [m(rows[:i] + rows[i + 1:], r) for i, r in enumerate(rows)]


def ahead(rows, m, start=1980):
    return {r['year']: m([t for t in rows if t['year'] < r['year']], r) for r in rows if r['year'] >= start}


def score(rows, preds):
    err = [abs(p - r['y']) for p, r in zip(preds, rows)]
    miss = [r['year'] for p, r in zip(preds, rows) if (p > 50) != (r['y'] > 50)]
    return {'n': len(rows), 'winners': len(rows) - len(miss), 'mae': round(st.mean(err), 2), 'misses': miss}


def report(rows, name, m, out):
    p = loo(rows, m); s = score(rows, p)
    a = ahead(rows, m); ar = [r for r in rows if r['year'] in a]; s2 = score(ar, [a[r['year']] for r in ar])
    out[name] = {'loo': s, 'ahead': s2, 'loo_pred': {r['year']: round(x, 2) for r, x in zip(rows, p)}, 'ahead_pred': {y: round(x, 2) for y, x in a.items()}}
    print(f"  {name:46s} left out: {s['winners']:2d}/{s['n']}, {s['mae']:.2f}  {str(s['misses']):30s} since 1980 from earlier: {s2['winners']:2d}/{s2['n']}, {s2['mae']:.2f} {s2['misses']}")
    return p


# ---------------------------------------------------------------- states
def state_results():
    """{year: {state: (dem two-party share, electoral votes)}} for 1952-2020 from the course file, 2024 from certified results."""
    out = {}
    for r in csv.DictReader(open(os.path.join(HERE, 'data', 'course', 'elec_full.csv'))):
        y = int(r['year']); ab = r['abbr'].split('_')[0]
        ev = 0.0 if r['electors'] in ('', 'NA', '-') else float(r['electors'])
        d = out.setdefault(y, {}).setdefault(ab, [None, 0.0])
        d[1] += ev
        if '_' not in r['abbr'] or r['abbr'].endswith('_full'):
            d[0] = float(r['d_2pv'])
    s24 = json.load(open(os.path.join(HERE, 'data', 'state_results_2024.json')))
    out[2024] = {ab: [v['share'], float(v['ev'])] for ab, v in s24.items()}
    return out


def electoral(states, y, dem_forecast, dem_prev_national, base_year=None, adj=None):
    """Democratic electoral votes in year y if every state moves from its previous result by the national swing
    (plus, if adj is given, each state's own adjustment in points of Democratic share)."""
    base = states[base_year or y - 4]; now = states[y]
    swing = dem_forecast - dem_prev_national
    dem = 0.0
    for ab, (_, ev) in now.items():
        st_ = ab if ab in base else ab[:2]                      # a Maine or Nebraska district follows its state's last result
        s = base[st_][0] + swing if st_ in base and base[st_][0] is not None else dem_forecast  # new states follow the nation
        if adj:
            s += adj.get(ab[:2], 0.0)
        dem += ev if s > 50 else 0
    return dem, sum(v[1] for v in now.values())


def main():
    rows = load()
    out = {'elections': [r['year'] for r in rows], 'n_keys': len(ALL), 'groups': {g: len(ks) for g, ks in GROUPS.items()}}
    for r in rows:
        r['idx'] = index(r); r['flat'] = share(r, ALL)
    print(len(rows), 'elections', rows[0]['year'], '-', rows[-1]['year'], '|', len(ALL), 'keys')
    print('\nyear pty share | true/avail  index | ' + '     '.join(GROUPS))
    for r in rows:
        print(r['year'], r['party'], f"{r['y']:5.1f} | {sum(1 for k in ALL if r[k] == 1):2d}/{sum(1 for k in ALL if r[k] is not None):2d}      {r['idx']:.2f} |", '  '.join(f"{share(r, ks):.2f}" for ks in GROUPS.values()))
    won = {r['year']: bool(TOOK_OFFICE[r['year']]) for r in rows}
    years = [r['year'] for r in rows]

    def calls(rs, groups=GROUPS):
        return {r['year']: index(r, groups) > 0.5 for r in rs}

    def record(c):
        wrong = [y for y in c if c[y] != won[y]]
        return {'right': len(c) - len(wrong), 'n': len(c), 'misses': wrong}

    said = calls(rows)                                                                    # the call: the count decides
    model_said = said
    call_miss = record(said)['misses']
    part = lambda v: {'n': sum(1 for y in said if said[y] == v), 'right': sum(1 for y in said if said[y] == v and won[y] == v)}
    since = lambda wrong, y0: {'right': sum(1 for r in rows if r['year'] >= y0) - sum(1 for y in wrong if y >= y0), 'n': sum(1 for r in rows if r['year'] >= y0)}
    split = [r['year'] for r in rows if r['y'] > 50 and not won[r['year']]]               # won the most votes, lost the Electoral College
    near = sorted((abs(r['idx'] - 0.5), r['year']) for r in rows)
    close = [y for d, y in near if d < 0.05]                                              # within five points of the line
    out['call'] = {'n': len(rows), 'right': len(rows) - len(call_miss), 'misses': call_miss, 'said_win': part(True), 'said_lose': part(False),
                   'since_1984': since(call_miss, 1984), 'split': split, 'closest': [[y, round(d, 3)] for d, y in near[:4]],
                   'close': {'years': close, 'right': sum(1 for y in close if y not in call_miss)},
                   'clear': {'n': len(rows) - len(close), 'right': sum(1 for y in years if y not in close and y not in call_miss)}}
    print('\nTHE CALL (index above one half: the party in office wins the election; nothing fitted, nothing overrides the count):', len(rows) - len(call_miss), 'of', len(rows), 'misses', call_miss)
    print(f"  said win: right {part(True)['right']} of {part(True)['n']} | said lose: right {part(False)['right']} of {part(False)['n']} | since 1984: {since(call_miss, 1984)['right']} of {since(call_miss, 1984)['n']}")
    print('  party in office won the most votes and lost the Electoral College:', split, '| closest calls (distance from one half):', out['call']['closest'])
    print(f"  within five points of the line: {close}, right in {out['call']['close']['right']} of {len(close)} | further out: right in {out['call']['clear']['right']} of {out['call']['clear']['n']}")
    maj = [r['year'] for r in rows if (r['idx'] > 0.5) != (r['y'] > 50)]
    print('NATIONAL VOTE: the same call scored on the national vote instead:', len(rows) - len(maj), 'of', len(rows), 'misses', maj)
    out['verdict'] = {'right': len(rows) - len(maj), 'misses': maj}

    # HOW SURE: what happened to the party in office at each level of the count. The bands are every ten points, round numbers set
    # before the tally. This describes the record; it does not change the call, and the line stays at one half.
    sure = []
    for lo, hi, label in BANDS:
        rs = [r for r in rows if lo <= r['idx'] < hi]
        sure.append({'lo': lo, 'hi': hi, 'label': label, 'n': len(rs), 'won': sum(1 for r in rs if won[r['year']]), 'years': [r['year'] for r in rs],
                     'share': round(float(np.mean([r['y'] for r in rs])), 1) if rs else None})
    xs, ys = np.array([r['idx'] for r in rows]), np.array([r['y'] for r in rows])
    slope, icept = np.polyfit(xs, ys, 1)
    left = []
    for i in range(len(rows)):
        m = np.arange(len(rows)) != i; b1, b0 = np.polyfit(xs[m], ys[m], 1); left.append(float(ys[i] - (b0 + b1 * xs[i])))
    out['sure'] = {'bands': sure, 'r_vote': round(float(np.corrcoef(xs, ys)[0, 1]), 2), 'line': [round(float(icept), 2), round(float(slope), 2)],
                   'at_half': round(float(icept + slope / 2), 1), 'miss': round(float(np.mean(np.abs(left))), 1),
                   'largest': sorted(((round(e, 1), r['year']) for e, r in zip(left, rows)), key=lambda t: -abs(t[0]))[:2],
                   # each election's vote estimated from the line through the other eighteen, so no election helps to estimate itself
                   'votes': [{'year': r['year'], 'est': round(float(r['y'] - e), 1), 'actual': round(float(r['y']), 1), 'miss': round(float(e), 1)} for e, r in zip(left, rows)],
                   'rmse': round(float(np.sqrt(np.mean(np.square(left)))), 1), 'within3': int(sum(1 for e in left if abs(e) <= 3))}
    print('HOW SURE (the party in office, by its share of keys; a description of the record, not a rule):')
    for b in sure:
        print(f"  {100 * b['lo']:.0f}% to {min(100, 100 * b['hi']):.0f}%, {b['label']}: won {b['won']} of {b['n']} {b['years']}, average share of the vote {b['share']}")
    sr = out['sure']
    print(f"  against the national vote: correlation {sr['r_vote']}; share = {sr['line'][0]} + {sr['line'][1]} x index, {sr['at_half']} at one half;"
          f" typical miss with the election left out {sr['miss']} points; largest {sr['largest']}")

    print('\n' + '-' * 30 + ' CHECKS FOR OVERFITTING: NONE OF THESE CHANGES THE MODEL ' + '-' * 30)
    model_right = out['call']['right']

    # 1. the three changes that were tried after the results were in, and taken out
    six = {g: list(ks) for g, ks in GROUPS.items()}; six['F'] = six['E'][4:]; six['E'] = six['E'][:4]
    nominee = [dict(r, E05_office_won_primary=r['E05_if_nominee'], E06_primary_stronger=r['E06_if_nominee']) for r in rows]
    fired = {r['year']: [k for k in TRIED_DEAL_BREAKERS if r[k] == 0] for r in rows}
    tried = {'own_group': calls(rows, six), 'nominee': calls(nominee), 'both': calls(nominee, six), 'deal_breakers': {y: said[y] and not fired[y] for y in said}}
    out['tried'] = {name: dict(record(c), changed=[y for y in c if c[y] != said[y]]) for name, c in tried.items()}
    out['tried']['rescored'] = [r['year'] for r, f in zip(rows, nominee) if any(r[k] != f[k] for k in ALL)]
    print('TRIED AFTER THE RESULTS WERE IN, AND TAKEN OUT (calls each one changes)')
    for name, lab in (('own_group', 'a group of their own for the three primary keys'), ('nominee', 'the primary keys scored on the November nominee'),
                      ('both', 'both of those'), ('deal_breakers', 'two keys that could overrule the count')):
        t = out['tried'][name]
        print(f"  {lab:50s} {t['right']} of {len(rows)}  misses {t['misses']}  changes {t['changed']}")

    # 2. would picking among those versions by their record so far have helped? (ties go to the version with fewer changes)
    order = ['model', 'own_group', 'nominee', 'both']
    cand = {'model': said, 'own_group': tried['own_group'], 'nominee': tried['nominee'], 'both': tried['both']}
    picks = {}
    for y in years:
        if y >= 1984:
            past = [t for t in years if t < y]
            picks[y] = max(order, key=lambda name: (sum(cand[name][t] == won[t] for t in past), -order.index(name)))
    pk = sum(cand[picks[y]][y] == won[y] for y in picks)
    out['picked_from_earlier'] = {'right': pk, 'n': len(picks), 'picks': picks, 'model': since(call_miss, 1984)}
    print(f"PICKED FROM EARLIER ELECTIONS ONLY, each election since 1984: {pk} of {len(picks)} (the model itself: {since(call_miss, 1984)['right']} of {len(picks)}) | picked: {sorted(set(picks.values()))}")

    # 3. every way to split three keys off one group into a group of their own
    tally, in_e = {}, []
    for g0, ks in GROUPS.items():
        for trio in itertools.combinations(ks, 3):
            gs = {h: [k for k in v if k not in trio] for h, v in GROUPS.items()}; gs['new'] = list(trio)
            h = record(calls(rows, gs))['right']; tally[h] = tally.get(h, 0) + 1
            if g0 == 'E':
                in_e.append(h)
    out['regroupings'] = {'n': sum(tally.values()), 'right': dict(sorted(tally.items())), 'better': sum(v for k, v in tally.items() if k > model_right),
                          'worse': sum(v for k, v in tally.items() if k < model_right), 'from_E': {'n': len(in_e), 'better': sum(1 for h in in_e if h > model_right)}}
    rg = out['regroupings']
    print(f"REGROUPING: {rg['n']} ways to split three keys off a group: elections right {rg['right']} | better than the model {rg['better']}, worse {rg['worse']}"
          f" | of the {rg['from_E']['n']} splits of the incumbency and nominations group, {rg['from_E']['better']} are better")

    # 4. one key at a time
    without = {k: record(calls(rows, {g: [x for x in ks if x != k] for g, ks in GROUPS.items()}))['right'] for k in ALL}
    flips = {}
    for r in rows:
        flips[r['year']] = [k[:3] for k in ALL if r[k] is not None and (index(dict(r, **{k: 1 - r[k]})) > 0.5) != said[r['year']]]
    out['one_key'] = {'left_out': {'min': min(without.values()), 'max': max(without.values()), 'lower': sorted(k[:3] for k, v in without.items() if v < model_right),
                                   'higher': sorted(k[:3] for k, v in without.items() if v > model_right)},
                      'flipped': {y: len(v) for y, v in flips.items() if v}, 'flipped_keys': {y: v for y, v in flips.items() if v}}
    ok = out['one_key']
    print(f"ONE KEY LEFT OUT: the record stays between {ok['left_out']['min']} and {ok['left_out']['max']} of {len(rows)} (lower without {ok['left_out']['lower']}, higher without {ok['left_out']['higher']})")
    print('ONE KEY THE OTHER WAY: elections whose call would change, and how many of their keys could do it:', ok['flipped'])

    # 5. the keys that use Lichtman's own ratings for the past (his third-party rating uses the final vote)
    c = calls(rows, {g: [x for x in ks if x not in HIS_RATINGS] for g, ks in GROUPS.items()})
    c2 = calls([dict(r, B01_lt_growth=None) if r['year'] in HIS_RATING_B01 else r for r in rows], {g: [x for x in ks if x not in HIS_RATINGS] for g, ks in GROUPS.items()})
    e03 = [r['year'] for r in rows if (index(dict(r, E03_no_third_party=1 - r['E03_no_third_party'])) > 0.5) != said[r['year']]]
    out['without_his_ratings'] = dict(record(c), changed=[y for y in c if c[y] != said[y]], also_without_early_b01=dict(record(c2), changed=[y for y in c2 if c2[y] != said[y]]),
                                      third_party_flip_changes=e03)
    print(f"WITHOUT THE TWO KEYS AT LICHTMAN'S OWN RATING ({', '.join(k[:3] for k in HIS_RATINGS)}): {out['without_his_ratings']['right']} of {len(rows)}, calls changed {out['without_his_ratings']['changed']}"
          f" | and without B01 in {HIS_RATING_B01}: {record(c2)['right']} of {len(rows)} | the third-party key the other way would change the call in {e03}")

    # 6. one group left out
    out['one_group_out'] = {g: record(calls(rows, {h: ks for h, ks in GROUPS.items() if h != g})) for g in GROUPS}
    print('ONE GROUP LEFT OUT:', ' | '.join(f"without {GROUP_NAMES[g]}: {v['right']} {v['misses']}" for g, v in out['one_group_out'].items()))

    # how rules like the deal-breakers have held up
    upto = lambda k, y1: [r['year'] for r in rows if r['year'] <= y1 and r[k] == 0]
    look = [k for k in ALL if len(upto(k, 1980)) >= 2 and not any(won[y] for y in upto(k, 1980))]
    later = {k: [r['year'] for r in rows if r['year'] > 1980 and r[k] == 0] for k in look}
    tested = [k for k in look if later[k]]; broke = [k for k in tested if any(won[y] for y in later[k])]
    wf = []
    for r in rows:
        if r['year'] >= 1984:
            db = [k for k in ALL if len(upto(k, r['year'] - 1)) >= 2 and not any(won[y] for y in upto(k, r['year'] - 1))]
            wf.append((said[r['year']] and not any(r[k] == 0 for k in db)) == won[r['year']])
    out['deal_breakers_tried'] = {'keys': TRIED_DEAL_BREAKERS, 'lookalikes_by_1980': len(look), 'tested_after': len(tested), 'broke_after': len(broke),
                                  'walk_forward': {'right': sum(wf), 'n': len(wf)}}
    print(f"RULES LIKE THE DEAL-BREAKERS: {len(look)} keys looked like deal-breakers on the elections to 1980; {len(tested)} came up again later; {len(broke)} of those failed at least once"
          f" | picked by the record itself, election by election since 1984: {sum(wf)} of {len(wf)} (the count: {since(call_miss, 1984)['right']} of {len(wf)})")

    print('\n' + '-' * 30 + ' KEPT FOR THE RECORD: NOT PART OF THE MODEL ' + '-' * 30)

    print('\nVOTE FORECASTS')
    keys, appr = line_on(lambda r: r['idx']), line_on(lambda r: r['net'])
    blend = average(keys, appr)
    report(rows, 'keys, equal groups', keys, out)
    report(rows, 'keys, plain count', line_on(lambda r: r['flat']), out)
    report(rows, 'net approval alone', appr, out)
    pb = report(rows, 'keys averaged with net approval (the forecast)', blend, out)
    b = ols([[r['idx']] for r in rows], [r['y'] for r in rows]); out['keys_line'] = [round(float(x), 2) for x in b]
    b2 = ols([[r['net']] for r in rows], [r['y'] for r in rows]); out['approval_line'] = [round(float(x), 3) for x in b2]
    res = [p - r['y'] for p, r in zip(pb, rows)]
    out['blend_sd'] = round(float(np.sqrt(np.mean(np.square(res)))), 2)
    print(f"  keys line: share = {b[0]:.1f} + {b[1]:.1f} x index | approval line: {b2[0]:.1f} + {b2[1]:.3f} x net | left-out miss of the forecast, root mean square {out['blend_sd']}")

    print('\nELECTORAL COLLEGE: every state moves from its last result by the forecast national swing')
    states = state_results()
    hist = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'data', 'keys_history.csv')))}
    dem_nat = {y: float(h['dem_two_party']) for y, h in hist.items()}
    ec = {}
    for label, preds in (('forecast, each election left out', dict(zip([r['year'] for r in rows], pb))), ('forecast, from earlier elections only', ahead(rows, blend)),
                         ('the actual national vote (tests the state step alone)', {r['year']: r['y'] for r in rows})):
        right, miss, detail = 0, [], {}
        for r in rows:
            y = r['year']
            if y not in preds or y - 4 not in states:
                continue
            dem_f = preds[y] if r['party'] == 'D' else 100 - preds[y]
            dev, tot = electoral(states, y, dem_f, dem_nat[y - 4])
            office_ev = dev if r['party'] == 'D' else tot - dev
            call = office_ev > tot / 2
            detail[y] = round(office_ev)
            if call == bool(TOOK_OFFICE[y]): right += 1
            else: miss.append(y)
        n = len(detail); ec[label] = {'right': right, 'n': n, 'misses': miss, 'office_ev': detail}
        print(f"  {label:56s} {right} of {n}  misses {miss}")
    out['electoral'] = ec

    print("\nSTATE STEP: each state's weighted growth against the average, on top of the national swing (declared in states.py)")
    W, sev = S.measures(), S.electoral_votes()
    party = {r['year']: r['party'] for r in rows}
    fc_loo, fc_ahead = dict(zip([r['year'] for r in rows], pb)), ahead(rows, blend)
    panel = {}
    for y in range(S.FIRST, rows[-1]['year'] + 1, 4):
        sign = 1 if party[y] == 'D' else -1
        nat, avg = sign * (dem_nat[y] - dem_nat[y - 4]), S.national(W, sev, y)
        panel[y] = [(s, sign * (states[y][s][0] - states[y - 4][s][0]) - nat, W[(s, y)] - avg) for s in sev[y]]

    def slope(years):
        top = bottom = 0.0
        for y in years:
            mr, me = st.mean(p[1] for p in panel[y]), st.mean(p[2] for p in panel[y])
            top += sum((p[1] - mr) * (p[2] - me) for p in panel[y]); bottom += sum((p[2] - me) ** 2 for p in panel[y])
        return top / bottom

    def call(y, national_share, b):
        """Does the map give the party in office the Electoral College? national_share is that party's two-party share."""
        sign = 1 if party[y] == 'D' else -1
        dem_f = national_share if party[y] == 'D' else 100 - national_share
        adj = None if b is None else {s: sign * b * e for s, _, e in panel[y]}
        dev, tot = electoral(states, y, dem_f, dem_nat[y - 4], adj=adj)
        return (dev if party[y] == 'D' else tot - dev) > tot / 2

    step = {'slope_all': round(slope(list(panel)), 2), 'slope_by_election': {y: round(slope([y]), 2) for y in panel}, 'by_election': {}}
    tally = {k: [0, 0] for k in ('loo', 'ahead', 'actual_loo', 'actual_ahead')}       # [plain swing right, adjusted right]
    miss = {'loo': [[], []], 'ahead': [[], []]}
    for y in panel:
        b_loo = slope([t for t in panel if t != y]); b_ahead = slope([t for t in panel if t < y]) if y > S.FIRST else None
        true = bool(TOOK_OFFICE[y]); actual = next(r['y'] for r in rows if r['year'] == y)
        m0 = st.mean(abs(p[1]) for p in panel[y]); m1 = st.mean(abs(p[1] - b_loo * p[2]) for p in panel[y])
        miss['loo'][0].append(m0); miss['loo'][1].append(m1)
        d = {'b_loo': round(b_loo, 2), 'miss_plain': round(m0, 2), 'miss_adjusted_loo': round(m1, 2)}
        for name, nat_share, b in (('loo', fc_loo[y], b_loo), ('actual_loo', actual, b_loo)):
            tally[name][0] += call(y, nat_share, None) == true; tally[name][1] += call(y, nat_share, b) == true
        if b_ahead is not None:
            m2 = st.mean(abs(p[1] - b_ahead * p[2]) for p in panel[y])
            miss['ahead'][0].append(m0); miss['ahead'][1].append(m2)
            d.update({'b_ahead': round(b_ahead, 2), 'miss_adjusted_ahead': round(m2, 2)})
            for name, nat_share in (('ahead', fc_ahead[y]), ('actual_ahead', actual)):
                tally[name][0] += call(y, nat_share, None) == true; tally[name][1] += call(y, nat_share, b_ahead) == true
        step['by_election'][y] = d
    step['calls'] = {k: {'plain': v[0], 'adjusted': v[1], 'n': len(panel) if 'ahead' not in k else len(panel) - 1} for k, v in tally.items()}
    step['state_miss'] = {k: {'plain': round(st.mean(v[0]), 3), 'adjusted': round(st.mean(v[1]), 3), 'adjusted_better_in': sum(a < b for a, b in zip(v[1], v[0])), 'n': len(v[0])} for k, v in miss.items()}
    step['adopted'] = bool(step['state_miss']['ahead']['adjusted'] < step['state_miss']['ahead']['plain'] and step['calls']['ahead']['adjusted'] >= step['calls']['ahead']['plain'])
    out['state_step'] = step
    print(f"  slope, all elections: {step['slope_all']} points of a state's swing per 1.0 of the measure | by election: {step['slope_by_election']}")
    for k, lab in (('loo', 'slope from the other elections'), ('ahead', 'slope from earlier elections only (1984 on)')):
        m = step['state_miss'][k]
        print(f"  {lab:46s} average state miss given the true national vote: plain {m['plain']:.3f}, adjusted {m['adjusted']:.3f} (closer in {m['adjusted_better_in']} of {m['n']} elections)")
    for k, lab in (('loo', 'forecast, each election left out'), ('ahead', 'forecast, from earlier elections only'), ('actual_loo', 'true national vote, slope from other elections'), ('actual_ahead', 'true national vote, slope from earlier elections')):
        c = step['calls'][k]
        print(f"  Electoral College calls, {lab:50s} plain {c['plain']} of {c['n']}, adjusted {c['adjusted']} of {c['n']}")
    print('  DECISION (rule fixed in advance):', 'the adjustment goes into the map' if step['adopted'] else 'the plain national swing stays; the adjustment is left out')

    print("\nNEXT TO LICHTMAN'S 13 KEYS (his ratings as listed on Wikipedia; for comparison only, nothing here feeds the model)")
    L = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'data', 'lichtman13_wikipedia.csv')))}
    for r in rows:
        r['l_true'] = sum(L[r['year']][f'key{i}'] == 'T' for i in range(1, 14))
    said = {r['year']: 13 - r['l_true'] <= 5 for r in rows}             # his rule: six or more false keys and the party in office loses
    l_nat = [r['year'] for r in rows if said[r['year']] != (r['y'] > 50)]
    l_off = [r['year'] for r in rows if said[r['year']] != bool(TOOK_OFFICE[r['year']])]
    l_line = score(rows, loo(rows, line_on(lambda r: r['l_true'])))
    l_blend = score(rows, loo(rows, average(line_on(lambda r: r['l_true']), appr)))
    out['lichtman'] = {'national': {'right': len(rows) - len(l_nat), 'n': len(rows), 'misses': l_nat}, 'national_since_1984': since(l_nat, 1984),
                       'office': {'right': len(rows) - len(l_off), 'n': len(rows), 'misses': l_off}, 'count_line': l_line, 'count_line_with_approval': l_blend,
                       'ours_since_1984': since(maj, 1984), 'office_since_1984': since(l_off, 1984), 'ours_office_since_1984': since(call_miss, 1984)}
    # the same one-key check on his keys: with five or six false keys, one key rated the other way changes his call
    his_edge = [r['year'] for r in rows if 13 - r['l_true'] in (5, 6)]
    our_edge = sorted(out['one_key']['flipped'])
    edge = lambda ys, wrong: {'years': ys, 'right': sum(1 for y in ys if y not in wrong), 'rest': {'n': len(rows) - len(ys), 'right': sum(1 for y in years if y not in ys and y not in wrong)}}
    out['one_key_from_the_line'] = {'his': edge(his_edge, l_off), 'these': edge(our_edge, call_miss)}
    pm = PRIMARY_MODEL_MISSES
    out['primary_model'] = {'right': len(rows) - len(pm), 'n': len(rows), 'misses': pm, 'in_advance': since(pm, 1996)}
    either = [y for y in call_miss if y not in l_off or y not in pm]
    out['missed_but_called_by_either'] = either
    out['called_but_missed_by_both'] = [r['year'] for r in rows if r['year'] not in call_miss and r['year'] in l_off and r['year'] in pm]
    print(f"  Primary Model (as its site states it): {len(rows) - len(pm)} of {len(rows)} (misses {pm}); forecasts made in advance, from 1996: {since(pm, 1996)['right']} of {since(pm, 1996)['n']}")
    for who in ('his', 'these'):
        e = out['one_key_from_the_line'][who]
        print(f"  one key the other way would change the call, {who} keys: {e['years']}, right in {e['right']} of {len(e['years'])}; the rest right in {e['rest']['right']} of {e['rest']['n']}")
    print('  elections that his keys or the Primary Model called and these keys miss:', either, '| that both of them missed and these keys call:', out['called_but_missed_by_both'])
    print(f"  his rule against the national vote: {len(rows) - len(l_nat)} of {len(rows)} (misses {l_nat}); since 1984: {out['lichtman']['national_since_1984']['right']} of {out['lichtman']['national_since_1984']['n']}"
          f" | against who took office: {len(rows) - len(l_off)} of {len(rows)} (misses {l_off})")
    print(f"  WHO WON THE ELECTION: his rule {len(rows) - len(l_off)} of {len(rows)} (misses {l_off}), since 1984 {since(l_off, 1984)['right']} of {since(l_off, 1984)['n']}"
          f" | these keys {len(rows) - len(call_miss)} of {len(rows)} (misses {call_miss}), since 1984 {since(call_miss, 1984)['right']} of {since(call_miss, 1984)['n']}")
    print(f"  national vote, these keys since 1984: {out['lichtman']['ours_since_1984']['right']} of {out['lichtman']['ours_since_1984']['n']}"
          f" | vote miss, a line through his count: {l_line['mae']:.2f} (ours {out['keys, equal groups']['loo']['mae']:.2f}); with approval {l_blend['mae']:.2f} (ours {out['keys averaged with net approval (the forecast)']['loo']['mae']:.2f})")

    print('\nEACH KEY (for the record only; not used to choose or weight keys): true in, agrees with the national-vote winner in')
    out['each_key'] = {}
    for g, ks in GROUPS.items():
        for k in ks:
            n = sum(1 for r in rows if r[k] is not None); t = sum(1 for r in rows if r[k] == 1); a = sum(1 for r in rows if r[k] is not None and (r[k] == 1) == (r['y'] > 50))
            out['each_key'][k] = {'n': n, 'true': t, 'agree': a}
            print(f"  {k:30s} {t:2d}/{n:2d}   {a:2d}/{n:2d}")

    print(f'\nDOES IT MATTER WHICH KEYS? Random halves of the {len(ALL)} keys ({len(ALL) // 2}, same groups), verdict rule and left-out vote miss of the keys line')
    rnd = random.Random(2028); hits, maes, calls = [], [], []
    for _ in range(2000):
        sub = set(rnd.sample(ALL, len(ALL) // 2)); gs = {g: [k for k in ks if k in sub] for g, ks in GROUPS.items()}
        gs = {g: ks for g, ks in gs.items() if ks}
        f = lambda r, gs=gs: st.mean(share(r, ks) for ks in gs.values())
        hits.append(sum((f(r) > 0.5) == (r['y'] > 50) for r in rows))
        calls.append(sum((f(r) > 0.5) == won[r['year']] for r in rows))
        maes.append(score(rows, loo(rows, line_on(f)))['mae'])
    hits.sort(); maes.sort(); calls.sort()
    out['halves_call'] = {'p10': calls[200], 'median': calls[1000], 'p90': calls[1800], 'min': calls[0], 'max': calls[-1]}
    print('  THE CALL (who won the election) right, 10th-50th-90th percentile:', calls[200], calls[1000], calls[1800], '| range', calls[0], calls[-1])
    out['halves'] = {'verdict_p10': hits[200], 'verdict_median': hits[1000], 'verdict_p90': hits[1800], 'mae_p10': maes[200], 'mae_median': maes[1000], 'mae_p90': maes[1800]}
    print('  verdict right, 10th-50th-90th percentile:', hits[200], hits[1000], hits[1800], '| vote miss:', maes[200], maes[1000], maes[1800])
    # the lock: a copy of the key table, and of every election's index and call, as they stood when last locked.
    # After a deliberate change, add it to the change log in README.md and run: python test.py --lock
    lock_keys, lock_index = os.path.join(HERE, 'locked_keys.csv'), os.path.join(HERE, 'locked_index.csv')
    index_now = {r['year']: (f"{r['idx']:.4f}", 'win' if model_said[r['year']] else 'lose') for r in rows}
    if '--lock' in sys.argv:
        shutil.copyfile(os.path.join(HERE, 'keys_table.csv'), lock_keys)
        with open(lock_index, 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['year', 'index', 'call'])
            for y, (i, c) in index_now.items():
                w.writerow([y, i, c])
        print('\nlocked: locked_keys.csv and locked_index.csv now hold this version')
    if os.path.exists(lock_keys) and os.path.exists(lock_index):
        was = {int(r['year']): r for r in csv.DictReader(open(lock_keys))}
        now = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'keys_table.csv')))}
        cols = sorted({k for r in list(was.values()) + list(now.values()) for k in r} - {'year', 'inc_share'})      # every key, in either copy
        diff = [f"{y} {k}: {was.get(y, {}).get(k, 'absent')!r} to {now.get(y, {}).get(k, 'absent')!r}" for y in sorted(set(was) | set(now)) for k in cols
                if was.get(y, {}).get(k, 'absent') != now.get(y, {}).get(k, 'absent')]
        was_i = {int(r['year']): (r['index'], r['call']) for r in csv.DictReader(open(lock_index))}
        diff += [f"{y} index and call: {was_i.get(y)} to {index_now.get(y)}" for y in sorted(set(was_i) | set(index_now)) if was_i.get(y) != index_now.get(y)]
        out['lock'] = {'matches': not diff, 'entries_changed': len(diff), 'first': diff[:25]}
        print('\nLOCK: every key, index and call is the same as in the locked copy' if not diff else
              f"\nLOCK: {len(diff)} entries differ from the locked copy. Add the change to the log in README.md, then run: python test.py --lock\n  " + '\n  '.join(diff[:25]))
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w'), indent=1)
    return rows, out


if __name__ == '__main__':
    main()
