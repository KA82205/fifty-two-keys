"""The four nomination keys, read and not typed: who the nominees are, the delegates they won, and New Hampshire.

    E04  the party in office: the candidate with a majority of its pledged delegates won two-thirds of them or more
    E05  the party in office: its nominee won its New Hampshire primary
    E06  its nominee's share of that primary was larger than the other party's nominee's share of his
    E07  the other party's nominee lost its New Hampshire primary

The rules are the keys' own (KEYS.md) and are not touched here. This file only finds the evidence.

Where it looks, in order of authority. Nothing is typed in: every address is made from the election year or found by
following the site's own links.
    1  The official record.
       New Hampshire   the Secretary of State's results page for each party's presidential primary (sos.nh.gov), found at
                       its usual address or by following the site's links from "Elections" to the year, to the presidential
                       primary, to the party. Its two "Summary By Counties" workbooks are read, the names on the ballot and
                       the write-ins, and added together. Each workbook is checked against itself: ten counties in every
                       block, and every column of counties adding up to its "TOTALS". A reading is kept once made, because
                       the state's site turns away most requests from where this runs
       The parties     the conventions' roll calls. Neither party publishes one in a form a program can find ahead of
                       time, so the roll call is read as The Green Papers records it (the "Floor" column of each party's page)
    2  The Green Papers (thegreenpapers.com/P28/R, /D, /NH-R, /NH-D): the preferred source for pledged delegates, its
       "hard" count, which is the count of delegates pledged by the primaries and caucuses. Its New Hampshire pages
       carry the Secretary of State's figures and are marked "Official" once those are certified
    3  Wikipedia, as a check and as the fallback: the election boxes of "2028 Republican Party presidential primaries",
       "2028 New Hampshire Republican presidential primary", the same for the Democrats, and "2028 United States
       presidential election", through the MediaWiki API in one request, with the revision of each page kept. Text is
       used under CC BY-SA 4.0, with the page and revision named. Alone, it supports a provisional call only, and only
       when the page has stood unchanged for a day

One good source is enough. A key is called from the highest source that has the figure. What the sources below it say
is then sorted into three kinds, and only the last holds a key open:
    not there yet      a source with no figure has not been updated. That is a delay, not a disagreement
    counted another    the same result on another footing: shares that differ because of what is in the total, a box
    way                that lists only the leading candidates, a delegate figure that is the convention's roll call or
                       includes unpledged delegates. Written down with the evidence; the answer does not change
    a contradiction    two sources that both have the result give the key different answers: different winners, different
                       nominees, delegate counts of the same kind on opposite sides of two-thirds. The Secretary of
                       State's own count settles a contradiction about New Hampshire, unless both other sources agree
                       against the reading of it, which more likely means its file was misread. Anything else stays
                       open, with the reason, and the next run looks again

    the nominee        the candidate the convention's roll call nominated (formal). Before the roll call, the candidate
                       with a majority of all pledged delegates in The Green Papers: the presumptive nominee, and a call
                       that rests on one is provisional. If Wikipedia's box for the election names somebody else (a
                       nominee who withdrew, or was replaced), the New Hampshire keys wait for the roll call. This is
                       how a nominee replaced before the convention is followed. One replaced after it would leave the
                       keys open, to be settled by hand
    write-ins          counted with the candidate's other votes: a candidate who wins as a write-in has won
    not on the ballot  a nominee with no line in a primary got none of its vote and did not win it
    pledged delegates  the hard count of each candidate. "Uncommitted" and "available" delegates are not a candidate's. If
                       counting the uncommitted among the pledged would change the side of two-thirds, the key is left open

What each key can be: not yet (the event has not happened), waiting (it has, and the evidence is not all in), provisional,
settled, in conflict (a contradiction as above), or a source failed. data/primaries.json holds the latest reading with
every source's address, revision and retrieval time, and the official record once read; data/primaries_log.jsonl gains a
line whenever a reading changes.

    python primaries.py            read the sources for the current cycle and print what they give, changing nothing
"""
import datetime, html, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
AGENT = {'User-Agent': 'Mozilla/5.0 (compatible; fifty-two-keys/1.0; +https://github.com/KA82205/fifty-two-keys)'}
WIKI = 'https://en.wikipedia.org/w/api.php'
GREEN = 'https://www.thegreenpapers.com/P{yy}/{page}'
NH_HOME = 'https://www.sos.nh.gov'
NH_STATE = NH_HOME + '/{year}-{party}-presidential-primary-election-results'
PARTY = {'R': 'Republican', 'D': 'Democratic'}
NOT_A_CANDIDATE = ('uncommitted', '(available)', 'available', 'total', 'abstention', '(present)', 'present', 'no preference', 'scatter', 'scattering', 'write-in', 'blank', 'other', 'others', 'none of these candidates',
                   'uninstructed delegate', 'uncommitted delegates', 'ceasefire', 'cease fire', 'misc.', 'void', '(not', 'not announced', 'totals')
CLOSE = 1.5                                           # points of share two sources may differ by and still be the same figure
STOOD = 24                                            # hours a Wikipedia page must have stood unchanged to be used alone
CLEAR = 5.0                                           # points from two-thirds a delegate share must be to be used from Wikipedia alone: its box may count unpledged delegates


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def get_bytes(url, timeout=60, limit=4_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit: raise ValueError('the file is larger than a results workbook should be')
    return data


def surname(name):
    """The family name, for matching one source's spelling with another's: 'Trump, Donald John', 'Donald John Trump',
    '[[Donald Trump]]' and 'Joseph Robinette "Joe" Biden, Jr. (write-in)' all have one."""
    n = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r'\1', name or ''); n = re.sub(r"'''?|\(write-in\)|\bwrite-in\b|\((?:r|d)\)|<[^>]*>|\{\{.*?\}\}", '', n, flags=re.I)
    n = re.sub(r'"[^"]*"', ' ', n); n = re.sub(r',?\s+(Jr\.?|Sr\.?|II|III|IV)\b\.?', '', n).strip(' ,')
    if ',' in n: n = n.split(',')[0]
    parts = [p for p in re.split(r'\s+', n.strip()) if p]
    return parts[-1].lower() if parts else ''


def shown(name):
    """'Trump, Donald John, Sr.' as 'Donald John Trump, Sr.': the order people write a name in."""
    m = re.match(r'([^,]+),\s*(.+?)((?:,\s*(?:Jr|Sr|II|III|IV)\.?)?)$', name or '')
    return f'{m.group(2)} {m.group(1)}{m.group(3)}' if m else (name or '')


def is_candidate(name):
    low = re.sub(r'\(write-in\)', '', (name or '').lower()).strip()
    return bool(low) and not any(low == x or low.startswith(x + ' ') or low.startswith(x + ',') for x in NOT_A_CANDIDATE) and not low.startswith('(')


num = lambda s: float(re.sub(r'[^\d.]', '', s)) if re.search(r'\d', s or '') else None


# ------------------------------------------------------------------------------------------------------ The Green Papers
def cells(page):
    """The page as rows of cells, tags and scripts gone."""
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S | re.I)
    rows = re.split(r'</?tr[^>]*>', t, flags=re.I)      # rows are cut at every row tag, opening or closing: these pages often leave one of the two out
    clean = lambda c: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c))).strip()
    return [[clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, flags=re.S | re.I)] for r in rows], re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))


def green_delegates(page):
    """{'candidates': {surname: {'name', 'hard'}}, 'floor': {surname: {'name', 'votes'}}, 'uncommitted': n, 'total': n} from a
    party's page, or None if the page has no count yet. The hard count is the first figure of the cell under "Hard Total";
    the roll call is the first figure of the cell beside it ("Floor", or in 2024 "Virtual Roll Call")."""
    rows, flat = cells(page); out = {'candidates': {}, 'floor': {}, 'uncommitted': 0.0, 'total': None, 'unpledged': 0.0}; on = False
    m = re.search(r'([\d,]+)\s+Unpledged', flat); out['unpledged'] = num(m.group(1)) if m else 0.0
    for r in rows:
        r = [c for c in r if c != '']
        if len(r) >= 2 and r[0].lower() == 'candidate' and 'delegate' in r[1].lower(): on = True; continue
        if not on or not r: continue
        if r[0].lower() == 'total':
            m = re.match(r'([\d,]+)', r[1] if len(r) > 1 else ''); out['total'] = num(m.group(1)) if m else None; break
    # the count sits in one cell, "2,160 88.93%"; a candidate with no hard delegates has an empty first cell, which the
    # clean-up above would drop, so the cells are read again in place
    on = False
    for r in rows:
        if len(r) >= 2 and r[0].lower() == 'candidate' and 'delegate' in ' '.join(r[1:]).lower(): on = True; continue
        if not on or not r or not r[0]: continue
        if r[0].lower() == 'total': break
        m = re.match(r'([\d,]+)\s+[\d.]+%', r[1]) if len(r) > 1 else None
        hard = num(m.group(1)) if m else 0.0
        m = re.match(r'([\d,]+)\s+[\d.]+%', r[2]) if len(r) > 2 else None                  # the next cell: the convention's roll call, once it has met
        floor = num(m.group(1)) if m else 0.0
        if r[0].lower().startswith('uncommitted'): out['uncommitted'] += hard
        elif is_candidate(r[0]) and hard > 0: out['candidates'][surname(r[0])] = {'name': r[0], 'hard': hard}
        if is_candidate(r[0]) and floor > 0: out['floor'][surname(r[0])] = {'name': r[0], 'votes': floor}
    return out if (out['candidates'] or out['floor']) and out['total'] else None


def green_nh(page):
    """{'official': bool, 'status': words, 'votes': {surname: {'name', 'votes', 'share', 'write_in'}}, 'winner': surname} from a
    New Hampshire page, or None if it has no vote yet."""
    rows, flat = cells(page); votes = {}; on = False
    for r in rows:
        r2 = [c for c in r if c != '']
        if len(r2) >= 2 and r2[0].lower() == 'candidate' and r2[1].lower().replace(' ', '').startswith('popvote'): on = True; continue
        if not on: continue
        if len(r2) < 3 or not re.search(r'%', r2[2]):
            if votes: break
            continue
        if r2[0].lower().startswith('total'): break
        if is_candidate(r2[0]) and num(r2[1]) is not None:
            k = surname(r2[0])
            if k not in votes: votes[k] = {'name': r2[0], 'votes': num(r2[1]), 'share': num(r2[2]), 'write_in': '(write-in)' in r2[0].lower()}
    if not votes: return None
    m = re.search(r'Status:\s*([A-Za-z ]+?)\.', flat); status = m.group(1).strip() if m else ''
    return {'official': status.lower().startswith('official'), 'status': status, 'votes': votes, 'winner': max(votes, key=lambda k: votes[k]['votes'])}


# ------------------------------------------------------------------------------------------ New Hampshire's own record
MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
COUNTIES = ('belknap', 'carroll', 'cheshire', 'coos', 'grafton', 'hillsborough', 'merrimack', 'rockingham', 'strafford', 'sullivan')


class Refused(Exception):
    """The state's site did not let the request through. Not a failure of the reading: the next source is used."""


def sheet_rows(data):
    """The first sheet of an .xlsx workbook as rows of text. A workbook is a zip of XML files; nothing is needed to read
    one but what Python carries. An older .xls file, or anything that is not a plain workbook, is refused."""
    if data[:2] != b'PK': raise ValueError('not an .xlsx workbook')
    z = zipfile.ZipFile(io.BytesIO(data)); names = z.namelist()
    sheets = sorted(n for n in names if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n))
    if not sheets: raise ValueError('the workbook has no sheet')
    def part(name):
        if z.getinfo(name).file_size > 20_000_000: raise ValueError('the workbook is larger than a results workbook should be')
        raw = z.read(name)
        if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw: raise ValueError('the workbook carries a document type declaration')
        return ET.fromstring(raw)
    strings = [''.join(t.text or '' for t in si.iter(MAIN + 't')) for si in part('xl/sharedStrings.xml').iter(MAIN + 'si')] if 'xl/sharedStrings.xml' in names else []
    rows = []
    for row in part(sheets[0]).iter(MAIN + 'row'):
        got = {}
        for c in row.iter(MAIN + 'c'):
            letters = re.match(r'[A-Z]+', c.get('r') or ''); col = 0
            for ch in (letters.group(0) if letters else 'A'): col = col * 26 + ord(ch) - 64
            v = c.find(MAIN + 'v'); kind = c.get('t')
            got[col - 1] = (strings[int(v.text)] if kind == 's' and v is not None else ''.join(t.text or '' for t in c.iter(MAIN + 't')) if kind == 'inlineStr' else (v.text or '') if v is not None else '').strip()
        rows.append([got.get(i, '') for i in range(max(got) + 1)] if got else [])
    return rows


def nh_workbook(rows, party, year, write_ins):
    """{name as printed: votes} from one "Summary By Counties" workbook, after checking that it is what it should be: the
    right office, party and year, the ten counties in every block, and every column adding up to its TOTALS row."""
    title = re.sub(r'\s+', ' ', ' '.join(rows[0] if rows else [])).upper()
    if 'PRESIDENT OF THE UNITED STATES' not in title or PARTY[party].upper() not in title or str(year) not in title: raise ValueError(f'the workbook is headed "{title[:80]}"')
    if ('WRITE-IN' in title) != write_ins: raise ValueError('the workbook is not the one its link said it was')
    whole = lambda c: int(float(c)) if re.fullmatch(r'\d+(\.0+)?', c or '') else 0 if (c or '') == '' else None
    out = {}; names = None; counties = []
    for r in rows[1:]:
        first = (r[0] if r else '').strip().lower()
        if first == 'summary': names = r[1:]; counties = []; continue
        if names is None or not first: continue
        if first in COUNTIES: counties.append(r[1:]); continue
        if first == 'totals':
            if len(counties) != len(COUNTIES): raise ValueError(f'a block has {len(counties)} counties, not {len(COUNTIES)}')
            for i, name in enumerate(names):
                if not name: continue
                total = whole(r[1 + i] if len(r) > 1 + i else ''); col = [whole(c[i] if len(c) > i else '') for c in counties]
                if total is None or None in col or sum(col) != total: raise ValueError(f'the counties do not add up to the total for {name}')
                out[name] = out.get(name, 0) + total
            names = None
    if not out or names is not None: raise ValueError('the workbook has no finished block of votes')
    return out


def nh_links(page, base):
    """(the ballot workbook's address, the write-ins workbook's address or None, whether the page has a write-ins part) from a
    party's results page: the links marked "Summary", told apart by the heading above them and by their own names."""
    marks = [(m.start(), 'h', re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1)))).strip()) for m in re.finditer(r'<h[1-6][^>]*>(.*?)</h[1-6]>', page, flags=re.S | re.I)]
    marks += [(m.start(), 'a', html.unescape(m.group(1))) for m in re.finditer(r'<a\s[^>]*href="([^"]+\.xlsx?)(?:\?[^"]*)?"', page, flags=re.I)]
    heading = ''; main = []; written = []; has = False
    for at, kind, text in sorted(marks):
        if kind == 'h': heading = text; has = has or 'write-in' in text.lower(); continue
        label = re.sub(r'<[^>]+>', ' ', page[max(page.rfind('<p', 0, at), page.rfind('<li', 0, at), at - 300):at]) + ' ' + text.rsplit('/', 1)[-1]
        if 'summary' not in label.lower() or 'president' not in (heading + ' ' + text).lower(): continue
        (written if 'write' in (heading + ' ' + text.rsplit('/', 1)[-1]).lower() else main).append(urllib.parse.urljoin(base, text))
    if len(main) != 1 or len(written) > 1: raise ValueError(f'the page has {len(main)} summary workbooks for the ballot and {len(written)} for write-ins')
    return main[0], (written[0] if written else None), has


def nh_find(year, party, read):
    """(address, page) of the Secretary of State's results page for a party's primary, or None if it does not exist yet. Its
    usual address is tried first; failing that the site's own links are followed from "Elections"."""
    def ask(url):
        try: return read(url)
        except urllib.error.HTTPError as err:
            if err.code == 404: return None
            if err.code in (401, 403, 429): raise Refused(f'HTTP {err.code}') from None
            raise
    is_it = lambda page: bool(page) and re.search(rf'<h1[^>]*>[^<]*{year}[^<]*{PARTY[party]}[^<]*Presidential Primary[^<]*Results', page, flags=re.I)
    url = NH_STATE.format(year=year, party=PARTY[party].lower()); page = ask(url)
    if is_it(page): return url, page
    url = NH_HOME + '/elections'
    for want in (rf'{year}\s+Election Results', rf'{year}\s+Presidential Primary', rf'{year}\s+{PARTY[party]}\s+Presidential Primary'):
        page = ask(url)
        if not page: return None
        nxt = next((html.unescape(m.group(1)) for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I) if re.search(want, re.sub(r'<[^>]+>', ' ', m.group(2)), flags=re.I)), None)
        if not nxt: return None
        url = urllib.parse.urljoin(url, nxt)
        if not url.startswith(NH_HOME + '/'): return None
    page = ask(url)
    return (url, page) if is_it(page) else None


def nh_official(year, party, read=get, read_bytes=get_bytes):
    """The Secretary of State's count of a party's primary, in the shape green_nh() gives, or None if the state has not
    published it. Raises Refused when the site turns the request away and ValueError when what it sends cannot be trusted."""
    found = nh_find(year, party, read)
    if not found: return None
    url, page = found; main, written, has = nh_links(page, url)
    if has and not written: raise ValueError('the page has a write-ins part and no summary workbook for it')
    def book(address, write_ins):
        try: return nh_workbook(sheet_rows(read_bytes(address)), party, year, write_ins)
        except urllib.error.HTTPError as err:
            if err.code in (401, 403, 429): raise Refused(f'HTTP {err.code}') from None
            raise
    ballot = book(main, False); extra = book(written, True) if written else {}
    total = sum(ballot.values()) + sum(extra.values()); votes = {}
    if total <= 0: raise ValueError('the workbooks hold no votes')
    def shown(name):
        n = re.sub(r'\((?:r|d)\)|write-in', '', name, flags=re.I); n = re.sub(r'\s+', ' ', n).strip(' ,')
        return ' '.join(p.strip(' ,') for p in reversed(n.split(',', 1))) if ',' in n else n
    for src, write_in in ((ballot, False), (extra, True)):
        for name, v in src.items():
            if not is_candidate(re.sub(r'\((?:r|d)\)', '', name, flags=re.I)): continue
            k = surname(name); row = votes.setdefault(k, {'name': shown(name), 'votes': 0, 'ballot': 0})
            row['votes'] += v; row['ballot'] += 0 if write_in else v
    for row in votes.values(): row['share'] = round(100 * row['votes'] / total, 2); row['write_in'] = row.pop('ballot') == 0
    return {'official': True, 'status': 'Official', 'votes': votes, 'winner': max(votes, key=lambda k: votes[k]['votes']), 'total': total, 'url': url, 'files': [f for f in (main, written) if f]}


# -------------------------------------------------------------------------------------------------------------- Wikipedia
def box(text, name='Infobox election'):
    """The fields of the first election box on a page: {field: value}. The box is cut at its own closing braces and split at
    the bars that are its own, so a field left empty stays empty and a link with a bar in it stays whole."""
    i = text.find('{{' + name)
    if i < 0: return None
    depth = 0; j = i; parts = []; start = None; link = 0
    while j < len(text):
        two = text[j:j + 2]
        if two == '{{': depth += 1; j += 2; continue
        if two == '}}':
            depth -= 1; j += 2
            if depth == 0:
                if start is not None: parts.append(text[start:j - 2])
                break
            continue
        if two == '[[': link += 1; j += 2; continue
        if two == ']]': link = max(0, link - 1); j += 2; continue
        if text[j] == '|' and depth == 1 and (link == 0 or text[:j].rstrip(' \t').endswith('\n')):      # a bar that opens a line is a field's, whatever came before it
            link = 0
            if start is not None: parts.append(text[start:j])
            start = j + 1
        j += 1
    out = {}
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1); out[k.strip().lower()] = v.strip()
    return out


def boxes(text):
    """Every election box on a page, the ones set inside another (a "module") included, outermost first."""
    out = []; i = 0
    while True:
        i = text.find('{{Infobox election', i)
        if i < 0: break
        b = box(text[i:]); i += 2
        if b: out.append(b)
    return out


def best_box(text, primary=False):
    """The box to read. For a party's primaries page some years carry two, one for the primaries and one for the convention's
    roll call: the pledged delegates are in the first."""
    bs = [b for b in boxes(text) if any(k.startswith('candidate') or k.startswith('nominee') or k.startswith('party') for k in b)]
    if not bs: return (boxes(text) or [None])[0]
    if primary:
        named = [b for b in bs if 'primar' in plain(b.get('election_name', '')).lower() and 'roll call' not in plain(b.get('election_name', '')).lower() and wiki_candidates(b)]
        if named: return named[0]
    return next((b for b in bs if wiki_candidates(b)), bs[0])


def plain(v):
    v = re.sub(r'<!--.*?-->', '', v or '', flags=re.S); v = re.sub(r'<ref[^>]*/>|<ref.*?</ref>', '', v, flags=re.S); v = re.sub(r'\{\{efn.*', '', v, flags=re.S | re.I)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r'\1', v); v = re.sub(r"'''?|<br ?/?>", ' ', v); v = re.sub(r'\{\{[^{}]*\}\}', ' ', v)
    return re.sub(r'\s+', ' ', v).strip()


def wiki_candidates(b):
    """[{name, key, delegates, votes, share}] from an election box, in the box's order."""
    out = []
    for n in range(1, 13):
        name = plain(b.get(f'candidate{n}') or b.get(f'nominee{n}') or '')
        if not name or not is_candidate(name) or 'abstention' in name.lower(): continue
        d = re.match(r'[\d,]+', plain(b.get(f'delegate_count{n}', ''))); pv = re.match(r'[\d,]+', plain(b.get(f'popular_vote{n}', ''))); pc = re.match(r'[\d.]+', plain(b.get(f'percentage{n}', '')))
        out.append({'name': name, 'key': surname(name), 'delegates': num(d.group(0)) if d else None, 'votes': num(pv.group(0)) if pv else None, 'share': float(pc.group(0)) if pc else None,
                    'party': plain(b.get(f'party{n}', ''))})
    return out


def wiki(titles, read=get):
    """{title: {'revision', 'time', 'text'}} for the pages that exist, in one request. A page that does not exist is left out."""
    q = {'action': 'query', 'prop': 'revisions', 'rvprop': 'content|ids|timestamp', 'rvslots': 'main', 'redirects': 1, 'format': 'json', 'formatversion': 2, 'maxlag': 5, 'titles': '|'.join(titles)}
    for attempt in range(3):
        try:
            got = json.loads(read(WIKI + '?' + urllib.parse.urlencode(q))); break
        except urllib.error.HTTPError as err:
            if err.code not in (429, 503) or attempt == 2: raise
            time.sleep(min(30, int(err.headers.get('Retry-After') or 5) + 1))
    back = {r['to']: r['from'] for r in (got.get('query') or {}).get('redirects') or []}; back.update({n['to']: n['from'] for n in (got.get('query') or {}).get('normalized') or []})
    out = {}
    for p in (got.get('query') or {}).get('pages') or []:
        if p.get('missing') or not p.get('revisions'): continue
        r = p['revisions'][0]; out[back.get(p['title'], p['title'])] = {'title': p['title'], 'revision': r['revid'], 'time': r['timestamp'], 'text': r['slots']['main']['content']}
    return out


# ------------------------------------------------------------------------------------------------------------- the reading
def titles(year):
    return {**{('primaries', p): f'{year} {PARTY[p]} Party presidential primaries' for p in 'RD'}, **{('nh', p): f'{year} New Hampshire {PARTY[p]} presidential primary' for p in 'RD'},
            ('election', ''): f'{year} United States presidential election'}


def addresses(year):
    yy = f'{year % 100:02d}'
    return {**{('delegates', p): GREEN.format(yy=yy, page=p) for p in 'RD'}, **{('nh', p): GREEN.format(yy=yy, page='NH-' + p) for p in 'RD'}}


def gather(year, read=get, now=None, kept=None, read_bytes=None):
    """Everything the sources give for `year`, each with its address, revision and the time it was read. A source that fails
    is recorded as failed, with the reason, and the rest goes on. `kept` is the official record read on an earlier run."""
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'); today = datetime.date.fromisoformat(now[:10])
    out = {'year': year, 'read': now, 'sources': [], 'failed': [], 'notes': [], 'down': [], 'green': {}, 'wiki': {}, 'official': {}}
    read_bytes = read_bytes or (get_bytes if read is get else getattr(read, 'bytes', None)); T = titles(year)
    try:
        pages = wiki(list(T.values()), read)
        for key, title in T.items():
            if title in pages:
                p = pages[title]; b = best_box(p['text'], primary=key[0] in ('primaries', 'nh'))
                out['wiki'][key] = {'box': b, 'candidates': wiki_candidates(b) if b else [], 'edited': p['time']}
                out['sources'].append({'source': 'Wikipedia', 'what': title, 'url': 'https://en.wikipedia.org/w/index.php?oldid=%s' % p['revision'], 'revision': p['revision'], 'edited': p['time'], 'retrieved': now, 'licence': 'CC BY-SA 4.0'})
    except Exception as err:                            # noqa: BLE001
        out['failed'].append(f'Wikipedia was not read ({type(err).__name__}: {str(err)[:80]})'); out['down'].append('Wikipedia')
    for key, url in addresses(year).items():
        try:
            page = read(url); got = (green_delegates if key[0] == 'delegates' else green_nh)(page)
            if got is not None:
                out['green'][key] = got; out['sources'].append({'source': 'The Green Papers', 'what': f"{PARTY[key[1]]} {'delegates' if key[0] == 'delegates' else 'New Hampshire primary'}", 'url': url, 'retrieved': now})
        except urllib.error.HTTPError as err:
            if err.code != 404: out['failed'].append(f'The Green Papers, {url}: HTTP {err.code}'); out['down'].append('The Green Papers')
        except Exception as err:                        # noqa: BLE001
            out['failed'].append(f'The Green Papers, {url}: {type(err).__name__}: {str(err)[:80]}'); out['down'].append('The Green Papers')
        time.sleep(0.2 if read is get else 0)
    # the state's own count. It is asked for from the year of the primary on. Once read it is kept, and asked for again only
    # on Mondays, in case a recount has changed it: the state's site turns away most requests from where this runs
    kept = {p: v for p, v in (kept or {}).items() if v.get('year') == year}
    for p in 'RD':
        old = kept.get(p)
        if today.year >= year and read_bytes and not (old and today.weekday() != 0):
            try:
                got = nh_official(year, p, read, read_bytes)
                if got: old = dict(got, year=year, retrieved=now)
            except Refused as err:
                out['notes'].append(f"New Hampshire's Secretary of State turned the request for its {PARTY[p]} results away ({err}); " + ('the count read from it earlier is used.' if old else 'the next source is used.'))
            except Exception as err:                    # noqa: BLE001  a page or a workbook that is not as expected is not used, and is said
                out['notes'].append(f"New Hampshire's Secretary of State, {PARTY[p]} results: not used ({type(err).__name__}: {str(err)[:100]}).")
        if old:
            out['official'][p] = old
            out['sources'].append({'source': 'New Hampshire Secretary of State', 'what': f'{PARTY[p]} primary, official results (summary by counties, with write-ins)', 'url': old['url'], 'files': old.get('files'), 'retrieved': old['retrieved']})
    return out


def majority(g):
    """From The Green Papers' count: (surname, name, share of the delegates pledged to candidates, the same with the
    uncommitted counted in) for the candidate who holds more than half of all the pledged delegates there are, or None."""
    if not g or not g['candidates']: return None
    c = g['candidates']; pledged = sum(v['hard'] for v in c.values()); top = max(c, key=lambda k: c[k]['hard'])
    if pledged <= 0 or c[top]['hard'] <= (g['total'] - g['unpledged']) / 2: return None          # more than half of every pledged delegate there is, not of those awarded so far
    return top, c[top]['name'], 100 * c[top]['hard'] / pledged, 100 * c[top]['hard'] / (pledged + g['uncommitted'])


def roll_call(g):
    """From The Green Papers' record of a convention: (surname, name, votes) for the candidate a majority of the roll call
    nominated, or None if the convention has not met."""
    if not g or not g.get('floor') or not g['total']: return None
    f = g['floor']; top = max(f, key=lambda k: f[k]['votes'])
    return (top, f[top]['name'], f[top]['votes']) if f[top]['votes'] > g['total'] / 2 else None


def stood(G, key):
    """Has this Wikipedia page gone a day without an edit? A page being changed by the hour is not used alone."""
    w = G['wiki'].get(key)
    if not w or not w.get('edited'): return False
    at = lambda t: datetime.datetime.strptime(t[:16], '%Y-%m-%dT%H:%M')
    try: return (at(G['read']) - at(w['edited'])).total_seconds() >= STOOD * 3600
    except ValueError: return False


def nominee(G, party, year):
    """(surname, name, 'formal' or 'presumptive', words, None) for a party; (None, None, None, why not, 'conflict' or None) when
    there is none to name."""
    e = (G['wiki'].get(('election', '')) or {}).get('candidates') or []
    named = next((c for c in e if PARTY[party].lower() in c['party'].lower()), None)
    w = (G['wiki'].get(('primaries', party)) or {}); wb = w.get('box') or {}; wc = [c for c in w.get('candidates') or [] if c['delegates']]
    lead = max(wc, key=lambda c: c['delegates']) if wc else None; need = num(plain(wb.get('needed_votes', ''))) or 0
    wiki_majority = bool(lead) and lead['delegates'] > sum(c['delegates'] for c in wc) / 2 and (not need or lead['delegates'] >= need)
    g = G['green'].get(('delegates', party)); floor = roll_call(g); m = majority(g); P_ = PARTY[party]
    if floor:
        if named and named['key'] != floor[0]:
            return None, None, None, f"the {P_} convention's roll call nominated {shown(floor[1])} (The Green Papers); Wikipedia's box for the {year} election names {named['name']}", 'conflict'
        floor = (floor[0], named['name'] if named else shown(floor[1]), floor[2])
        return floor[0], floor[1], 'formal', f"{floor[1]} was nominated by the {P_} convention's roll call, as The Green Papers records it" + ("; Wikipedia's box for the election names the same nominee" if named else "; Wikipedia's box for the election is not filled in yet"), None
    if m:
        if named and named['key'] != m[0]:
            return None, None, None, f"The Green Papers gives {shown(m[1])} a majority of pledged {P_} delegates; Wikipedia's box for the {year} election names {named['name']}. The convention's roll call will say which", 'conflict'
        if wiki_majority and lead['key'] != m[0]:
            return None, None, None, f"the sources disagree on who holds a majority of {P_} delegates (The Green Papers: {shown(m[1])}; Wikipedia: {lead['name']} with {lead['delegates']:.0f})", 'conflict'
        m = (m[0], lead['name'] if lead and lead['key'] == m[0] else shown(m[1]), m[2], m[3])
        also = (f" and in Wikipedia ({lead['delegates']:.0f})" if lead and lead['key'] == m[0] else "; Wikipedia's box has no delegate count yet" if not lead else f"; Wikipedia's box puts {lead['name']} ahead without a majority")
        return m[0], m[1], 'presumptive', f"{m[1]} holds a majority of pledged {P_} delegates in The Green Papers ({m[2]:.0f}%)" + also, None
    if g is None and 'The Green Papers' in G['down']:                                           # the fallback: the preferred source cannot be read at all
        if named and stood(G, ('election', '')): return named['key'], named['name'], 'presumptive', f"{named['name']} is the {P_} nominee in Wikipedia's box for the {year} election; The Green Papers could not be read", None
        if wiki_majority and stood(G, ('primaries', party)): return lead['key'], lead['name'], 'presumptive', f"{lead['name']} holds a majority of {P_} delegates in Wikipedia's box ({lead['delegates']:.0f}); The Green Papers could not be read", None
        return None, None, None, f'The Green Papers could not be read, and Wikipedia alone does not name a {P_} nominee on a page that has stood for a day', None
    return None, None, None, f'no {P_} candidate has a majority of pledged delegates in The Green Papers', None


def nh_sources(G, party):
    """The sources that have this party's New Hampshire result, highest first: [(who, votes, winner, certified, whole)].
    `whole` says the source lists every candidate; Wikipedia's box lists only the leading ones."""
    out = []; o = G['official'].get(party); g = G['green'].get(('nh', party)); w = [c for c in (G['wiki'].get(('nh', party)) or {}).get('candidates') or [] if c['votes'] or c['share']]
    if o: out.append(('the New Hampshire Secretary of State', o['votes'], o['winner'], True, True))
    if g: out.append(('The Green Papers', g['votes'], g['winner'], g['official'], True))
    if w:
        votes = {}
        for c in w: votes.setdefault(c['key'], {'name': c['name'], 'votes': c['votes'], 'share': c['share'], 'write_in': False})
        out.append(('Wikipedia', votes, max(w, key=lambda c: (c['votes'] or 0, c['share'] or 0))['key'], False, False))
    return out


def nh_reading(G, party, who):
    """A nominee in a party's New Hampshire primary, from the highest source that has the result:
    {'share', 'won', 'certified', 'said', 'from', 'others': {who: (share or None, won)}, 'notes', 'against'}; or a pair
    (state, why) when there is nothing to read yet. `against` lists the lower sources whose result gives another winner
    or another answer to whether the nominee won."""
    P_ = PARTY[party]; S = nh_sources(G, party)
    if not S: return 'not yet', f'no source has a {P_} New Hampshire result'
    top, votes, winner, certified, whole = S[0]
    if top == 'Wikipedia' and not stood(G, ('nh', party)): return 'waiting', f'only Wikipedia has a {P_} New Hampshire result so far, and its page has changed within the last day'
    share = votes[who]['share'] if who in votes and votes[who]['share'] is not None else 0.0 if whole and who not in votes else None
    won = winner == who; others = {}; notes = []; against = []
    for name, v, win, cert, wh in S[1:]:
        s = v[who]['share'] if who in v and v[who]['share'] is not None else 0.0 if wh and who not in v else None
        others[name] = (s, win == who)
        if (win == who) != won: against.append(f"{name} has {v[win]['name']} as the winner of the {P_} primary")
        elif win != winner: notes.append(f"{name} has {v[win]['name']} ahead in the {P_} primary; the nominee did not win it in either count")
        elif s is not None and share is not None and abs(s - share) > CLOSE: notes.append(f"{name} gives the nominee {s:g}% of the {P_} primary, not {share:g}%: counted on another total, or an earlier count")
    row = votes.get(who); victor = votes[winner]['name'] + (' (write-in)' if votes[winner].get('write_in') and 'write-in' not in votes[winner]['name'].lower() else '')
    said = (f"{row['name']} had {share:g}% of the {P_} primary" + (' as a write-in' if row.get('write_in') else '') + (' and won it' if won else f"; {victor} won it") if row and share is not None
            else f"{row['name']} did not win the {P_} primary; {victor} won it" if row
            else f"the nominee was not on the {P_} ballot; {victor} won it" if whole else f"the nominee is not among the leading candidates in Wikipedia's box for the {P_} primary; {victor} won it")
    agree = [n for n, (s, w_) in others.items() if w_ == won and not any(x.startswith(n) for x in notes)]
    basis = ("The Green Papers' count" if top == 'The Green Papers' else f"{top}'s count" if top != 'Wikipedia' else "Wikipedia's box, alone") + ('' if certified or top == 'Wikipedia' else ', not yet certified') + (f"; {' and '.join(agree)} agree{'s' if len(agree) == 1 else ''}" if agree else '')
    return {'share': share, 'won': won, 'certified': certified, 'said': said, 'from': top, 'basis': basis, 'others': others, 'notes': notes, 'against': against}


def evaluate(G, office, today, closes=None):
    """The four keys for the party in office ('R' or 'D'), from what gather() found. Returns {'nominees', 'keys', 'failed', 'notes'}.
    Each key: {'state', 'value', 'why', 'evidence'}; state is one of not yet, waiting, provisional, settled, conflict, failed."""
    other = 'D' if office == 'R' else 'R'; year = G['year']; out = {'nominees': {}, 'keys': {}, 'failed': G['failed'], 'notes': list(G.get('notes') or [])}
    noms = {p: nominee(G, p, year) for p in (office, other)}
    for p, (k, name, kind, words, _) in noms.items(): out['nominees'][PARTY[p]] = {'name': name, 'kind': kind, 'why': words}
    down = bool(G['failed']) and not G['green'] and not G['wiki'] and not G['official']
    blank = lambda state, why: {'state': 'failed' if down else state, 'value': None, 'why': ('No source could be read: ' + '; '.join(G['failed'])) if down else why, 'evidence': ''}
    # E04: the delegates. The Green Papers' hard count is the count; Wikipedia's box checks it, and stands in when it cannot be read
    g = G['green'].get(('delegates', office)); m = majority(g); wp = G['wiki'].get(('primaries', office)) or {}; wc = [c for c in wp.get('candidates') or [] if c['delegates']]
    over = str((wp.get('box') or {}).get('ongoing', '')).strip().lower() == 'no' or today >= datetime.date(year, 6, 20) or bool(roll_call(g)); side = lambda x: x >= 200 / 3
    lead = max(wc, key=lambda c: c['delegates']) if wc else None; ws = 100 * lead['delegates'] / sum(c['delegates'] for c in wc) if wc else None
    if not m and not wc: out['keys']['E04'] = blank('not yet', 'No delegates have been pledged yet.')
    elif not over: out['keys']['E04'] = blank('not yet', 'The primaries are not over; the count of pledged delegates is taken at their end.')
    elif m:
        m = (m[0], lead['name'] if lead and lead['key'] == m[0] else shown(m[1]), m[2], m[3])
        hard = g['candidates'][m[0]]['hard']; pledged = sum(v['hard'] for v in g['candidates'].values()); floor = (g.get('floor') or {}).get(m[0], {}).get('votes')
        near = lambda a, b: b is not None and abs(a - b) <= max(2.0, 0.01 * b)
        if side(m[2]) != side(m[3]): out['keys']['E04'] = blank('conflict', f"{m[1]} has {m[2]:.1f}% of the delegates pledged to candidates but {m[3]:.1f}% once uncommitted delegates are counted: the sides of two-thirds differ, and the rule does not say which count to use.")
        elif lead and lead['key'] != m[0]: out['keys']['E04'] = blank('conflict', f"The sources disagree on who leads in delegates ({m[1]} and {lead['name']}).")
        else:
            if not lead: check = "Wikipedia's box has no delegate count yet"
            elif side(ws) == side(m[2]): check = f"Wikipedia's box gives {ws:.1f}%"
            elif near(lead['delegates'], hard): check = f"Wikipedia's box has the same {hard:.0f} delegates and gives {ws:.1f}%, because it lists fewer of the other candidates"
            elif near(lead['delegates'], floor): check = f"Wikipedia's box shows the convention's roll call ({lead['delegates']:.0f} votes), not the pledged count"
            elif side(100 * lead['delegates'] / pledged) == side(m[2]): check = f"Wikipedia's box has {lead['delegates']:.0f} delegates for the same candidate, the same side of two-thirds on the same total"
            else: check = None
            if check is None: out['keys']['E04'] = blank('conflict', f"{m[1]}'s pledged delegates are {hard:.0f} ({m[2]:.1f}%) in The Green Papers and {lead['delegates']:.0f} ({ws:.1f}%) in Wikipedia: opposite sides of two-thirds, and not a difference in what is counted that can be recognised.")
            else: out['keys']['E04'] = {'state': 'settled', 'value': side(m[2]), 'why': '', 'evidence': f"{m[1]} won {m[2]:.1f}% of the delegates pledged to candidates (The Green Papers' hard count; {check})."}
    elif g is None and 'The Green Papers' in G['down'] and lead:
        need = num(plain((wp.get('box') or {}).get('needed_votes', ''))) or 0
        if not stood(G, ('primaries', office)): out['keys']['E04'] = blank('waiting', "The Green Papers could not be read, and Wikipedia's page has changed within the last day.")
        elif lead['delegates'] <= sum(c['delegates'] for c in wc) / 2 or (need and lead['delegates'] < need): out['keys']['E04'] = blank('waiting', "The Green Papers could not be read, and Wikipedia's box shows no candidate with a majority of delegates.")
        elif abs(ws - 200 / 3) < CLEAR: out['keys']['E04'] = blank('waiting', f"The Green Papers could not be read. Wikipedia's box gives {lead['name']} {ws:.1f}% of delegates, too near two-thirds to call from a box that may count unpledged delegates.")
        else: out['keys']['E04'] = {'state': 'provisional', 'value': side(ws), 'why': '', 'evidence': f"{lead['name']} has {ws:.1f}% of the delegates in Wikipedia's box, alone: The Green Papers could not be read."}
    else: out['keys']['E04'] = blank('waiting', noms[office][3])
    # E05, E06, E07: New Hampshire, for the nominees
    ko, ka = noms[office][0], noms[other][0]; ro = nh_reading(G, office, ko) if ko else None; ra = nh_reading(G, other, ka) if ka else None
    held = lambda r: isinstance(r, tuple)
    def settles(r):
        """A reading stands against a lower source that says otherwise only when it is the state's own count, and only one
        source says otherwise: two sources agreeing against it more likely mean its file was misread."""
        if not r['against']: return True, []
        if r['from'] == 'the New Hampshire Secretary of State' and len(r['against']) < 2: return True, [a + '; the Secretary of State\'s count is used' for a in r['against']]
        return False, r['against']
    def state_of(*pairs):
        for r, n in pairs:
            if r is None and n[4] == 'conflict': return 'conflict'
        if any(r is None for r, n in pairs): return 'waiting' if all(nh_sources(G, p) for p in 'RD') else 'not yet'
        for s in ('conflict', 'waiting', 'not yet'):
            if any(held(r) and r[0] == s for r, n in pairs): return s
        if any(not settles(r)[0] for r, n in pairs): return 'conflict'
        return 'settled' if all(r['certified'] for r, n in pairs) and all(n[2] == 'formal' for r, n in pairs) else 'provisional'
    def why_of(*pairs):
        said = []
        for r, n in pairs:
            if r is None: said.append(n[3][0].upper() + n[3][1:] + '.')
            elif held(r): said.append(r[1][0].upper() + r[1][1:] + '.')
            elif not settles(r)[0]: said.append(f"{r['from']} and another source name different winners: " + '; '.join(r['against']) + '.')
        return ' '.join(dict.fromkeys(said))
    sentence = lambda r: r['said'][0].upper() + r['said'][1:] + f" ({r['basis']})." + ''.join(' ' + x[0].upper() + x[1:] + '.' for x in r['notes'] + settles(r)[1])
    po, pa = (ro, noms[office]), (ra, noms[other])
    s = state_of(po)
    out['keys']['E05'] = {'state': s, 'value': bool(ro['won']), 'why': '', 'evidence': sentence(ro)} if s in ('settled', 'provisional') else blank(s, why_of(po) or 'The New Hampshire primary has not been held.')
    s = state_of(pa)
    out['keys']['E07'] = {'state': s, 'value': not ra['won'], 'why': '', 'evidence': sentence(ra)} if s in ('settled', 'provisional') else blank(s, why_of(pa) or 'The New Hampshire primary has not been held.')
    s = state_of(po, pa)
    if s in ('settled', 'provisional'):
        if ro['share'] is None or ra['share'] is None: out['keys']['E06'] = blank('waiting', "A nominee's share of the vote is not in Wikipedia's box, which is the only source with the result so far.")
        else:
            value = ro['share'] > ra['share']; both = [n for n in ro['others'] if n in ra['others'] and ro['others'][n][0] is not None and ra['others'][n][0] is not None]
            say_other = [n for n in both if (ro['others'][n][0] > ra['others'][n][0]) != value]; official = ro['from'] == ra['from'] == 'the New Hampshire Secretary of State'
            if say_other and not (official and len(say_other) < 2):
                out['keys']['E06'] = blank('conflict', f"The sources put the two nominees' shares in a different order: {ro['share']:g}% and {ra['share']:g}% in {ro['from'] if ro['from'] == ra['from'] else 'the first sources'}, {ro['others'][say_other[0]][0]:g}% and {ra['others'][say_other[0]][0]:g}% in {say_other[0]}.")
            else:
                out['keys']['E06'] = {'state': s, 'value': value, 'why': '', 'evidence': sentence(ro) + ' ' + sentence(ra) + (f" {say_other[0]} puts the two shares in the other order; the Secretary of State's count is used." if say_other else '')}
    else: out['keys']['E06'] = blank(s, why_of(po, pa) or 'The New Hampshire primaries have not been held.')
    for k, v in out['keys'].items():
        if v['state'] in ('settled', 'provisional') and k != 'E04':
            who = (office,) if k == 'E05' else (other,) if k == 'E07' else (office, other); formal = [noms[p][2] == 'formal' for p in who]
            v['evidence'] += (' Both nominees are formally nominated.' if all(formal) else ' At least one nominee is presumptive: a majority of pledged delegates, the convention not yet held.') if k == 'E06' else \
                             ' The nominee is ' + ('formally nominated.' if all(formal) else 'presumptive: a majority of pledged delegates.')
    if closes and today >= closes:                      # the count is closed: what was provisional stands as read that day
        for v in out['keys'].values():
            if v['state'] == 'provisional': v['state'] = 'settled'
    return out


RULE = 'primaries.py: the highest source that has the figure is used (the official record, then The Green Papers, then Wikipedia); a contradiction between sources holds the key open'


def refresh(today, year, office, path=None, read=get, closes=None, log=None, read_bytes=None):
    """Read the sources and write data/primaries.json; add a line to the log when the reading has changed. Returns
    (state, words): 'new', 'same' or 'unreachable'. A run that reads nothing leaves the last reading in place."""
    path = path or os.path.join(D, 'primaries.json'); log = log or os.path.join(os.path.dirname(path), 'primaries_log.jsonl')
    old = json.load(open(path)) if os.path.exists(path) else {}
    G = gather(year, read, now=datetime.datetime.combine(today, datetime.datetime.now(datetime.timezone.utc).time()).strftime('%Y-%m-%dT%H:%MZ'), kept=old.get('official'), read_bytes=read_bytes); E = evaluate(G, office, today, closes)
    if not G['green'] and not G['wiki'] and not G['official'] and G['failed']:
        if old: old['last_failure'] = {'date': str(today), 'why': G['failed']}; json.dump(old, open(path, 'w'), indent=1)
        return 'unreachable', 'the nomination sources were not read (' + '; '.join(G['failed'])[:160] + '); the last reading stays'
    out = {'year': year, 'party_in_office': PARTY[office], 'read': G['read'], 'checked': str(today), 'nominees': E['nominees'], 'keys': E['keys'], 'sources': G['sources'], 'failed': G['failed'], 'notes': E['notes'],
           'official': G['official'], 'rule': RULE}
    core = lambda x: json.dumps({'n': x.get('nominees'), 'k': {k: [v['state'], v['value'], v.get('evidence')] for k, v in (x.get('keys') or {}).items()}}, sort_keys=True)
    same = bool(old) and core(old) == core(out)
    json.dump(out, open(path, 'w'), indent=1)
    if not same:
        with open(log, 'a') as f: f.write(json.dumps({'recorded': str(today), 'read': G['read'], 'nominees': E['nominees'], 'keys': E['keys'], 'sources': G['sources']}) + '\n')
    said = ', '.join(f"{k} {v['state']}" + (f" ({'yes' if v['value'] else 'no'})" if v['value'] is not None else '') for k, v in E['keys'].items())
    return ('same' if same else 'new'), f"the nomination keys: {said}" + (f". Not read: {'; '.join(G['failed'])[:120]}" if G['failed'] else '')


if __name__ == '__main__':
    y = int(sys.argv[1]) if len(sys.argv) > 1 else 2028; office = sys.argv[2] if len(sys.argv) > 2 else 'R'
    G = gather(y); E = evaluate(G, office, datetime.date.today())
    print(json.dumps({'nominees': E['nominees'], 'keys': E['keys'], 'failed': E['failed'], 'notes': E['notes'], 'official': {p: {'winner': v['winner'], 'total': v['total'], 'files': v['files']} for p, v in G['official'].items()},
                      'sources': [s['url'] for s in G['sources']]}, indent=1))
