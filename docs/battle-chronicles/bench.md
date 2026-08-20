# The battle bench

How to exercise Battle Chronicles from a running game, without a 7-minute
restart per question. Everything here runs in the in-game console, which means
**only the user can drive it** - the console is an overlay, not an OS window, so
`SendKeys` types into the game instead of into it.

Launch with `-debug_mode`. `python tools/ck3.py launch` does that; note it
detaches, so exit 0 is not the game closing.

Read every result with `python tools/ck3.py probe '<regex>'`, never from stdout
and never from `ck3.py errors` - that is a tail slice and mod script errors are
logged at the TOP of a 46 MB `error.log`.

---

## 0. Before anything, confirm the mod is loaded

A workspace mod can silently fall out of `dlc_load.json` when the Paradox
launcher regenerates it, and the symptom is a perfect run with zero `BC:` lines.

    python tools/ck3.py playset list        # Battle Chronicles must be present
    python tools/ck3.py probe 'BC:'         # after any test below

`probe` exits **1** when nothing matches. For an error sweep that non-zero exit
is the pass condition.

---

## 1. The eve, with no battle at all

This is the cheap one and it answers most of what the eve needs answering.
`bc_chronicles.0011` can be raised directly: every scope it reads
(`bc_eve_foe`, `bc_eve_ground`) is `exists`-guarded, so raising it outside a
battle renders the guarded fallback arms instead of failing.

    event bc_chronicles.0011

**Use `event`, not `effect`.** `effect = { trigger_event = ... }` was written here
from the API dump and never run; the console answers **`effect is empty`** to it
and nothing reaches script - no log line either, so the failure is silent in
`error.log`. Verified 2026-08-19. `event` also bypasses `bc_eve_offer_effect`
entirely, so there is no cooldown to clear between raises.

Fire it ten to fifteen times, dismissing each. What to look for:

| surface | pass |
|---|---|
| the title | all five of `The Lines Close` / `Before the First Order` / `The Last Quiet` / `What the Day Gets Built On` / `Nothing Is Settled Yet` appear |
| first paragraph | four different intro lines appear |
| second paragraph | reads the `stranger` arm - correct, there is no foe scope |
| third paragraph | reads the `open` arm - correct, there is no ground scope |
| the three base options | the trio CHANGES between eves, across three sets |

The three sets are variant 1 `press / hold / wait`, variant 2 `thin the centre
/ refuse the left / everything forward`, variant 3 `down off the horses / where
it is thickest / hold the ends`. Options d-k will not show: they gate on a
ground scope, a foe scope, dread or stress, and only the last two are reachable
outside a battle.

**Judge this one on screen, not from the log.** The three variant markers are at
`bc_eve_events.txt:502`, `:532` and `:563`, which are the `:option` effects of
each variant's **first option only** - so a marker means "the player clicked
option A of variant N", never "variant N was rolled". An earlier revision of this
section claimed three roughly equal `probe` lines were the pass; that can only
happen if you pick the first option on every single eve, and dismissing is what
the section tells you to do.

    python tools/ck3.py probe 'BC: eve variant'
    python tools/ck3.py probe 'BC: eve popup 0011'

So read it as: `eve popup 0011` is the true raise count, the variant lines are a
subset bounded by how many eves you answered, and **a missing variant line is not
evidence of anything** unless you answered its first option. To measure the roll
itself a marker would have to go next to the `random_list` in `immediate`
(`:450-453`); there is none today.

RUN 2026-08-19: 12 raises, all 5 titles and all 3 trios seen on screen - the
`random_list`, `var:bc_eve_variant` and all three arms of
`bc_eve_variant_trigger` PASS. The log showed variant 2 twice and variant 3 once,
which is just the three eves that were answered.

Also seen: the dread option renders **truncated** to one line
(`... across that fiel ...`). CK3 clips option text rather than wrapping it, so
long option strings are a real cosmetic defect, unrelated to the variant work.

---

## 2. Forcing a real battle

`Advanced Cheat Menu` is already enabled in the playset (slot 35) and its UI is
far less error-prone than hand-writing `start_war` effects. Use it to give
yourself a war and to spawn both hosts.

The eve additionally requires `var:bc_battle_size >= 3`, which the size ladder
in `bc_ledger_effects.txt` sets from `num_total_troops >= 10000` on the COMBAT
scope - **ten thousand men across both hosts, not per side**. A small skirmish
will produce moments and no eve, and that is correct behaviour, not a bug.

You must be **personally leading** the army. `type = commander` roots on the
commander, so `is_ai = no` there means the player is commanding in person; it
is not a "player is watching" test.

---

## 3. Clearing the cooldowns to re-fire

**The exact `effect` console syntax below is still unverified** - the form
`effect = { ... }` failed with `effect is empty` in §1 on 2026-08-19, and the
alternatives (`effect remove_character_flag = X`, or the braces with no inner
spaces) have not been tried. `event` covers the eve without any of this; the
flags below only matter for re-firing moments inside a battle.

Every throttle in the mod is a character flag, so all of them clear in one line
on the character you are playing:

    effect = { remove_character_flag = bc_eve_cooldown remove_character_flag = bc_toast_cooldown remove_character_flag = bc_chronicle_recent remove_character_flag = bc_popup_cooldown }

| flag | days | what it gates |
|---|---|---|
| `bc_chronicle_recent` | 15, size-scaled on commanders | whether any moment may fire for that character |
| `bc_toast_cooldown` | 10 | whether the RECIPIENT is shown a toast |
| `bc_popup_cooldown` | 60 | whether a moment escalates to a full pop-up |
| `bc_eve_cooldown` | 90 | whether the eve is offered |

To re-test the eve back to back, clear `bc_eve_cooldown` only - clearing
`bc_toast_cooldown` at the same time changes what you are measuring.

---

## 4. Counting toasts per battle

This is the regression test for the recipient toast budget. Fight one battle of
roughly 30 days while personally commanding, then:

    python tools/ck3.py probe 'BC: fired'

That counts moments, not messages - a moment whose recipient was over budget
still fires, applies its momentum and writes its memory, and only the toast is
suppressed. So the numbers to compare are:

- `BC: fired *` - total moments. Should be unchanged from before the budget.
- toasts actually seen on screen. Should now be about **three per 30-day
  battle** (10-day flag against a 5-day roll), where it was of order thirty.

There is no marker for "toast suppressed" and adding one would cost a
`debug_log` on every AI commander in the world. Count what you see on screen;
the moment count in the log is the control.

---

## 5. Measuring the depth escalator

Both ladders escalate on ledger depth instead of being capped by it. Rungs are
**9 and 13** as of 2026-08-20, the fourth pair. Every pair measured so far:

| rungs | moments/side | minor | major | decisive | verdict |
|---|---|---|---|---|---|
| 4 / 6 | 6.3 | 40% | 19% | 41% | top rung below the mean |
| 8 / 13 | 7.5 | 61% | 21% | 18% | still hot |
| 11 / 16 | 6.14 | 83.9% | 11.6% | 4.5% | **regression, under the 5% floor** |
| **9 / 13** | — | *73.2%* | *17.1%* | *9.7%* | predicted, unrun |

**THE MEAN IS NOT A CONSTANT OF THE MOD — RE-READ IT EVERY RUN.** This is what
broke 11/16. It was fitted against the 7.5 mean measured at rungs 8/13; the next
run's mean was 6.14, an 18% drop, so the same rungs sat far further out on the
tail than the fit assumed and decisive collapsed to 4.5%. The rungs did not change
behaviour, the battle sample did. A rung pair is only meaningful next to the mean
it was fitted against, so always quote the two together.

9/13 is fitted to the 11/16 run's own two points - `P(d>=11) = 0.161` and
`P(d>=16) = 0.045` give `r = 0.775` per step. Two points cannot tell a geometric
tail from a heavier one, so this is the best available estimate, not a settled
number.

**The top rung is not aimed at the 5% in the table below.** The tail fit puts 5%
near depth 21; the top rung aims at ~10% on purpose, because `bc_wound_effect` and
style RANK 3 hang off `decisive` and nothing else, and 5% starves them back toward
the three runs of zero the ledger already documents. Judge the next run against
**~72 / ~18 / ~10**, and treat a decisive share under 5% as a regression, not a win.

    python tools/ck3.py probe 'BC: momentum depth'
    python tools/ck3.py probe 'BC: moment '

`probe` groups by `args#` hash, so it will split each marker across call sites.
For shares, count the whole log instead:

    grep -cF "BC: moment decisive" "<user dir>/logs/debug.log"

Wanted, on the tier list: **~72% minor / ~18% major / ~10% decisive** - the same
figures as the paragraph above, and not the ~23/~5 this line carried until
2026-08-20. The 5% was the spec's inherited target and was deliberately abandoned
for the reason given above; a bench that states both cannot judge the run it
drives.

**EVERY RUN-2 FIGURE IN THE REST OF THIS SECTION WAS A MID-SESSION READ AND WAS
WRONG UNTIL 2026-08-20.** The log is written live, and the counts below were taken
while `ck3.exe` was still running - they undercounted by roughly half. They have
been replaced with counts from `logs/archive-20260819-run2/debug.log`, taken after
the process left `tasklist`. The one figure that was always right is `:155`'s 41%
decisive for the 4/6 rungs. This is the third time this trap has put a wrong
number into a document; read counts only after the game has exited.

### Do NOT read a divergence between the two lists as a scope bug

The previous revision of this section said the two lists must track each other
and that **divergence means one escalator reads `var:bc_battle_moments` on the
wrong scope**. The 2026-08-19 run diverged hard - depth 80/7/13 against tier
40/19/41 - and that diagnosis was **wrong**. There is a third cause, and it is
the likelier one:

**The momentum call is gated at the template and the tier call is not.** 420 of
the templates wrap their momentum call in a settled-gate, while
`bc_record_effective_tier_effect` is called unconditionally from inside
`bc_record_moment_effect` (`bc_ledger_effects.txt:260`), one line after the
increment. So the tier list has one entry per moment and the momentum list has
one entry per *grant*. **The two totals are not comparable and the two shares are
not comparable.** In that run: 1175 moments, 329 momentum calls.

Order of elimination when they disagree:

1. **Totals far apart** (329 vs 1175) - the gate is refusing calls. Expected to
   some degree; it is only a fault if `depth none` also dominates, because that
   means the calls that do get through are all a battle's first moment.
2. **Tier shares wrong but internally smooth** - the rungs are mistuned against
   the current moment volume. Re-fit, do not go looking for a scope.
3. **`depth none` at or near 100% with a healthy total** - now suspect the scope.
   The else arm of `bc_add_momentum_effect` fires when `var:bc_battle_moments`
   does not exist where it ran.

### The rungs are fitted to moments per COMMANDER, not per battle

This is what went wrong in the first run. 4 and 6 were fitted to "4.2 moments per
battle", a figure the 434-template batch had already invalidated, and the rungs
are not read per battle anyway - `bc_battle_moments` accumulates on the
commander, and every knight's moment on that side increments it too.

Measure it as **moments ÷ commander-sides**:

    grep -cF "BC: fired" debug.log                 # moments      1175
    grep -cF "BC: combat end cleanup" debug.log    # sides         186

1175 ÷ 186 = **~6.3 per commander**. The old top rung of 6 therefore sat *below*
the mean, which is why 41% of all moments resolved decisive. A rung pair is only
sane if the lower one is above the mean.

8 and 13 were fitted to that run's three buckets **as they were read
mid-session** - P(depth<4)=0.37, P(4-5)=0.18, P(>=6)=0.45 - by fitting a
declining tail to `P(N>=d)` and solving for the 72/5 points. The final log says
those buckets were **0.40 / 0.19 / 0.41**. The two are close enough that 8/13 was
not a bad pair for the wrong reason, but the fit was made against numbers nobody
had yet earned the right to use. **That is a model, not a census.** The honest way
to settle it is a
depth histogram, which does not exist today; `debug_log` cannot print a variable,
so it would need bucket markers beside the increment in
`bc_record_moment_effect`.

### The wound follows the top two rungs

`BC: wound gates passed` reads **96 at 4/6, 55 at 8/13, and 24 at 11/16**, after
three runs of zero - the arm is alive, and it is already falling as designed. It
hangs off the decisive and major arms only, needs `SWING = down`, and is capped at
one per battle by `var:bc_battle_wounded`. Raising the rungs makes those arms
rarer, so **expect this number to keep falling**; if it returns to 0 the rungs went
too far.

24 at 11/16 was the second reading agreeing that those rungs overshot - the series
96 → 55 → 24 is closing on the 0 that means the arm is dead. **9/13 lowers the
rungs, so this number should now RISE**, and a rise is the expected direction for
the first time in the series. Judge the 9/13 run against **comfortably above 24**;
if it does not move, the rung change did not reach the wound arm.

This line read **62** until 2026-08-20, which was neither run: it was a
mid-session read of the 4/6 run, whose final log says 96. Scored against 62, a
rise from 55 to 56-61 would have been recorded as the expected fall.

---

## 6. Inspecting BC state on a character

`every_living_character` is a global iterator (`Supported Scopes: none`), so a
whole-world sweep is one line. Useful for leak checks:

    effect = { every_living_character = { limit = { exists = var:bc_eve_variant } debug_log = "BENCH: eve variant present" } }

`var:bc_eve_variant` is deliberately never cleared, but it should only ever
exist on characters that have been PLAYED - `bc_eve_offer_effect` gates
`is_ai = no` before raising the event. More than a handful of hits means the
gate leaked.

Note `debug_show_variables` **is not a CK3 console command** despite appearing
in an old plan. `effect` is the one that exists - but see §3: the `= { ... }`
spelling used above is the one the console rejected on 2026-08-19, so confirm the
working form before trusting a zero-hit sweep from this line. A silent parse
failure and a clean leak check look identical.

---

## What this bench cannot answer

- **Whether a modifier reaches the combat roll.** The advantage breakdown in
  the combat view is the only readout, and only family 1 (`advantage`) appears
  there; family 2 is `army_*`/`knight_*` and shows in the army stat breakdown.
- **Whether the roll pool is balanced against AGOT's own events.** BC markers
  only log when BC wins. Measuring the losses needs a probe mod that marks the
  AGOT events too - see `open-questions.md`.
- **Game rules.** They are baked into a save at creation and nothing logs which
  option is active. Put a marker in the run if the rule matters.
