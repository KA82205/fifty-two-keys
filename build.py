"""The Keys, full version: 52 keys in five groups. Builds the key table for 1952-2024.

THE KEY LIST AND RULES BELOW WERE WRITTEN BEFORE ANY OF THE NEW KEYS WAS SCORED AGAINST A RESULT.
No key from the 27-key pilot was dropped. The two state keys (A18, B15) were added later, by the same rule:
defined in states.py first, scored afterwards. Every key is TRUE when it favors the party holding the White House.

Conventions (the same for every key):
  y             the election year
  June          the monthly value for June of y (a forecast made at the end of July can use it)
  spring        the April-June average of y (used for two noisy series: jobless claims and housing starts)
  a year ago    the same month or months of y-1
  start of term January of y-3 (for the two noisy series, January-March of y-3)
  previous term January of y-7 to January of y-3
  Ties are FALSE (a key needs a strict improvement) unless the rule says "at least" or "did not lose".
  A key that cannot be computed for a year is left blank.
  No cut-off is estimated from election results: every rule compares with zero, a year ago, the start of the
  term, the previous term, 50%, or a fact (who holds the House, who is on the ballot).

A  ECONOMY NOW (18)
 Output and spending
  A01 gdp_q2_growing         real GDP grew in the second quarter
  A02 gdp_pc_up_year         real GDP per person in Q2 higher than a year ago
  A03 indpro_up_year         industrial production in June higher than a year ago                              NEW
  A04 spending_pc_up_year    real consumer spending per person in June higher than a year ago                  NEW
 Jobs
  A05 unemp_down_year        unemployment rate in June lower than a year ago
  A06 jobs_up_year           payroll jobs in June higher than a year ago
  A07 factory_jobs_up_year   manufacturing jobs in June higher than a year ago                                 NEW
  A08 claims_down_year       new claims for jobless benefits in spring lower than a year ago                   NEW
  A09 no_recession_signal    the three-month average unemployment rate in June is less than half a point above
                             its low of the previous twelve months (the Sahm rule). Replaces Lichtman's own
                             rating of his key 5.                                                              RULE
 Pay and prices
  A10 income_pc_up_year      real disposable income per person in Q2 higher than a year ago
  A11 wages_up_year          hourly pay in goods-producing industries rose faster than prices over the year    NEW
  A12 inflation_down_year    12-month CPI inflation in June lower than 12-month inflation a year ago
  A13 oil_down_year          the price of oil, after inflation, in June lower than a year ago                  NEW
 Markets and mood
  A14 stocks_up_year         S&P 500 in June higher than a year ago
  A15 stocks_up_this_year    S&P 500 in June higher than in December                                           NEW
  A16 sentiment_up_year      consumer sentiment in June higher than a year ago
  A17 housing_up_year        housing starts in spring higher than a year ago                                   NEW
 State by state
  A18 states_growing         state economies are growing in states that hold a majority of the electoral votes.
                             Growth is the Philadelphia Fed's State Coincident Index, each quarter weighted
                             toward the election as in Enns et al. (2024); see states.py. From 1980.          STATES
B  ECONOMY THIS TERM (15)
 Output and spending
  B01 lt_growth              real GDP per person grew at least as fast this term (to Q2) as on average over the
                             previous two terms. Lichtman's key 6, scored from data from 1960; his rating for
                             1952 and 1956, where the data do not reach back.                                  RULE
  B02 indpro_beats_prev      industrial production grew faster this term than over the previous term           NEW
  B03 spending_beats_prev    real consumer spending per person grew faster this term than over the previous    NEW
 Jobs
  B04 unemp_below_start      unemployment in June lower than at the start of the term
  B05 jobs_beat_prev         payroll jobs grew faster this term than over the previous term
  B06 factory_jobs_above_start  manufacturing jobs in June higher than at the start of the term                NEW
  B07 claims_below_start     jobless claims in spring lower than at the start of the term                      NEW
 Pay and prices
  B08 income_beats_prev      real disposable income per person grew faster this term than over the previous
  B09 wages_above_start      hourly pay, after inflation, in June higher than at the start of the term         NEW
  B10 inflation_below_prev   average CPI inflation this term lower than over the previous term
  B11 oil_below_start        the price of oil, after inflation, in June lower than at the start of the term    NEW
 Markets and mood
  B12 real_stocks_above_start   S&P 500, after inflation, in June higher than at the start of the term
  B13 sentiment_above_start  consumer sentiment in June higher than at the start of the term
  B14 housing_above_start    housing starts in spring higher than at the start of the term                     NEW
 State by state
  B15 states_beat_prev       the same weighted growth is higher than at the same point of the previous term in
                             states that hold a majority of the electoral votes. From 1984.                   STATES
C  APPROVAL OF THE PRESIDENT (6)
  C01 approval_50            at least 50% approve (average of polls completed in June; May if there are none)
  C02 approval_net_positive  more approve than disapprove (same polls)
  C03 approval_up_year       approval higher than in June a year ago
  C04 approval_above_midterm approval higher than at the midterm elections (polls completed in October or
                             November of y-2)                                                                  NEW
  C05 approval_up_this_year  approval higher than in January (December if there are no January polls)          NEW
  C06 disapproval_under_50   fewer than 50% disapprove (June polls)                                            NEW
D  PARTY STRENGTH (6)
  D01 mandate                more House seats after the midterm than after the previous midterm. Lichtman's
                             key 1, scored from seat counts.                                                   RULE
  D02 holds_house            the party has a majority in the House in the election year
  D03 holds_senate           the party controls the Senate in the election year
  D04 prev_majority          the party won more than half of all votes cast in the previous presidential election
  D05 kept_house_seats       the party did not lose House seats at the midterm                                 NEW
  D06 kept_senate_seats      the party did not lose Senate seats at the midterm                                NEW
E  INCUMBENCY AND NOMINATIONS (7)
  E01 sitting_president      the party's candidate is the sitting president (a fact; Lichtman's key 3)
  E02 first_term_party       the party has held the White House for one term only
  E03 no_third_party         no significant third-party campaign. Lichtman's key 4, HIS RATING (he scores it by
                             the final vote). For 2028 the rule is: no third candidate at 10% or more in the
                             June polls.
  E04 no_contest             no serious contest for the party's nomination. Lichtman's key 2, HIS RATING. For
                             2028 the rule is his: the nominee has at least two-thirds of the delegates.
  E05 office_won_primary     the party's candidate (the sitting president if he was in the race, else the
                             nominee) won the New Hampshire primary                                            NEW
  E06 primary_stronger       he won a larger share of his New Hampshire primary than the challenger won of his NEW
  E07 challenger_lost_primary   the challenger did not win his own party's New Hampshire primary               NEW

NOTHING ABOVE WAS CHANGED BECAUSE OF HOW IT SCORED. Three changes were tried after the results were in. Each raised
the record on paper, each was chosen by looking at the elections the keys had missed, and each was taken out again
for that reason. test.py still reports what they would have done:
  1 a group of their own for E05-E07 (six groups)
  2 E05 and E06 scored on the November nominee. In 1952, 1968 and 2024 the president left the race after the New
    Hampshire primary and the nominee was never in a primary; scored this way both keys would be false in those years
  3 two keys (C06 and E05) that could overrule the count

Left out on purpose: head-to-head polls (this is meant to be separate from a polls model); scandal, unrest,
charisma and policy change (judgment calls); war and peace (no casualty rule simple enough to be fair gives
sensible answers: it would count against presidents who inherited a war as much as those who began one).
"""
import csv, datetime, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
sys.path.insert(0, HERE)
import states as STATES                                # noqa: E402

GROUPS = {
    'A': ['A01_gdp_q2_growing', 'A02_gdp_pc_up_year', 'A03_indpro_up_year', 'A04_spending_pc_up_year',
          'A05_unemp_down_year', 'A06_jobs_up_year', 'A07_factory_jobs_up_year', 'A08_claims_down_year', 'A09_no_recession_signal',
          'A10_income_pc_up_year', 'A11_wages_up_year', 'A12_inflation_down_year', 'A13_oil_down_year',
          'A14_stocks_up_year', 'A15_stocks_up_this_year', 'A16_sentiment_up_year', 'A17_housing_up_year', 'A18_states_growing'],
    'B': ['B01_lt_growth', 'B02_indpro_beats_prev', 'B03_spending_beats_prev',
          'B04_unemp_below_start', 'B05_jobs_beat_prev', 'B06_factory_jobs_above_start', 'B07_claims_below_start',
          'B08_income_beats_prev', 'B09_wages_above_start', 'B10_inflation_below_prev', 'B11_oil_below_start',
          'B12_real_stocks_above_start', 'B13_sentiment_above_start', 'B14_housing_above_start', 'B15_states_beat_prev'],
    'C': ['C01_approval_50', 'C02_approval_net_positive', 'C03_approval_up_year', 'C04_approval_above_midterm',
          'C05_approval_up_this_year', 'C06_disapproval_under_50'],
    'D': ['D01_mandate', 'D02_holds_house', 'D03_holds_senate', 'D04_prev_majority', 'D05_kept_house_seats', 'D06_kept_senate_seats'],
    'E': ['E01_sitting_president', 'E02_first_term_party', 'E03_no_third_party', 'E04_no_contest', 'E05_office_won_primary',
          'E06_primary_stronger', 'E07_challenger_lost_primary'],
}
GROUP_NAMES = {'A': 'Economy now', 'B': 'Economy this term', 'C': 'Approval', 'D': 'Party strength', 'E': 'Incumbency and nominations'}
ALL = [k for g in GROUPS.values() for k in g]
IF_NOMINEE = ['E05_if_nominee', 'E06_if_nominee']     # not keys: E05 and E06 as they would be under tried change 2 (see above)

assert len(ALL) == 52 and len(set(ALL)) == 52

# The winner's share of all votes cast (Wikipedia, "List of United States presidential elections by popular vote margin").
WINNER_PCT = {1944: 53.39, 1948: 49.55, 1952: 55.18, 1956: 57.37, 1960: 49.72, 1964: 61.05, 1968: 43.42, 1972: 60.67,
              1976: 50.08, 1980: 50.75, 1984: 58.77, 1988: 53.37, 1992: 43.01, 1996: 49.23, 2000: 47.87, 2004: 50.73,
              2008: 52.93, 2012: 51.06, 2016: 46.09, 2020: 51.31, 2024: 49.80}
# Gallup's trend table for Biden (the course file mixes in polls of the vice president from 2021 on).
GALLUP_BIDEN = [('2022-10-20', 40, 56), ('2022-12-02', 40, 55), ('2023-06-22', 43, 54), ('2024-01-22', 41, 54), ('2024-06-23', 38, 58)]


def num(s):
    return None if s in ('NA', '', None, '-') else float(s)


def load():
    d = {}
    C = os.path.join(DATA, 'course')
    d['monthly'] = {(int(r['year']), int(r['month'])): {k: num(r[k]) for k in ('jobs', 'cpi', 'ics', 'sp500', 'unemp')}
                    for r in csv.DictReader(open(os.path.join(C, 'econ_fundamentals.csv')))}
    d['quarterly'] = {(int(r['year']), int(r['quarter'])): {'g_gdp': num(r['GDP_growth_quarterly']), 'g_rdpi': num(r['RDPI_growth_quarterly'])}
                      for r in csv.DictReader(open(os.path.join(C, 'fred_econ.csv')))}
    d['pop'] = {(int(r['Year']), int(r['Quarter'])): float(r['Population..midperiod..thousands.'])
                for r in csv.DictReader(open(os.path.join(C, 'other_econ_indicators.csv')))}
    md = {}
    rows = list(csv.reader(open(os.path.join(DATA, 'fred_md_2025-06.csv'))))
    head = rows[0]
    for r in rows[2:]:
        if not r or '/' not in r[0]:
            continue
        m, _, y = r[0].split('/')
        for name, x in zip(head[1:], r[1:]):
            if x != '':
                md[(name, int(y), int(m))] = float(x)
    d['md'] = md
    d['early'] = {(r['series'], int(r['date'][:4]), int(r['date'][5:7])): float(r['value'])
                  for r in csv.DictReader(open(os.path.join(DATA, 'fred_early.csv')))}
    polls = []
    for r in csv.DictReader(open(os.path.join(C, 'approval.csv'), encoding='utf-8-sig')):
        if not r['end_date'] or r['approve'] in ('', 'NA'):
            continue
        m, dd, yy = r['end_date'].split('/')
        yy = int(yy); yy = 1900 + yy if yy >= 40 else 2000 + yy
        day = datetime.date(yy, int(m), int(dd))
        if day >= datetime.date(2021, 1, 20):
            continue
        polls.append((day, float(r['approve']), num(r['disapprove'])))
    for day, a, dis in GALLUP_BIDEN:
        polls.append((datetime.date.fromisoformat(day), float(a), float(dis)))
    d['polls'] = polls
    d['hist'] = {int(r['year']): r for r in csv.DictReader(open(os.path.join(DATA, 'keys_history.csv')))}
    d['lich'] = {int(r['year']): r for r in csv.DictReader(open(os.path.join(DATA, 'lichtman13_wikipedia.csv')))}
    d['seats'] = {int(r['start_year']): r for r in csv.DictReader(open(os.path.join(DATA, 'congress_seats.csv')))}
    d['nh'] = {int(r['year']): r for r in csv.DictReader(open(os.path.join(DATA, 'nh_primaries.csv')))}
    d['state_measure'], d['state_ev'] = STATES.measures(), STATES.electoral_votes()
    return d


def quarters(first, last):
    out, (y, q) = [], first
    while (y, q) <= last:
        out.append((y, q)); y, q = (y, q + 1) if q < 4 else (y + 1, 1)
    return out


def score_year(d, y):
    """Returns (keys, raw): every key as True/False/None, and the figures behind them."""
    mv = lambda yy, m, k: d['monthly'].get((yy, m), {}).get(k)
    Q, P = d['quarterly'], d['pop']
    k, v = {}, {}

    def series(name, months):
        """Values of one FRED series for several (year, month)s, all from the same vintage, or None."""
        for src in (d['md'], d['early']):
            vals = [src.get((name, yy, m)) for yy, m in months]
            if all(x is not None for x in vals):
                return vals
        return None

    def avg3(name, yy, months):
        vals = [d['md'].get((name, yy, m)) for m in months]
        return None if any(x is None for x in vals) else st.mean(vals)

    def ratio(field, qs):
        x = 1.0
        for q in qs:
            g = Q.get(q, {}).get(field)
            if g is None:
                return None
            x *= (1 + g / 100) ** 0.25
        return x

    def gt(a, b):
        return None if a is None or b is None else a > b

    def lt(a, b):
        return None if a is None or b is None else a < b

    def ann(a, b, months):
        return None if a is None or b is None else 100 * ((a / b) ** (12 / months) - 1)

    h, L = d['hist'][y], d['lich'][y]
    inc = h['incumbent_party']
    dem = float(h['dem_two_party'])
    share = dem if inc == 'D' else 100 - dem
    T = lambda i: L[f'key{i}'] == 'T'
    pr_year = P[(y, 2)] / P[(y - 1, 2)] if (y - 1, 2) in P else None

    # ------------------------------------------------------------------ A economy now
    g = Q.get((y, 2), {}).get('g_gdp'); v['gdp_q2_growth'] = g
    k['A01_gdp_q2_growing'] = None if g is None else g > 0
    yq = quarters((y - 1, 3), (y, 2))
    for key, field, name in (('A02_gdp_pc_up_year', 'g_gdp', 'gdp_pc_year_pct'), ('A10_income_pc_up_year', 'g_rdpi', 'income_pc_year_pct')):
        r = ratio(field, yq)
        v[name] = None if r is None or pr_year is None else 100 * (r / pr_year - 1)
        k[key] = None if v[name] is None else v[name] > 0
    s = series('INDPRO', [(y, 6), (y - 1, 6)])
    v['indpro_year_pct'] = None if s is None else 100 * (s[0] / s[1] - 1)
    k['A03_indpro_up_year'] = None if s is None else s[0] > s[1]
    s = series('DPCERA3M086SBEA', [(y, 6), (y - 1, 6)])
    v['spending_pc_year_pct'] = None if s is None or pr_year is None else 100 * (s[0] / s[1] / pr_year - 1)
    k['A04_spending_pc_up_year'] = None if v['spending_pc_year_pct'] is None else v['spending_pc_year_pct'] > 0
    a, b = mv(y, 6, 'unemp'), mv(y - 1, 6, 'unemp'); v['unemp_june'], v['unemp_year_ago'] = a, b
    k['A05_unemp_down_year'] = lt(a, b)
    a, b = mv(y, 6, 'jobs'), mv(y - 1, 6, 'jobs'); v['jobs_year_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    k['A06_jobs_up_year'] = gt(a, b)
    s = series('MANEMP', [(y, 6), (y - 1, 6)])
    v['factory_jobs_year_pct'] = None if s is None else 100 * (s[0] / s[1] - 1)
    k['A07_factory_jobs_up_year'] = None if s is None else s[0] > s[1]
    a, b = avg3('CLAIMSx', y, (4, 5, 6)), avg3('CLAIMSx', y - 1, (4, 5, 6)); v['claims_year_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    k['A08_claims_down_year'] = lt(a, b)
    # Sahm rule in June: three-month average unemployment against its low over the previous twelve months
    def u3(yy, m):
        ms = [(yy, m)]
        for _ in range(2):
            yy, m = (yy, m - 1) if m > 1 else (yy - 1, 12); ms.append((yy, m))
        vals = [mv(a_, b_, 'unemp') for a_, b_ in ms]
        return None if any(x is None for x in vals) else st.mean(vals)
    prev12 = []; yy, m = y, 6
    for _ in range(12):
        yy, m = (yy, m - 1) if m > 1 else (yy - 1, 12); prev12.append(u3(yy, m))
    now3 = u3(y, 6)
    v['sahm_june'] = None if now3 is None or any(x is None for x in prev12) else now3 - min(prev12)
    k['A09_no_recession_signal'] = None if v['sahm_june'] is None else v['sahm_june'] < 0.5
    w = series('CES0600000008', [(y, 6), (y - 1, 6)]); c0, c1, c2 = mv(y, 6, 'cpi'), mv(y - 1, 6, 'cpi'), mv(y - 2, 6, 'cpi')
    v['real_wage_year_pct'] = None if w is None or c0 is None or c1 is None else 100 * ((w[0] / c0) / (w[1] / c1) - 1)
    k['A11_wages_up_year'] = None if v['real_wage_year_pct'] is None else v['real_wage_year_pct'] > 0
    v['inflation_june'] = None if c0 is None or c1 is None else 100 * (c0 / c1 - 1)
    v['inflation_year_ago'] = None if c1 is None or c2 is None else 100 * (c1 / c2 - 1)
    k['A12_inflation_down_year'] = lt(v['inflation_june'], v['inflation_year_ago'])
    o = series('OILPRICEx', [(y, 6), (y - 1, 6)])
    v['real_oil_year_pct'] = None if o is None or c0 is None or c1 is None else 100 * ((o[0] / c0) / (o[1] / c1) - 1)
    k['A13_oil_down_year'] = None if v['real_oil_year_pct'] is None else v['real_oil_year_pct'] < 0
    a, b, dec = mv(y, 6, 'sp500'), mv(y - 1, 6, 'sp500'), mv(y - 1, 12, 'sp500')
    v['stocks_year_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    v['stocks_ytd_pct'] = None if a is None or dec is None else 100 * (a / dec - 1)
    k['A14_stocks_up_year'] = gt(a, b)
    k['A15_stocks_up_this_year'] = gt(a, dec)
    a, b = mv(y, 6, 'ics'), mv(y - 1, 6, 'ics'); v['sentiment_june'], v['sentiment_year_ago'] = a, b
    k['A16_sentiment_up_year'] = gt(a, b)
    a, b = avg3('HOUST', y, (4, 5, 6)), avg3('HOUST', y - 1, (4, 5, 6)); v['housing_year_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    k['A17_housing_up_year'] = gt(a, b)
    k['A18_states_growing'], b15, sv = STATES.state_keys(y, d['state_measure'], d['state_ev'])
    v.update(sv)

    # ------------------------------------------------------------------ B economy this term
    def term_growth_pc(field, end_y):
        """Annualized growth per person over the term that ends in end_y: to Q2 if end_y is the election year, else to Q4."""
        last = (end_y, 2) if end_y == y else (end_y, 4)
        r = ratio(field, quarters((end_y - 3, 1), last))
        base = (end_y - 4, 4)
        if r is None or base not in P or last not in P:
            return None
        n = len(quarters((end_y - 3, 1), last))
        return 100 * ((r / (P[last] / P[base])) ** (4 / n) - 1)
    t0, t1, t2 = term_growth_pc('g_gdp', y), term_growth_pc('g_gdp', y - 4), term_growth_pc('g_gdp', y - 8)
    v['gdp_pc_term'], v['gdp_pc_prev_two'] = t0, (None if t1 is None or t2 is None else (t1 + t2) / 2)
    k['B01_lt_growth'] = T(6) if v['gdp_pc_prev_two'] is None or t0 is None else t0 >= v['gdp_pc_prev_two']
    v['B01_from'] = 'Lichtman rating' if v['gdp_pc_prev_two'] is None or t0 is None else 'data'
    s = series('INDPRO', [(y, 6), (y - 3, 1), (y - 7, 1)])
    v['indpro_term'], v['indpro_prev_term'] = (None, None) if s is None else (ann(s[0], s[1], 41), ann(s[1], s[2], 48))
    k['B02_indpro_beats_prev'] = gt(v['indpro_term'], v['indpro_prev_term'])
    s = series('DPCERA3M086SBEA', [(y, 6), (y - 3, 1), (y - 7, 1)])
    if s is None or (y - 3, 1) not in P or (y - 7, 1) not in P:
        v['spending_pc_term'] = v['spending_pc_prev_term'] = None
    else:
        v['spending_pc_term'] = ann(s[0] / P[(y, 2)], s[1] / P[(y - 3, 1)], 41)
        v['spending_pc_prev_term'] = ann(s[1] / P[(y - 3, 1)], s[2] / P[(y - 7, 1)], 48)
    k['B03_spending_beats_prev'] = gt(v['spending_pc_term'], v['spending_pc_prev_term'])
    a, b = mv(y, 6, 'unemp'), mv(y - 3, 1, 'unemp'); v['unemp_term_start'] = b
    k['B04_unemp_below_start'] = lt(a, b)
    j0, j1, j2 = mv(y, 6, 'jobs'), mv(y - 3, 1, 'jobs'), mv(y - 7, 1, 'jobs')
    v['jobs_term'], v['jobs_prev_term'] = ann(j0, j1, 41), ann(j1, j2, 48)
    k['B05_jobs_beat_prev'] = gt(v['jobs_term'], v['jobs_prev_term'])
    s = series('MANEMP', [(y, 6), (y - 3, 1)])
    v['factory_jobs_term_pct'] = None if s is None else 100 * (s[0] / s[1] - 1)
    k['B06_factory_jobs_above_start'] = None if s is None else s[0] > s[1]
    a, b = avg3('CLAIMSx', y, (4, 5, 6)), avg3('CLAIMSx', y - 3, (1, 2, 3)); v['claims_term_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    k['B07_claims_below_start'] = lt(a, b)
    r1, r0 = term_growth_pc('g_rdpi', y), term_growth_pc('g_rdpi', y - 4)
    v['income_pc_term'], v['income_pc_prev_term'] = r1, r0
    k['B08_income_beats_prev'] = gt(r1, r0)
    w = series('CES0600000008', [(y, 6), (y - 3, 1)]); c0, c1, c2 = mv(y, 6, 'cpi'), mv(y - 3, 1, 'cpi'), mv(y - 7, 1, 'cpi')
    v['real_wage_term_pct'] = None if w is None or c0 is None or c1 is None else 100 * ((w[0] / c0) / (w[1] / c1) - 1)
    k['B09_wages_above_start'] = None if v['real_wage_term_pct'] is None else v['real_wage_term_pct'] > 0
    v['inflation_term'], v['inflation_prev_term'] = ann(c0, c1, 41), ann(c1, c2, 48)
    k['B10_inflation_below_prev'] = lt(v['inflation_term'], v['inflation_prev_term'])
    o = series('OILPRICEx', [(y, 6), (y - 3, 1)])
    v['real_oil_term_pct'] = None if o is None or c0 is None or c1 is None else 100 * ((o[0] / c0) / (o[1] / c1) - 1)
    k['B11_oil_below_start'] = None if v['real_oil_term_pct'] is None else v['real_oil_term_pct'] < 0
    s0, s1 = mv(y, 6, 'sp500'), mv(y - 3, 1, 'sp500')
    v['real_stocks_term_pct'] = None if None in (s0, s1, c0, c1) else 100 * ((s0 / c0) / (s1 / c1) - 1)
    k['B12_real_stocks_above_start'] = None if v['real_stocks_term_pct'] is None else v['real_stocks_term_pct'] > 0
    a, b = mv(y, 6, 'ics'), mv(y - 3, 1, 'ics'); v['sentiment_term_start'] = b
    k['B13_sentiment_above_start'] = gt(a, b)
    a, b = avg3('HOUST', y, (4, 5, 6)), avg3('HOUST', y - 3, (1, 2, 3)); v['housing_term_pct'] = None if a is None or b is None else 100 * (a / b - 1)
    k['B14_housing_above_start'] = gt(a, b)
    k['B15_states_beat_prev'] = b15

    # ------------------------------------------------------------------ C approval
    def polls_in(yy, months):
        for m in months:
            p = [x for x in d['polls'] if x[0].year == yy + (m // 100) and x[0].month == m % 100] if m > 12 else [x for x in d['polls'] if x[0].year == yy and x[0].month == m]
            if p:
                dis = [x[2] for x in p if x[2] is not None]
                return st.mean(x[1] for x in p), (st.mean(dis) if dis else None), len(p)
        return None, None, 0
    ap, dis, n = polls_in(y, (6, 5))
    ap0, _, _ = polls_in(y - 1, (6, 5))
    mid = [x[1] for x in d['polls'] if x[0].year == y - 2 and x[0].month in (10, 11)] or [x[1] for x in d['polls'] if (x[0].year, x[0].month) in ((y - 2, 9), (y - 2, 12))]
    apm = st.mean(mid) if mid else None
    jan, _, _ = polls_in(y, (1,))
    if jan is None:
        jan, _, _ = polls_in(y - 1, (12,))
    v['approval_june'], v['disapproval_june'], v['approval_polls'], v['approval_year_ago'], v['approval_midterm'], v['approval_january'] = ap, dis, n, ap0, apm, jan
    k['C01_approval_50'] = None if ap is None else ap >= 50
    k['C02_approval_net_positive'] = gt(ap, dis)
    k['C03_approval_up_year'] = gt(ap, ap0)
    k['C04_approval_above_midterm'] = gt(ap, apm)
    k['C05_approval_up_this_year'] = gt(ap, jan)
    k['C06_disapproval_under_50'] = None if dis is None else dis < 50

    # ------------------------------------------------------------------ D party strength
    S = d['seats']
    hs = lambda yy: float(S[yy]['house_d' if inc == 'D' else 'house_r']) if yy in S else None
    ss = lambda yy: float(S[yy]['senate_d' if inc == 'D' else 'senate_r']) if yy in S else None
    v['house_after_midterm'], v['house_after_prev_midterm'], v['house_start_of_term'] = hs(y - 1), hs(y - 5), hs(y - 3)
    v['senate_after_midterm'], v['senate_start_of_term'] = ss(y - 1), ss(y - 3)
    k['D01_mandate'] = gt(hs(y - 1), hs(y - 5))
    k['D02_holds_house'] = float(S[y - 1]['house_d']) > float(S[y - 1]['house_r']) if inc == 'D' else float(S[y - 1]['house_r']) > float(S[y - 1]['house_d'])
    # Senate control: more seats, or a tie broken by the party's own vice president
    sd, sr = float(S[y - 1]['senate_d']), float(S[y - 1]['senate_r'])
    k['D03_holds_senate'] = (sd > sr) if inc == 'D' else (sr > sd)
    if sd == sr:
        k['D03_holds_senate'] = True      # a tied Senate is organized by the president's party
    prev = WINNER_PCT.get(y - 4); v['prev_total_share'] = prev
    k['D04_prev_majority'] = None if prev is None else prev > 50
    k['D05_kept_house_seats'] = None if hs(y - 1) is None or hs(y - 3) is None else hs(y - 1) >= hs(y - 3)
    k['D06_kept_senate_seats'] = None if ss(y - 1) is None or ss(y - 3) is None else ss(y - 1) >= ss(y - 3)

    # ------------------------------------------------------------------ E incumbency and nominations
    n = d['nh'][y]
    k['E01_sitting_president'] = T(3)
    k['E02_first_term_party'] = d['hist'][y - 4]['incumbent_party'] != inc
    k['E03_no_third_party'] = T(4)
    k['E04_no_contest'] = T(2)
    k['E05_office_won_primary'] = n['office_won'] == '1'
    k['E06_primary_stronger'] = float(n['office_share']) > float(n['challenger_share'])
    k['E07_challenger_lost_primary'] = n['challenger_won'] == '0'
    ran = n['office_ran'] == n['office_nominee']            # the candidate who ran in New Hampshire was the nominee in November
    v['nh_office_share'], v['nh_challenger_share'] = float(n['office_share']), float(n['challenger_share'])
    v['nh_office_ran'], v['nh_office_won'], v['nh_nominee'], v['nh_nominee_ran'] = n['office_ran'], int(n['office_won']), n['office_nominee'], int(ran)
    v['nh_challenger'], v['nh_challenger_won'] = n['challenger'], int(n['challenger_won'])
    # not keys: the two as they would be if scored on the November nominee (a change that was tried and left out)
    tried = {'E05_if_nominee': ran and k['E05_office_won_primary'], 'E06_if_nominee': ran and k['E06_primary_stronger']}
    return {'year': y, 'inc_party': inc, 'inc_share': round(share, 2), **k, **tried}, {'year': y, **v}, L


def build(first=1952, last=2024):
    d = load()
    rows, raw, checks = [], [], []
    for y in range(first, last + 1, 4):
        r, v, L = score_year(d, y)
        rows.append(r); raw.append(v)
        # how the rule-based versions compare with Lichtman's own ratings (for the record only)
        checks.append({'year': y, 'A09_vs_key5': (r['A09_no_recession_signal'], L['key5'] == 'T'),
                       'B01_vs_key6': (r['B01_lt_growth'], L['key6'] == 'T'), 'D01_vs_key1': (r['D01_mandate'], L['key1'] == 'T')})
    return rows, raw, checks


if __name__ == '__main__':
    rows, raw, checks = build()
    with open(os.path.join(HERE, 'keys_table.csv'), 'w', newline='') as f:
        cols = ALL + IF_NOMINEE
        w = csv.writer(f); w.writerow(['year', 'inc_party', 'inc_share'] + cols)
        for r in rows:
            w.writerow([r['year'], r['inc_party'], r['inc_share']] + ['' if r[x] is None else int(r[x]) for x in cols])
    with open(os.path.join(HERE, 'keys_raw_values.csv'), 'w', newline='') as f:
        cols = list(raw[0].keys()); w = csv.writer(f); w.writerow(cols)
        for r in raw:
            w.writerow(['' if r[c] is None else (round(r[c], 3) if isinstance(r[c], float) else r[c]) for c in cols])
    print('keys:', len(ALL), {g: len(ks) for g, ks in GROUPS.items()})
    for r in rows:
        av = [x for x in ALL if r[x] is not None]
        per = {g: f"{sum(1 for x in ks if r[x] is not None)}/{len(ks)}" for g, ks in GROUPS.items()}
        print(r['year'], r['inc_party'], f"{r['inc_share']:5.2f}", f"available {len(av)}/{len(ALL)}", per, 'blank:', ' '.join(x[:3] for x in ALL if r[x] is None))
    print('\nRule-based keys against Lichtman\'s own ratings (rule, his):')
    for name in ('A09_vs_key5', 'B01_vs_key6', 'D01_vs_key1'):
        diff = [c['year'] for c in checks if c[name][0] is not None and c[name][0] != c[name][1]]
        print(f"  {name}: differ in {diff}")
