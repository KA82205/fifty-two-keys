"""Writes docs/index.html from template.html: one self-contained page (data, script and typefaces inside it)
showing where 2028 stands, the record, every key in every election and the full key list.
Run after build.py and test.py. The figures printed on the page are checked against results.json before writing."""
import base64, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import GROUPS, GROUP_NAMES, ALL, build     # noqa: E402
import states as S                                    # noqa: E402
from test import TOOK_OFFICE                          # noqa: E402

WORD = {50: 'fifty', 51: 'fifty-one', 52: 'fifty-two', 53: 'fifty-three', 54: 'fifty-four', 55: 'fifty-five', 56: 'fifty-six',
        57: 'fifty-seven', 58: 'fifty-eight', 59: 'fifty-nine', 60: 'sixty'}[len(ALL)]
STATE_NAME = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
              'DE': 'Delaware', 'DC': 'Washington, D.C.', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
              'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
              'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
              'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
              'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
              'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
              'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}
MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

TEXT = {
 'A01': ("Real GDP grew in the second quarter", "Second-quarter growth above zero."),
 'A02': ("Real GDP per person is higher than a year ago", "Second quarter against the second quarter a year earlier."),
 'A03': ("Industrial production is higher than a year ago", "June against June a year earlier."),
 'A04': ("Real consumer spending per person is higher than a year ago", "June against June a year earlier."),
 'A05': ("Unemployment is lower than a year ago", "The June rate against June a year earlier."),
 'A06': ("There are more payroll jobs than a year ago", "June against June a year earlier."),
 'A07': ("There are more factory jobs than a year ago", "Manufacturing jobs, June against June a year earlier."),
 'A08': ("New jobless claims are lower than a year ago", "April to June average against the same months a year earlier."),
 'A09': ("Unemployment is not signalling a recession", "The three-month average rate in June is less than half a point above its low of the past twelve months. Replaces Lichtman's own rating of his recession key."),
 'A10': ("Real disposable income per person is higher than a year ago", "Second quarter against the second quarter a year earlier."),
 'A11': ("Hourly pay rose faster than prices over the year", "Pay in goods-producing industries, divided by consumer prices, June against June."),
 'A12': ("Inflation is lower than a year ago", "Twelve-month inflation in June against twelve-month inflation a year earlier."),
 'A13': ("Oil is cheaper than a year ago, after inflation", "The crude oil price divided by consumer prices, June against June."),
 'A14': ("Stocks are higher than a year ago", "The S&P 500 in June against June a year earlier."),
 'A15': ("Stocks are higher than in December", "The S&P 500 in June against the December before."),
 'A16': ("Consumer sentiment is higher than a year ago", "The Michigan index in June against June a year earlier."),
 'A17': ("More homes are being started than a year ago", "Housing starts, April to June average against a year earlier."),
 'A18': ("Most electoral votes are in states with a growing economy", "Each state's coincident index from the Philadelphia Fed, with the quarters nearest the election counting most, the way Enns and colleagues (2024) weight it. True when that growth is above zero in states holding at least 270 electoral votes. The indexes begin in 1979."),
 'B01': ("Real GDP per person grew at least as fast this term as over the last two", "Lichtman's long-term economy key, scored from the data from 1960 on. His own rating is used for 1952 and 1956."),
 'B02': ("Industrial production grew faster this term than last", "Yearly growth from January of the first year to June, against the previous four years."),
 'B03': ("Real consumer spending per person grew faster this term than last", "Yearly growth from January of the first year to June, against the previous four years."),
 'B04': ("Unemployment is lower than when the term began", "The June rate against January of the first year."),
 'B05': ("Jobs grew faster this term than last", "Yearly growth in payroll jobs from January of the first year to June, against the previous four years."),
 'B06': ("There are more factory jobs than when the term began", "Manufacturing jobs in June against January of the first year."),
 'B07': ("Jobless claims are lower than when the term began", "April to June average against the first three months of the term."),
 'B08': ("Real disposable income per person grew faster this term than last", "Yearly growth to the second quarter, against the previous four years."),
 'B09': ("Hourly pay buys more than when the term began", "Pay divided by consumer prices, June against January of the first year."),
 'B10': ("Inflation has been lower this term than last", "Average yearly inflation from January of the first year to June, against the previous four years."),
 'B11': ("Oil is cheaper than when the term began, after inflation", "The crude oil price divided by consumer prices, June against January of the first year."),
 'B12': ("Stocks are higher than when the term began, after inflation", "The S&P 500 divided by consumer prices, June against January of the first year."),
 'B13': ("Consumer sentiment is higher than when the term began", "The Michigan index in June against January of the first year."),
 'B14': ("More homes are being started than when the term began", "Housing starts, April to June average against the first three months of the term."),
 'B15': ("Most electoral votes are in states growing faster than at this point last term", "The same weighted growth in each state, against its own figure four years earlier. True when it is higher in states holding at least 270 electoral votes."),
 'C01': ("At least half approve of the president", "Average of polls finished in June."),
 'C02': ("More approve than disapprove", "Average of polls finished in June."),
 'C03': ("Approval is higher than a year ago", "June against June a year earlier."),
 'C04': ("Approval is higher than at the midterms", "June against polls finished in October and November two years earlier."),
 'C05': ("Approval is higher than in January", "June against January of the election year."),
 'C06': ("Fewer than half disapprove", "Average of polls finished in June."),
 'D01': ("The party holds more House seats than after the previous midterm", "Lichtman's mandate key, scored from seat counts."),
 'D02': ("The party holds the House", "A majority of seats in the election year."),
 'D03': ("The party holds the Senate", "Control of the chamber in the election year."),
 'D04': ("The party won more than half of all votes last time", "Its share of every vote cast in the previous presidential election."),
 'D05': ("The party did not lose House seats at the midterm", "Seats after the midterm against seats at the start of the term."),
 'D06': ("The party did not lose Senate seats at the midterm", "Seats after the midterm against seats at the start of the term."),
 'E01': ("The sitting president is the candidate", "A fact."),
 'E02': ("The party has held the White House for one term only", "A fact."),
 'E03': ("No third candidate has a significant following", "Lichtman's third-party key at his own rating, which uses the final vote. For 2028: no third candidate at 10% or more in the June polls."),
 'E04': ("The party's nomination was not seriously contested", "Lichtman's contest key at his own rating. For 2028: the nominee has at least two-thirds of the delegates."),
 'E05': ("The party's candidate won the New Hampshire primary", "The sitting president if he was in the race, otherwise the nominee."),
 'E06': ("The party's candidate did better in New Hampshire than the challenger did", "His share of his party's primary against the challenger's share of the other party's."),
 'E07': ("The challenger lost the New Hampshire primary", "The other party's nominee did not win that party's primary."),
}
# where a key descends from one of Lichtman's thirteen
TAG = {'A09': "Lichtman's key 5, scored by a rule", 'B01': "Lichtman's key 6, scored by a rule", 'D01': "Lichtman's key 1, scored by a rule",
       'E01': "Lichtman's key 3", 'E03': "Lichtman's key 4, at his rating", 'E04': "Lichtman's key 2, at his rating"}
GROUP_DESC = {'A': 'Is the economy doing better than a year ago? Scored on the June figures of the election year.',
              'B': 'Is the economy doing better than when the term began, or than it did last term?',
              'C': 'What people tell pollsters about the president in June of the election year.',
              'D': "The party's standing in Congress and at the last presidential election.",
              'E': 'Who is on the ticket, and how the nominations went.'}
NOMINEES = {1952: ('Stevenson', 'Eisenhower'), 1956: ('Eisenhower', 'Stevenson'), 1960: ('Nixon', 'Kennedy'), 1964: ('Johnson', 'Goldwater'),
            1968: ('Humphrey', 'Nixon'), 1972: ('Nixon', 'McGovern'), 1976: ('Ford', 'Carter'), 1980: ('Carter', 'Reagan'), 1984: ('Reagan', 'Mondale'),
            1988: ('Bush', 'Dukakis'), 1992: ('Bush', 'Clinton'), 1996: ('Clinton', 'Dole'), 2000: ('Gore', 'Bush'), 2004: ('Bush', 'Kerry'),
            2008: ('McCain', 'Obama'), 2012: ('Obama', 'Romney'), 2016: ('Clinton', 'Trump'), 2020: ('Trump', 'Biden'), 2024: ('Harris', 'Trump')}
# 2028: the party in office is Republican. What is already settled, and why.
S2028 = {
 'D01': (0, "Republicans will hold at most 178 House seats, against 222 after the 2022 midterm."),
 'D02': (0, "Democrats won the House on November 3, 2026."),
 'D03': (0, "Democrats won the Senate, 56 seats to 44."),
 'D04': (0, "Trump won 49.8% of all votes in 2024."),
 'D05': (0, "Republicans went from 220 House seats to at most 178."),
 'D06': (0, "Republicans went from 53 Senate seats to 44."),
 'E01': (0, "Trump cannot run for a third term."),
 'E02': (1, "Republicans are in their first term back in the White House."),
}
WHEN = {'A': 'Scored in June 2028', 'B': 'Scored in June 2028', 'C': 'Scored in June 2028', 'E03': 'Scored in June 2028',
        'E04': 'Settled by the convention', 'E05': 'Settled once the nominees are known', 'E06': 'Settled once the nominees are known',
        'E07': 'Settled once the nominees are known'}
BUILT = 'November 22, 2026'


def f1(x, d=1, plus=True):
    return '' if x is None else (f"{x:+.{d}f}" if plus else f"{x:.{d}f}")


def detail(k, v):
    """The figure behind a key, in words."""
    g = v.get
    try:
        return {
            'A01': lambda: f"second-quarter growth {f1(g('gdp_q2_growth'))}% a year",
            'A02': lambda: f"{f1(g('gdp_pc_year_pct'))}% over the year",
            'A03': lambda: f"{f1(g('indpro_year_pct'))}% over the year",
            'A04': lambda: f"{f1(g('spending_pc_year_pct'))}% over the year",
            'A05': lambda: f"{f1(g('unemp_june'), 1, False)}% against {f1(g('unemp_year_ago'), 1, False)}% a year earlier",
            'A06': lambda: f"{f1(g('jobs_year_pct'))}% over the year",
            'A07': lambda: f"{f1(g('factory_jobs_year_pct'))}% over the year",
            'A08': lambda: f"{f1(g('claims_year_pct'), 0)}% over the year",
            'A09': lambda: f"signal at {f1(g('sahm_june'), 2, False)}; 0.50 or more points to recession",
            'A10': lambda: f"{f1(g('income_pc_year_pct'))}% over the year",
            'A11': lambda: f"pay after inflation {f1(g('real_wage_year_pct'))}% over the year",
            'A12': lambda: f"{f1(g('inflation_june'), 1, False)}% against {f1(g('inflation_year_ago'), 1, False)}% a year earlier",
            'A13': lambda: f"{f1(g('real_oil_year_pct'), 0)}% over the year",
            'A14': lambda: f"{f1(g('stocks_year_pct'), 0)}% over the year",
            'A15': lambda: f"{f1(g('stocks_ytd_pct'), 0)}% since December",
            'A16': lambda: f"{f1(g('sentiment_june'), 1, False)} against {f1(g('sentiment_year_ago'), 1, False)} a year earlier",
            'A17': lambda: f"{f1(g('housing_year_pct'), 0)}% over the year",
            'A18': lambda: f"growing in {g('states_growing_n')} of 51, holding {g('states_growing_ev'):.0f} of 538 electoral votes",
            'B01': lambda: "Lichtman's rating" if g('B01_from') != 'data' else f"{f1(g('gdp_pc_term'), 1, False)}% a year against {f1(g('gdp_pc_prev_two'), 1, False)}% over the last two terms",
            'B02': lambda: f"{f1(g('indpro_term'), 1, False)}% a year against {f1(g('indpro_prev_term'), 1, False)}% last term",
            'B03': lambda: f"{f1(g('spending_pc_term'), 1, False)}% a year against {f1(g('spending_pc_prev_term'), 1, False)}% last term",
            'B04': lambda: f"{f1(g('unemp_june'), 1, False)}% against {f1(g('unemp_term_start'), 1, False)}% when the term began",
            'B05': lambda: f"{f1(g('jobs_term'), 1, False)}% a year against {f1(g('jobs_prev_term'), 1, False)}% last term",
            'B06': lambda: f"{f1(g('factory_jobs_term_pct'))}% since the term began",
            'B07': lambda: f"{f1(g('claims_term_pct'), 0)}% since the term began",
            'B08': lambda: f"{f1(g('income_pc_term'), 1, False)}% a year against {f1(g('income_pc_prev_term'), 1, False)}% last term",
            'B09': lambda: f"pay after inflation {f1(g('real_wage_term_pct'))}% since the term began",
            'B10': lambda: f"{f1(g('inflation_term'), 1, False)}% a year against {f1(g('inflation_prev_term'), 1, False)}% last term",
            'B11': lambda: f"{f1(g('real_oil_term_pct'), 0)}% since the term began",
            'B12': lambda: f"{f1(g('real_stocks_term_pct'), 0)}% since the term began",
            'B13': lambda: f"{f1(g('sentiment_june'), 1, False)} against {f1(g('sentiment_term_start'), 1, False)} when the term began",
            'B14': lambda: f"{f1(g('housing_term_pct'), 0)}% since the term began",
            'B15': lambda: f"faster in {g('states_better_n')} of 51, holding {g('states_better_ev'):.0f} of 538 electoral votes",
            'C01': lambda: f"{f1(g('approval_june'), 0, False)}% approve",
            'C02': lambda: f"{f1(g('approval_june'), 0, False)}% approve, {f1(g('disapproval_june'), 0, False)}% disapprove",
            'C03': lambda: f"{f1(g('approval_june'), 0, False)}% against {f1(g('approval_year_ago'), 0, False)}% a year earlier",
            'C04': lambda: f"{f1(g('approval_june'), 0, False)}% against {f1(g('approval_midterm'), 0, False)}% at the midterms",
            'C05': lambda: f"{f1(g('approval_june'), 0, False)}% against {f1(g('approval_january'), 0, False)}% in January",
            'C06': lambda: f"{f1(g('disapproval_june'), 0, False)}% disapprove",
            'D01': lambda: f"{f1(g('house_after_midterm'), 0, False)} House seats against {f1(g('house_after_prev_midterm'), 0, False)} after the previous midterm",
            'D04': lambda: f"{f1(g('prev_total_share'), 1, False)}% of all votes last time",
            'D05': lambda: f"{f1(g('house_after_midterm'), 0, False)} House seats against {f1(g('house_start_of_term'), 0, False)} at the start of the term",
            'D06': lambda: f"{f1(g('senate_after_midterm'), 0, False)} Senate seats against {f1(g('senate_start_of_term'), 0, False)} at the start of the term",
            'E05': lambda: f"{g('nh_office_ran')} {'won' if g('nh_office_won') else 'lost'} it with {f1(g('nh_office_share'), 0, False)}%" +
                           ('' if g('nh_nominee_ran') else f". He later left the race and {g('nh_nominee')} was nominated"),
            'E06': lambda: f"{g('nh_office_ran')} {f1(g('nh_office_share'), 0, False)}% in New Hampshire, {g('nh_challenger')} {f1(g('nh_challenger_share'), 0, False)}%",
            'E07': lambda: f"{g('nh_challenger')} {'won' if g('nh_challenger_won') else 'lost'} it with {f1(g('nh_challenger_share'), 0, False)}%",
        }[k]()
    except KeyError:
        return ''


def main():
    rows, raw, _ = build()
    res = json.load(open(os.path.join(HERE, 'results.json')))
    call = res['call']
    ids = [k[:3] for k in ALL]
    full = dict(zip(ids, ALL))
    elections = []
    for r, v in zip(rows, raw):
        y = r['year']
        gs = []
        for ks in GROUPS.values():
            vals = [r[k] for k in ks if r[k] is not None]; gs.append(sum(vals) / len(vals))
        # w: the party in office won the election; sp: it won the most votes nationwide and lost the Electoral College
        elections.append({'y': y, 'p': r['inc_party'], 'c': NOMINEES[y][0], 'o': NOMINEES[y][1], 'w': bool(TOOK_OFFICE[y]), 'sp': y in call['split'], 'v': round(float(r['inc_share']), 1),
                          'k': ''.join('?' if r[k] is None else ('T' if r[k] else '.') for k in ALL), 'i': round(sum(gs) / len(gs), 3),
                          'd': [detail(k[:3], v) if r[k] is not None else '' for k in ALL]})
    run_path = os.path.join(HERE, 'projection_2028.json')
    run = json.load(open(run_path)) if os.path.exists(run_path) else None

    def chance(p):                                       # a chance in words: these are estimates, so nothing finer than five points
        return 'almost no chance of yes' if p < 0.03 else 'almost sure to be yes' if p > 0.97 else f'about {5 * round(20 * p):d}% chance of yes'
    keys = []
    for k in ALL:
        i = k[:3]; e = res['each_key'][k]
        s = S2028.get(i)
        est = run['keys'].get(i) if run else None
        keys.append({'id': i, 'g': i[0], 't': TEXT[i][0], 'r': TEXT[i][1], 'tag': TAG.get(i, ''), 'n': e['n'], 'true': e['true'],
                     's': None if s is None else s[0], 'why': '' if s is None else s[1], 'when': WHEN.get(i, WHEN.get(i[0], '')),
                     'est': chance(est['p']) if est else '', 'note': est['note'] if est else ''})
    if run:
        assert set(run['keys']) == {k[:3] for k in ALL} - set(S2028), 'the run ahead covers exactly the open keys'
    assert all(i in TEXT for i in ids) and len(keys) == len(ALL)
    payload = {'groups': [{'id': g, 'name': GROUP_NAMES[g], 'n': len(ks), 'desc': GROUP_DESC[g]} for g, ks in GROUPS.items()], 'keys': keys, 'elections': elections, 'word': WORD}

    # what the page says in so many words, checked against the results
    by = {e['y']: e for e in elections}
    assert [e['y'] for e in elections if (e['i'] > 0.5) != e['w']] == call['misses']
    assert call['misses'] == [1952, 2000, 2016, 2024] and all(by[y]['p'] == 'D' for y in call['misses']), 'the page names the four misses and says the Democrats were in office each time'
    assert call['split'] == [2000, 2016], 'the page says the party in office won the most votes and lost the Electoral College in 2000 and 2016'
    assert call['said_lose']['right'] == call['said_lose']['n'], 'the page says every miss was a call to win'
    assert all(S2028[k[:3]][0] == 0 for k in GROUPS['D']), 'the page says party strength is 0 of 6'
    left = [v['year'] for v in raw if not v['nh_nominee_ran']]
    assert left == [1952, 1968, 2024] and all(y in left for y in (1952, 2024)), 'the page says the president left the race in 1952 and 2024 and the nominee had not run in the primaries'
    for r in rows:                                               # "an unpopular president", "a strong economy", in 1952 and 2024
        if r['year'] in (1952, 2024):
            sh = {g: [r[k] for k in ks if r[k] is not None] for g, ks in GROUPS.items()}
            assert sum(sh['C']) / len(sh['C']) < 0.5 and r['C01_approval_50'] == 0 and all(sum(sh[g]) / len(sh[g]) > 0.6 for g in 'AB'), r['year']
    tried, lich, pm = res['tried'], res['lichtman'], res['primary_model']
    t_right = [tried[k]['right'] for k in ('own_group', 'nominee', 'both', 'deal_breakers')]
    assert all(set(tried[k]['changed']) <= set(call['misses']) and tried[k]['right'] == call['right'] + len(tried[k]['changed']) for k in ('own_group', 'nominee', 'both', 'deal_breakers')), \
        'the page says each tried change altered only the calls it was meant to fix'
    assert min(t_right) > call['right']
    nr = res['without_his_ratings']
    assert sorted(nr['changed']) == sorted(y for y, _ in call['closest'][:2]), 'the page says the two closest calls flip without his ratings'
    assert all(y not in call['misses'] for y in nr['changed']) and nr['right'] == call['right'] - len(nr['changed'])
    assert len(call['close']['years']) == 4, 'the fine print says four calls were close'
    ok = res['one_key']['left_out']
    payload['rec'] = call
    sure = res['sure']                                   # how sure: the record at each level of the count
    assert [b['label'] for b in sure['bands']] == ['clear loss', 'likely loss', 'toss-up', 'lean win', 'clear win'] and all(b['n'] for b in sure['bands'])
    assert all(b['won'] == 0 for b in sure['bands'][:2]) and sure['bands'][-1]['won'] == sure['bands'][-1]['n'], 'the page says no party under one half won and every party at 70% or more did'
    mid = [b for b in sure['bands'] if 0.5 <= b['lo'] < 0.7]
    assert (sum(b['won'] for b in mid), sum(b['n'] for b in mid)) == (4, 8), 'the page says four of eight between 50% and 70%'
    assert res['verdict']['misses'] == [1952, 2024] and abs(sure['at_half'] - 50) < 1, 'the page says the vote call misses 1952 and 2024 and that one half of the keys is about half of the vote'
    assert [y for _, y in sure['largest']] == [1972, 1952]
    payload['sure'] = dict(sure, vote_right=res['verdict']['right'])
    payload['lich'] = {'office': lich['office'], 'office_since_1984': lich['office_since_1984']}
    payload['pm'] = pm
    # they: called by both of the other models and missed here; we: missed by both and called here
    payload['vs'] = {'they': [y for y in call['misses'] if y not in lich['office']['misses'] and y not in pm['misses']], 'we': res['called_but_missed_by_both']}
    assert pm['misses'] == [1960, 2000, 2020, 2024], 'the note under the table spells out the Primary Model record'
    need = 100 * 0.5 * len(GROUPS) / (len(GROUPS) - 1)          # with one group at zero, what the others must average to pass one half
    if run:
        ix, above = run['index'], run['index']['above_half']
        odds = min(((abs(above - a / b), f'{a} in {b}') for a, b in ((1, 2), (2, 5), (1, 3), (1, 4), (1, 5), (1, 6), (1, 8), (1, 10), (1, 20), (1, 50))))[1]
        assert ix['median'] < 0.5 and ix['mean'] < 0.5 and run['likely']['index'] < 0.5, 'the page says the keys would say the Republicans lose on today\'s outlook'
        assert run['groups']['D']['mean'] == 0 and run['calm']['above_half'] > above
        shares = [sum(h['share'] for h in run['hist'] if round(100 * b['lo']) <= h['lo'] < round(100 * min(b['hi'], 1))) for b in sure['bands']]
        assert abs(sum(shares) - 1) < 0.01
        payload['sure']['run'] = {'shares': [round(x, 3) for x in shares], 'vote': round(sure['line'][0] + sure['line'][1] * ix['mean'], 1)}
        tl = res['tilt']
        line = round(100 * (0.5 - tl['x']))
        assert line % 5 == 0 and tl['misses'] == [2000, 2016] and tl['changed'] == [1952, 2024], 'the page says the tilt fixes 1952 and 2024 and not 2000 or 2016'
        over = sum(h['share'] for h in run['hist'] if h['lo'] >= line)
        assert run['likely']['index'] < line / 100 and over > above, 'the page says the 2028 call is still a loss with the tilt'
        payload['tilt'] = dict(tl, line=line, over=round(over, 3))
        payload['run'] = {'mean': ix['mean'], 'median': ix['median'], 'p25': ix['p25'], 'p75': ix['p75'], 'above': above, 'odds': odds, 'runs': f"{run['runs']:,}",
                          'hist': run['hist'], 'hmax': max(b['share'] for b in run['hist']), 'groups': run['groups'], 'likely': run['likely']['index'], 'likely_for': run['likely']['in_favor'],
                          'stretches': run['stretches']['n'], 'recession': run['recession_share'], 'n_econ': len(GROUPS['A']) + len(GROUPS['B']),
                          'take': ("To finish above one half the Republicans would need most things outside Congress to break their way at once: no recession, "
                                   "approval rising through 2028 and a smooth nomination. With party strength at 0 of 6 and approval near 38%, a normal economy is not enough. "
                                   f"Without a recession the chance is about {5 * round(20 * run['calm']['above_half']):d}%; with one it is close to nil.")}
    assert len(GROUPS) == 5, 'the page says five groups, and that the other four must make up for party strength'

    # how the states stand so far this term (a reading, not a key)
    now, last = S.so_far(); ev = S.electoral_votes()[2028]
    up = [x for x in now if now[x] > 0]; down = sorted((STATE_NAME[x] for x in now if now[x] <= 0))
    when = f"{MONTH[int(last[5:7]) - 1]} {last[:4]}"
    so_far = (f"Weighted the same way over the term to date, state economies were growing through {when} in {len(up)} of the 50 states and "
              f"Washington, D.C., which together hold {sum(ev[x] for x in up):.0f} of the 538 electoral votes.")
    if 0 < len(down) <= 4:
        so_far += ' The exception' + ('s are ' if len(down) > 1 else ' is ') + (' and '.join([', '.join(down[:-1]), down[-1]]) if len(down) > 1 else down[0]) + '.'
    title = ' '.join(['-'.join(w.capitalize() for w in WORD.split('-')), 'Keys'])
    b64 = lambda name: base64.b64encode(open(os.path.join(HERE, 'fonts', name), 'rb').read()).decode()
    html = open(os.path.join(HERE, 'template.html')).read()
    for token, text in (('{{TITLE}}', title), ('{{Count}}', WORD.capitalize()), ('{{count}}', WORD), ('{{STATES_SO_FAR}}', so_far), ('{{DATE}}', BUILT),
                        ('{{NEED}}', f'{need:g}'), ('{{REST}}', str(len(ALL) - len(TAG))),
                        ('{{I1952}}', f"{100 * by[1952]['i']:.1f}"), ('{{I2024}}', f"{100 * by[2024]['i']:.1f}"),
                        ('{{RUN_DATE}}', run['as_of'] if run else ''), ('{{RUN_STRETCHES}}', str(run['stretches']['n']) if run else ''),
                        ('{{RUN_REC}}', f"{100 * run['recession_share']:.0f}" if run else ''), ('{{N_EL}}', str(len(elections))),
                        ('{{TRIED_LOW}}', str(min(t_right))), ('{{TRIED_HIGH}}', str(max(t_right))), ('{{HALF}}', str(res['halves_call']['median'])),
                        ('{{KEY_LOW}}', str(ok['min'])), ('{{KEY_HIGH}}', str(ok['max'])), ('{{NORATE}}', str(nr['right'])),
                        ('{{NORATE_FLIPS}}', ' and '.join(map(str, sorted(nr['changed'])))),
                        ('{{FONT_DISPLAY}}', b64('besley-latin-wght-normal.woff2')), ('{{FONT_TEXT}}', b64('libre-franklin-latin-wght-normal.woff2'))):
        assert token in html, token
        html = html.replace(token, text)
    assert '{{' not in html
    html = html.replace('/*DATA*/null', json.dumps(payload, separators=(',', ':')))
    os.makedirs(os.path.join(HERE, 'docs'), exist_ok=True)
    open(os.path.join(HERE, 'docs', 'index.html'), 'w').write(html)
    print('docs/index.html', len(html), 'bytes;', len(elections), 'elections;', len(keys), 'keys')


if __name__ == '__main__':
    main()
