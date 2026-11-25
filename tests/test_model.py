"""The official model is locked. These checks fail if any key, any election's count or any call differs from the locked copy,
or if a missing figure has turned into an answer.

    python tests/test_model.py
"""
import csv, os, sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, HERE)
from build import GROUPS, ALL, build      # noqa: E402
from test import TOOK_OFFICE              # noqa: E402


def cell(v):
    return '' if v is None else str(int(v))


def test_every_key_matches_the_locked_table():
    rows, _, _ = build()
    locked = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'locked_keys.csv')))}
    assert sorted(locked) == [r['year'] for r in rows] and len(rows) == 19
    wrong = [(r['year'], k) for r in rows for k in ALL if cell(r[k]) != locked[r['year']][k]]
    assert not wrong, f'{len(wrong)} entries differ from the locked table, first {wrong[:5]}'
    assert len(ALL) == 52 and [len(v) for v in GROUPS.values()] == [18, 15, 6, 6, 7]


def test_missing_stays_missing():
    """A key whose figures do not exist for an election is left out of that election's count. It is never scored as no."""
    rows, _, _ = build()
    locked = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'locked_keys.csv')))}
    blanks = [(r['year'], k) for r in rows for k in ALL if r[k] is None]
    assert len(blanks) == sum(1 for y in locked for k in ALL if locked[y][k] == '') > 0
    assert all(r[k] in (None, 0, 1, True, False) for r in rows for k in ALL)
    by = {r['year']: r for r in rows}
    assert by[1952]['A04_spending_pc_up_year'] is None, 'monthly spending starts in 1959: the key has no answer for 1952'


def test_the_count_and_the_call():
    rows, _, _ = build()
    index = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'locked_index.csv')))}
    misses = []
    for r in rows:
        shares = []
        for ks in GROUPS.values():
            vals = [r[k] for k in ks if r[k] is not None]
            assert vals, 'a group with no answers would have no share'
            shares.append(sum(vals) / len(vals))
        ix = sum(shares) / len(shares)
        assert abs(ix - float(index[r['year']]['index'])) < 5e-4, (r['year'], ix, index[r['year']]['index'])
        if (ix > 0.5) != bool(TOOK_OFFICE[r['year']]):
            misses.append(r['year'])
    assert misses == [1952, 2000, 2016, 2024], misses


if __name__ == '__main__':
    test_every_key_matches_the_locked_table(); test_missing_stays_missing(); test_the_count_and_the_call()
    print('ok (the locked model: 52 keys, 19 elections, 15 called)')
