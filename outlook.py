"""The forecasters' outlook, read from the Survey of Professional Forecasters instead of typed in.

The run-ahead lays past stretches of the economy over the outlook forecasters hold (run_2028.py). That outlook is
data/outlook.json. Four parts of it come from the survey the Federal Reserve Bank of Philadelphia publishes in the middle of
February, May, August and November, and this file reads them from the survey's own table of median forecasts:

    growth            real GDP, each quarter's growth at a yearly rate, from the median level of each quarter
    jobs_a_month      payroll jobs, the change in the median level from one quarter to the next, divided by three
    unemployment      the median rate for the second quarter of 2028 once the survey reaches it; before that its figure
                      for 2028 as a whole, or the furthest quarter it gives if it has none
    cpi_quarters      consumer prices, each quarter's median rate of inflation at a yearly rate

The survey gives five quarters: the one it is taken in and the next four. A quarter beyond them takes the survey's figure for
its calendar year (growth of the yearly average for GDP and jobs, fourth quarter on fourth quarter for prices); where the
survey gives no such figure, its last quarterly figure is carried on. Quarters before the survey keep what they had: by then
they are published, and the run-ahead follows the published figures.

The rest of the outlook is not in the survey and stays as entered, with the month it was entered: income, hourly pay,
spending, industrial production, factory jobs, the price of oil, consumer sentiment, the growth of the population, and the
share of runs with a recession. So do the odds for the approval and nomination keys.

The outlook is replaced only by a survey later than the one it holds. Reading the same survey again changes nothing, and
says how closely this rule gives the figures that were entered by hand. A survey that cannot be read, or whose figures are
outside what a forecast can be, is not used: the outlook in hand stays, and update.py says so.

    python outlook.py            read the survey and say what it gives, changing nothing
"""
import copy, datetime, io, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'data', 'outlook.json')
URL = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/survey-of-professional-forecasters/historical-data/medianLevel.xlsx'
PAGE = 'https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/median-forecasts'
Q0 = 2026 * 4 + 3                                      # 2026 Q4: the first quarter of the outlook's lists (run_2028.Q0)
SHEETS = {'gdp': 'RGDP', 'jobs': 'EMP', 'u': 'UNEMP', 'cpi': 'CPI'}
# what a forecast can be: outside these the survey was misread, or its units changed
LIMITS = {'gdp': (-8.0, 10.0), 'cpi_quarters': (-2.0, 12.0), 'unemployment': (2.5, 12.0), 'jobs_a_month': (-800.0, 800.0)}
KEPT = 'income, hourly pay, spending, industrial production, factory jobs, oil, sentiment and population'


class Unreadable(ValueError):
    """The table is not in the shape this file knows, or a figure in it cannot be a forecast."""


def number(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) < 1e12 else None


def table(xlsx, sheet):
    """One sheet of the survey's workbook: {(year, quarter): {column: number}}, with the column names in capitals."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    names = {n.upper(): n for n in wb.sheetnames}
    if sheet not in names:
        raise Unreadable(f'no sheet {sheet} (the sheets are {", ".join(wb.sheetnames[:12])})')
    rows = wb[names[sheet]].iter_rows(values_only=True)
    head = [str(c).strip().upper() if c is not None else '' for c in next(rows)]
    if 'YEAR' not in head or 'QUARTER' not in head:
        raise Unreadable(f'sheet {sheet} has no YEAR and QUARTER columns (it has {", ".join(head[:8])})')
    out = {}
    for r in rows:
        d = dict(zip(head, r)); y, q = number(d.get('YEAR')), number(d.get('QUARTER'))
        if y and q:
            out[(int(y), int(q))] = {k: number(v) for k, v in d.items() if k not in ('YEAR', 'QUARTER', '')}
    if not out:
        raise Unreadable(f'sheet {sheet} has no rows')
    return out


def survey(xlsx):
    """The latest survey in the workbook: its quarter, and for each series the columns 1 to 6 (the quarter before the survey,
    the survey's own quarter, and the next four) and A to D (the survey's year and the three after)."""
    out = {}
    for name, sheet in SHEETS.items():
        t = table(xlsx, sheet); when = max(t); row = t[when]
        cols = {m.group(1): v for k, v in row.items() for m in [re.fullmatch(sheet + r'([1-6A-D])', k)] if m}
        if not all(cols.get(str(i)) is not None for i in range(2, 7)):
            raise Unreadable(f'sheet {sheet}, {when[0]} Q{when[1]}: the five quarterly figures are not all there (columns {", ".join(sorted(row)[:12])})')
        out[name] = cols; out.setdefault('when', when)
        if out['when'] != when:
            raise Unreadable(f'the sheets end in different surveys: {out["when"]} and {when}')
    return out


def from_survey(sv):
    """The four parts of the outlook the survey gives, by quarter number (year x 4 + quarter - 1)."""
    y, q = sv['when']; s = y * 4 + q - 1                # the survey's own quarter is column 2
    g, e, u, c = sv['gdp'], sv['jobs'], sv['u'], sv['cpi']
    rate = lambda a, b: 100 * ((a / b) ** 4 - 1)
    quarters = lambda f: {s + k - 2: f(k) for k in range(2, 7)}
    out = {'gdp': quarters(lambda k: rate(g[str(k)], g[str(k - 1)]) if g.get(str(k - 1)) else None),
           'jobs_a_month': quarters(lambda k: (e[str(k)] - e[str(k - 1)]) / 3 if e.get(str(k - 1)) is not None else None),
           'cpi_quarters': quarters(lambda k: c[str(k)])}
    target = Q0 + 6                                     # the second quarter of 2028: the quarter the keys are scored on
    by_year = dict(zip(range(y, y + 4), (u.get(a) for a in 'ABCD')))
    out['unemployment'] = u[str(target - s + 2)] if s <= target <= s + 4 else by_year.get(target // 4) if by_year.get(target // 4) is not None else u['6']
    year = {}                                           # the survey's figure for a calendar year, for quarters beyond its five
    for i, (a, b) in enumerate(zip('ABCD', ' ABC')):
        year[y + i] = {'gdp': 100 * (g[a] / g[b] - 1) if g.get(a) and g.get(b) else None,
                       'jobs_a_month': (e[a] - e[b]) / 12 if e.get(a) is not None and e.get(b) is not None else None,
                       'cpi_quarters': c.get(a)}
    return out, year, s


def apply(cfg, sv, today):
    """The outlook with a later survey laid in. Returns (new outlook file, what changed in plain words), or (None, why not)."""
    y, q = sv['when']; label = f'{y}Q{q}'
    if label <= (cfg.get('outlook_survey') or ''):
        return None, f'the survey of {y} Q{q} is the one the outlook already holds'
    part, year, s = from_survey(sv)
    new = copy.deepcopy(cfg); o = new['outlook']; said = []
    for name, per in (('gdp', 1), ('cpi_quarters', 1), ('jobs_a_month', 3)):
        old = list(o[name]); n = len(old) if per == 1 else (len(old) + 3) // 3
        for i in range(n):                              # i: quarters from 2026 Q4
            k = Q0 + i
            if k < s:
                continue
            v = part[name].get(k)
            if v is None:
                v = (year.get(k // 4) or {}).get(name)
            if v is None:
                v = part[name][s + 4]                   # the last quarterly figure, carried on
            lo, hi = LIMITS[name]
            if not lo <= v <= hi:
                raise Unreadable(f'{name}, {k // 4} Q{k % 4 + 1}: {v:.1f} cannot be a forecast')
            v = round(v, 1) if per == 1 else round(v)
            if per == 1:
                o[name][i] = v
            else:                                       # months: the list starts with November 2026, the second month of its quarter
                for m in range(max(0, 3 * i - 1), min(len(old), 3 * i + 2)):
                    o[name][m] = v
        if o[name] != old:
            said.append(f"{name.replace('_', ' ')}: {old} to {o[name]}")
    lo, hi = LIMITS['unemployment']
    if not lo <= part['unemployment'] <= hi:
        raise Unreadable(f"unemployment {part['unemployment']} cannot be a forecast")
    if round(part['unemployment'], 1) != o['unemployment']:
        said.append(f"unemployment: {o['unemployment']} to {round(part['unemployment'], 1)}")
        o['unemployment'] = round(part['unemployment'], 1)
    entered = cfg.get('outlook_entered') or cfg.get('outlook_date')
    new.update(outlook_survey=label, outlook_date=str(today), outlook_entered=entered,
               outlook_note=f"Survey of Professional Forecasters, {y} Q{q}, read on {today:%B} {today.day}, {today.year}: growth, jobs, unemployment and inflation. "
                            f"{KEPT[0].upper() + KEPT[1:]} as entered by hand ({entered}).")
    return new, said


def compare(cfg, sv):
    """How closely this file's reading of a survey gives an outlook that was entered by hand from the same survey."""
    trial = copy.deepcopy(cfg); trial['outlook_survey'] = ''
    new, _ = apply(trial, sv, datetime.date.today())
    return {k: (cfg['outlook'][k], new['outlook'][k]) for k in ('gdp', 'cpi_quarters', 'jobs_a_month', 'unemployment') if cfg['outlook'][k] != new['outlook'][k]}


def fetch(url=URL, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; fifty-two-keys update; +https://ka82205.github.io/fifty-two-keys/)', 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def refresh(today, path=PATH, read=fetch):
    """Read the survey; if it is later than the one the outlook holds, write the outlook with it laid in.
    Returns (state, words): state is 'new', 'same', 'unreachable' or 'unreadable'."""
    cfg = json.load(open(path))
    try:
        raw = read()
    except Exception as err:                            # noqa: BLE001  the source did not answer: the outlook in hand stays
        return 'unreachable', f'the Survey of Professional Forecasters was not reached ({type(err).__name__}: {str(err)[:80]}); the outlook in hand stays'
    try:
        sv = survey(raw)
        new, said = apply(cfg, sv, today)
        if new is None:
            off = compare(cfg, sv) if cfg.get('outlook_survey') and not cfg.get('outlook_entered') else {}
            return 'same', said + ('' if not off else '; read by rule it would give ' + '; '.join(f'{k} {b} (entered: {a})' for k, (a, b) in off.items()))
    except Unreadable as err:
        return 'unreadable', f'the Survey of Professional Forecasters could not be used: {err}; the outlook in hand stays'
    except Exception as err:                            # noqa: BLE001  a workbook that is not a workbook, or a layout never seen
        return 'unreadable', f'the Survey of Professional Forecasters could not be read ({type(err).__name__}: {str(err)[:120]}); the outlook in hand stays'
    json.dump(new, open(path, 'w'), indent=1)
    return 'new', f"the survey of {sv['when'][0]} Q{sv['when'][1]} is in: " + ('; '.join(said) if said else 'it gives the figures the outlook already had')


if __name__ == '__main__':
    raw = fetch(); sv = survey(raw); cfg = json.load(open(PATH))
    print('survey of', sv['when'], '| the outlook holds', cfg.get('outlook_survey'))
    part, year, s = from_survey(sv)
    print(json.dumps({k: ({f'{a // 4}Q{a % 4 + 1}': round(b, 2) for a, b in v.items()} if isinstance(v, dict) else v) for k, v in part.items()}, indent=1))
    print('by year', json.dumps({k: {a: (round(b, 2) if b is not None else None) for a, b in v.items()} for k, v in year.items()}))
    print('against the outlook in hand:', compare(cfg, sv) or 'the same')
