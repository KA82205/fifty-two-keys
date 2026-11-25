"""Seats in Congress and third candidates, read by rule from made-up copies of their sources.

    python tests/test_facts.py

The lists here are built in the layout of the real ones (the list of sitting members kept at
github.com/unitedstates/congress-legislators, and PollResults.org's list of presidential polls). Nothing here touches the
repository's own files, and nothing here says who will hold a seat or stand as a third candidate.
"""
import csv, datetime, json, os, shutil, sys, tempfile

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import facts as X, calls as C                           # noqa: E402
from test_engine import case, rerun                     # noqa: E402

D = datetime.date


def members(house_d, house_r, senate_d, senate_r, year, fresh=None, ind_with_d=0):
    """A list of sitting members: the House all newly sworn in January of `year` (or only `fresh` of them)."""
    states = sorted(X.STATES); out = []; fresh = house_d + house_r if fresh is None else fresh
    for i in range(house_d + house_r):
        out.append({'terms': [{'type': 'rep', 'state': states[i % 50], 'party': 'Democrat' if i < house_d else 'Republican', 'start': f'{year}-01-03' if i < fresh else f'{year - 2}-01-03'}]})
    for i in range(senate_d + senate_r):
        t = {'type': 'sen', 'state': states[i % 50], 'party': 'Democrat' if i < senate_d else 'Republican', 'start': f'{year - 2}-01-03'}
        if i < ind_with_d: t.update(party='Independent', caucus='Democrat')
        out.append({'terms': [t]})
    out += [{'terms': [{'type': 'rep', 'state': s, 'party': 'Democrat', 'start': f'{year}-01-03'}]} for s in ('DC', 'PR', 'GU')]      # delegates do not vote and are not counted
    return out


def test_seats_are_counted_once_the_new_congress_is_on_the_list():
    path = os.path.join(tempfile.mkdtemp(), 'seats.csv'); shutil.copy(os.path.join(HERE, 'data', 'congress_seats.csv'), path)
    n = len(open(path).readlines())
    assert X.refresh_seats(D(2026, 12, 20), path, lambda: members(257, 178, 56, 44, 2027))[0] == 'same'             # not yet January
    assert X.refresh_seats(D(2027, 1, 4), path, lambda: members(257, 178, 56, 44, 2027, fresh=300))[0] == 'early' and len(open(path).readlines()) == n      # the list is half updated: not counted
    def down(): raise TimeoutError('timed out')
    assert X.refresh_seats(D(2027, 1, 5), path, down)[0] == 'unreachable' and len(open(path).readlines()) == n
    state, words = X.refresh_seats(D(2027, 1, 6), path, lambda: members(257, 178, 56, 44, 2027, ind_with_d=2))
    row = list(csv.DictReader(open(path)))[-1]
    assert state == 'new' and (row['congress'], row['start_year'], row['house_d'], row['house_r'], row['senate_d'], row['senate_r']) == ('120', '2027', '257', '178', '56', '44'), row
    assert 'congress-legislators' in row['note'] and X.refresh_seats(D(2027, 1, 7), path, lambda: members(250, 185, 56, 44, 2027))[0] == 'same', 'a line once written is not written again'
    assert X.seats(members(215, 220, 47, 53, 2025, ind_with_d=2), 2025) == {'house_d': 215, 'house_r': 220, 'senate_d': 47, 'senate_r': 53, 'house_new': 435}


def poll(pollster, end, *questions, made=None, state='US', pid=None):
    q = [{'stage': 'general', 'answers': [{'party': p, 'pct': v, 'candidateName': n} for p, n, v in ans]} for ans in questions]
    f = lambda d: f'{d.month}/{d.day}/{d.year % 100}'
    return {'pollId': pid or f'{pollster}-{end}', 'pollster': pollster, 'endDate': f(end), 'createdAt': f(made or end) + ' 10:00', 'state': state, 'cycle': '2028', 'url': 'https://example.org/p', 'questions': q}


TWO = [('DEM', 'A Democrat', 45), ('REP', 'A Republican', 44), ('NONE', "Don't know", 11)]
def three(v, name='A Third', party='IND'): return [('DEM', 'A Democrat', 41), ('REP', 'A Republican', 40), (party, name, v), ('NONE', 'Someone else', 15)]


def test_the_third_candidate_reading():
    lo, hi, by = D(2028, 6, 1), D(2028, 6, 30), D(2028, 7, 7)
    polls = [poll('One', D(2028, 6, 10), three(8), three(12), TWO),                 # two pairings in one poll count once: 10
             poll('One', D(2028, 6, 24), three(6)),                                 # the same pollster again: its mean is 8
             poll('Two', D(2028, 6, 15), three(9, 'B. Third', 'OTH')), poll('Three', D(2028, 6, 20), three(13)),
             poll('Four', D(2028, 6, 18), TWO),                                     # names no third candidate: says nothing, and is not a zero
             poll('Five', D(2028, 6, 19), three(30, 'Generic candidate')), poll('Six', D(2028, 6, 19), [('DEM', 'A', 40), ('REP', 'B', 40), ('NONE', 'Someone else', 20)]),      # not candidates
             poll('Seven', D(2028, 5, 30), three(25)), poll('Eight', D(2028, 6, 28), three(25), made=D(2028, 7, 9)),      # out of the window; published after the cutoff
             poll('Nine', D(2028, 6, 12), three(25), state='PA')]                   # a poll of one state
    r = X.third_reading(polls, lo, hi, by)
    assert r['pollsters'] == 3 and r['reading'] == 10.0 and len(r['polls']) == 4, r
    assert X.third_reading(polls + [dict(polls[2])], lo, hi, by)['reading'] == 10.0, 'the same poll listed twice counts once'
    few = X.third_reading(polls[:3], lo, hi, by); assert few['pollsters'] == 2 and few['reading'] is None, 'two pollsters are not a reading'
    assert X.third_in({'answers': [{'party': 'IND', 'pct': 9, 'candidateName': 'A Third'}, {'party': 'LIB', 'pct': 12.5, 'candidateName': 'A Fourth'}]}) == ('A Fourth', 12.5)
    assert X.third_reading(polls, lo, hi, by)['reading'] >= 10                      # exactly 10 is not under 10: the key would be no


def test_the_third_candidate_key_is_called_from_the_june_polls_and_only_from_them():
    under = [poll(n, D(2028, 6, 10 + i), three(v)) for i, (n, v) in enumerate((('One', 4), ('Two', 6), ('Three', 5)))]
    over = [poll(n, D(2028, 6, 10 + i), three(v)) for i, (n, v) in enumerate((('One', 14), ('Two', 11), ('Three', 12)))]
    def read_as(polls, day):
        return lambda dst: X.refresh_third(day, os.path.join(dst, 'data', 'third_candidates.json'), lambda: polls)
    pr, dst = case((2028, 5), '2028-06-25', keep=True, runs='3000', edit=read_as(under, D(2028, 6, 25)))
    assert pr['calls']['E03']['status'] == 'unresolved' and 0 < pr['keys']['E03']['p'] < 1, 'June is not over: a reading so far moves the chance and calls nothing'
    assert pr['keys']['E03']['p'] > pr['third_candidates']['odds_entered'] - 0.2
    shutil.rmtree(os.path.dirname(dst))
    for polls, want in ((under, True), (over, False)):
        pr = case((2028, 6), '2028-07-20', runs='3000', edit=read_as(polls, D(2028, 7, 20)))
        c = pr['calls']['E03']; assert c['status'] == 'provisional' and c['value'] is want and c['basis'] == 'rule' and 'pollsters named a third candidate' in c['evidence'], c
    pr = case((2028, 6), '2028-07-20', runs='3000', edit=read_as(under[:2], D(2028, 7, 20)))
    assert pr['calls']['E03']['status'] in ('unresolved', 'held') and pr['calls']['E03']['value'] is None and 'three are needed' in pr['calls']['E03']['why'], 'too few pollsters: open, never no'
    pr = case((2028, 6), '2028-08-20', runs='3000', edit=read_as(under[:2], D(2028, 8, 20)))
    assert pr['observed'] and pr['observed']['final'] and 'E03' in pr['observed']['left_out'] and 0 <= pr['observed']['index'] <= 1, 'after the last day the count stands on the keys that could be scored'


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
