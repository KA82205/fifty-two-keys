"""The four nomination keys, read and not typed: who the nominees are, the delegates they won, and New Hampshire.

    E04  the party in office: the candidate with a majority of its pledged delegates won two-thirds of them or more
    E05  the party in office: its nominee won its New Hampshire primary
    E06  its nominee's share of that primary was larger than the other party's nominee's share of his
    E07  the other party's nominee lost its New Hampshire primary

The rules are the keys' own (KEYS.md) and are not touched here. This file only finds the evidence.

Where it looks. Nothing is typed in and no address is entered: every address is made from the election year.
    The Green Papers   thegreenpapers.com/P28/R and /D (each party's count of delegates: the "hard" count, which is the count of
                       delegates pledged by the primaries and caucuses, apart from the convention's roll call) and
                       /P28/NH-R and /NH-D (the New Hampshire vote, which the page takes from the New Hampshire Secretary of State
                       and marks "Official" once it is certified)
    Wikipedia          the election boxes of "2028 Republican Party presidential primaries", "2028 New Hampshire Republican
                       presidential primary", the same for the Democrats, and "2028 United States presidential election",
                       through the MediaWiki API, all in one request, with the revision of each page kept. Text is used under
                       CC BY-SA 4.0, with the page and revision named
    New Hampshire      the Secretary of State's page for each primary is looked for and its address kept with the evidence
                       when it answers. Its spreadsheets are not read: The Green Papers' figures are its certified ones

Two sources, or no call. A figure is used only when The Green Papers and Wikipedia give it alike: the same nominee, the
same winner in New Hampshire, shares within a point and a half, and the same side of two-thirds. Anything else is not a
"no": the key stays open, the reason is written down, and the next run looks again.

    the nominee        the candidate named in the general election's box once a party has formally nominated (this is how a
                       nominee who withdraws or is replaced is followed); before that, the candidate with a majority of
                       the pledged delegates in both sources: the presumptive nominee. A call that rests on a presumptive
                       nominee is provisional
    write-ins          counted as the sources count them: a candidate who wins as a write-in has won
    not on the ballot  a nominee with no line in a primary got none of its vote and did not win it
    pledged delegates  the hard count of each candidate. "Uncommitted" and "available" delegates are not a candidate's. If
                       counting the uncommitted among the pledged would change the side of two-thirds, the key is left open

What each key can be: not yet (the event has not happened), waiting (it has, and the evidence is not all in), provisional,
settled, in conflict (the sources disagree), or a source failed. data/primaries.json holds the latest reading with every
source's address, revision and retrieval time; data/primaries_log.jsonl gains a line whenever a reading changes.

    python primaries.py            read the sources for the current cycle and print what they give, changing nothing
"""
import datetime, html, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
AGENT = {'User-Agent': 'Mozilla/5.0 (compatible; fifty-two-keys/1.0; +https://github.com/KA82205/fifty-two-keys)'}
WIKI = 'https://en.wikipedia.org/w/api.php'
GREEN = 'https://www.thegreenpapers.com/P{yy}/{page}'
NH_STATE = 'https://www.sos.nh.gov/{year}-{party}-presidential-primary-election-results'
PARTY = {'R': 'Republican', 'D': 'Democratic'}
NOT_A_CANDIDATE = ('uncommitted', '(available)', 'available', 'total', 'abstention', '(present)', 'present', 'no preference', 'scatter', 'scattering', 'write-in', 'blank', 'other', 'others', 'none of these candidates',
                   'uninstructed delegate', 'uncommitted delegates', 'ceasefire', 'misc.', 'void', '(not')
CLOSE = 1.5                                           # points of share two sources may differ by and still be the same figure


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def surname(name):
    """The family name, for matching one source's spelling with another's: 'Trump, Donald John', 'Donald John Trump',
    '[[Donald Trump]]' and 'Joseph Robinette "Joe" Biden, Jr. (write-in)' all have one."""
    n = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r'\1', name or ''); n = re.sub(r"'''?|\(write-in\)|<[^>]*>|\{\{.*?\}\}", '', n, flags=re.I)
    n = re.sub(r'"[^"]*"', ' ', n); n = re.sub(r',?\s+(Jr\.?|Sr\.?|II|III|IV)\b\.?', '', n).strip(' ,')
    if ',' in n: n = n.split(',')[0]
    parts = [p for p in re.split(r'\s+', n.strip()) if p]
    return parts[-1].lower() if parts else ''


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
    """{'candidates': {surname: {'name', 'hard'}}, 'uncommitted': n, 'total': n} from a party's page, or None if the page has no
    count yet. The hard count is the first figure of the cell under "Hard Total"."""
    rows, flat = cells(page); out = {'candidates': {}, 'uncommitted': 0.0, 'total': None, 'unpledged': 0.0}; on = False
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
        if r[0].lower().startswith('uncommitted'): out['uncommitted'] += hard
        elif is_candidate(r[0]) and hard > 0: out['candidates'][surname(r[0])] = {'name': r[0], 'hard': hard}
    return out if out['candidates'] and out['total'] else None


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


def gather(year, read=get, now=None):
    """Everything the sources give for `year`, each with its address, revision and the time it was read. A source that fails
    is recorded as failed, with the reason, and the rest goes on."""
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'); out = {'year': year, 'read': now, 'sources': [], 'failed': [], 'green': {}, 'wiki': {}}
    T = titles(year)
    try:
        pages = wiki(list(T.values()), read)
        for key, title in T.items():
            if title in pages:
                p = pages[title]; b = best_box(p['text'], primary=key[0] in ('primaries', 'nh'))
                out['wiki'][key] = {'box': b, 'candidates': wiki_candidates(b) if b else []}
                out['sources'].append({'source': 'Wikipedia', 'what': title, 'url': 'https://en.wikipedia.org/w/index.php?oldid=%s' % p['revision'], 'revision': p['revision'], 'edited': p['time'], 'retrieved': now, 'licence': 'CC BY-SA 4.0'})
    except Exception as err:                            # noqa: BLE001
        out['failed'].append(f'Wikipedia was not read ({type(err).__name__}: {str(err)[:80]})')
    for key, url in addresses(year).items():
        try:
            page = read(url); got = (green_delegates if key[0] == 'delegates' else green_nh)(page)
            if got is not None:
                out['green'][key] = got; out['sources'].append({'source': 'The Green Papers', 'what': f"{PARTY[key[1]]} {'delegates' if key[0] == 'delegates' else 'New Hampshire primary'}", 'url': url, 'retrieved': now})
        except urllib.error.HTTPError as err:
            if err.code != 404: out['failed'].append(f'The Green Papers, {url}: HTTP {err.code}')
        except Exception as err:                        # noqa: BLE001
            out['failed'].append(f'The Green Papers, {url}: {type(err).__name__}: {str(err)[:80]}')
        time.sleep(0.2 if read is get else 0)
    for p in 'RD':                                      # the state's own page: its address is kept with the evidence when it answers
        url = NH_STATE.format(year=year, party=PARTY[p].lower())
        try:
            if 'presidential' in read(url)[:200000].lower(): out['sources'].append({'source': 'New Hampshire Secretary of State', 'what': f'{PARTY[p]} primary, official results (found, not parsed)', 'url': url, 'retrieved': now})
        except Exception:                               # noqa: BLE001  not there yet, or not answering: The Green Papers carries its certified figures
            pass
    return out


def majority(g):
    """From The Green Papers' count: (surname, name, share of the delegates pledged to candidates, the same with the
    uncommitted counted in) for the candidate who holds more than half of all the pledged delegates there are, or None."""
    if not g: return None
    c = g['candidates']; pledged = sum(v['hard'] for v in c.values()); top = max(c, key=lambda k: c[k]['hard'])
    if pledged <= 0 or c[top]['hard'] <= (g['total'] - g['unpledged']) / 2: return None          # more than half of every pledged delegate there is, not of those awarded so far
    return top, c[top]['name'], 100 * c[top]['hard'] / pledged, 100 * c[top]['hard'] / (pledged + g['uncommitted'])


def nominee(G, party, year):
    """(surname, name, 'formal' or 'presumptive', words) for a party, or (None, None, None, why not)."""
    e = (G['wiki'].get(('election', '')) or {}).get('candidates') or []
    formal = next((c for c in e if PARTY[party].lower() in c['party'].lower()), None)
    w = (G['wiki'].get(('primaries', party)) or {}); wb = w.get('box') or {}; wc = [c for c in w.get('candidates') or [] if c['delegates']]
    if formal:
        return formal['key'], formal['name'], 'formal', f"{formal['name']} is the {PARTY[party]} nominee in Wikipedia's box for the {year} election"
    m = majority(G['green'].get(('delegates', party)))
    if not m: return None, None, None, f'no {PARTY[party]} candidate has a majority of pledged delegates in The Green Papers'
    if not wc: return None, None, None, f"The Green Papers gives {m[1]} a majority of pledged delegates; Wikipedia's box has no delegate count yet"
    lead = max(wc, key=lambda c: c['delegates']); need = num(plain(wb.get('needed_votes', ''))) or 0
    if lead['key'] != m[0] or (need and lead['delegates'] < need and lead['delegates'] <= sum(c['delegates'] for c in wc) / 2):
        return None, None, None, f"the sources disagree on who holds a majority of {PARTY[party]} delegates (The Green Papers: {m[1]}; Wikipedia: {lead['name']} with {lead['delegates']:.0f})"
    return m[0], m[1], 'presumptive', f"{m[1]} holds a majority of pledged {PARTY[party]} delegates in The Green Papers ({m[2]:.0f}%) and in Wikipedia ({lead['delegates']:.0f})"


def nh_reading(G, party, who):
    """(share, won, 'official' or 'not official', words) for a nominee in a party's New Hampshire primary when the two sources
    agree; ('conflict', why) when they do not; ('waiting', why) when one is missing."""
    g = G['green'].get(('nh', party)); w = (G['wiki'].get(('nh', party)) or {}).get('candidates') or []; w = [c for c in w if c['votes'] or c['share']]
    if not g and not w: return 'not yet', f'neither source has a {PARTY[party]} New Hampshire result'
    if not g or not w: return 'waiting', f"only {'The Green Papers' if g else 'Wikipedia'} has a {PARTY[party]} New Hampshire result so far"
    wtop = max(w, key=lambda c: (c['votes'] or 0, c['share'] or 0))
    if wtop['key'] != g['winner']: return 'conflict', f"the sources name different winners of the {PARTY[party]} primary ({g['votes'][g['winner']]['name']} and {wtop['name']})"
    gs = g['votes'].get(who, {}).get('share', 0.0); wrow = next((c for c in w if c['key'] == who), None); ws = wrow['share'] if wrow and wrow['share'] is not None else None
    if ws is not None and abs(ws - gs) > CLOSE: return 'conflict', f"the sources give the nominee {gs:g}% and {ws:g}% of the {PARTY[party]} primary"
    if ws is None and gs >= 15 and wrow is None and len(w) >= 2: return 'conflict', f"The Green Papers gives the nominee {gs:g}% of the {PARTY[party]} primary and Wikipedia's box does not list him or her"
    won = g['winner'] == who
    said = (f"{g['votes'][who]['name']} had {gs:g}% of the {PARTY[party]} primary" + (' as a write-in' if g['votes'][who]['write_in'] else '') + (' and won it' if won else f"; {g['votes'][g['winner']]['name']} won it") if who in g['votes']
            else f"the nominee was not on the {PARTY[party]} ballot; {g['votes'][g['winner']]['name']} won it")
    return gs, won, 'official' if g['official'] else 'not official', said


def evaluate(G, office, today, closes=None):
    """The four keys for the party in office ('R' or 'D'), from what gather() found. Returns {'nominees', 'keys', 'failed'}.
    Each key: {'state', 'value', 'why', 'evidence'}; state is one of not yet, waiting, provisional, settled, conflict, failed."""
    other = 'D' if office == 'R' else 'R'; year = G['year']; out = {'nominees': {}, 'keys': {}, 'failed': G['failed']}
    noms = {p: nominee(G, p, year) for p in (office, other)}
    for p, (k, name, kind, words) in noms.items(): out['nominees'][PARTY[p]] = {'name': name, 'kind': kind, 'why': words}
    down = bool(G['failed']) and not G['green'] and not G['wiki']
    blank = lambda state, why: {'state': 'failed' if down else state, 'value': None, 'why': ('No source could be read: ' + '; '.join(G['failed'])) if down else why, 'evidence': ''}
    # E04: the delegates
    g = G['green'].get(('delegates', office)); m = majority(g); wc = [c for c in (G['wiki'].get(('primaries', office)) or {}).get('candidates') or [] if c['delegates']]
    over = str((G['wiki'].get(('primaries', office)) or {}).get('box', {}).get('ongoing', '')).strip().lower() == 'no' or today >= datetime.date(year, 6, 20)
    if not m and not wc: out['keys']['E04'] = blank('not yet', 'No delegates have been pledged yet.')
    elif not over: out['keys']['E04'] = blank('not yet', 'The primaries are not over; the count of pledged delegates is taken at their end.')
    elif not m or not wc: out['keys']['E04'] = blank('waiting', noms[office][3])
    else:
        lead = max(wc, key=lambda c: c['delegates']); ws = 100 * lead['delegates'] / sum(c['delegates'] for c in wc); side = lambda x: x >= 200 / 3
        if lead['key'] != m[0]: out['keys']['E04'] = blank('conflict', f"The sources disagree on who leads in delegates ({m[1]} and {lead['name']}).")
        elif side(m[2]) != side(ws): out['keys']['E04'] = blank('conflict', f"{m[1]}'s share of pledged delegates is {m[2]:.1f}% in The Green Papers and {ws:.1f}% in Wikipedia: opposite sides of two-thirds.")
        elif side(m[2]) != side(m[3]): out['keys']['E04'] = blank('conflict', f"{m[1]} has {m[2]:.1f}% of the delegates pledged to candidates but {m[3]:.1f}% once uncommitted delegates are counted: the sides of two-thirds differ, and the rule does not say which count to use.")
        else:
            out['keys']['E04'] = {'state': 'settled', 'value': side(m[2]), 'why': '', 'evidence': f"{m[1]} won {m[2]:.1f}% of the delegates pledged to candidates (The Green Papers' hard count; Wikipedia's box gives {ws:.1f}%)."}
    # E05, E06, E07: New Hampshire, for the nominees
    ko, ka = noms[office][0], noms[other][0]; ro = nh_reading(G, office, ko) if ko else None; ra = nh_reading(G, other, ka) if ka else None
    def state_of(*readings, kinds=()):
        if any(r is None for r in readings): return 'waiting' if all((G['green'].get(('nh', p)) or (G['wiki'].get(('nh', p)) or {}).get('candidates')) for p in 'RD') else 'not yet'
        for s in ('conflict', 'waiting', 'not yet'):
            if any(r[0] == s for r in readings): return s
        return 'settled' if all(r[2] == 'official' for r in readings) and all(k == 'formal' for k in kinds) else 'provisional'
    why_of = lambda *pairs: ' '.join(dict.fromkeys(x for x in ((r[1] if r and isinstance(r[0], str) else None) or (None if r else n[3]) for r, n in pairs) if x))
    s = state_of(ro, kinds=(noms[office][2],))
    out['keys']['E05'] = {'state': s, 'value': bool(ro[1]), 'why': '', 'evidence': ro[3][0].upper() + ro[3][1:] + '.'} if s in ('settled', 'provisional') else blank(s, why_of((ro, noms[office])) or 'The New Hampshire primary has not been held.')
    s = state_of(ra, kinds=(noms[other][2],))
    out['keys']['E07'] = {'state': s, 'value': not ra[1], 'why': '', 'evidence': ra[3][0].upper() + ra[3][1:] + '.'} if s in ('settled', 'provisional') else blank(s, why_of((ra, noms[other])) or 'The New Hampshire primary has not been held.')
    s = state_of(ro, ra, kinds=(noms[office][2], noms[other][2]))
    out['keys']['E06'] = ({'state': s, 'value': ro[0] > ra[0], 'why': '', 'evidence': f"{ro[3][0].upper() + ro[3][1:]}; {ra[3]}."} if s in ('settled', 'provisional')
                          else blank(s, why_of((ro, noms[office]), (ra, noms[other])) or 'The New Hampshire primaries have not been held.'))
    for k, v in out['keys'].items():
        if v['state'] in ('settled', 'provisional'):
            v['evidence'] += ' The nominee is ' + ('formally nominated.' if all(noms[p][2] == 'formal' for p in ((office,) if k in ('E04', 'E05') else (other,) if k == 'E07' else (office, other))) else 'presumptive: a majority of pledged delegates.') if k != 'E04' else ''
    if closes and today >= closes:                      # the count is closed: what was provisional stands as read that day
        for v in out['keys'].values():
            if v['state'] == 'provisional': v['state'] = 'settled'
    return out


def refresh(today, year, office, path=None, read=get, closes=None, log=None):
    """Read the sources and write data/primaries.json; add a line to the log when the reading has changed. Returns
    (state, words): 'new', 'same' or 'unreachable'. A run that reads nothing leaves the last reading in place."""
    path = path or os.path.join(D, 'primaries.json'); log = log or os.path.join(os.path.dirname(path), 'primaries_log.jsonl')
    G = gather(year, read); E = evaluate(G, office, today, closes)
    old = json.load(open(path)) if os.path.exists(path) else {}
    if not G['green'] and not G['wiki'] and G['failed']:
        if old: old['last_failure'] = {'date': str(today), 'why': G['failed']}; json.dump(old, open(path, 'w'), indent=1)
        return 'unreachable', 'the nomination sources were not read (' + '; '.join(G['failed'])[:160] + '); the last reading stays'
    out = {'year': year, 'party_in_office': PARTY[office], 'read': G['read'], 'checked': str(today), 'nominees': E['nominees'], 'keys': E['keys'], 'sources': G['sources'], 'failed': G['failed'],
           'rule': 'primaries.py: two sources must agree, or the key stays open'}
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
    print(json.dumps({'nominees': E['nominees'], 'keys': E['keys'], 'failed': E['failed'], 'sources': [s['url'] for s in G['sources']]}, indent=1))
