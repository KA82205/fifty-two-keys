"""The nomination keys read from the sources, on the pages of 2016, 2020 and 2024 as they stood when sampled, and on
made-up pages for 2028. Two sources must agree or nothing is called.

    python tests/test_primaries.py
"""
import copy, datetime, gzip, json, os, re, sys, tempfile, urllib.error

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE)
import primaries as P                      # noqa: E402

FX = os.path.join(HERE, 'tests', 'fixtures', 'primaries')
WIKI = json.load(open(os.path.join(FX, 'wikipedia.json')))


def reader(wiki=None, green=None, fail=()):
    """A stand-in for the network. wiki: the API's answer; green: {(year, page): html} in place of the kept pages;
    fail: sources that do not answer."""
    def read(url):
        if 'wikipedia.org' in url:
            if 'wikipedia' in fail: raise ConnectionError('down')
            return json.dumps(wiki or WIKI)
        m = re.search(r'/P(\d\d)/(NH-)?([RD])$', url)
        if m:
            if 'green' in fail: raise ConnectionError('down')
            key = (2000 + int(m.group(1)), (m.group(2) or '') + m.group(3))
            if green is not None and key in green: return green[key]
            f = os.path.join(FX, f"green_{key[0]}_{'nh_' if m.group(2) else ''}{m.group(3)}.html.gz")
            if os.path.exists(f): return gzip.open(f, 'rt').read()
        raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
    return read


def run(year, office, day=None, **kw):
    G = P.gather(year, reader(**kw), now='2028-07-01T00:00Z'); return P.evaluate(G, office, day or datetime.date(year, 8, 1)), G


def test_the_record_of_2016_2020_and_2024():
    """What the reader gives for three past elections, against the locked table (the columns for the eventual nominee)."""
    E, G = run(2016, 'D'); k = E['keys']
    assert E['nominees']['Democratic']['name'] == 'Hillary Clinton' and E['nominees']['Republican']['name'] == 'Donald Trump'
    assert [k[i]['state'] for i in ('E04', 'E05', 'E06', 'E07')] == ['settled'] * 4, k
    assert [k[i]['value'] for i in ('E04', 'E05', 'E06', 'E07')] == [False, False, True, False], k      # 54% of pledged delegates; lost to Sanders; 38% against Trump's 35%; Trump won his
    assert '54.4%' in k['E04']['evidence'] and 'Sanders' in k['E05']['evidence']
    E, G = run(2020, 'R'); k = E['keys']
    assert [k[i]['value'] for i in ('E04', 'E05', 'E06', 'E07')] == [True, True, True, True] and all(k[i]['state'] == 'settled' for i in k), k
    assert all(s.get('url') and s.get('retrieved') for s in G['sources']) and any(s.get('revision') for s in G['sources'])
    # 2024: the nominee was replaced after the primaries. The pledged delegates were Biden's (the page carries two boxes, the
    # primaries and the convention's roll call: the first is read). Harris was on no primary ballot, so the party's nominee
    # did not win New Hampshire
    E, G = run(2024, 'D'); k = E['keys']
    assert E['nominees']['Democratic']['name'] == 'Kamala Harris' and k['E04']['state'] == 'settled' and k['E04']['value'] is True and 'Biden' in k['E04']['evidence']
    assert k['E05']['value'] is False and k['E06']['value'] is False and k['E07']['value'] is False and 'not on the Democratic ballot' in k['E05']['evidence']
    # each of the three against the locked table, in its columns for the eventual nominee
    import csv
    locked = {int(r['year']): r for r in csv.DictReader(open(os.path.join(HERE, 'keys_table.csv')))}
    for y, office in ((2016, 'D'), (2020, 'R'), (2024, 'D')):
        k = run(y, office)[0]['keys']; r = locked[y]
        assert [int(k[i]['value']) for i in ('E04', 'E05', 'E06', 'E07')] == [int(r['E04_no_contest']), int(r['E05_if_nominee']), int(r['E06_if_nominee']), int(r['E07_challenger_lost_primary'])], (y, k)


def pages_2028(nominee_r='Marco Rubio', nominee_d=None, over=True, formal=False, nh_r=(('Marco Rubio', 91000, 41.2), ('JD Vance', 84000, 38.0)), nh_d=(('Josh Shapiro', 70000, 35.0), ('Gavin Newsom', 61000, 30.5)),
               delegates_r=(('Marco Rubio', 1650), ('JD Vance', 700)), delegates_d=(('Gavin Newsom', 2300), ('Josh Shapiro', 1500))):
    """Made-up Wikipedia pages for 2028, in the layout the real ones have."""
    def boxed(name, cands, extra=''):
        rows = ''.join(f"| candidate{i} = [[{n}]]\n| color{i} =\n| delegate_count{i} = {v[0] if v[0] is not None else ''}\n| popular_vote{i} = {v[1] if len(v) > 1 else ''}\n| percentage{i} = {str(v[2]) + '%' if len(v) > 2 else ''}\n" for i, (n, *v) in enumerate(cands, 1))
        return '{{Infobox election\n| election_name = ' + name + '\n| type = primary\n| ongoing = ' + ('no' if over else 'yes') + '\n' + extra + rows + '}}'
    page = lambda title, text: {'title': title, 'revisions': [{'revid': 1500000001, 'timestamp': '2028-06-30T12:00:00Z', 'slots': {'main': {'content': text}}}]}
    el = '{{Infobox election\n| election_name = 2028 United States presidential election\n| type = presidential\n' + (f"| nominee1 = [[{nominee_r}]]\n" if formal else '| nominee1 =\n') + '| party1 = Republican Party (United States)\n' + \
         (f"| nominee2 = [[{nominee_d or delegates_d[0][0]}]]\n" if formal else '| nominee2 =\n') + '| party2 = Democratic Party (United States)\n}}'
    return {'query': {'pages': [page('2028 Republican Party presidential primaries', boxed('2028 Republican Party presidential primaries', [(n, d) for n, d in delegates_r], '| needed_votes = 1,215 delegates\n')),
                                page('2028 Democratic Party presidential primaries', boxed('2028 Democratic Party presidential primaries', [(n, d) for n, d in delegates_d], '| needed_votes = 1,900 delegates\n')),
                                page('2028 New Hampshire Republican presidential primary', boxed('NH R', [(n, None, v, s) for n, v, s in nh_r])), page('2028 New Hampshire Democratic presidential primary', boxed('NH D', [(n, None, v, s) for n, v, s in nh_d])),
                                page('2028 United States presidential election', el)]}}


def green_2028(nh_r=(('Marco Antonio Rubio', 91000, 41.2), ('James David "JD" Vance', 84000, 38.0)), nh_d=(('Joshua David "Josh" Shapiro', 70000, 35.0), ('Gavin Christopher Newsom', 61000, 30.5)), status='Official',
               delegates_r=(('Rubio, Marco Antonio', 1650), ('Vance, James David "JD"', 700), ('Uncommitted', 79)), delegates_d=(('Newsom, Gavin Christopher', 2300), ('Shapiro, Joshua David "Josh"', 1500), ('Uncommitted', 700))):
    """Made-up Green Papers pages for 2028, with that site's own habits: rows that open without a row tag, a count and its
    percentage in one cell."""
    def nh(rows):
        return f'<p>Source: New Hampshire Secretary of State.<br>Status: {status}. Retrieved: Saturday 18 March 2028.</p><table><tr><td>Candidate</td><td>Pop<br>Vote</td><td>%</td></tr>' + \
               ''.join(f'<td><a href="x">{n}</a></td><td>{v:,}</td><td>{s:.2f}%</td></tr>' for n, v, s in rows) + f'<td>Total</td><td>{sum(v for _, v, _ in rows):,}</td><td>100.00%</td></tr></table>'
    def dl(rows):
        tot = sum(v for _, v in rows)
        return '<table><tr><td>Candidate</td><td colspan=2>Delegate Votes</td></tr><tr><td></td><td>Hard Total</td><td>Floor</td></tr>' + ''.join(f'<tr><td>{n}</td><td>{v:,} {100 * v / tot:.2f}%</td><td></td></tr>' for n, v in rows) + \
               f'<tr><td>Total</td><td>{tot:,} 100.00%</td><td></td></tr></table>'
    return {(2028, 'NH-R'): nh(nh_r), (2028, 'NH-D'): nh(nh_d), (2028, 'R'): dl(delegates_r), (2028, 'D'): dl(delegates_d)}


def test_2028_as_it_could_go():
    july = datetime.date(2028, 7, 1)
    # the pages as they are in 2026: boxes with nothing in them, no Green Papers pages. Nothing has happened and nothing is called
    E, _ = run(2028, 'R', datetime.date(2026, 11, 25)); assert all(v['state'] == 'not yet' and v['value'] is None for v in E['keys'].values()), E['keys']
    # February 2028: New Hampshire has voted, nobody has a majority of delegates. The result is in; whose result counts is not known
    E, _ = run(2028, 'R', datetime.date(2028, 2, 20), wiki=pages_2028(over=False, delegates_r=(('Marco Rubio', 40), ('JD Vance', 38))), green=green_2028(delegates_r=(('Rubio, Marco Antonio', 40), ('Vance, James David "JD"', 38), ('(available)', 2351))))
    assert E['keys']['E04']['state'] == 'not yet' and E['keys']['E05']['state'] == 'waiting' and E['nominees']['Republican']['name'] is None
    # July: both parties have a candidate with a majority, the conventions have not met. Called, and provisional
    E, G = run(2028, 'R', july, wiki=pages_2028(), green=green_2028()); k = E['keys']
    assert E['nominees']['Republican'] == dict(E['nominees']['Republican'], kind='presumptive') and 'Rubio' in E['nominees']['Republican']['name'] and 'Newsom' in E['nominees']['Democratic']['name']
    assert k['E04']['state'] == 'settled' and k['E04']['value'] is True and '70.2%' in k['E04']['evidence']
    assert [k[i]['state'] for i in ('E05', 'E06', 'E07')] == ['provisional'] * 3 and [k[i]['value'] for i in ('E05', 'E06', 'E07')] == [True, True, True], k   # Rubio won with 41.2%; Newsom had 30.5% and lost to Shapiro
    assert 'presumptive' in k['E05']['evidence']
    # after the conventions the same calls are settled; and at the close of the count a provisional call stands as read
    assert all(v['state'] == 'settled' for v in run(2028, 'R', july, wiki=pages_2028(formal=True), green=green_2028())[0]['keys'].values())
    assert all(v['state'] == 'settled' for v in P.evaluate(G, 'R', datetime.date(2028, 8, 1), closes=datetime.date(2028, 8, 1))['keys'].values())
    # the nominee is replaced before the convention: the keys follow the new nominee, who lost New Hampshire
    k = run(2028, 'R', july, wiki=pages_2028(formal=True, nominee_r='JD Vance'), green=green_2028())[0]['keys']
    assert k['E05']['value'] is False and k['E06']['value'] is True and 'Vance' in k['E05']['evidence']           # 38.0% lost to Rubio, and is still above Newsom's 30.5%
    # a nominee who was not on the ballot, and a write-in who won
    g = green_2028(nh_d=(('Joshua David "Josh" Shapiro', 70000, 53.0), ('Dean Benson Phillips', 62000, 47.0)))
    k = run(2028, 'R', july, wiki=pages_2028(nh_d=(('Josh Shapiro', 70000, 53.0), ('Dean Phillips', 62000, 47.0))), green=g)[0]['keys']
    assert k['E07']['value'] is True and k['E06']['value'] is True and 'not on the Democratic ballot' in k['E07']['evidence']
    g = green_2028(nh_d=(('Gavin Christopher Newsom (write-in)', 80000, 61.0), ('Joshua David "Josh" Shapiro', 51000, 39.0)))
    k = run(2028, 'R', july, wiki=pages_2028(nh_d=(('Gavin Newsom', 80000, 61.0), ('Josh Shapiro', 51000, 39.0))), green=g)[0]['keys']
    assert k['E07']['value'] is False and k['E06']['value'] is False and 'write-in' in k['E07']['evidence']
    # a contested nomination: 58% of pledged delegates is a majority and not two-thirds
    k = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('Marco Rubio', 1400), ('JD Vance', 1000))), green=green_2028(delegates_r=(('Rubio, Marco Antonio', 1400), ('Vance, James David "JD"', 1000))))[0]['keys']
    assert k['E04']['state'] == 'settled' and k['E04']['value'] is False


def test_when_the_sources_disagree_or_fail_nothing_is_called():
    july = datetime.date(2028, 7, 1)
    # different winners of New Hampshire
    k = run(2028, 'R', july, wiki=pages_2028(nh_r=(('JD Vance', 91000, 41.2), ('Marco Rubio', 84000, 38.0))), green=green_2028())[0]['keys']
    assert k['E05']['state'] == 'conflict' and k['E05']['value'] is None and k['E06']['state'] == 'conflict' and k['E07']['state'] == 'provisional'
    # the same winner, shares three points apart
    k = run(2028, 'R', july, wiki=pages_2028(nh_r=(('Marco Rubio', 91000, 44.5), ('JD Vance', 84000, 38.0))), green=green_2028())[0]['keys']
    assert k['E05']['state'] == 'conflict' and '41.2% and 44.5%' in k['E05']['why']
    # the delegate counts on opposite sides of two-thirds, and a count that depends on how the uncommitted are treated
    k = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('Marco Rubio', 1500), ('JD Vance', 900))), green=green_2028())[0]['keys']
    assert k['E04']['state'] == 'conflict' and k['E04']['value'] is None
    k = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(delegates_r=(('Rubio, Marco Antonio', 1650), ('Vance, James David "JD"', 700), ('Uncommitted', 300))))[0]['keys']
    assert k['E04']['state'] == 'conflict' and 'uncommitted' in k['E04']['why']
    # the sources disagree on who holds the majority: no nominee, so no New Hampshire key either
    E = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('JD Vance', 1650), ('Marco Rubio', 700))), green=green_2028())[0]
    assert E['nominees']['Republican']['name'] is None and E['keys']['E05']['value'] is None and E['keys']['E04']['state'] == 'conflict'
    # one source down: waiting, with the reason; both down: a failure, and the file on disk keeps the last reading
    E = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(), fail=('green',))[0]
    assert all(v['value'] is None for v in E['keys'].values()) and E['failed'] and E['keys']['E05']['state'] in ('waiting', 'not yet')
    E = run(2028, 'R', july, fail=('green', 'wikipedia'))[0]; assert all(v['state'] == 'failed' for v in E['keys'].values())
    # results not yet certified are provisional even with a formal nominee
    k = run(2028, 'R', july, wiki=pages_2028(formal=True), green=green_2028(status='Unofficial'))[0]['keys']; assert k['E05']['state'] == 'provisional'


def test_the_file_and_the_log():
    d = tempfile.mkdtemp(); path = os.path.join(d, 'primaries.json'); july = datetime.date(2028, 7, 1)
    state, words = P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(), green=green_2028())); out = json.load(open(path))
    assert state == 'new' and 'E05 provisional (yes)' in words and out['keys']['E04']['value'] is True and len(out['sources']) >= 9 and all(s['retrieved'] for s in out['sources'])
    assert P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(), green=green_2028()))[0] == 'same' and len(open(os.path.join(d, 'primaries_log.jsonl')).readlines()) == 1
    assert P.refresh(july, 2028, 'R', path, reader(fail=('green', 'wikipedia')))[0] == 'unreachable' and json.load(open(path))['keys']['E04']['value'] is True
    assert P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(formal=True), green=green_2028()))[0] == 'new' and len(open(os.path.join(d, 'primaries_log.jsonl')).readlines()) == 2


def test_the_keys_are_called_from_the_reading():
    """The run-ahead takes the reading as it stands: provisional calls are provisional, a conflict holds the key with its
    reason, an entry by hand that disagrees with the sources holds it too, and nothing unread is ever a no."""
    import test_engine as T
    d = tempfile.mkdtemp(); path = os.path.join(d, 'primaries.json'); july = datetime.date(2028, 7, 1)
    P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(), green=green_2028())); good = open(path).read()
    put = lambda text: (lambda dst: open(os.path.join(dst, 'data', 'primaries.json'), 'w').write(text))
    pr = T.case((2028, 5), '2028-07-01', edit=put(good), runs='4000'); c = pr['calls']
    assert c['E04']['status'] == 'settled' and c['E04']['value'] is True and c['E04']['basis'] == 'rule' and [c[i]['status'] for i in ('E05', 'E06', 'E07')] == ['provisional'] * 3
    assert all(pr['keys'][i]['p'] in (0, 1) for i in ('E04', 'E05', 'E06', 'E07') if i in pr['keys']) and 'Rubio' in c['E05']['evidence']
    P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(nh_r=(('JD Vance', 91000, 41.2), ('Marco Rubio', 84000, 38.0))), green=green_2028()))
    pr = T.case((2028, 5), '2028-07-01', edit=put(open(path).read()), runs='4000'); c = pr['calls']
    assert c['E05']['status'] == 'held' and c['E05']['value'] is None and c['E05']['why'].startswith('The sources disagree.') and 0 < pr['keys']['E05']['p'] < 1 and c['E07']['status'] == 'provisional'
    def both(dst):                                      # an entry by hand that says the opposite of what the sources say
        put(good)(dst); p = os.path.join(dst, 'data', 'outlook.json'); o = json.load(open(p)); o['settled']['E04'] = {'value': 0, 'why': 'entered for the test'}; json.dump(o, open(p, 'w'))
    c = T.case((2028, 5), '2028-07-01', edit=both, runs='4000')['calls']; assert c['E04']['status'] == 'held' and 'disagree' in c['E04']['basis']
    # no reading at all, as today: open, and said to be an event that has not happened
    c = T.case((2027, 6), '2027-07-20', runs='4000')['calls']; assert c['E05']['status'] == 'unresolved' and c['E05']['why'].startswith('The event has not happened.')


def test_names_and_boxes():
    for name in ('Trump, Donald John', 'Donald John Trump', "'''[[Donald Trump]]'''", '[[Donald Trump|Trump]]'): assert P.surname(name) == 'trump', name
    assert P.surname('Joseph Robinette "Joe" Biden, Jr. (write-in)') == 'biden' and P.surname('Robert F. Kennedy, Jr. (write-in)') == 'kennedy' and P.surname('Roque "Rocky" De La Fuente Guerra') == 'guerra'
    assert not P.is_candidate('Uncommitted') and not P.is_candidate('Scatter (write-in)') and not P.is_candidate('(available)') and P.is_candidate('Vermin Supreme')
    b = P.box('{{Infobox election\n| candidate1 =\n| color1 =\n| candidate2 = [[A|B]] {{efn|x|y}}\n| ongoing = yes\n}} after')
    assert b['candidate1'] == '' and b['color1'] == '' and b['ongoing'] == 'yes' and P.plain(b['candidate2']) == 'B'


if __name__ == '__main__':
    test_the_record_of_2016_2020_and_2024(); test_2028_as_it_could_go(); test_when_the_sources_disagree_or_fail_nothing_is_called(); test_the_file_and_the_log(); test_the_keys_are_called_from_the_reading(); test_names_and_boxes()
    print('ok (the nomination keys: three past elections, 2028 as it could go, disagreement and failure)')
