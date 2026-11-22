"""State economies, weighted toward the election the way Enns, Colner, Kumar and Lagodny (2024) weight them.

EVERYTHING BELOW WAS WRITTEN DOWN BEFORE ANY OF IT WAS SCORED AGAINST AN ELECTION RESULT.

The measure
  For each state, the monthly percent change in the Philadelphia Fed's State Coincident Index, averaged over
  the term with weights 0.55 ** (15 - q), where q is the quarter of the presidency (q = 14 is April-June of the
  election year). The last quarter before the forecast counts in full, the one before it 55% as much, the one
  before that 30%, and so on. 0.55 is the value in the paper; it is not fitted here.
  It is computed from quarter-end index values for the last six quarters (December of y-2 to June of y), which
  carry 97% of the weight. The indexes begin in January 1979 (April 1979 for Kansas, Oklahoma, Texas, Virginia,
  Washington and Wisconsin), so 1980 is the first election and uses what there is.

Two keys for the national index (the pattern of the other economy keys: one for now, one for the term)
  A18 states_growing     the measure is above zero in states that hold a majority of the electoral votes
  B15 states_beat_prev   the measure is higher than at the same point of the previous term in states that hold
                         a majority of the electoral votes
  Electoral votes are those of the election year, so a majority is 270. The District of Columbia has no index
  of its own; as in the paper's data it is given Maryland's and Virginia's indexes averaged month by month.
  A18 can be scored from 1980 and B15 from 1984; both are blank before that.

A state step for the Electoral College
  Until now every state moved from its last result by the national swing. Tested here: the same, plus
      b x (the state's measure - the electoral-vote-weighted average of all states' measures)
  added for the party in office. b is one number: the pooled slope, within elections, of a state's swing
  on its measure (both taken as differences from that election's average), estimated from other elections only.
  Decision rule, fixed in advance: the adjustment goes into the map only if, with each election from 1984 on
  forecast from earlier elections alone, it lowers the average state miss and loses no Electoral College call.
  Otherwise the plain national swing stays and the adjustment is reported as tested and left out.
"""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
DELTA = 0.55
FIRST = 1980


def load_index():
    d = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'state_coincident_index.csv'))):
        d.setdefault(r['state'], {})[r['month']] = float(r['index'])
    d['DC'] = {m: (x + d['VA'][m]) / 2 for m, x in d['MD'].items() if m in d['VA']}
    return d


def quarter_ends(y):
    """The seven months that bound the last six quarters before the forecast: December of y-2 to June of y."""
    ends = [f'{y - 2}-12', f'{y - 1}-03', f'{y - 1}-06', f'{y - 1}-09', f'{y - 1}-12', f'{y}-03', f'{y}-06']
    months = [3] * 6
    if y == 1980:
        ends[0], months[0] = '1979-01', 2          # the indexes begin in January 1979
    return ends, months


def weighted_growth(series, y, delta=DELTA):
    """Average monthly percent change over quarters 9-14 of the term, quarter q weighted delta ** (15 - q)."""
    ends, months = quarter_ends(y)
    top = bottom = 0.0
    for i in range(1, 7):
        a, b = series.get(ends[i - 1]), series.get(ends[i])
        if a is None or b is None:
            continue
        w = delta ** (15 - (8 + i))
        top += w * 100 * (b / a - 1); bottom += w * months[i - 1]
    return top / bottom if bottom else None


def electoral_votes():
    """{year: {state: electoral votes}}, Maine's and Nebraska's districts counted with their state."""
    ev = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'course', 'elec_full.csv'))):
        y, ab = int(r['year']), r['abbr'].split('_')[0]
        e = 0.0 if r['electors'] in ('', 'NA', '-') else float(r['electors'])
        ev.setdefault(y, {}); ev[y][ab] = ev[y].get(ab, 0.0) + e
    ev[2024] = {}
    for ab, v in json.load(open(os.path.join(DATA, 'state_results_2024.json'))).items():
        ev[2024][ab[:2]] = ev[2024].get(ab[:2], 0.0) + float(v['ev'])
    ev[2028] = dict(ev[2024])                      # the 2020 census decides both
    return ev


def measures(last=2024):
    """{(state, year): measure} for every election from 1980."""
    idx = load_index()
    return {(s, y): weighted_growth(idx[s], y) for s in idx for y in range(FIRST, last + 1, 4)}


def national(W, ev, y):
    """Electoral-vote-weighted average of the states' measures."""
    ss = [s for s in ev[y] if W.get((s, y)) is not None]
    return sum(ev[y][s] * W[(s, y)] for s in ss) / sum(ev[y][s] for s in ss)


def state_keys(y, W=None, ev=None):
    """(A18, B15, figures). A key is None where it cannot be scored."""
    W = W if W is not None else measures(); ev = ev if ev is not None else electoral_votes()
    out = {'states_growing_ev': None, 'states_growing_n': None, 'states_better_ev': None, 'states_better_n': None, 'states_measure_avg': None}
    if y < FIRST or (next(iter(ev[y])), y) not in W:
        return None, None, out
    tot = sum(ev[y].values())
    up = [s for s in ev[y] if W[(s, y)] > 0]
    out['states_growing_ev'], out['states_growing_n'] = sum(ev[y][s] for s in up), len(up)
    out['states_measure_avg'] = national(W, ev, y)
    a18 = out['states_growing_ev'] > tot / 2
    b15 = None
    if y - 4 >= FIRST:
        better = [s for s in ev[y] if W[(s, y)] > W[(s, y - 4)]]
        out['states_better_ev'], out['states_better_n'] = sum(ev[y][s] for s in better), len(better)
        b15 = out['states_better_ev'] > tot / 2
    return a18, b15, out


def so_far(term_start='2025-01', delta=DELTA):
    """The same measure on the current term to date, from monthly values, with the latest quarter given the top
    weight (as if June of the election year were the latest month). Returns ({state: measure}, last month).
    This is a reading, not a key: the keys are scored on the figures to June of the election year."""
    d = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'state_index_this_term.csv'))):
        d.setdefault(r['state'], {})[r['month']] = float(r['index'])
    d['DC'] = {m: (x + d['VA'][m]) / 2 for m, x in d['MD'].items() if m in d['VA']}
    mi = lambda ym: int(ym[:4]) * 12 + int(ym[5:7]) - 1
    t0, out, last = mi(term_start), {}, None
    for s, ser in d.items():
        months = sorted(m for m in ser if mi(m) >= t0)
        last = months[-1]; last_q = (mi(last) - t0) // 3 + 1
        top = bottom = 0.0
        for m in months:
            i = mi(m) - 1; prev = f'{i // 12}-{i % 12 + 1:02d}'
            if prev not in ser:
                continue
            w = delta ** (15 - ((mi(m) - t0) // 3 + 1 + 14 - last_q))
            top += w * 100 * (ser[m] / ser[prev] - 1); bottom += w
        out[s] = top / bottom
    return out, last


if __name__ == '__main__':
    W, ev = measures(), electoral_votes()
    with open(os.path.join(HERE, 'state_economy.csv'), 'w', newline='') as f:
        w = csv.writer(f); years = list(range(FIRST, 2025, 4)); w.writerow(['state'] + years)
        for s in sorted({s for s, _ in W}):
            w.writerow([s] + [f'{W[(s, y)]:.4f}' for y in years])
    print('year  average  states up  their votes  | states above last term  their votes  (of 538)')
    for y in range(FIRST, 2025, 4):
        a, b, o = state_keys(y, W, ev)
        print(y, f"{o['states_measure_avg']:7.3f}   {o['states_growing_n']:2d}        {o['states_growing_ev']:5.0f}      |",
              '' if b is None else f"{o['states_better_n']:2d}      {o['states_better_ev']:5.0f}", '  A18', a, ' B15', b)
    # the two data files overlap in June 2025 and June 2026: they should agree
    idx, term = load_index(), {}
    for r in csv.DictReader(open(os.path.join(DATA, 'state_index_this_term.csv'))):
        term[(r['state'], r['month'])] = float(r['index'])
    off = [(s, m) for s in idx if s != 'DC' for m in ('2025-06', '2026-06') if abs(idx[s][m] - term[(s, m)]) > 0.006]
    print('June 2025 and June 2026 agree between the two index files for', 50 - len({s for s, _ in off}), 'of 50 states')
    now, last = so_far(); up = [s for s in now if now[s] > 0]
    print(f"this term to {last}: above zero in {len(up)} of {len(now)}, holding {sum(ev[2028][s] for s in up):.0f} electoral votes; at or below zero: {sorted(s for s in now if now[s] <= 0)}")
