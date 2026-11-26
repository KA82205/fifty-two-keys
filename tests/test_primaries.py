"""The nomination keys read from the sources, on the pages of 2016, 2020 and 2024 as they stood when sampled, and on
made-up pages for 2028; New Hampshire's own count on the pages and workbooks its site served for 2024. The highest
source that has a figure is used, and only a contradiction holds a key open.

    python tests/test_primaries.py
"""
import copy, datetime, gzip, json, os, re, sys, tempfile, urllib.error

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE)
import primaries as P                      # noqa: E402

FX = os.path.join(HERE, 'tests', 'fixtures', 'primaries')
WIKI = json.load(open(os.path.join(FX, 'wikipedia.json')))


NH_FILES = '/sites/g/files/ehbemt561/files/inline-documents/sonh/'


def reader(wiki=None, green=None, fail=(), state=None):
    """A stand-in for the network. wiki: the API's answer; green: {(year, page): html} in place of the kept pages;
    fail: sources that do not answer; state: what New Hampshire's site holds, {(year, party): 'kept'} for the pages and
    workbooks of 2024 as its site served them, or 'refuse' to turn every request away as it does to most machines."""
    def nh(url, binary):
        if state == 'refuse': raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
        m = re.search(r'/(\d{4})-(republican|democratic)-presidential-primary-election-results$', url)
        if m and (state or {}).get((int(m.group(1)), m.group(2)[0].upper())): return open(os.path.join(FX, f'nh_2024_{m.group(2)[0].upper()}_page.html')).read().replace('2024', m.group(1))
        m = re.search(r'/(\d{4})-pp-(write-ins-)?(republican|democratic)-summary_\d\.xlsx$', url)
        if m and binary and (state or {}).get((int(m.group(1)), m.group(3)[0].upper())):
            data = open(os.path.join(FX, f"nh_2024_{m.group(3)[0].upper()}_{'writeins' if m.group(2) else 'summary'}.xlsx"), 'rb').read()
            return data if m.group(1) == '2024' else redated(data, m.group(1))
        raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
    def read(url):
        if 'sos.nh.gov' in url: return nh(url, False)
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
    read.bytes = lambda url: nh(url, True)
    return read


def redated(data, year):
    """A kept workbook with its date moved to another year, for the made-up elections."""
    import io, zipfile
    src = zipfile.ZipFile(io.BytesIO(data)); out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in src.namelist(): z.writestr(n, src.read(n).replace(b'January 23, 2024', b'January 25, ' + year.encode()) if n.endswith('sharedStrings.xml') else src.read(n))
    return out.getvalue()


def run(year, office, day=None, **kw):
    now = kw.pop('now', '2028-07-03T00:00Z'); G = P.gather(year, reader(**kw), now=now); return P.evaluate(G, office, day or datetime.date(year, 8, 1)), G


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
               delegates_r=(('Rubio, Marco Antonio', 1650), ('Vance, James David "JD"', 700), ('Uncommitted', 79)), delegates_d=(('Newsom, Gavin Christopher', 2300), ('Shapiro, Joshua David "Josh"', 1500), ('Uncommitted', 700)),
               floor_r=None, floor_d=None):
    """Made-up Green Papers pages for 2028, with that site's own habits: rows that open without a row tag, a count and its
    percentage in one cell."""
    def nh(rows):
        return f'<p>Source: New Hampshire Secretary of State.<br>Status: {status}. Retrieved: Saturday 18 March 2028.</p><table><tr><td>Candidate</td><td>Pop<br>Vote</td><td>%</td></tr>' + \
               ''.join(f'<td><a href="x">{n}</a></td><td>{v:,}</td><td>{s:.2f}%</td></tr>' for n, v, s in rows) + f'<td>Total</td><td>{sum(v for _, v, _ in rows):,}</td><td>100.00%</td></tr></table>'
    def dl(rows, floor):
        """floor: the name the convention's roll call nominated, with nine votes in ten."""
        tot = sum(v for _, v in rows); rows = list(rows) + ([(floor, 0)] if floor and floor not in [n for n, _ in rows] else [])
        cell = lambda n, v: f'<td>{v:,} {100 * v / tot:.2f}%</td>' if v else '<td></td>'
        return '<table><tr><td>Candidate</td><td colspan=2>Delegate Votes</td></tr><tr><td></td><td>Hard Total</td><td>Floor</td></tr>' + ''.join(f'<tr><td>{n}</td>{cell(n, v)}{cell(n, round(0.9 * tot) if n == floor else 0)}</tr>' for n, v in rows) + \
               f'<tr><td>Total</td><td>{tot:,} 100.00%</td><td>{tot if floor else ""}</td></tr></table>'
    return {(2028, 'NH-R'): nh(nh_r), (2028, 'NH-D'): nh(nh_d), (2028, 'R'): dl(delegates_r, floor_r), (2028, 'D'): dl(delegates_d, floor_d)}


HELD = dict(floor_r='Rubio, Marco Antonio', floor_d='Newsom, Gavin Christopher')       # both conventions have met


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
    # after the conventions the same calls are settled: the roll call is the record, whether or not Wikipedia has caught up.
    # And at the close of the count a provisional call stands as read
    assert all(v['state'] == 'settled' for v in run(2028, 'R', july, wiki=pages_2028(formal=True), green=green_2028(**HELD))[0]['keys'].values())
    E2 = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(**HELD))[0]; assert all(v['state'] == 'settled' for v in E2['keys'].values()) and E2['nominees']['Republican']['kind'] == 'formal' and 'not filled in yet' in E2['nominees']['Republican']['why']
    assert all(v['state'] == 'settled' for v in P.evaluate(G, 'R', datetime.date(2028, 8, 1), closes=datetime.date(2028, 8, 1))['keys'].values())
    # the nominee is replaced before the convention. While The Green Papers' majority and Wikipedia's box name different people
    # the New Hampshire keys wait; once the roll call names the new nominee they follow him, and he lost New Hampshire
    E3 = run(2028, 'R', july, wiki=pages_2028(formal=True, nominee_r='JD Vance'), green=green_2028())[0]; k = E3['keys']
    assert k['E05']['state'] == 'conflict' and k['E05']['value'] is None and 'roll call will say which' in k['E05']['why'] and E3['nominees']['Republican']['name'] is None and k['E04']['state'] == 'settled'
    k = run(2028, 'R', july, wiki=pages_2028(formal=True, nominee_r='JD Vance'), green=green_2028(floor_r='Vance, James David "JD"', floor_d='Newsom, Gavin Christopher'))[0]['keys']
    assert k['E05']['state'] == 'settled' and k['E05']['value'] is False and k['E06']['value'] is True and 'Vance' in k['E05']['evidence']           # 38.0% lost to Rubio, and is still above Newsom's 30.5%
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


def test_one_good_source_is_enough_and_a_delay_is_not_a_disagreement():
    july = datetime.date(2028, 7, 1); empty = pages_2028(nh_r=(), nh_d=(), delegates_r=(), delegates_d=())
    # Wikipedia has not been updated at all: everything is called from The Green Papers, and says so
    E, G = run(2028, 'R', july, wiki=empty, green=green_2028()); k = E['keys']
    assert k['E04']['state'] == 'settled' and k['E04']['value'] is True and 'no delegate count yet' in k['E04']['evidence']
    assert [k[i]['state'] for i in ('E05', 'E06', 'E07')] == ['provisional'] * 3 and [k[i]['value'] for i in ('E05', 'E06', 'E07')] == [True, True, True] and "The Green Papers' count" in k['E05']['evidence']
    assert all(v['state'] == 'settled' for v in run(2028, 'R', july, wiki=empty, green=green_2028(**HELD))[0]['keys'].values())
    # the same winner with shares three points apart is the same result counted another way: called, with the difference written down
    k = run(2028, 'R', july, wiki=pages_2028(nh_r=(('Marco Rubio', 91000, 44.5), ('JD Vance', 84000, 38.0))), green=green_2028())[0]['keys']
    assert k['E05']['state'] == 'provisional' and k['E05']['value'] is True and '44.5%' in k['E05']['evidence'] and 'another total' in k['E05']['evidence']
    # Wikipedia's box shows the roll call where The Green Papers has the pledged count: 58% pledged is not two-thirds, whatever the floor vote was
    g = green_2028(delegates_r=(('Rubio, Marco Antonio', 1400), ('Vance, James David "JD"', 1000)), **HELD)
    k = run(2028, 'R', july, wiki=pages_2028(formal=True, delegates_r=(('Marco Rubio', 2160), ('JD Vance', 240))), green=g)[0]['keys']
    assert k['E04']['state'] == 'settled' and k['E04']['value'] is False and 'roll call' in k['E04']['evidence']
    # Wikipedia's box lists only the leader: the same 1,400 delegates look like 100%. Not a disagreement
    k = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('Marco Rubio', 1400),)), green=green_2028(delegates_r=(('Rubio, Marco Antonio', 1400), ('Vance, James David "JD"', 1000))))[0]['keys']
    assert k['E04']['state'] == 'settled' and k['E04']['value'] is False and 'lists fewer' in k['E04']['evidence']
    # The Green Papers cannot be read. Wikipedia alone gives a provisional call, if its page has stood a day; never a settled one
    # before the count closes, and not a delegate share within five points of two-thirds
    E = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(), fail=('green',))[0]; k = E['keys']
    assert E['failed'] and k['E05']['state'] == 'provisional' and k['E05']['value'] is True and 'alone' in k['E05']['evidence'] and E['nominees']['Republican']['kind'] == 'presumptive'
    assert k['E04']['state'] == 'waiting' and k['E04']['value'] is None and 'too near two-thirds' in k['E04']['why']
    k = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('Marco Rubio', 2100), ('JD Vance', 300))), green=green_2028(), fail=('green',))[0]['keys']; assert k['E04']['state'] == 'provisional' and k['E04']['value'] is True
    E = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(), fail=('green',), now='2028-06-30T20:00Z')[0]          # the pages were edited eight hours before
    assert all(v['value'] is None for v in E['keys'].values()) and E['keys']['E05']['state'] == 'waiting'


def test_a_contradiction_holds_the_key_and_a_failure_is_a_failure():
    july = datetime.date(2028, 7, 1)
    # different winners of New Hampshire in the two sources that have it
    k = run(2028, 'R', july, wiki=pages_2028(nh_r=(('JD Vance', 91000, 41.2), ('Marco Rubio', 84000, 38.0))), green=green_2028())[0]['keys']
    assert k['E05']['state'] == 'conflict' and k['E05']['value'] is None and k['E06']['state'] == 'conflict' and k['E07']['state'] == 'provisional' and 'different winners' in k['E05']['why']
    # delegate counts of the same kind on opposite sides of two-thirds, and a count that depends on how the uncommitted are treated
    k = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('Marco Rubio', 1500), ('JD Vance', 900))), green=green_2028())[0]['keys']
    assert k['E04']['state'] == 'conflict' and k['E04']['value'] is None
    k = run(2028, 'R', july, wiki=pages_2028(), green=green_2028(delegates_r=(('Rubio, Marco Antonio', 1650), ('Vance, James David "JD"', 700), ('Uncommitted', 300))))[0]['keys']
    assert k['E04']['state'] == 'conflict' and 'uncommitted' in k['E04']['why']
    # the sources disagree on who holds the majority: no nominee, so no New Hampshire key either
    E = run(2028, 'R', july, wiki=pages_2028(delegates_r=(('JD Vance', 1650), ('Marco Rubio', 700))), green=green_2028())[0]
    assert E['nominees']['Republican']['name'] is None and E['keys']['E05']['value'] is None and E['keys']['E05']['state'] == 'conflict' and E['keys']['E04']['state'] == 'conflict'
    # the roll call names one nominee and Wikipedia's box another: held, and said
    E = run(2028, 'R', july, wiki=pages_2028(formal=True, nominee_r='JD Vance'), green=green_2028(**HELD))[0]
    assert E['keys']['E05']['state'] == 'conflict' and "roll call nominated Marco Antonio Rubio" in E['keys']['E05']['why']
    # no source at all: a failure, and the file on disk keeps the last reading
    E = run(2028, 'R', july, fail=('green', 'wikipedia'))[0]; assert all(v['state'] == 'failed' for v in E['keys'].values())
    # results not yet certified are provisional even with a formal nominee
    k = run(2028, 'R', july, wiki=pages_2028(formal=True), green=green_2028(status='Unofficial', **HELD))[0]['keys']; assert k['E05']['state'] == 'provisional' and 'not yet certified' in k['E05']['evidence']


def test_new_hampshires_own_count():
    """The Secretary of State's pages and workbooks for 2024, as its site served them (the Democratic workbooks are its own
    sheet and strings, zipped again). The count is found, checked against itself, and outranks the other two."""
    both = {(2024, 'R'): 'kept', (2024, 'D'): 'kept'}; G = P.gather(2024, reader(state=both), now='2028-07-03T00:00Z'); o = G['official']
    assert o['R']['winner'] == 'trump' and o['R']['votes']['trump']['votes'] == 176391 and o['R']['votes']['haley']['votes'] == 140491 and o['R']['total'] == 324731 and o['R']['votes']['biden']['write_in']
    assert o['D']['winner'] == 'biden' and o['D']['votes']['biden'] == {'name': 'Joseph Biden', 'votes': 79100, 'share': 63.79, 'write_in': True} and o['D']['votes']['phillips']['votes'] == 24377 + 0 and o['D']['total'] == 123996
    assert abs(o['R']['votes']['trump']['share'] - G['green'][('nh', 'R')]['votes']['trump']['share']) < 0.1 and len(o['R']['files']) == 2 and any(s['source'] == 'New Hampshire Secretary of State' for s in G['sources'])
    k = P.evaluate(G, 'D', datetime.date(2024, 8, 1))['keys']
    assert [k[i]['value'] for i in ('E04', 'E05', 'E06', 'E07')] == [True, False, False, False] and "Secretary of State's count; The Green Papers and Wikipedia agree" in k['E07']['evidence'] and 'write-in' in k['E05']['evidence']
    # the site turns the request away, as it does to most machines: that is said, nothing fails, and the next source is used
    E, G = run(2024, 'D', state='refuse'); assert not G['official'] and not E['failed'] and len(E['notes']) == 2 and 'turned the request' in E['notes'][0] and all(v['state'] == 'settled' for v in E['keys'].values())
    # 2028, made up around the same workbooks: the state's count has Trump over Haley. The Green Papers says Haley won. One source
    # against the state's own count does not hold the key; two sources agreeing against it do, since its file may have been misread
    def scene(nh_wiki):
        g = green_2028(nh_r=(('Nimarata "Nikki" Haley', 150000, 50.1), ('Donald John Trump', 149000, 49.9)), nh_d=(('Dean Benson Phillips', 24377, 19.7), ('Joseph Robinette "Joe" Biden, Jr. (write-in)', 79100, 63.8)),
                       delegates_r=(('Trump, Donald John', 1650), ('Haley, Nimarata "Nikki"', 700)), delegates_d=(('Phillips, Dean Benson', 2300), ('Williamson, Marianne', 1500)), floor_r='Trump, Donald John', floor_d='Phillips, Dean Benson')
        w = pages_2028(nh_r=nh_wiki, nh_d=(), delegates_r=(), delegates_d=())
        return run(2028, 'R', datetime.date(2028, 7, 1), wiki=w, green=g, state={(2028, 'R'): 'kept', (2028, 'D'): 'kept'})
    E, G = scene(()); k = E['keys']
    assert k['E05']['state'] == 'settled' and k['E05']['value'] is True and "the Secretary of State's count is used" in k['E05']['evidence'] and k['E07']['value'] is True and k['E06']['value'] is True      # Trump 54.3% and won; Phillips 19.7% and lost to a write-in
    k = scene((('Nikki Haley', 150000, 50.1), ('Donald Trump', 149000, 49.9)))[0]['keys']; assert k['E05']['state'] == 'conflict' and k['E05']['value'] is None and k['E07']['state'] == 'settled'
    # a workbook that does not add up, or is another party's, or is not a workbook, is not used
    rows = P.sheet_rows(open(os.path.join(FX, 'nh_2024_R_summary.xlsx'), 'rb').read()); assert P.nh_workbook(rows, 'R', 2024, False)['Trump, Donald J. (r)'] == 176391
    bad = copy.deepcopy(rows); bad[2][8] = '7640'
    for args in ((bad, 'R', 2024, False), (rows, 'D', 2024, False), (rows, 'R', 2028, False), (rows, 'R', 2024, True), (rows[:9], 'R', 2024, False)):
        try: P.nh_workbook(*args)
        except ValueError: continue
        raise AssertionError('a workbook that should be refused was read')
    for junk in (b'\xd0\xcf\x11\xe0 an old .xls file', b'<html>not found</html>'):
        try: P.sheet_rows(junk)
        except ValueError: continue
        raise AssertionError('something that is not a workbook was read')
    # the page is not at its usual address: it is found by following the site's own links
    page = open(os.path.join(FX, 'nh_2024_R_page.html')).read().replace('2024', '2028'); site = {'/elections': '<a href="/2028-election-results">2028 Election Results</a>', '/2028-election-results': '<a href="/2028-presidential-primary">2028 Presidential Primary Election Results</a>',
                                                                          '/2028-presidential-primary': '<a href="/pp28-gop">2028 Republican Presidential Primary Election Results</a>', '/pp28-gop': page}
    def read(url):
        if url[len(P.NH_HOME):] in site: return site[url[len(P.NH_HOME):]]
        raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
    assert P.nh_find(2028, 'R', read)[0] == P.NH_HOME + '/pp28-gop' and P.nh_find(2028, 'D', read) is None and P.nh_find(2032, 'R', read) is None


def test_the_file_and_the_log():
    d = tempfile.mkdtemp(); path = os.path.join(d, 'primaries.json'); july = datetime.date(2028, 7, 1)
    state, words = P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(), green=green_2028())); out = json.load(open(path))
    assert state == 'new' and 'E05 provisional (yes)' in words and out['keys']['E04']['value'] is True and len(out['sources']) >= 9 and all(s['retrieved'] for s in out['sources']) and 'highest source' in out['rule']
    assert P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(), green=green_2028()))[0] == 'same' and len(open(os.path.join(d, 'primaries_log.jsonl')).readlines()) == 1
    assert P.refresh(july, 2028, 'R', path, reader(fail=('green', 'wikipedia')))[0] == 'unreachable' and json.load(open(path))['keys']['E04']['value'] is True
    assert P.refresh(july, 2028, 'R', path, reader(wiki=pages_2028(formal=True), green=green_2028(**HELD)))[0] == 'new' and len(open(os.path.join(d, 'primaries_log.jsonl')).readlines()) == 2
    # the state's count, once read, is kept: on a day its site turns the request away the reading is the same
    path = os.path.join(tempfile.mkdtemp(), 'primaries.json'); monday = datetime.date(2024, 7, 29); both = {(2024, 'R'): 'kept', (2024, 'D'): 'kept'}
    assert P.refresh(monday, 2024, 'D', path, reader(state=both))[0] == 'new'; out = json.load(open(path)); assert out['official']['R']['votes']['trump']['votes'] == 176391 and "Secretary of State's count" in out['keys']['E07']['evidence']
    assert P.refresh(monday, 2024, 'D', path, reader(state='refuse'))[0] == 'same'; out = json.load(open(path)); assert out['official']['D']['winner'] == 'biden' and 'read from it earlier is used' in out['notes'][0]
    asked = []; quiet = reader(state='refuse'); quiet_read = lambda url: (asked.append(url), quiet(url))[1]; quiet_read.bytes = quiet.bytes
    assert P.refresh(monday + datetime.timedelta(days=1), 2024, 'D', path, quiet_read)[0] == 'same' and not any('sos.nh.gov' in u for u in asked) and not json.load(open(path))['notes']      # not asked again until Monday


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
    test_the_record_of_2016_2020_and_2024(); test_2028_as_it_could_go(); test_one_good_source_is_enough_and_a_delay_is_not_a_disagreement(); test_a_contradiction_holds_the_key_and_a_failure_is_a_failure(); test_new_hampshires_own_count()
    test_the_file_and_the_log(); test_the_keys_are_called_from_the_reading(); test_names_and_boxes()
    print("ok (the nomination keys: three past elections, 2028 as it could go, one source enough, delay against contradiction, New Hampshire's own count)")
