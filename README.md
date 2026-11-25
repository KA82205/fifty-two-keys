# Fifty-Two Keys

Fifty-two yes-or-no questions about the party that holds the White House, each answered by a fixed rule
from public data. When more than half go its way, the keys say it wins the election. Inspired by Allan
Lichtman's 13 Keys to the White House. A separate project from Tipping Point: nothing here is used by the
Nowcast, and nothing here reads from it.

The figures behind the 2028 page are checked every hour, and the page is rebuilt whenever one of them has changed. The key list is not frozen yet. The name follows the count.

**Read the audit first.** `research/audit.md` ([on the site](https://ka82205.github.io/fifty-two-keys/audit.html)) sets out what the record does and does not show, where hindsight
enters, and what should change before 2028. The short version: 15 of 19 is the record as built; a one-fact rule
calls as many; without two keys rated after the fact it is 13; and no election has been called in advance yet.

## What it is

- **52 keys in five groups:** economy now (18), economy this term (15), approval (6), party strength (6),
  incumbency and nominations (7). Every key is true when it favors the party in office. The full list and
  every rule are at the top of `build.py`, and on the page in `docs/index.html`.
- **Equal groups.** A group's score is the share of its keys that are true. The index is the average of the
  five group scores.
- **One call.** An index above one half says the party in office wins the election, meaning the Electoral
  College and the presidency. At one half or below it loses. The count decides: nothing is fitted to past
  results and no single key can overrule the rest. The model makes no other forecast: no share of the vote,
  no map.

## Record, 1952 to 2024 (19 elections)

| | Result |
|---|---|
| Called the winner | 15 of 19 (the misses: 1952, 2000, 2016, 2024) |
| When the keys said the party in office would lose | right 7 times of 7 |
| When the keys said it would win | right 8 times of 12 |
| The 11 elections since 1984 | 8 of 11 |
| Calls more than five points from the line | 13 of 15 |
| Calls within five points of the line (1968, 1988, 2024, 1952) | 2 of 4 |

All four misses are calls that the Democrats, in office each time, would win.

- **2000 and 2016.** The party in office won the most votes nationwide and lost the Electoral College. In
  2000 Al Gore lost Florida, and with it the election, by 537 votes after the Supreme Court stopped the
  recount. In 2016 Hillary Clinton lost Michigan, Pennsylvania and Wisconsin by about 78,000 votes
  combined. The keys read the country as a whole, so they cannot see a split like that coming.
- **1952 and 2024.** An unpopular president left the race in the election year (Truman in March, Biden in
  July) and the party nominated someone who had not run in the primaries. A strong economy carried the
  count just over the line both times, to 53.9% and 53.2%.

## How sure a call is

The call is yes or no. The count behind it says how much to trust it. This is a description of the record, printed by `test.py`
under HOW SURE. It changes nothing in the model: the call is still made at one half.

| Share of keys in favor | Label | Elections | Party in office won | Its average share of the two-party vote |
|---|---|---|---|---|
| under 40% | clear loss | 1980, 1992, 2008, 2020 | 0 of 4 | 46.3% |
| 40% to 50% | likely loss | 1960, 1968, 1976 | 0 of 3 | 49.5% |
| 50% to 60% | toss-up | 1952, 1988, 2024 | 1 of 3 | 49.3% |
| 60% to 70% | lean win | 1956, 1972, 2000, 2004, 2016 | 3 of 5 | 54.4% |
| 70% and up | clear win | 1964, 1984, 1996, 2012 | 4 of 4 | 56.8% |

- The ranges are every ten points: round numbers, not tuned. The labels only name what happened in each range.
- Under one half the party in office lost all 7 times and at 70% or more it won all 4. From 50% to 70% it won 4 of 8, so a call
  to win in that range is closer to a coin flip than the bare call suggests.
- Against the national vote the count does better than against the winner. The correlation between the index and the party's
  share of the two-party vote is 0.82; the line is share = 38.07 + 24.42 x index, which is 50.3 at one half, though the line at
  one half was never fitted. Ten points of keys is worth about 2.4 points of vote.
- Read as a call on who wins the most votes, the keys are right in 17 of 19 (misses 1952 and 2024). In 2000 and 2016 they had
  the vote right and the Electoral College wrong.
- Estimating each election's vote from the other 18, the typical miss is 2.5 points. The largest are 1972 (7.8 above the line)
  and 1952 (6.9 below).
- The 2028 prediction at the top of the page is stated the same way: the call (win or lose) and its range. Until the keys are
  scored it uses the count with every open key landing the way it leans, now 27 of 52 and 42.0% group by group, which is a
  likely loss. Beside each range it shows the share of the run-ahead runs that end there.

## Guarding against overfitting

The model has 52 keys and 19 elections to check them on, which would be a recipe for overfitting if anything
were fitted. Nothing is: no key has a weight, no cut-off is estimated, and the line is one half. That leaves
one way for the past to leak in, which is through choices made after seeing the results. So the rule is:

**No key, group or scoring rule is chosen or changed because of how it scores on these elections.** The
key list and the five groups were written down before they were scored, and that is the model.

### What was taken out for breaking the rule

Three changes were made after the results were in. Each raised the record, and each was chosen by looking at
the elections the keys had missed. All three are out. `test.py` still reports what they would have done.

| Change | Record on paper | Calls it changes |
|---|---|---|
| A group of their own for the three primary keys | 16 of 19 | 1952 |
| The primary keys scored on the November nominee, not on whoever ran in New Hampshire | 16 of 19 | 2024 |
| Both of those | 17 of 19 | 1952, 2024 |
| Two keys that could overrule the count ("deal-breakers") | 18 of 19 | 1952, 2016, 2024 |

Each one changes the elections it was meant to fix and no other call. That is what a fix fitted to the past
looks like: nothing else in the record supports it. Choosing among these versions by their record on earlier
elections would not have helped either. Election by election since 1984 that gets 8 of 11, the same as the
model.

### Checks

`test.py` runs these every time, under "checks for overfitting". None of them changes the model.

- **Which keys.** A random half of the keys calls 14 of 19 in the typical draw, and between 13 and 16 in
  four draws out of five. The full list is not a lucky pick of keys.
- **One key left out.** The record stays between 13 and 15. It is never higher, and it is lower without any
  one of 21 keys, because the two closest correct calls sit right on the line.
- **One key the other way.** A single key scored the other way would change the call in 1968 (any of 19
  keys), 1988 (8 keys) and 2024 (3 keys). Every other call holds.
- **Regrouping.** Of the 1,346 ways to split three keys off a group into a group of their own, 1,224 score
  worse than the model, 83 the same and 39 better. Thirty-five of the 39 are splits of the incumbency and
  nominations group: more weight on that group would have helped, and on the economy it would have hurt.
- **One group left out.** 16 of 19 without either economy group, 14 without approval, 15 without party
  strength or without incumbency and nominations. The economy holds two of the five groups. The record
  would be one election better with one, and that was not acted on.
- **Lichtman's own ratings.** Two keys use his ratings for past elections (third party and nomination
  contest). Without them the record is 13 of 19: the two closest calls, 1968 and 1988, go the other way.
  His third-party rating also uses the final vote, which nobody has before the election. Scored the other
  way it would change a call only in 1968 and 1988, and neither year is in doubt: George Wallace was a
  major third candidate all through 1968, and there was none in 1988.

### What the checks say

The record is not built on fitted numbers or on a lucky set of keys. It is thin at the margin. Four calls
were within five points of the line and the keys got two of them, which is a coin toss. Away from the line
they got 13 of 15. A fair reading of 15 of 19 is "about 14, give or take one or two", and less than that for
an election that ends up close to one half.

### What cannot be fixed before 2028

- The keys were written in 2026 by someone who knew how these elections went. No test on the same 19
  elections can remove that. The first election the model has not seen is 2028.
- Economic figures are today's revised ones, not the first estimates published before each election.
- All four misses came with a Democrat in the White House. With nineteen elections that may be chance.

### The lock

`locked_keys.csv` and `locked_index.csv` hold every key, index and call as they stood on November 22, 2026.
`test.py` compares them with the current run and lists anything that differs, including a regrouping that
changes no key. After a deliberate change: add a line to the change log below with the record before and
after, then run `python test.py --lock`.

## Change log

Changes to the model made after its keys were first scored.

| Date | Change | Record | Status |
|---|---|---|---|
| November 21, 2026 | Two keys that could overrule the count | 15 to 18 of 19 | Taken out November 22 |
| November 22, 2026 | A group of their own for the three primary keys | 15 to 16 | Taken out the same day |
| November 22, 2026 | The primary keys scored on the November nominee | 15 to 16 | Taken out the same day |

One change of a different kind is kept. The model first scored the national vote (17 of 19 on that basis)
and now scores who won the election (15 of 19). That changed the question, not the keys, and it lowered the
record.

Also on November 22, 2026, the page and `test.py` began reporting how sure each call is (see "How sure a call is"). That
adds labels to the record. No key, index or call changed, and the locked copy still matches.

## Next to Lichtman's 13 Keys and the Primary Model

The same 19 elections, scored the same way: did the call match who won? (`test.py` prints this; the page
shows it.)

| | Lichtman's 13 | Primary Model | Fifty-Two Keys |
|---|---|---|---|
| Called the winner, 1952 to 2024 | 17 of 19 | 15 of 19 | 15 of 19 |
| Forecasts made before the election | 9 of 11 (1984 on) | 5 of 8 (1996 on) | none yet |

Lichtman's ratings are the ones listed on Wikipedia, read with his rule (six or more false keys and the
party in office loses). His keys miss 2000 and 2024. The Primary Model is scored as its own site describes
it: in hindsight it calls every election from 1952 to 1992 except 1960, and its forecasts from 1996 missed
2000, 2020 and 2024. Both of them call 1952 and 2016, which these keys miss.

Two things put the gap to Lichtman in proportion. Up to 1980 every column is hindsight: his keys were built
on the elections to 1980, and these were written in 2026. And both sets of keys have a handful of calls that
one key would change. For his, a single key rated the other way changes four calls (1992, 1996, 2000, 2016),
and he has three of those right. For these it changes three (1968, 1988, 2024), with two right. Away from
those, his keys are right in 14 of 15 and these in 13 of 16.

Six of Lichtman's thirteen keys have a counterpart here: three scored by a rule (recession, long-term
growth, mandate), one plain fact (sitting president), and two still at his own rating for past elections
(third party, nomination contest). His seven judgment keys are left out.

## 2028 so far

Republicans hold the White House. Eight keys are settled, seven of them against: fewer House seats than
after 2022, no House majority, no Senate majority, under half of all votes in 2024, lost House seats and
Senate seats at the midterm, and no sitting president on the ticket. One is in favor: it is the party's
first term. Party strength is 0 of 6, so to get above one half overall the other four groups would need to
average more than 62.5% of their keys.

The states so far: weighted the same way over the term to date, state economies were growing through
September 2026 in 49 of the 50 states and Washington, D.C. (all but Alabama and Hawaii), which hold 525 of
the 538 electoral votes. This is a reading, not a score. The two state keys are scored on the figures to
June 2028.

Gallup stopped publishing presidential approval in February 2026, so the six approval keys will need an
average of polls of all adults for 2028.

## 2028, run ahead

`run_2028.py` estimates how the 44 open keys are likely to land and writes `projection_2028.json`. It is an
estimate, rerun whenever a figure it reads changes (see "Updates, archive and tests"). It is not part of the model, it changes no key, and it was not checked against
any election result. The page shows it under "The run ahead".

| | |
|---|---|
| Share of keys in the Republicans' favor, by group, on average | 40% |
| Half of the runs end between | 31% and 48% |
| Nine runs in ten end between | 20% and 57% |
| Runs that end above one half (the keys would say the Republicans win) | 20%, about 1 in 5 |
| The same, in runs without a recession | 28% |
| If every open key goes the likelier way | 27 of 52 in favor, 42% by group |

Expected share of yes answers by group: economy now 64%, economy this term 47%,
approval 18%, party strength 0% (settled), incumbency and nominations 69%.

So on today's outlook the keys would say the Republicans lose. In the back-test, the party in office lost
every time the keys were between 35% and 45% (1960, 1976, 2020).

### How the economy keys are run (33 keys)

1. Start from the figures published so far (FRED) and the outlook forecasters hold (`data/outlook.json`).
2. Take every stretch of 20 months since 1964 that began, like now, with unemployment at or below its normal
   rate and no recession under way: 117 stretches, 39 of which ran into a recession.
3. Lay each stretch over today's outlook and score all 33 keys on the result. One stretch gives one complete
   set of keys, so keys that move together in real life move together in the run.
4. Weight the stretches so that 30% of runs include a recession. History alone gives 33%, and
   forecasters put the risk of a falling quarter near 20%.

The outlook: growth of 2.1% to 2.3% a year, unemployment near 4.2%, about 50,000 new jobs a month, and
inflation slowing from 3.8% this year to 2.4% in 2027 and 2.3% in 2028 (Survey of Professional Forecasters,
November 16, 2026; the Federal Reserve's September projections are close). Oil at about $80 a barrel in
mid-2027 and $70 in mid-2028 (futures, the Energy Information Administration's November outlook). The S&P 500
starts from its close of 6,910 on November 20, after a fall of 8.6% in a week.

Three series are handled apart. Unemployment is put halfway between the forecasters' flat path and its drift
in the past stretches, and never below 3.4%. Payroll jobs follow the outlook and unemployment, because past
job booms came with a fast-growing workforce. The two state keys use a stand-in for the state indexes: across
the twelve elections from 1980, the electoral-vote-weighted measure is explained almost entirely by growth and
the change in unemployment (R-squared 0.98 without 2020).

### How the other keys are run (11 keys)

These are odds set by judgment from polls and from the 19 elections, and they are the softest part.

- **Approval.** The reading is the average, pollster by pollster, of the polls of all adults that finished in the past 30
  days, from VoteHub's listing (32% approve and 65% disapprove on November 22, 2026, from three pollsters). The three keys
  that need half the country on side get a 1% to 3% chance. The three that ask whether approval is rising
  are drawn from what they did in the 19 cycles, with years when the president was not running counted double.
- **Third candidate.** 88% that none reaches 10% in June polls. One did in 4 of 19 elections.
- **The nomination.** Rubio and Vance are level nationally (35% and 34%) and Vance leads in New Hampshire (39%
  to 27%). 68% that the nominee wins New Hampshire; Republican nominees did in 8 of 11 open contests. 75% that
  the nominee has two-thirds of the delegates.
- **The challenger.** 63% that the Democratic nominee does not win New Hampshire. The field is split five ways,
  and the state is in dispute with the national party over its date.

### The open keys, from least to most likely

B05 0%, C01 1%, C02 1%, C06 2%, B13 9%, B03 16%, B14 20%, C05 28%, C04 34%, B01 37%, B04 37%, A05 40%, B08 40%, A07 40%, B06 40%, A08 41%, A17 41%, C03 44%, B07 54%, A03 56%, B15 56%, A06 59%, B02 61%, A16 63%, E07 63%, A15 64%, A02 66%, A01 67%, E05 68%, A09 70%, A14 70%, B11 71%, A12 72%, A13 74%, E04 75%, A10 76%, B12 76%, A04 77%, A11 85%, A18 85%, E03 88%, E06 88%, B09 89%, B10 95%.

### How far the answer moves

| If | Average share in favor | Runs above one half |
|---|---|---|
| Recession in 20% of runs | 41% | 23% |
| Recession in 40% of runs | 38% | 17% |
| A rougher nomination season | 38% | 16% |
| A smoother nomination season | 40% | 22% |
| No chance that disapproval falls below half | 39% | 19% |
| An 8% chance that it does | 40% | 22% |

### What to keep in mind

- The run is a second layer of estimates on top of a model whose own record is 15 of 19.
- The approval and nomination odds are judgment. The economy keys lean on forecasts made before the stock
  market's fall in the week of November 16 and on a conflict with Iran whose course nobody knows.
- Nineteen months is a long time. The run will move as figures come in, and it should be re-run rather than
  read as a forecast of the election.

Sources: [Survey of Professional Forecasters, fourth quarter 2026](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/spf-q4-2026);
[Federal Reserve projections, September 16, 2026](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm);
[GDP, third quarter 2026, advance estimate](https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026);
[Short-Term Energy Outlook, November 2026](https://www.eia.gov/outlooks/steo/pdf/steo_full.pdf);
[oil futures strip of October 15, 2026](https://baratelliinstitute.com/oil-futures-curve);
[Surveys of Consumers](https://www.sca.isr.umich.edu/);
[market close of November 20, 2026](https://investrade.com/market-review-november-20-2026/);
VoteHub's listing of approval polls (api.votehub.com); RealClearPolitics averages for
the [Republican](https://www.realclearpolling.com/polls/president/republican-primary/2028/national) and
[Democratic](https://www.realclearpolling.com/polls/president/democratic-primary/2028/national) nominations, and New Hampshire
([Republican](https://www.realclearpolling.com/polls/president/republican-primary/2028/new-hampshire),
[Democratic](https://www.realclearpolling.com/polls/president/democratic-primary/2028/new-hampshire));
[2028 Democratic primary calendar](https://en.wikipedia.org/wiki/2028_Democratic_Party_presidential_primaries).

## The two state keys

The idea is from Enns, Colner, Kumar and Lagodny (2024): take the Philadelphia Fed's coincident index for
every state and average its monthly growth over the term, with quarter q of the presidency weighted
0.55 ** (15 - q). April to June of the election year counts in full, the quarter before it 55% as much, the
one before that 30%, and so on. 0.55 is the paper's value; it is not fitted here. `states.py` computes the
measure for every state and every election since 1980 (the indexes begin in 1979) and writes
`state_economy.csv`. Both keys were written down at the top of `states.py` before they were scored.

- A18: the measure is above zero in states holding a majority of the electoral votes. True in 10 of 12
  elections; false in 1980 and 2020.
- B15: the measure is higher than at the same point of the previous term in states holding a majority of the
  electoral votes. True in 5 of 11: 1984, 1996, 2004, 2012 and 2024.

Notes on the calculation:

- The measure is computed from quarter-end index values for the last six quarters, which carry 97% of the
  weight. On the California figures printed in the paper's appendix this gives 0.224 against the published
  0.2245. Today's revised index gives 0.186 for the same months; the keys use today's figures throughout.
- The District of Columbia has no index. As in the paper's data it is given Maryland's and Virginia's,
  averaged month by month.
- Six states' indexes begin in April 1979 (Kansas, Oklahoma, Texas, Virginia, Washington, Wisconsin), so
  their 1980 figure uses the last four quarters.

## Tested and left out

These are still computed by `test.py`, under "kept for the record", but they are not part of the model and
not on the page. The three changes that were taken out for overfitting are listed above.

- **A share of the national vote.** Two straight lines (the index, and the president's June net approval),
  fitted to past elections and averaged. Average miss 1.9 points with each election left out; right side of
  50% in 16 of 19. Left out because the model makes one call: who wins the election.
- **A map by national swing.** Every state moved from its last result by that vote forecast. With each
  election since 1980 forecast from earlier ones only, it called the Electoral College in 10 of 12, missing
  2000 and 2016 like the keys themselves.
- **Moving each state by its own economy.** On top of the national swing, each state was moved by how its
  weighted growth compared with the country's. The average state miss stayed at 2.53 points and no
  Electoral College call changed, so by the rule fixed in advance it was left out.
- **Fitted weights.** On the 27-key pilot they matched every election on paper and only 14 of 19 once each
  election was held out.

## What changed from the 27-key pilot

- 23 keys added: industrial production, consumer spending, factory jobs, jobless claims, wages, oil, housing,
  the stock market's direction this year, three more approval readings, midterm seat changes, and how each
  party's New Hampshire primary went. Then the two state keys.
- Three of Lichtman's own ratings are now scored by rule: the recession key (the Sahm rule), the long-term
  growth key (from GDP per person) and the mandate key (from House seats). The rules differ from his ratings
  once each: 1960 for recession and 1984 for long-term growth.
- No pilot key was dropped. Each batch of keys was written down before it was scored against a result.
- Approval for 2021 to 2024 comes from Gallup's own trend for Biden. The course file mixes in polls of the
  vice president for those years.
- The model makes one call, who wins the election. Earlier versions scored the national vote.

## Updates, archive and tests

`update.py` runs every hour (`.github/workflows/update.yml`) and can be started by hand. Most runs end after the first
two steps, because nothing has changed.

**What is read, and when.** Approval polls are read on every run. The economic series are read when a release could be
out: on working days at 8, 9, 10 and 11 in the morning, Eastern time (the statistical agencies publish at 8:30 and
10:00, and FRED carries a new figure within the hour), at 2 and 8 in the afternoon and evening of every day in case a
release is late or a morning run did not start, and on the first run of each day.

**When the model is run again.** After reading, every file the run ahead reads is fingerprinted and compared with the
fingerprints of the last run (`data/fingerprint.json`). The date a file was fetched is not part of the fingerprint. If
nothing differs and the day is the same, the run ends: nothing is recalculated and nothing is saved. The first run of
each day always goes through, because the page's date and the 30-day approval window move with the day.

1. **Fetch.** Twelve monthly and five quarterly series, the latest S&P 500 and oil prices and the 50 state indexes from
   FRED; approval polls from VoteHub.
2. **Check.** Each series must be a table of that series, in order, with every figure inside the range the series can
   take. A figure for a date not held before must sit within a tight limit of the figure before it; a figure already
   held must not have been revised by more than the series is revised (`MONTHLY`, `QUARTERLY`, `DAILY`, `STATE_RULE`
   in `update.py`). The two limits are separate on purpose: the swings of 2020 and 2021 are in the tables already and
   are checked only for revision, so they do not loosen the limit on a new figure. A wrong unit, a slipped decimal
   point, a flipped sign, a zero or a re-based history is held back, and so is a real move as large as spring 2020
   until somebody has looked at it. A series that fails is **held back**: the figures already in the repository stay,
   the run goes on with them, and it ends as failed so that somebody looks, at once when a figure is first held and
   then once a day until it is settled. `--trust SERIES` accepts a held series after it has been looked at. A source
   that cannot be reached is tried again on the next run and reported once it has been out of reach for two days.
3. **Run.** `run_2028.py` reads the published months and runs only the months still ahead. A key **lands** when the
   figures it is scored on are published through June 2028: the economy keys from FRED, the six approval keys from the
   June 2028 polls, the two state keys from the state indexes by the rule in `states.py`. The nomination keys are
   entered in `data/outlook.json` when they are settled. A key with a missing figure stays open. It is never scored as
   no.
4. **Archive.** Each run whose projection says something the last one kept did not is written to `archive/` under its
   own time stamp, with the national figures it used, fingerprints of the longer files, the assumptions, the checks,
   the versions, and a list of what changed and why. "Something new" is a headline figure, a key that landed or changed
   its lean, a key whose odds moved by a point or more, a new month or quarter of figures, or a change to the method or
   the assumptions; a price that ticked without moving any of these is not. Archive files
   are opened for writing once and never again. `archive/index.json` is the list; the page shows it as "Forecast
   history".
5. **Build.** `make_page.py` rebuilds the page, the downloads in `docs/data/`, and `docs/keys.json`, a small feed of
   the headline figures. The Margin reads that feed. If the repository has a secret named `DISPATCH_TOKEN` (a token
   allowed to start workflows in the `the-margin` repository), The Margin is told the moment the feed changes; without
   it The Margin finds the change at its own next hourly check.

**FRED needs a key on GitHub.** FRED's download links do not answer requests from GitHub's servers, so the workflow
reads FRED through its API, which needs a free key. Add it once as a repository secret named `FRED_API_KEY`
(Settings, Secrets and variables, Actions). Without it a run still refreshes the approval polls, reruns,
archives and rebuilds, keeps the last good economic figures, and ends as failed to say so.

The outlook (the Survey of Professional Forecasters) and the odds for the approval and nomination keys are still typed
in by hand, in `data/outlook.json`. Between entries the latest figures are carried along the shape of the last outlook.

Tests (`tests/`, run before every update): the key table against the locked copy; that a missing figure stays
missing; the checks, on new figures and on history separately; when the economy is read, when the model is run again
and when a run ends as failed; the archive; and the run ahead on made-up future figures, where keys must land when June 2028 is
published and not before, and a hole in the figures must leave a key open.

On November 25, 2026 the run ahead was changed to work this way (version `2026.11b`). On the same figures it gave the
same answer as the version of November 22, key for key. Two things then changed the numbers a little: housing starts
and jobless claims are now held at the average of their latest months rather than at a typed-in level, and approval is
read from polls of all adults (32% approve) rather than from an average of all polls (38%).

### The run ahead, tried on the past

`research.py` runs the stretch method at the same distance before each election from 1968 to 2024, on 13
year-over-year keys, with stretches that do not overlap the months being forecast. Across 195 cases it picked the
right side in 123 (each key's plain record: 97), but its error was barely lower (Brier 0.238 against 0.243). Chances
from 60% to 80% held up; chances under 40% came true more often than not. So the run ahead knows which way a key
usually goes and little more, and the page gives ranges, not decimals. Resampling the history in four-year blocks, with
the recession share between 20% and 40%, moves the share of runs above one half between 15% and 24%.

That share is not a chance of winning. In the record a party with 50% to 60% of the keys won one time in three. A
logistic curve through the 19 elections puts the 2028 chance of winning near 8% (1% to 16%). It is research and is
shown as such.

## Run it

```
python states.py       # optional: prints the state measure and writes state_economy.csv
python build.py        # scores the keys: keys_table.csv, keys_raw_values.csv
python test.py         # the record and the checks: results.json (needs numpy)

python run_2028.py     # the run ahead for 2028, projection_2028.json (about fifteen seconds)
python research.py     # the audit's numbers: research.json
python update.py       # the update: read, check, and if anything is new run, archive, build (--offline to skip the reading)
python make_page.py    # docs/index.html, from template.html (checks what the page says against results.json)
```

The logo is `docs/logo.svg` (`logo.png`, `logo-lockup.png`, `favicon.svg`, `apple-touch-icon.png` and `og.png` are made from it). The ring has fifty-two marks, one for each key.

`keys_table.csv` has one column for each key, then two columns that are not keys: two primary keys as they
would be under a change that was tried and left out, which `test.py` uses to report it.

The page is one self-contained file: data, script and both typefaces are inside it, so it makes no outside
requests and can be put on any static host as it is.

## Limits

- The record is a back-test. See "Guarding against overfitting" for what was checked and what cannot be.
- Nineteen elections. One election more or less changes the picture.
- Equal groups make the small groups heavy. A key in the incumbency and nominations group moves the index
  by 2.9 points and an approval or party key by 3.3, against 1.1 for a key in the largest economy group.
- 2000 and 2016 count as misses, although the party in office won the most votes both times.
- The two state keys can be scored from 1980 and 1984 only. Earlier elections are scored without them.
- Two keys are still Lichtman's own ratings for past elections (third party, nomination contest). Both
  have a rule for 2028.
- Twelve keys cannot be scored for 1952 and eight for 1956, because some series start in 1959 or later.
- Left out on purpose: head-to-head polls; scandal, unrest, charisma and policy change (judgment calls);
  war and peace (no casualty rule simple enough to be fair gives sensible answers).

## Data

- `data/course/`: monthly and quarterly economic series, population, approval polls (Roper Center) and
  state results, from the data files of Harvard's Gov 1347 election analytics course (2024), as shared at
  https://github.com/julienberman/Election-Analytics.
- `data/fred_md_2025-06.csv`: the FRED-MD monthly database, June 2025 vintage, as shared at
  https://github.com/tdistudent27/fred-md-data. The series it shares with the course file agree.
- `data/fred_early.csv`: values before 1959 for industrial production, manufacturing jobs, hourly earnings
  and the oil price, read from FRED's series pages (INDPRO, MANEMP, CES0600000008, WTISPLC).
- `data/state_coincident_index.csv`: the Philadelphia Fed's State Coincident Indexes, read from FRED
  (series ALPHCI to WYPHCI) in November 2026: the quarter-end values for the six quarters before each
  election from 1980 to 2024, plus June 2025 and June 2026. 
- `data/state_index_this_term.csv`: the same indexes month by month from December 2024 to September 2026,
  read from FRED by `update.py`. Used for the reading of the current term and, once it runs through June 2028,
  to score the two state keys.
- `data/fred_md_2026-09.csv`: the FRED-MD monthly database, September 2026 vintage, as shared at
  https://github.com/ThevinSilva/Fred-MD. Used only by the run ahead.
- `data/approval_polls.json`: polls of presidential approval as listed by VoteHub (api.votehub.com), refreshed by `update.py`.
  Only polls of all adults count toward the reading; campaign and party internals are left out.
- `data/outlook.json`: the forecasters' outlook, the odds for the approval and nomination keys, and the keys already
  settled with the reason for each. Entered by hand.
- `archive/`: every published run. See "Updates, archive and tests".
- `data/latest_monthly.csv`, `data/quarterly.csv`, `data/latest.json`: the latest monthly and quarterly figures and daily
  prices, read from FRED by `update.py` (UNRATE, PAYEMS, MANEMP, CPIAUCSL, INDPRO, DPCERA3M086SBEA,
  CES0600000008, HOUST, UMCSENT, MCOILWTICO, SP500, ICSA; A191RL1Q225SBEA, A067RL1Q156SBEA, B230RC0Q173SBEA,
  A939RX0Q048SBEA, A229RX0Q048SBEA). Used only by the run ahead.
- `data/congress_seats.csv`: Wikipedia, "Party divisions of United States Congresses". Senators who caucus
  with a party are counted with it from 2007.
- `data/nh_primaries.csv`: Wikipedia, "New Hampshire presidential primary". For the party in office it
  lists who ran in New Hampshire and who was the nominee in November. Eisenhower's 50% in 1952 is from
  Wikipedia's page on that primary (46,661 votes of 92,865); the overview page shows 56%.
- `data/lichtman13_wikipedia.csv`, `data/keys_history.csv`: Lichtman's ratings and the two-party vote.
- `data/june_net_approval_gallup.csv`: The Economist's file of Abramowitz's data through 2016; Gallup's trend
  tables for 2020 and 2024.
- `data/state_results_2024.json`: certified 2024 results by state.
- Midterm results for 2026: Associated Press counts as reported on November 18, 2026.
- `fonts/`: Besley and Libre Franklin, both under the SIL Open Font License 1.1 (licenses alongside), from
  the Fontsource packages. They are embedded in the page.
- State weighting: Enns, Colner, Kumar and Lagodny, "Understanding Biden's Exit and the 2024 Election: The
  State Presidential Approval/State Economy Model", PS: Political Science & Politics (2024).
