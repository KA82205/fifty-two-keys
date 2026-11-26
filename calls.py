"""The 2028 calls: which keys can be called on real evidence, and which are still open.

THIS FILE HOLDS NO RULE OF ITS OWN. A key is scored by build.score_year, the same function that scores 1952 to 2024, run
on the figures published so far. This file decides only whether the evidence a rule needs exists yet, keeps a record of
every call, and writes the list of what each key reads and when it can be called.

A key is in one of four states:
  unresolved   the figures or the event its rule needs do not exist yet. The run-ahead gives it a chance.
  provisional  every figure its rule reads is published, and the rule has been applied to them. The figures can still be
               revised, so the call can still change. It is fixed in every run, and it is not the official call yet.
  settled      called yes or no on evidence that will not change: a fact, an election result, or, from the day the
               count is closed, the figures as they stood that day.
  held         the evidence should be there by now and is not, or two sources contradict each other. The key keeps its chance in the
               run-ahead, it is never counted as no, and the run is flagged until somebody has looked.
`final` marks a call that is closed: later revisions are written down and do not change it.

    python calls.py            writes data/key_registry.json and KEYS.md, the list of all 52
"""
import csv, datetime, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
sys.path.insert(0, HERE)
import build as B                                      # noqa: E402

ym = lambda y, m: y * 12 + (m - 1)
IDS = [k[:3] for k in B.ALL]
FULL = dict(zip(IDS, B.ALL))

# The election this file is set up for. Another election is another table like this one and nothing else.
CYCLE = {
    'year': 2028, 'party': 'R',
    'closes': '2028-08-01',        # the count is closed on the figures published by this day (approved November 25, 2026)
    'last_day': '2028-08-15',      # a figure that comes out late is used when it first appears, up to this day; after it the key is left out
    'approval_in': '2028-07-08',   # the June polls are taken as complete a week after the month ends
    # the day by which each kind of evidence should exist; after it, a key without evidence is held and the run is flagged
    'expected': {'seats': '2027-02-01', 'approval': '2028-07-15', 'monthly': '2028-07-31', 'quarterly': '2028-07-31', 'state': '2028-07-31',
                 'E03': '2028-07-15', 'E04': '2028-07-15', 'E05': '2028-07-15', 'E06': '2028-07-15', 'E07': '2028-07-15'},
}
HISTORY = os.path.join(D, 'key_calls.csv')
HEAD = ['recorded', 'key', 'status', 'value', 'final', 'basis', 'evidence']

# ---------------------------------------------------------------------------------------------------------------------
# What each key reads. One line a key: kind, sources, the comparison (left, sign, right), and whether a tie counts as yes.
FRED = 'https://fred.stlouisfed.org/series/'
SOURCES = {
    'gdp': dict(ids=['A191RL1Q225SBEA'], what='real GDP, growth on the quarter before at a yearly rate', by='Bureau of Economic Analysis', units='percent a year', every='quarter',
                out='late in the month after the quarter ends (the first estimate)', revised='in each of the next two months, and every summer'),
    'rdpi': dict(ids=['A067RL1Q156SBEA'], what='real disposable personal income, growth on the quarter before at a yearly rate', by='Bureau of Economic Analysis', units='percent a year', every='quarter',
                 out='late in the month after the quarter ends', revised='in each of the next two months, and every summer'),
    'pop': dict(ids=['B230RC0Q173SBEA'], what='population, mid-quarter', by='Bureau of Economic Analysis', units='thousands', every='quarter', out='with the GDP release', revised='every summer'),
    'u': dict(ids=['UNRATE'], what='unemployment rate', by='Bureau of Labor Statistics', units='percent', every='month', out='the first Friday of the next month', revised='each January (seasonal factors)'),
    'jobs': dict(ids=['PAYEMS'], what='payroll jobs', by='Bureau of Labor Statistics', units='thousands', every='month', out='the first Friday of the next month', revised='in each of the next two months, and each February'),
    'man': dict(ids=['MANEMP'], what='manufacturing jobs', by='Bureau of Labor Statistics', units='thousands', every='month', out='the first Friday of the next month', revised='in each of the next two months, and each February'),
    'wage': dict(ids=['CES0600000008'], what='hourly pay of production workers in goods-producing industries', by='Bureau of Labor Statistics', units='dollars an hour', every='month',
                 out='the first Friday of the next month', revised='in each of the next two months, and each February'),
    'cpi': dict(ids=['CPIAUCSL'], what='consumer price index', by='Bureau of Labor Statistics', units='index, 1982-84 = 100', every='month', out='the middle of the next month', revised='each February (seasonal factors)'),
    'ip': dict(ids=['INDPRO'], what='industrial production', by='Federal Reserve Board', units='index, 2017 = 100', every='month', out='the middle of the next month', revised='in the following months, and once a year'),
    'pce': dict(ids=['DPCERA3M086SBEA'], what='real consumer spending', by='Bureau of Economic Analysis', units='index, 2017 = 100', every='month', out='the end of the next month', revised='in the following months, and every summer'),
    'houst': dict(ids=['HOUST'], what='housing starts', by='Census Bureau', units='thousands a year', every='month', out='the third week of the next month', revised='in each of the next two months'),
    'claims': dict(ids=['ICSA'], what='new claims for unemployment insurance, averaged over the weeks of each month', by='Department of Labor', units='claims a week', every='week',
                   out='every Thursday, for the week before', revised='the week after'),
    'ics': dict(ids=['UMCSENT'], what='index of consumer sentiment', by='University of Michigan', units='index, 1966 Q1 = 100', every='month', out='the end of the month', revised='not revised'),
    'oil': dict(ids=['MCOILWTICO'], what='West Texas Intermediate crude oil, monthly average', by='Energy Information Administration', units='dollars a barrel', every='month', out='the first days of the next month', revised='not revised'),
    'sp': dict(ids=['SP500'], what='S&P 500, monthly average of daily closes', by='S&P Dow Jones Indices', units='index', every='day', out='every trading day', revised='not revised',
               licence='S&P Dow Jones Indices, through FRED: the daily closes may be read and not republished in bulk; only monthly averages are kept here'),
    'state': dict(ids=['(state)PHCI, 50 series'], what='state coincident indexes', by='Federal Reserve Bank of Philadelphia', units='index', every='month', out='about four weeks after the month ends',
                  revised='with every release', url='https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-coincident-indexes'),
    'approval': dict(ids=['api.votehub.com/polls?poll_type=approval'], what="approval of the president in polls of all adults, each pollster's own average, then the average of pollsters",
                     by='VoteHub', units='percent', every='poll', out='as polls are published; read every hour', revised='a poll can be corrected by its pollster', url='https://votehub.com/polls/',
                     licence='VoteHub poll list, used with credit'),
    'seats': dict(ids=['data/congress_seats.csv'], what='House and Senate seats by party when each Congress begins', by='Clerk of the House and the Senate Historical Office', units='seats', every='two years',
                  out='when the new Congress meets, on January 3', revised='not revised', url='https://history.house.gov/Institution/Party-Divisions/Party-Divisions/', entered=True),
    'vote': dict(ids=['build.WINNER_PCT'], what="the winner's share of all votes cast for president", by='Federal Election Commission', units='percent', every='four years',
                 out='in the weeks after the states certify', revised='not revised', url='https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/', entered=True),
    'fact': dict(ids=['data/outlook.json, settled'], what='a fact of the calendar or the Constitution', by='public record', units='yes or no', every='once', out='known in advance', revised='not revised', entered=True),
    'third': dict(ids=['api.pollresults.org/v1.0/politics/results/president'], what='national polls finished in June that name a third candidate', by='PollResults.org', units='percent', every='poll',
                  out='as polls are published; read on every run', revised='a poll can be corrected by its pollster', url='https://pollresults.org/', licence='PollResults.org, CC BY 4.0'),
    'delegates': dict(ids=['data/outlook.json, settled'], what="the nominee's share of his party's convention delegates", by='the party', units='share of delegates', every='once',
                      out='when the primaries end in June, or at the convention', revised='not revised', entered=True),
    'nh': dict(ids=['data/nh_primaries.csv'], what='the vote in each party\'s New Hampshire primary', by='New Hampshire Secretary of State', units='percent of the vote', every='four years',
               out='the days after the primary', revised='not revised', url='https://www.sos.nh.gov/elections', entered=True),
}
for _n, _s in SOURCES.items():
    _s.setdefault('url', FRED + _s['ids'][0] if _s['ids'][0].isupper() and '/' not in _s['ids'][0] and '(' not in _s['ids'][0] else '')
    _s.setdefault('licence', 'public domain (a United States government figure)' if 'Bureau' in _s['by'] or _s['by'] in ('Federal Reserve Board', 'Census Bureau', 'Department of Labor', 'Energy Information Administration', 'Federal Election Commission')
                  else 'public record' if _s.get('entered') else 'published for public use, with credit')

M, Q, T = 'a monthly figure', 'a quarterly figure', 'a comparison over the term'
RULES = {
    'A01': (Q, ['gdp'], 'growth in the second quarter of 2028', '>', 'zero'),
    'A02': (Q, ['gdp', 'pop'], 'real GDP per person in the second quarter of 2028', '>', 'the same a year earlier'),
    'A03': (M, ['ip'], 'June 2028', '>', 'June 2027'),
    'A04': (M, ['pce', 'pop'], 'real spending per person in June 2028', '>', 'June 2027'),
    'A05': (M, ['u'], 'the rate in June 2028', '<', 'June 2027'),
    'A06': (M, ['jobs'], 'June 2028', '>', 'June 2027'),
    'A07': (M, ['man'], 'June 2028', '>', 'June 2027'),
    'A08': ('a three-month average', ['claims'], 'the April to June 2028 average', '<', 'the April to June 2027 average'),
    'A09': ('a trailing average', ['u'], 'the three-month average rate in June 2028, less its lowest value in the twelve months before', '<', '0.5 points'),
    'A10': (Q, ['rdpi', 'pop'], 'real disposable income per person in the second quarter of 2028', '>', 'the same a year earlier'),
    'A11': (M, ['wage', 'cpi'], 'hourly pay divided by consumer prices, June 2028', '>', 'June 2027'),
    'A12': (M, ['cpi'], 'inflation over the twelve months to June 2028', '<', 'inflation over the twelve months to June 2027'),
    'A13': (M, ['oil', 'cpi'], 'the price of oil divided by consumer prices, June 2028', '<', 'June 2027'),
    'A14': (M, ['sp'], 'June 2028', '>', 'June 2027'),
    'A15': (M, ['sp'], 'June 2028', '>', 'December 2027'),
    'A16': (M, ['ics'], 'June 2028', '>', 'June 2027'),
    'A17': ('a three-month average', ['houst'], 'the April to June 2028 average', '>', 'the April to June 2027 average'),
    'A18': ('the state indexes', ['state'], 'the electoral votes of states whose weighted growth is above zero', '>', 'half of 538'),
    'B01': (T, ['gdp', 'pop'], 'yearly growth of real GDP per person from the start of 2025 to the second quarter of 2028', '>=', 'the average of the two terms before'),
    'B02': (T, ['ip'], 'yearly growth from January 2025 to June 2028', '>', 'yearly growth from January 2021 to January 2025'),
    'B03': (T, ['pce', 'pop'], 'yearly growth of real spending per person from January 2025 to June 2028', '>', 'the same from January 2021 to January 2025'),
    'B04': (T, ['u'], 'the rate in June 2028', '<', 'January 2025'),
    'B05': (T, ['jobs'], 'yearly growth from January 2025 to June 2028', '>', 'yearly growth from January 2021 to January 2025'),
    'B06': (T, ['man'], 'June 2028', '>', 'January 2025'),
    'B07': (T, ['claims'], 'the April to June 2028 average', '<', 'the January to March 2025 average'),
    'B08': (T, ['rdpi', 'pop'], 'yearly growth of real disposable income per person from the start of 2025 to the second quarter of 2028', '>', 'the same over 2021 to 2024'),
    'B09': (T, ['wage', 'cpi'], 'hourly pay divided by consumer prices, June 2028', '>', 'January 2025'),
    'B10': (T, ['cpi'], 'yearly inflation from January 2025 to June 2028', '<', 'yearly inflation from January 2021 to January 2025'),
    'B11': (T, ['oil', 'cpi'], 'the price of oil divided by consumer prices, June 2028', '<', 'January 2025'),
    'B12': (T, ['sp', 'cpi'], 'the S&P 500 divided by consumer prices, June 2028', '>', 'January 2025'),
    'B13': (T, ['ics'], 'June 2028', '>', 'January 2025'),
    'B14': (T, ['houst'], 'the April to June 2028 average', '>', 'the January to March 2025 average'),
    'B15': ('the state indexes', ['state'], 'the electoral votes of states whose weighted growth is above their own 2024 figure', '>', 'half of 538'),
    'C01': ('polls in a window', ['approval'], 'approval in polls finished in June 2028 (May if there are none)', '>=', '50%'),
    'C02': ('polls in a window', ['approval'], 'approval in the June 2028 polls', '>', 'disapproval in the same polls'),
    'C03': ('polls in a window', ['approval'], 'approval in the June 2028 polls', '>', 'approval in the June 2027 polls'),
    'C04': ('polls in a window', ['approval'], 'approval in the June 2028 polls', '>', 'approval in polls finished in October and November 2026'),
    'C05': ('polls in a window', ['approval'], 'approval in the June 2028 polls', '>', 'approval in the January 2028 polls (December 2027 if there are none)'),
    'C06': ('polls in a window', ['approval'], 'disapproval in the June 2028 polls', '<', '50%'),
    'D01': ('an election result', ['seats'], "the party's House seats after the 2026 midterm", '>', 'its seats after the 2022 midterm'),
    'D02': ('an election result', ['seats'], "the party's House seats in 2027", '>', "the other party's"),
    'D03': ('an election result', ['seats'], "the party's Senate seats in 2027", '>', "the other party's (a tied Senate counts as held: the vice president breaks the tie)"),
    'D04': ('an election result', ['vote'], "the party's share of all votes cast in 2024", '>', '50%'),
    'D05': ('an election result', ['seats'], "the party's House seats after the 2026 midterm", '>=', 'its seats when the term began'),
    'D06': ('an election result', ['seats'], "the party's Senate seats after the 2026 midterm", '>=', 'its seats when the term began'),
    'E01': ('a fact', ['fact'], "the party's candidate", 'is', 'the sitting president'),
    'E02': ('a fact', ['fact'], 'the party that held the White House in the term before', 'is not', 'the party that holds it now'),
    'E03': ('polls in a window', ['third'], 'the best-placed third candidate in the June 2028 polls', '<', '10%'),
    'E04': ('a nomination', ['delegates'], "the nominee's share of his party's delegates", '>=', 'two-thirds'),
    'E05': ('a primary result', ['nh'], "the party's nominee in its New Hampshire primary", 'is', 'the winner'),
    'E06': ('a primary result', ['nh'], "the nominee's share of his party's New Hampshire primary", '>', "the other party's nominee's share of his"),
    'E07': ('a primary result', ['nh'], "the other party's nominee in its New Hampshire primary", 'is not', 'the winner'),
}
WAITS = {'A': 'monthly', 'B': 'monthly', 'C': 'approval', 'D': 'seats'}       # which `expected` day applies; quarterly and state keys are told apart below
MANUAL = {
    'D': ('Nothing: the seats are counted from the public list of sitting members when a new Congress meets (facts.py).', 'None needed.'),
    'D04': ('One figure in build.py every four years, from the certified result. The 2024 figure is entered.', 'None needed before 2029.'),
    'E01': ('Nothing: the president cannot run again, which is fixed by the Constitution and was recorded when the cycle began.', 'None needed.'),
    'E02': ('None: read from the table of past elections.', 'None needed.'),
    'E04': ('Nothing: the pledged delegates of each candidate are read from The Green Papers, the preferred source for that count, and checked against Wikipedia (primaries.py). The Green Papers alone is enough; '
            'Wikipedia stands in, provisionally, only if The Green Papers cannot be read. The evidence is the pledged count at the end of the primaries, not the convention roll call. '
            'An entry in data/outlook.json is a recovery step for a case the sources cannot settle.',
            'None needed. If the sources contradict each other, or nobody holds a majority of pledged delegates by August 1, 2028, the key is left open and the count is closed without it.'),
    'E05': ('Nothing: the New Hampshire vote is read from the Secretary of State\'s own results workbooks when its site answers, then from The Green Papers, which carries the same certified figures, then from Wikipedia (primaries.py); '
            'the highest source that has the result is used. Each party\'s nominee is the one its convention\'s roll call nominated, or before that the candidate with a majority of pledged delegates. '
            'A nominee who withdraws or is replaced before the convention is followed. A line in data/nh_primaries.csv is a recovery step for a case the sources cannot settle.',
            'None needed. If the sources contradict each other, or a party has no presumptive nominee by August 1, 2028, its keys are left open and the count is closed without them.'),
}
MANUAL['E06'] = MANUAL['E07'] = MANUAL['E05']
MANUAL['E03'] = ('Nothing: scored from the June polls that name a third candidate (facts.py).', 'None needed.')


def registry():
    """One row a key: what it asks, what it reads, when it can be called, and what is still done by hand."""
    from make_page import TEXT                             # the wording on the page
    closes = datetime.date.fromisoformat(CYCLE['closes'])
    day = lambda d: f'{d:%B} {d.day}, {d.year}'
    rows = []
    for i in IDS:
        kind, src, left, sign, right = RULES[i]
        g, entered = i[0], all(SOURCES[s].get('entered') for s in src)
        mutable = g in 'ABC'
        tie = 'yes' if sign == '>=' or i == 'D03' else 'no' if sign in '<>' else 'does not arise'
        row = {
            'id': i, 'key': FULL[i], 'group': g, 'group_name': B.GROUP_NAMES[g], 'question': TEXT[i][0], 'rule': TEXT[i][1], 'rule_version': 'locked (locked_keys.csv)',
            'depends_on': kind, 'compares': left, 'sign': sign, 'with': right, 'a_tie_counts_as': tie,
            'scored_by': 'build.score_year' + (' and states.state_keys' if 'state' in src else ''),
            'sources': [{'name': s, 'series': SOURCES[s]['ids'], 'what': SOURCES[s]['what'], 'published_by': SOURCES[s]['by'], 'units': SOURCES[s]['units'], 'link': SOURCES[s]['url'],
                         'comes_out': SOURCES[s]['out'], 'revised': SOURCES[s]['revised'], 'licence': SOURCES[s]['licence']} for s in src],
            'read_through': ('https://api.stlouisfed.org/fred/series/observations (with a key), or the download link on each series page (without one)' if g in 'AB'
                             else 'https://api.votehub.com/polls' if g == 'C' else 'a file in this repository, entered by hand'),
        }
        if mutable:
            what = {'A': 'June 2028', 'B': 'June 2028', 'C': 'June 2028'}[g]
            row.update(
                window_closes='June 30, 2028',
                earliest_call=('July 8, 2028, a week after the month ends' if g == 'C' else 'when the last figure it reads for ' + what + ' is first published, in July 2028: ' + '; '.join(f"{SOURCES[s]['what']}, {SOURCES[s]['out']}" for s in src)),
                count_closes=day(closes),
                revisions=f"Until {day(closes)} the key is scored again on every run, on the figures as they then stand; a call that changes is written to the record as a correction. "
                          f"From that day the call is final. A later revision is noted beside it and does not change it.",
                called_yes=f"{left[0].upper() + left[1:]} {sign} {right}, on published figures.", called_no='The same comparison fails, on published figures.',
                stays_open='Any figure the rule reads is not published yet, or a month is missing from a series it reads. A month that has ended and is not published is not a figure.',
                checked='every hour for polls and prices; the economic series on weekday mornings, twice more each day, and on the first run of the day',
                checks=('each new figure against the range and the largest step the series has ever taken; each held figure against how far the series is revised' if g in 'AB'
                        else 'polls of all adults only, no campaign or party polls, each pollster once'),
                if_missing=f"The key stays open and keeps its chance. After {day(datetime.date.fromisoformat(CYCLE['expected']['approval' if g == 'C' else 'monthly']))} it is held and the run is flagged every day.",
                fallback=('the download link on the same series page when the API does not answer; the last figures read are kept meanwhile' if g in 'AB' else 'none: the last polls read are kept, and the run is flagged after two days'),
                automatic='yes', by_hand='nothing', remedy='none needed')
        else:
            done, remedy = MANUAL.get(i) or MANUAL[g]
            row.update(
                window_closes={'D': 'November 3, 2026 (the midterm)', 'E': 'June 30, 2028' if i == 'E03' else 'the end of the primaries' if i == 'E04' else 'the New Hampshire primary' if i > 'E04' else 'fixed'}[g],
                earliest_call={'D': 'when the result cannot change any more: here, when one party has won or lost enough seats', 'E': 'when the fact is on the public record'}[g],
                count_closes=day(closes),
                revisions='An election result, a primary result and a fact do not change. A mistake in what was entered is corrected in the open: the first entry stays in the record.',
                called_yes=f"{left[0].upper() + left[1:]} {sign} {right}.", called_no='The same statement is false.',
                stays_open='The result or the event has not happened, or it has not been entered with its source.',
                checked='on every run, from the files in this repository', checks='an entry is compared with what the rule gives wherever the rule can be scored from the files; if the two disagree the key is held',
                if_missing=f"The key stays open and keeps its chance. After {day(datetime.date.fromisoformat(CYCLE['expected'].get(i, CYCLE['expected']['seats'])))} it is held and the run is flagged every day."
                           if i not in ('D04', 'E01', 'E02') else 'Does not arise: the fact is known.',
                fallback='none', automatic='yes' if i in ('D04', 'E01', 'E02') else 'no: one entry', by_hand='nothing' if i == 'E01' else done, remedy=remedy)
            if g == 'D' and i != 'D04':
                row.update(automatic='yes', by_hand='nothing', remedy='none needed', read_through='github.com/unitedstates/congress-legislators (facts.py), in the January a new Congress meets',
                           checked='every day in January and February of an odd year, until the new Congress is on the list', fallback='a line entered by hand in data/congress_seats.csv, with its source')
            if i in ('E04', 'E05', 'E06', 'E07'):
                row.update(automatic='yes', by_hand='nothing', remedy='none needed', read_through='in order: sos.nh.gov (the New Hampshire Secretary of State\'s results workbooks), thegreenpapers.com/P28/ (pledged delegates, the conventions\' roll calls, the New Hampshire vote as certified) and the Wikipedia API (primaries.py)',
                           stays_open='The primary has not been held, the nominee is not known, the evidence is not all in, no source could be read, or two sources contradict each other. Each is reported apart; none is a no. A source that has not been updated yet is a delay and holds nothing.',
                           checked='every Monday until 2028, then on the first run of every day', checks='the highest source that has the figure is used; the others must not give the key a different answer (another winner, another nominee, a delegate count of the same kind on the other side of two-thirds). The state\'s workbooks must add up, county by county',
                           earliest_call='when one good source carries the result and the nominee is known; provisional while the nominee is presumptive, the result is not certified, or Wikipedia is the only source',
                           fallback='an entry by hand with its source, compared with what the sources give; if the two disagree the key is held')
            if i == 'E03':
                row.update(automatic='yes', by_hand='nothing', remedy='none needed', read_through='https://api.pollresults.org/v1.0/politics/results/president (facts.py)', window_closes='June 30, 2028',
                           earliest_call='July 8, 2028: polls finished in June and published by July 7',
                           stays_open='Fewer than three pollsters named a third candidate in June. A poll that names none is not counted as zero.',
                           checked='on every run', checks='only named candidates of neither party; each pollster once; undecided voters left as the poll left them',
                           fallback='none: without three pollsters the key stays open, and the count is closed without it')
        rows.append(row)
    assert len(rows) == 52 and [r['id'] for r in rows] == IDS
    return rows


def write_registry():
    rows = registry()
    json.dump({'election': CYCLE['year'], 'party_in_office': CYCLE['party'], 'count_closes': CYCLE['closes'], 'states': ['unresolved', 'provisional', 'settled', 'held'], 'keys': rows},
              open(os.path.join(D, 'key_registry.json'), 'w'), indent=1)
    cell = lambda s: str(s).replace('|', '/').replace('\n', ' ')
    L = ['# The 52 keys: what each reads, and when it can be called', '',
         'Written by `calls.py` from the rules in `build.py`. The same list, with every field, is in `data/key_registry.json`.', '',
         'A key is **unresolved** until the figures or the event its rule needs exist; **provisional** once every figure is published and the rule has been applied, while the figures can still be revised; '
         '**settled** when it is called on evidence that will not change; **held** when the evidence should be there and is not, or two sources contradict each other. A missing figure never counts as no.', '',
         f"The count is closed on **{registry()[0]['count_closes']}**, on the figures published by then. Every June figure is due before that day: jobs, unemployment and pay on the first Friday of July, "
         "prices and production by the middle of the month, second-quarter growth and income in the last week, June spending with it or a day later, the state indexes in the last days of July. "
         "A figure that comes out late is used as first published, up to August 15, 2028; a key still without evidence then stays open. Nothing is re-weighted: each group keeps all of its keys and its fifth of the count, the line stays at one half, the count is given as the lowest and highest it could be, and the keys make a call only if both fall on the same side of one half. "
         "The conventions may come after the close: the nomination keys rest on pledged delegates at the end of the primaries, not on the convention.", '']
    for g, name in B.GROUP_NAMES.items():
        L += [f'## {g}. {name}', '', '| Key | Asks | Compares | Sign | With | Tie | Reads | First possible call | By hand |', '|---|---|---|---|---|---|---|---|---|']
        for r in rows:
            if r['group'] == g:
                reads = '; '.join(f"{', '.join(s['series'])} ({s['published_by']})" for s in r['sources'])
                L.append('| ' + ' | '.join(cell(x) for x in (r['id'], r['question'], r['compares'], r['sign'], r['with'], r['a_tie_counts_as'], reads, r['earliest_call'], r['by_hand'])) + ' |')
        L.append('')
    L += ['## What is still done by hand, and what would end it', '']
    seen = set()
    for r in rows:
        if r['automatic'] != 'yes' and r['by_hand'] not in seen:
            seen.add(r['by_hand'])
            who = ', '.join(x['id'] for x in rows if x['by_hand'] == r['by_hand'])
            L += [f"**{who}.** {r['by_hand']} *What would end it:* {r['remedy']}", '']
    open(os.path.join(HERE, 'KEYS.md'), 'w').write('\n'.join(L))
    return rows


# ---------------------------------------------------------------------------------------------------------------------
def figures(P, QS, LEVEL, approval, entered, root=HERE):
    """The files build.score_year reads, with the figures published so far laid over them, for the election in CYCLE.
    P: monthly series by month number; QS: quarterly growth by quarter number; LEVEL: quarterly levels by (year, quarter);
    approval: the readings run_2028.approval() gives; entered: the settled block of data/outlook.json."""
    y = CYCLE['year']
    d = B.load()
    mo = lambda t: (t // 12, t % 12 + 1)
    for t in set(P['u']) | set(P['cpi']) | set(P['jobs']) | set(P['sp']) | set(P['ics']):
        d['monthly'][mo(t)] = {'jobs': P['jobs'].get(t), 'cpi': P['cpi'].get(t), 'ics': P['ics'].get(t), 'sp500': P['sp'].get(t), 'unemp': P['u'].get(t)}
    for name, s in (('INDPRO', 'ip'), ('DPCERA3M086SBEA', 'pce'), ('MANEMP', 'man'), ('CES0600000008', 'wage'), ('OILPRICEx', 'oil'), ('CLAIMSx', 'claims'), ('HOUST', 'houst')):
        for k in [k for k in d['md'] if k[0] == name]:
            del d['md'][k]                                 # one vintage throughout: the figures as they stand now
        for t, x in P[s].items():
            d['md'][(name,) + mo(t)] = x
    for q, x in QS.items():
        d['quarterly'][(q // 4, q % 4 + 1)] = {'g_gdp': x['gdp'], 'g_rdpi': x['rdpi']}
    for q, x in LEVEL.items():
        d['pop'][q] = x['pop']
    d['pop'].setdefault((y, 2), math.nan)                  # not published yet: every key that reads it is left open below
    polls = []
    for name, when in (('june28', (y, 6)), ('june27', (y - 1, 6)), ('jan28', (y, 1)), ('midterm', (y - 2, 10))):
        r = approval.get(name)
        if r and approval.get('in'):
            polls.append((datetime.date(when[0], when[1], 15), r['approve'], r['disapprove']))
    d['polls'] = polls
    d['hist'][y] = {'incumbent_party': CYCLE['party'], 'dem_two_party': 'nan'}
    tf = lambda k: 'T' if (entered.get(k) or {}).get('value') else 'F'
    d['lich'][y] = {'key2': tf('E04'), 'key3': tf('E01'), 'key4': tf('E03'), 'key6': 'F'}
    have = {'seats': y - 1 in d['seats'], 'nh': y in d['nh']}
    d['seats'].setdefault(y - 1, {'house_d': '0', 'house_r': '0', 'senate_d': '0', 'senate_r': '0'})
    d['nh'].setdefault(y, {'office_ran': '', 'office_share': '0', 'office_won': '0', 'office_nominee': '', 'challenger': '', 'challenger_share': '0', 'challenger_won': '0'})
    return d, have


def read_history(path=HISTORY):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def evaluate(today, P, QS, LEVEL, approval, states, entered, landed, history=(), held_series=(), root=HERE, third=None, primaries=None):
    """Every key's state on `today`. `landed`: the economy keys whose series all run through June without a gap (run_2028).
    `states`: what run_2028.state_figures() gives. Returns {id: {status, value, final, basis, evidence, why, next}}."""
    from make_page import detail
    y, closes = CYCLE['year'], datetime.date.fromisoformat(CYCLE['closes'])
    exp = {k: datetime.date.fromisoformat(v) for k, v in CYCLE['expected'].items()}
    d, have = figures(P, QS, LEVEL, approval, entered, root)
    auto = lambda i: ((primaries or {}).get('keys') or {}).get(i) if (primaries or {}).get('year') == y else None      # what primaries.py read, for this cycle
    keys, raw, _ = B.score_year(d, y)
    if states.get('keys'):
        raw.update(states['final'])
    last = {}
    for r in history:
        last[r['key']] = r
    out = {}
    for i in IDS:
        g, rule = i[0], keys[FULL[i]]
        e = entered.get(i)
        c = {'status': 'unresolved', 'value': None, 'final': False, 'basis': '', 'evidence': '', 'why': '', 'next': ''}
        if g in 'AB' and i not in ('A18', 'B15'):
            quarterly = RULES[i][1][0] in ('gdp', 'rdpi') or 'pop' in RULES[i][1]
            if i in landed and rule is not None:
                c.update(status='provisional', value=bool(rule), basis='rule', evidence=detail(i, raw))
            else:
                due = exp['quarterly' if quarterly else 'monthly']
                names = [SOURCES[s]['ids'][0] for s in RULES[i][1]]
                stuck = [n for n in names if n in held_series]
                c.update(why=('A figure it reads is held back: ' + ', '.join(stuck) + '.') if stuck else f"Its {'second-quarter' if quarterly and RULES[i][0] == Q else 'June'} 2028 figures are not published yet.",
                         next='July 2028', status='held' if stuck or today > due else 'unresolved')
        elif i in ('A18', 'B15'):
            if states.get('keys') and i in states['keys']:
                c.update(status='provisional', value=bool(states['keys'][i]), basis='rule', evidence=detail(i, raw))
            else:
                c.update(why='The state indexes do not run through June 2028 yet.', next='late July 2028', status='held' if today > exp['state'] else 'unresolved')
        elif g == 'C':
            if approval.get('in') and rule is not None:
                c.update(status='provisional', value=bool(rule), basis='rule', evidence=detail(i, raw))
            else:
                c.update(why='The June 2028 polls are not in yet.' if today < datetime.date.fromisoformat(CYCLE['approval_in']) else 'A reading the key compares is missing: no poll of all adults finished in that month.',
                         next='July 8, 2028', status='held' if today > exp['approval'] else 'unresolved')
        elif i in ('D04', 'E02'):
            c.update(status='settled', value=bool(rule), final=True, basis='rule', evidence=(e or {}).get('why') or detail(i, raw))
        elif g == 'D':
            scored = have['seats'] and rule is not None
            if e is not None and scored and bool(e['value']) != bool(rule):
                c.update(status='held', why=f"The entry says {'yes' if e['value'] else 'no'} and the seat counts say {'yes' if rule else 'no'}.", basis='entered and rule disagree')
            elif scored:
                c.update(status='settled', value=bool(rule), final=True, basis='rule', evidence=detail(i, raw) or (e or {}).get('why', ''))
            elif e is not None:
                c.update(status='settled', value=bool(e['value']), basis='entered', evidence=e.get('why', ''), next='January 2027, when the new Congress meets and its seats are counted')
            else:
                c.update(why='The midterm result is not entered.', status='held' if today > exp['seats'] else 'unresolved')
        elif i in ('E04', 'E05', 'E06', 'E07') and not (i == 'E04' and e is None and auto(i) is None):
            a = auto(i); read = a is not None and a['state'] in ('settled', 'provisional')
            by_hand = (bool(rule) if have['nh'] else bool(e['value']) if e is not None else None) if i != 'E04' else (bool(e['value']) if e is not None else None)
            if by_hand is not None and read and by_hand != bool(a['value']):
                c.update(status='held', why=f"The entry by hand says {'yes' if by_hand else 'no'} and the sources say {'yes' if a['value'] else 'no'} ({a['evidence']})", basis='entered and read disagree', reading='conflict')
            elif by_hand is not None:                      # a recovery entry, with its source
                c.update(status='settled', value=by_hand, final=True, basis='rule' if (have['nh'] and i != 'E04') else 'entered', evidence=detail(i, raw) if (have['nh'] and i != 'E04') else e.get('why', ''))
            elif read:
                c.update(status=a['state'], value=bool(a['value']), final=a['state'] == 'settled', basis='rule', evidence=a['evidence'], reading=a['state'])
            else:
                state = a['state'] if a else 'not yet'
                lead = {'not yet': 'The event has not happened. ', 'waiting': 'The evidence is not all in. ', 'conflict': 'The sources disagree. ', 'failed': 'A source could not be read. '}[state]
                c.update(why=lead + (a['why'] if a else ('The delegates are not chosen yet.' if i == 'E04' else 'The nominees are not known, so the New Hampshire result cannot be read for them yet.')), reading=state,
                         next='June 2028, when the primaries end' if i == 'E04' else 'when both nominees are known, by June 2028', status='held' if (state == 'conflict' or today > exp.get(i, closes)) else 'unresolved')
        elif i == 'E03' and e is None:                     # scored by rule on the June polls that name a third candidate (facts.py)
            june = (third or {}).get('june') or {}
            if june.get('reading') is not None and today >= datetime.date(y, 7, 8):
                top = max(june['polls'], key=lambda q: q['best_share'])
                c.update(status='provisional', value=bool(june['reading'] < 10), basis='rule',
                         evidence=f"{june['pollsters']} pollsters named a third candidate in polls finished in June {y}; the best-placed averaged {june['reading']}% (highest in one poll: {top['best']}, {top['best_share']}%).")
            else:
                few = today >= datetime.date(y, 7, 8)
                c.update(why=(f"Only {june.get('pollsters', 0)} pollsters named a third candidate in June {y}; three are needed for a reading." if few else f'The June {y} polls do not exist yet.'),
                         next=f'July 8, {y}', status='held' if today > exp.get(i, closes) else 'unresolved')
        else:                                              # E01, E04, and E03 when entered: entered, with what the entry rests on
            if e is not None:
                c.update(status='settled', value=bool(e['value']), final=True, basis='entered', evidence=e.get('why', ''))
            else:
                c.update(why={'E03': 'The June 2028 polls do not exist yet.', 'E04': 'The delegates are not chosen yet.'}.get(i, 'Not entered.'),
                         next={'E03': 'July 2028', 'E04': 'June 2028, when the primaries end'}.get(i, ''), status='held' if today > exp.get(i, closes) else 'unresolved')
        # the count is closed: what was provisional is final, on the figures of that day; what was final stays as recorded
        was = last.get(i)
        if was and was['final'] == '1' and was['value'] in ('0', '1'):
            if c['value'] is not None and int(c['value']) != int(was['value']):
                c['revised_since'] = f"On today's figures it would be {'yes' if c['value'] else 'no'} ({c['evidence']}). The call was closed on {was['recorded']} and stands."
            elif c['status'] == 'held':
                c['revised_since'] = f"{c['why']} The call was closed on {was['recorded']} and stands."
            c.update(status='settled', value=bool(int(was['value'])), final=True, basis=was['basis'], evidence=was['evidence'], why='', next='')
        elif c['status'] == 'provisional' and today >= closes:
            c.update(status='settled', final=True)
        if c['status'] == 'held' and not c['why']:
            c['why'] = 'The evidence should be there by now and is not.'
        if c['status'] == 'held' and was and was['value'] in ('0', '1'):
            c['last'] = bool(int(was['value']))            # the call it had before it was held
        out[i] = c
    return out


def record(calls, today, path=HISTORY):
    """Add a line to the record for every key whose state, call or evidence is not what its last line says. Lines are only ever added."""
    hist = read_history(path); last = {}
    for r in hist:
        last[r['key']] = r
    new = []
    for i in IDS:
        c = calls[i]
        if c['status'] == 'unresolved' and i not in last:
            continue
        row = {'recorded': str(today), 'key': i, 'status': c['status'], 'value': '' if c['value'] is None else str(int(c['value'])), 'final': str(int(c['final'])), 'basis': c['basis'],
               'evidence': c['evidence'] or c['why']}
        was = last.get(i)
        if was is None or any(was[k] != row[k] for k in ('status', 'value', 'final')) or (c['status'] == 'provisional' and was['evidence'] != row['evidence']):
            new.append(row)
    if new:
        fresh = not os.path.exists(path)
        with open(path, 'a', newline='') as f:
            w = csv.DictWriter(f, HEAD, lineterminator='\n')
            if fresh:
                w.writeheader()
            w.writerows(new)
    return new


def index(values):
    """The count, as the model makes it: the share of keys in favor in each group, the five groups counting the same."""
    return sum(sum(values[i] for i in IDS if i[0] == g) / len(ks) for g, ks in B.GROUPS.items()) / len(B.GROUPS)


if __name__ == '__main__':
    rows = write_registry()
    print(f"{len(rows)} keys listed in data/key_registry.json and KEYS.md; {sum(r['automatic'] == 'yes' for r in rows)} need nothing done by hand")
