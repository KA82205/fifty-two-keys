# Fifty-Two Keys: methodology audit

November 2026. Covers the key table (`build.py`), the validation (`test.py`), the 2028 run-ahead (`run_2028.py`), the
data, and the page. Every number below is produced by `research.py` (written to `research.json`) or by `test.py`
(`results.json`), so it can be checked.

The audit changes nothing in the official model. The 52 keys, the five groups and the line at one half are still the
locked version (`locked_keys.csv`). Section 9 lists changes that could be made, with the evidence, the risk and the test
each would have to pass first. Section 10 lists what was done alongside the audit: none of it touches a key or a rule.

## Summary

1. **The record is real but weaker than "15 of 19" sounds.** A rule that uses one fact, "the party wins after one term
   in office and loses after two or more", also calls 15 of 19. A three-variable equation (June approval, second-quarter
   growth, first term), with each election left out of its own fit, calls 16. Nineteen elections cannot tell these
   apart.
2. **The record is in-sample.** The keys were chosen in 2026 by someone who knew every result. No election has yet been
   called in advance. The first real test is 2028.
3. **Two keys use ratings made after the fact, and the record depends on them.** Without Lichtman's own ratings for the
   third-party and contest keys the record is 13 of 19.
4. **The grouping is favourable.** Of 1,346 other ways to group the same keys, 91% do worse than the published one.
5. **The 52 keys carry the information of about nine.** Four of them give the same answer in every election where all
   four exist.
6. **One half is not the break-even point.** All four misses are calls for the party in office. In the record a party
   with 50% to 60% of the keys won one time in three; the count at which it has been as likely to win as lose is about
   60%.
7. **The economy keys are scored on revised figures.** The historical table uses today's data, not what was published
   in each election year. About half the keys are exposed. This has not been measured yet.
8. **Historical and 2028 rules differ for four keys** (third party, contest, the two state keys in the run-ahead), and
   the approval source changes from Gallup to an average of polls.
9. **The 2028 run-ahead is honest about its mean and too sure about its extremes.** Tried on 15 past elections at the
   same distance, the stretch method barely beat each key's plain historical rate, and its chances below 40% were wrong
   more often than right.
10. **"20% of runs above one half" is not a 20% chance of winning.** A rough calibration puts the chance of winning
    nearer 8%, with a range of 1% to 16%. The page must not present the first number as the second.

## 1. What the record shows

The call matched the winner in 15 of 19 elections, 1952 to 2024. The misses are 1952, 2000, 2016 and 2024.

| Check | Result |
|---|---|
| 95% interval for a true hit rate, given 15 of 19 | 57% to 92% |
| Chance of 15 or more for a coin | 1% |
| Chance of 15 or more for a caller as good as "the party in office always loses" (11 of 19) | 5% |
| Random halves of the keys | median 14, middle 80% from 13 to 16 |
| Any one key removed | 13 to 15; 21 of the 52 keys lower the record when removed |
| Other groupings of the same keys (1,346) | 12: 4, 13: 654, 14: 566, 15: 83, 16: 39 |
| Since 1984 only | 8 of 11 |

Three things follow.

**The margin over nothing is thin.** The party in office lost 11 of these 19 elections, so "it always loses" is right
58% of the time. Fifteen is better than that at about the 5% level, and no better than that.

**Several calls sit on the line.** 1968 is at 49.55%. Removing any one of 19 different keys flips it. 1988 (52.3%),
2024 (53.2%) and 1952 (54.0%) are within four points. A model whose calls move with a single key in four elections out
of 19 should not be read as a yes-or-no instrument near one half. The page's bands (toss-up from 50% to 60%) already
say this and should stay.

**The published grouping is a good draw.** Most regroupings score 13 or 14. The published one scores 15 and only 9% do
as well or better. The groups were written down before they were scored, but they were written by someone who knew the
history, and this is what hindsight looks like in a number. The 13-to-14 range is the fairer statement of what this
family of models does.

## 2. Simple rules, scored the same way

"Right" means the call matched who took office. All 19 elections.

| Rule | Right | Misses |
|---|---|---|
| The party in office always loses | 11 | the eight years it won |
| It wins if the economy grew in the second quarter | 11 | 1952, 1968, 1976, 1992, 2000, 2008, 2016, 2024 |
| It wins if more approve than disapprove in June | 14 | 1960, 1976, 2000, 2004, 2016 |
| It wins after one term and loses after two or more | 15 | 1980, 1988, 2020, 2024 |
| **Fifty-Two Keys** | **15** | 1952, 2000, 2016, 2024 |
| Primary Model, rebuilt for every year (5 of 8 when published in advance) | 15 | 1960, 2000, 2020, 2024 |
| Approval, growth and first term in one equation, each election left out | 16 | 1960, 2000, 2024 |
| Lichtman's 13 Keys at his own ratings (9 of 11 since 1984, when he began publishing) | 17 | 2000, 2024 |

On the national vote the picture is the same. Estimating each election's two-party share from a line fitted to the other
eighteen, the typical miss is 2.5 points for the keys, 2.6 for net approval alone and 2.7 for the three-variable
equation. Guessing 50% every time misses by 4.0.

So the keys beat no-information rules clearly, and do not beat one- to three-variable rules. That is not an argument
against them: the keys were never fitted, and a rule that needs no estimation and still matches fitted equations is
worth having. But the page should not suggest that 52 measurements see more than three do. On this evidence they do not.

A caution about the comparison itself. Lichtman's calls before 1984 and the Primary Model's before 1996 were made after
the fact, as were all 19 of ours. Only published forecasts are a fair test, and there the counts are 9 of 11 and 5 of 8.
Ours is 0 of 0.

The repository also holds two series for June approval that do not agree exactly: the average of June polls that scores
the approval keys, and the June figure from Abramowitz's data used for the vote line in `test.py`. One should be chosen
and used throughout.

## 3. How alike the keys are

Across 1,275 pairs of keys with enough elections in common, 28 correlate at 0.7 or more and 138 at 0.5 or more. Inside a
group the average correlation is 0.36 (economy now), 0.30 (economy this term), 0.55 (approval), 0.31 (incumbency) and
0.06 (party strength); between groups it is 0.09.

- "GDP grew in the second quarter" and "GDP per person is higher than a year ago" give the same answer in all 19
  elections. Real spending per person agrees with both in all 17 elections where it exists, and the state-growth key in
  all 12.
- "Spending grew faster this term" and "unemployment is lower than when the term began" agree in all 15.
- Eight keys form one cluster that moves together: A01, A02, A03, A04, A06, A08, A09 and A18. It is one question, "is
  the economy growing?", asked eight ways.

A standard measure puts the 52 keys at about 9 independent ones. (With 19 elections no set of keys can show more than
18, so this is partly a ceiling.)

**What redundancy does here.** Because each group counts the same, a key's weight is one fifth divided by the size of
its group: 1.1% for an economy-now key, 1.3% for an economy-this-term key, 3.3% for an approval or party-strength key,
2.9% for an incumbency key. The eight-key growth cluster weighs 8.9% together, less than three approval keys. So the
duplication inside the economy groups mostly dilutes itself. It does not make growth dominate. What it does do is make
"52" a misleading count, and it hides the real weights: the six party-strength keys, five of which are settled by one
midterm election, carry 20% of the model.

**Experiments, for comparison only.** Every key counted equally: 14 of 19. One vote for each cluster of alike keys
(average correlation 0.6 or more): 14 of 19. Neither is better, so there is no case here for re-weighting.

## 4. The five equal groups

There is no theory that says the economy now, the economy this term, approval, party strength and incumbency each
deserve one fifth. Equal weights are a neutral prior, and they have one practical defence: they are not fitted. Leaving
any one group out gives 14 to 16 of 19, so no group is carrying the model or wrecking it.

Two consequences should be stated on the page.

- **Party strength is decided two years early.** For 2028 all six of its keys are already no. The count cannot exceed
  80%, and the other four groups need to average more than 62.5% for the party to pass one half. The midterm result
  therefore does most of the work in the 2028 call, long before the economy keys are scored.
- **Weights change across years.** Twelve keys cannot be scored for 1952 and eight for 1956, because their data begin
  later. The count uses only the keys that exist, so in 1952 an economy-now key weighs about 1.5%, not 1.1%. This is
  the right way to handle a missing key (the alternative, counting it as no, would be worse), but it means the early
  elections were judged by a different model. The 1952 miss sits in that zone.

## 5. Hindsight and leakage

**Ratings made after the fact.** Two keys are Lichtman's own ratings: E03 (no significant third party), which he scores
by the final vote, and E04 (no contest for the nomination). The final vote is not known in June. Without those ratings
the record is 13 of 19: 1968 and 1988 flip. `test.py` reports this, and the page mentions it in the fine print; it
belongs next to the headline. B01 also uses his rating for 1952 and 1956, where the data do not reach back far enough.

**Revised figures.** Every economy key for 1952 to 2024 is scored on the figures as they stand today. GDP, income,
payrolls, industrial production, spending and the state indexes are all revised, some of them for decades. A key that
was "no" on the figures published in July 1992 may be "yes" on today's. About 25 of the 52 keys rest on series that are
revised; stocks, oil, sentiment, approval, seats and the nomination keys are not. Nobody has measured how many
historical entries would change. Until that is done the record should be described as "on today's figures".

**Who chose the keys.** The rules compare with zero, a year ago, the start of the term, the last term, or 50%. None was
estimated from results, and that is a real protection. It is not a complete one. Which 52 measures to include, and how
to group them, was decided with the history in view. The regrouping test in section 1 puts a size on it.

**Changes that were tried and dropped.** Three adjustments that raised the record to between 16 and 18 were tried and
removed because each was picked knowing which elections it would fix. A fourth, a tilt by party, was removed for the
same reason. That was the right call, and the log of them should stay public.

## 6. Rules, cut-offs and edges

**History and 2028 are scored differently in four places.**

| Key | 1952 to 2024 | 2028 |
|---|---|---|
| E03 third party | Lichtman's rating, from the final vote | no third candidate at 10% or more in June polls |
| E04 contest | Lichtman's rating | nominee has two thirds of the delegates |
| A18, B15 states | state coincident indexes | a stand-in fitted on national figures, until the indexes exist |
| C01 to C06 approval | Gallup, polls completed in June | an average of polls of all adults (Gallup stopped in 2026) |

The first two should be rebuilt for the past by the 2028 rule (section 9). The approval change cannot be avoided, but
the gap between Gallup and a poll average should be estimated on the years when both exist.

**When the model can actually be scored.** "June figures" are not available in June. Payrolls arrive in early July,
prices and production in mid-July, spending, second-quarter GDP and the state indexes at the end of July. The earliest
honest date for a final count is about August 1 of the election year, and that count uses first estimates, which are
later revised. The page should say "scored at the start of August on June figures".

**Edges.** Ties are no, except where the rule says "at least" (C01, B01) or "did not lose" (D05, D06). That is stated
in `build.py` but applied key by key, and three conventions are in use. Two keys sit on their edge often:

- D04 (the party won more than half of all votes last time) is within one point of 50% in 6 of 19 elections, and in
  2028: Trump won 49.8%.
- C01 (at least half approve) was within two points in 1988 (49.5) and 2016 (51.1); net approval was within three
  points of zero in 1968, 2004 and 2012.

An average of polls carries decimals that a single Gallup figure did not. The rule should fix the precision (one decimal)
and the window (polls that finished in the month) before June 2028, not after.

**No tie in unemployment has ever occurred** in June against a year earlier or against the start of the term, so the
"a tie is no" rule has not yet decided a key. It may in 2028: unemployment is 4.1% now and forecasters expect 4.2%
throughout.

## 7. The 2028 run-ahead

The run-ahead is not the model. It estimates where the 44 open keys may land. It was audited separately.

**How much history is behind it.** 200,000 runs sounds like a large sample. It is 117 overlapping 20-month stretches,
drawn from 15 four-year blocks of history; the 39 stretches with a recession come from 7 recessions. The simulation
error is a tenth of a point. The real uncertainty is how well 15 blocks and 7 recessions describe the next 20 months.
Resampling those blocks, and letting the recession share vary from 20% to 40%, moves the headline share of runs above
one half between 15% and 24%.

**Assumptions set by hand.** The recession share (30%), the outlook for each series (the Survey of Professional
Forecasters, entered by hand each quarter), and eleven odds for the approval and nomination keys. The page shows what
happens when the main ones move. One could be checked against history, and it holds up: approval would have to rise
about 18 points by June 2028 to reach 50%, and disapproval fall about 15 to get under 50%. From the autumn of the
midterm year to June of the election year, approval has never risen by more than 12.5 points in 19 cycles (the typical
change is about minus 1, with a spread of 9.5). The run-ahead's 1% and 3% are consistent with zero in nineteen.

**Dependence.** One stretch scores all 33 economy keys together, which keeps their real co-movement. Approval is tied
to the economy only through one switch (a recession lowers the odds that approval is rising). The nomination keys are
independent of both. Real elections are more connected than that: a recession hurts approval levels and invites a
contested nomination. The spread of the count is probably somewhat too narrow as a result.

**A test on the past.** The stretch method was run at the same distance before each election from 1968 to 2024, on 13
year-over-year keys that need only monthly series, using stretches that do not overlap the 20 months being forecast. No
forecasters' outlook exists for those years, so each series was carried at its own pace; this tests the method, not the
full 2028 run.

| The method said | Cases | It happened |
|---|---|---|
| under 20% | 5 | 80% |
| 20% to 40% | 18 | 61% |
| 40% to 60% | 63 | 44% |
| 60% to 80% | 72 | 75% |
| 80% or more | 37 | 76% |

Across 195 cases its error (Brier score 0.238) was barely below that of each key's plain historical rate (0.243) and of
a flat 50% (0.250). It picked the right side in 123, against 97 for the plain rate. The cases are far from independent:
there are 15 elections, and an economy's keys move together.

The reading is that at 20 months the method knows which way a key usually goes and little more. Chances near 60% to 80%
held up. Chances under 40% did not: those keys came true more often than not. A key shown at 15% today should be read
as "leans no", not as six to one against.

**Not a chance of winning.** The run-ahead reports the share of runs in which the count ends above one half, 20%. That
is a statement about the count. Turning it into a chance of winning needs the record of what happened at each count,
and there the break-even is near 60%, not 50%. A logistic curve through the 19 elections, laid over the same runs,
gives about 8%, and resampling the elections moves it between 1% and 16%. That curve rests on 19 points and is research,
not a forecast. It is enough to say that the chance of winning is lower than the share of runs above one half, and that
neither number deserves a decimal.

## 8. What was not examined

- Real-time (vintage) data. Proposed below; not started.
- Published forecasts of other models beyond Lichtman's and the Primary Model. A fair comparison needs each model's
  forecast as published before the election (for example from the *PS: Political Science & Politics* symposia since
  1992), not a refit.
- The state coincident indexes, which are model-based and heavily revised, were taken as given.
- The approval polls from 1952 to 2024 were taken as given.

## 9. Proposed changes

None of these has been made. Each would be run as a separate experiment against the locked model, and adopted only if
it passes the test in its last column. A change that improves the historical record is not a reason to adopt it; a
change that removes hindsight is, even if the record falls.

| # | Proposal | Evidence | Risk | Test before adopting |
|---|---|---|---|---|
| 1 | Freeze the key list, every rule, tie convention, poll window and scoring date for 2028, and publish the freeze with a hash | The page says the list is not frozen; rules for four keys differ between history and 2028 | None to accuracy; removes room to adjust later | The freeze exists before any 2028 key is scored |
| 2 | Rebuild E03 and E04 for 1952 to 2024 by the 2028 rules (June polls of third candidates; delegate counts) | The record is 13 without the ratings | The record will probably fall | Sources found for all 19 years; the rebuilt keys replace the ratings whatever the record |
| 3 | Score the economy keys on the figures published by August 1 of each election year (ALFRED and the Philadelphia Fed real-time data) | About 25 keys rest on revised series | Vintages are missing for some series and early years | Report how many entries change and whether any call changes; keep both tables |
| 4 | State the record as a range on the page: 15 of 19 as built, 13 without after-the-fact ratings, 13 to 14 for typical groupings | Sections 1 and 5 | Less striking headline | None needed; this is reporting |
| 5 | Merge or flag keys that have never disagreed (A01 with A02; B03 with B04) | Section 3 | Changes the count; easy to tune | Only as a labelled experiment until 2028 is scored; equal-weight and cluster versions both score 14 |
| 6 | Shrink run-ahead chances for year-over-year keys toward each key's historical rate | Section 7: no skill beyond the plain rate at 20 months | Loses real information in clear cases (keys already decided by the figures) | The same test on the past, with the shrunk chances, must score better than both the raw chances and the plain rate |
| 7 | Replace the hand-set approval odds with the historical distribution of approval changes from the midterm autumn | 19 cycles available; agrees with the hand-set odds today | Thin tails: 19 cases cannot support a 1% chance | Leave-one-cycle-out error against the hand-set odds |
| 8 | Tie approval and the nomination keys to the economy in the run-ahead | Section 7, dependence | More assumptions | Compare the spread of the count with and without, and state both |
| 9 | Fetch the forecasters' outlook automatically | It is typed in by hand each quarter | A parsing error would move every economy key | Checks on each value, and a held-back update on failure, as for the other figures |
| 10 | Keep a forward scorecard | Nothing has been called in advance | None | Every archived run is kept; in November 2028 the archive is scored as it stands |

## 10. Done alongside this audit

No key, rule, group or threshold was changed.

- The run-ahead now reruns every week on fresh figures. Published months replace simulated ones, and a key lands when
  its June 2028 figures are out. On the day of the change it reproduced the previous run exactly.
- Figures are checked before use. One that fails is held back and the run is marked as failed. A missing figure leaves
  a key open; it is never scored as no.
- Every run is archived under its own time stamp with its figures, assumptions and versions. Archive files are not
  rewritten.
- Tests cover the locked table, the checks, the archive, and landing on made-up future figures.
- Approval now comes from polls of all adults, read directly from the poll listing rather than typed in.
- The page reports a range for the run-ahead, separates "runs above one half" from a chance of winning, and shows the
  findings above next to the record.

## Reproducing this

```
python test.py          # the record and its robustness: results.json
python run_2028.py      # the run-ahead: projection_2028.json
python research.py      # everything in sections 1 to 7: research.json
python tests/test_model.py && python tests/test_update.py && python tests/test_engine.py
```
