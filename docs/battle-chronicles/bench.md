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

    effect = { trigger_event = bc_chronicles.0011 }

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

Then:

    python tools/ck3.py probe 'BC: eve variant'

Three lines at roughly equal counts is the pass. **One line, or two, means the
`random_list` or `bc_eve_variant_trigger`'s guard failed** - and those are two
different fixes, which is why the marker is per variant.

`BC: eve popup 0011` counts every raise and is the denominator.

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

New on 2026-08-19 and **never run**. Both ladders now escalate on ledger depth
instead of being capped by it, and the two markers below are the only readout.

    python tools/ck3.py probe 'BC: momentum depth'
    python tools/ck3.py probe 'BC: moment '

Expected, against a measured mean of 4.2 moments per battle:

| marker | expected share |
|---|---|
| `momentum depth none` / `moment minor` | ~72% |
| `momentum depth one` / `moment major` | ~23% |
| `momentum depth two` / `moment decisive` | ~5% |

The two lists should track each other closely - they read the same
`var:bc_battle_moments` at the same two rungs, 4 and 6. **If they diverge, one
of the two escalators is reading the variable on the wrong scope**, which is the
failure this pairing exists to catch.

`depth none` at 100% means `var:bc_battle_moments` did not exist where
`bc_add_momentum_effect` ran - the guard fell through to the else arm, not that
battles were short. Check `BC: fired` in the same run: a run with moments and no
depth is the scope bug, a run with few moments of either is just short battles.

`BC: wound` should stop reading zero for the first time. It hangs off the
decisive and major arms only, needs `SWING = down`, and is capped at one per
battle by `var:bc_battle_wounded`.

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
in an old plan. `effect` is the one that exists.

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
