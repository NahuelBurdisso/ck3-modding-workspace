# Battle Chronicles — the toast slot becomes competitive

2026-08-20. Design only. Nothing here is implemented and **nothing here may be
implemented until the 11/16 rung run has been read** — see Section 7.

Companion documents: `../battle-chronicles/open-questions.md` (the agenda),
`../battle-chronicles/bench.md` (how to drive a run),
`2026-08-15-battle-chronicles-depth-design.md` (the ladder this builds on).

## 1. The problem

The mod's player-facing bandwidth is tiny and it is allocated by a timer.

444 templates exist. A commander's side averages **7.5 moments per battle** —
that is the 2026-08-19 run 3 figure, at the 8/13 rungs; the run before it, at
4/6, measured 6.3. Both are `moments ÷ BC: combat end cleanup`, and Run 1 in
Section 7 re-measures it at 11/16, so treat 7.5 as the working figure and not a
constant.

The player sees about **4 toasts** per 30-day battle after the flood cap shipped
that same day — and that figure is the weakest number in this document. **There is
no marker for a toast**; `bc_start_toast_cooldown_effect` runs only for the
player, so its count is single-digit and nothing in any log records what reached
the screen. The 4 is one player's on-screen count of one battle on 2026-08-19,
n = 1, against `bench.md` §4's *prediction* of "about three". Section 8 treats it
as an order of magnitude, never as a baseline to fit against.

Which 4 is decided
by two things, neither of which is importance:

- `bc_toast_cooldown`, a 10-day character flag on the recipient, first-come
  first-served;
- CK3's weighted `chance` roll, which picks *which* template speaks.

So a rare hand-authored major moment is silently swallowed if a batch context
read fired three days earlier. The depth escalator shipped on 2026-08-19 raises a
moment's effective rung as a battle deepens, and the player has no way to
perceive that, because the rung has no influence on whether the moment is spoken.

The content is not the bottleneck. 434 of the 444 templates are batch-generated
context reads and 437 of 444 request `TIER = minor`; that is honest, and
`2026-08-15-battle-chronicles-depth-design.md` argues at length why promoting
them is the wrong fix. What is wrong is that the escalation the mod computes is
never shown.

## 2. What this changes

A moment whose **effective** rank is major or decisive may speak over a cooldown
that a minor moment set. It draws on a second, scarcer budget of its own.

Two consequences, stated plainly because one of them is a cost:

- The 7 templates that request `major` or `decisive` outright can preempt from a
  battle's first moment. The other 437 can preempt only once depth has escalated
  them past rung 11 — which is the battle turning, and is exactly the moment
  worth interrupting for.
- **CK3 cannot un-send a toast.** Preemption can only ever *add* a message, never
  swap one. A design that holds total volume constant is impossible. Section 6
  bounds the increase.

## 3. Why it is cheap: zero call-site edits

Two properties of the existing code, both verified mechanically rather than
inferred, make the parameterless version work.

**The effective rank is already computed and thrown away.**
`bc_record_effective_tier_effect` (`bc_ledger_effects.txt:329`) resolves the
post-escalation rank in three mutually exclusive arms and writes only a
`debug_log`. It has exactly **one** call site, `bc_ledger_effects.txt:260`,
inside `bc_record_moment_effect`.

**The record call always precedes the toast gate, in the same scope.** Checked
across all 444 sites with `D:/ck3/tools/_bcorder.py`:

    bc_commander_phase_events.txt
      pairs: 238  events: 476
      out-of-order pairs: 0
      depth mismatches: 0
    bc_knight_phase_events.txt
      pairs: 206  events: 412
      out-of-order pairs: 0
      depth mismatches: 0

Every `bc_record_moment_effect = { ... }` is followed by exactly one
`limit = { bc_can_toast_trigger = yes }`, and the toast `if` block sits exactly
one brace level deeper — i.e. inside the same enclosing scope. In knight
templates that scope is the `scope:combat_side.side_commander ?= { ... }` wrapper,
so the rank is written on, and read from, the toast's recipient. That script sits
in `tools/` with the other `_bc*` scanners and is tracked rather than scratch,
because it guards an invariant this design depends on; re-run it after any bulk
edit to the phase-event files. It is already tracked; the outstanding ask is only
to document its two limits in its own header — its `SIDE` constant is dead, and
its brace counting does not strip comments, so an unbalanced brace inside a
comment would skew the depth column.

Because the rank is on the scope the gate already evaluates on, the gate needs no
parameter, and **no template is edited.** The change is **four definitions and one
comment, across three script files**:

| file | what changes |
|---|---|
| `bc_ledger_effects.txt` | `bc_record_effective_tier_effect` (4.1), `bc_clear_scratch_effect` (4.4), and a stale comment at `:271` (4.5) |
| `bc_scripted_triggers.txt` | `bc_can_toast_trigger` (4.2) |
| `bc_scripted_effects.txt` | `bc_start_toast_cooldown_effect` (4.3) |

Two non-script artefacts are also part of this change and not follow-up work:
`docs/battle-chronicles/bench.md` and the workspace memory file
`project_battle_chronicles.md`. See 4.6.

## 4. The mechanism

### 4.1 Store the rank — `bc_ledger_effects.txt`

One line in each of `bc_record_effective_tier_effect`'s three arms, beside the
existing `debug_log`:

    set_variable = { name = bc_last_moment_rank value = 3 }   # decisive arm
    set_variable = { name = bc_last_moment_rank value = 2 }   # major arm
    set_variable = { name = bc_last_moment_rank value = 1 }   # else arm

In the decisive and major arms the new line goes **above** `bc_wound_effect`, not
appended to the arm. `bc_ledger_effects.txt:352-356` records that the wound call
is last on purpose, so `BC: wound` can only ever appear after the
`BC: moment decisive` that caused it, and the pairing stays legible in a
500k-line log. Appending would silently break that ordering.

### 4.2 Let the gate read it — `bc_scripted_triggers.txt`

    bc_can_toast_trigger = {
    	is_ai = no
    	OR = {
    		NOT = { has_character_flag = bc_toast_cooldown }
    		AND = {
    			NOT = { has_character_flag = bc_toast_cooldown_high }
    			exists = var:bc_last_moment_rank
    			trigger_if = {
    				limit = { exists = var:bc_last_moment_rank }
    				var:bc_last_moment_rank >= 2
    			}
    		}
    	}
    }

**The `exists` sibling plus `trigger_if` is mandatory and is not defensive
padding.** CK3 does not short-circuit and guarantees no evaluation order among
siblings, so `exists = var:X` and `var:X >= 2` as plain siblings in an `AND`
still evaluates the comparison when the variable is absent and logs a read of a
missing variable. `bc_record_moment_effect`'s own header at
`bc_ledger_effects.txt:265-269` documents this trap, and
`bc_depth_rung_one_trigger` is the shipped example of the correct shape. The
first draft of this design got it wrong.

The `exists` sibling is load-bearing in a second way: a `trigger_if` whose
`limit` is false evaluates to **true**, so without the sibling the `AND` would
pass vacuously whenever the variable is absent — a rank-less toast would preempt.

`is_ai = no` stays the first row because it is the cheapest rejection and reads
as the gate's headline. **It does not make the rest conditional.** CK3 evaluates
every sibling regardless of order, so the guard above is required for AI
recipients too, and any argument of the form "row 1 already excluded that case"
is invalid in this codebase.

### 4.3 Spend the budget, and mark the preemption — `bc_scripted_effects.txt`

    bc_start_toast_cooldown_effect = {
    	# READ BEFORE WRITE, so the OLD flag state is still visible. Every one of
    	# the 444 call sites is the first statement inside a bc_can_toast_trigger
    	# gate, so "base held at entry" is equivalent to "passed through the high
    	# arm while base was held" — i.e. this branch IS the preemption, exactly.
    	# It is also the only obtainable counter: a trigger cannot log.
    	if = {
    		limit = { has_character_flag = bc_toast_cooldown }
    		debug_log = "BC: toast preempt"
    		add_character_flag = { flag = bc_toast_cooldown_high days = <fitted, Section 7> }
    	}
    	add_character_flag = { flag = bc_toast_cooldown days = 10 }

    	# Denominator for the Section 8 table: how often a rank-2+ moment spoke at
    	# all, by either arm. Not a budget, just a count.
    	if = {
    		limit = { exists = var:bc_last_moment_rank }
    		if = {
    			limit = { var:bc_last_moment_rank >= 2 }
    			debug_log = "BC: toast rank2"
    		}
    	}
    }

The nested `if` rather than two rows in one `limit`, for the reason in 4.2.

**THE HIGH FLAG IS SET ONLY BY A PREEMPTION, NEVER BY AN ORDINARY RANK-2+ TOAST,
AND THE FEATURE DIES IF THAT IS GOT WRONG.** The obvious alternative — set it
whenever the rank is 2+, including on toasts that took a free base slot — is
self-defeating in exactly the case this design exists to serve. Past rung 16
every moment is rank 3, so every toast would refresh a 20-day high flag while the
10-day base expires under it, the high arm could never pass again, and preemption
would become structurally impossible for the rest of the battle. It would also
make the Section 8 diagnostics undecidable: "preempt 0 with rank-2 toasts
counting" would be produced both by a feature that is unnecessary and by a
correctly wired one that over-refreshed itself, and the table would advise
reverting a working change. The high budget pays for **interruptions**, so only an
interruption spends it.

### 4.4 Clear the scratch — `bc_clear_scratch_effect`

    remove_variable = bc_last_moment_rank

**This is required, and not for the reason it first appears to be.** It is *not*
needed to stop a stale rank preempting: 3 proves the record always precedes the
read, so the gate always sees the current moment's rank. It is needed because
`bc_record_effective_tier_effect` runs for **every AI commander in the world** —
`is_ai = no` gates the toast, not the ledger — so without the clear,
`bc_last_moment_rank` accumulates as a permanent variable on every character who
has ever commanded. `bc_clear_scratch_effect` is invoked under
`side_commander ?=` and **outside** the aftermath gate at
`bc_aftermath_events.txt:321` and `:443`, i.e. on both sides of every combat in
the world, so it does reap that accumulation.

One residue survives it, and is accepted. A pop-up option answered *after* combat
end calls `bc_record_moment_effect` again — the leak already documented at
`bc_ledger_effects.txt:271-276` — and so rewrites `bc_last_moment_rank` after the
clear. It is harmless: Section 3's ordering proof means the next battle's first
moment overwrites the value before any gate reads it, and it affects only the 21
`bc_events.txt` sites, which never toast. It is the same accepted-leak class as
`var:bc_eve_variant`.

### 4.5 Fix a stale number while in the file

`bc_ledger_effects.txt:271` reads "Eight of the eighteen call sites are pop-up
options." **Both numbers are wrong.** The corrected sentence is *"Twenty-one of
the four hundred and sixty-five call sites are pop-up options"* — 465 = 238
commander + 206 knight + 21 in `bc_events.txt`, and all 21 of the `bc_events.txt`
sites sit inside `option` blocks while no phase-event site does. Fixing only the
denominator would put a fresh wrong number in the same header. The comment
predates the 434-template batch; the substance of the warning it introduces (a
pop-up option answered after combat end has had `bc_battle_size` cleared) is
still correct and must survive the edit.

### 4.6 Teach the bench the new flag

**Prerequisite, already done — not a task.** `bench.md` §5's run-2 figures were
mid-session reads throughout and undercounted by roughly half (888 moments / 236
momentum calls / 128 sides against a true 1175 / 329 / 186; `BC: wound gates
passed` 62 against a true 96). They were replaced with counts from
`logs/archive-20260819-run2/debug.log` in `3b52fb6`, and the same 62 was corrected
in the workspace memory. Sections 7 and 8 below are written against the corrected
bench; if a future reader finds them disagreeing, the bench is the one to trust,
because it now carries the provenance.

**The one bench edit this design owes**, and it must land with the code, not
before it, because the flag does not exist until then:

- **`bench.md:117`** is the single line the bench tells you to paste to clear the
  cooldowns and re-fire moments inside a battle, and **§3's flag table claims to
  enumerate every throttle in the mod** — it currently lists exactly the four `bc_`
  flags that exist, so it is complete today and becomes wrong the moment 4.3
  ships. Add `bc_toast_cooldown_high` to the clear line and the table.

That edit is load-bearing for the verification, not tidiness. A 20-day flag that
survives the bench's cooldown clear makes preemption impossible for the remainder
of the test session, producing exactly the `preempt 0` reading Section 8 instructs
the reader to revert on — the feature would be reverted on the strength of a bench
that failed to clear it.

## 5. Rejected alternatives

**A flag instead of a variable** (`bc_moment_rank_high`, `days = 1`). Avoids the
missing-read problem entirely. Rejected: day-granular flags linger for the rest of
the day, so a rank-1 moment later the same day would inherit a rank-2 grant. The
variable is overwritten on every moment and cannot.

**Parameterising `bc_can_toast_trigger = { RANK = $TIER$ }`.** Rejected: it would
require editing all 444 call sites for information already present on the scope,
and every parameter added is a chance to hit the declared-but-unread compile
failure that silently kills every call site.

**Shortening the base cooldown or reweighting `chance`.** Rejected: weights decide
*which* moment speaks, not how often the player hears one — the flood fix's header
records this. The base cooldown measured PASS on 2026-08-19 and changing two dials
at once makes the next run unreadable.

**Writing more physical moments so the ladder has real content to escalate.** The
larger and better idea, and deferred, not dismissed. It costs a content session of
the shape that produced 434 templates which all collapsed to minor, and it cannot
be *felt* until the bandwidth problem is fixed — a new major moment competing for
a slot allocated by a timer is a new major moment nobody sees. This design is its
precondition.

## 6. Volume, bounded honestly

Phase events roll every `COMBAT_EVENT_DAYS = 5`. Because 4.3 spends the high
budget only on interruptions, the ceiling is **at most** `battle_days ÷ 10`
ordinary toasts plus `battle_days ÷ high_days` preemptions. It is not "2 per
window" — at `high = 20` a 20-day window already permits 2 base toasts, so that
framing double-counts.

**The two budgets are sub-additive, not independent, and that is deliberate.** A
preemption also runs the unconditional `add_character_flag = { flag =
bc_toast_cooldown days = 10 }`, resetting the ordinary clock — so an interruption
costs the player a later routine toast. Keep it that way: moving the base write
into an `else` would "restore independence" and raise the ceiling to the full
additive bound, which is a real volume change dressed up as a tidy-up.

Both fits, over a 30-day battle:

| fit | additive bound | walked timeline |
|---|---|---|
| `high = 10` | 3 + 3 = 6 | 3 ordinary + 2 preemptions = **5** |
| `high = 20` | 3 + 1.5 = 4.5 | 3 ordinary + 1 preemption = **4** |

At the 72/18/10 target p = 0.28, so Section 7 selects `high = 20` and the expected
outcome is 4-5. **Section 8's band of 6 is retained across both fits** — it is the
worse case's bound, so it stays valid if Run 1 measures p below 0.20 and the fit
drops to `high = 10`. It is a ceiling, not a prediction.

At the 11/16 rungs' *target* split of 72/18/10, rank-2+ is 28% of moments, so the
player's side sees ~2.1 preemption candidates per 30-day battle against a cap of
`30 ÷ high_days`. Expected outcome at `high = 20`: **+1 per battle**, total ~5
against a measured 4.

Two second-order effects, both accepted:

- **Volume is per-day, not per-battle.** A 60-day battle allows ~6 base and ~3
  high, so ~9 toasts. Long battles get proportionally more, by design.
- **Crescendo.** Depth escalates monotonically within a battle, so past rung 16
  *every* moment is rank 3. Both budgets then run flat out — one ordinary toast
  per 10 days and one interruption per `high_days` — and every toast the player
  sees late in a long battle is top-rank. This is thematically right, and it
  means "decisive" is a per-moment share, not a per-toast one: a long battle will
  feel decisive throughout, and should.

## 7. Sequencing — this ships second, and the reason is not caution

**The 11/16 rungs have never been run.** Everything in Section 6 rests on a
72/18/10 split which is the *target* of that unrun change, not a measurement. The
two shares that have actually been measured are 40/19/41 (rungs 4/6) and
61/21/18 (rungs 8/13). If the real rank-2+ share lands near 18%, preemption fires
rarely enough to read as dead; if the rungs undershoot, it fires constantly.

Shipping this before that run also stacks two unmeasured changes onto a single
measurement, which is the failure `bench.md` §5 was rewritten to prevent.

So: **Run 1 first, with no code from this design in the build.** Run 1's job is
the criterion already written in `bench.md` §5 — `grep -cF` over the final
`debug.log` for `BC: moment minor|major|decisive` at ~72/~18/~10, moments ÷
`BC: combat end cleanup` for the denominator, and `BC: wound gates passed`
**nonzero and below 55**. The series is 96 at the 4/6 rungs and 55 at 8/13, both
counted off the archived final logs; `bench.md` §5 says to expect it to keep
falling as the rungs rise, with 0 meaning they went too far.

> **`bench.md:226` and `project_battle_chronicles.md:229` both say 62, and 62 is
> wrong.** It is a mid-session read of run 2, whose final log says 96 — the same
> undercount trap that had already forced one rung re-fit that day. Correct both
> as part of this change (4.6). A Run 1 scored against 62 would read a *rise* from
> 55 to 56-61 as the expected fall and pass a regression.

Plus one number this design needs:

> **p = (major + decisive) ÷ total moments.**
> Rank-2+ moments per side per battle ≈ 7.5 × p, capped by `battle_days ÷ high_days`.
> **p ≥ 0.20 → `high = 20` days. p < 0.20 → `high = 10` days.**

Read the log only after `ck3.exe` has left `tasklist`; it is written live and a
mid-session read undercounts.

## 8. Verification — Run 2

| reading | verdict |
|---|---|
| `BC: toast preempt` > 0, screen shows **up to 6** toasts per 30-day battle | **pass**. 6 is Section 6's ceiling, not a fitted band — the pre-change baseline is an n = 1 on-screen count and cannot support a lower bound |
| preempt 0, and `BC: moment major` + `decisive` also ~0 | not this feature — the rungs undershot. Re-fit and re-run 1 |
| preempt 0, `BC: toast rank2` > 0 | rank-2+ moments spoke, but always into a free slot — the base budget never collides. The feature is unnecessary, not broken; revert it. **This reading is only decisive because 4.3 spends the high budget on preemptions alone**; had an ordinary rank-2+ toast been allowed to refresh the high flag, an over-refreshed working feature would print the same thing |
| preempt 0, `BC: toast rank2` 0, world-wide `BC: moment major`+`decisive` healthy | the rank is not reaching the gate scope. Re-run `tools/_bcorder.py` first. Note this row crosses a **world-wide** count against **player-only** counters: at the three-long-battle floor below, the expected player rank-2 count is ~6, so a 0 here is meaningful rather than merely small |
| screen shows **7 or more** toasts per 30-day battle | above Section 6's ceiling of 6, so the volume model is wrong, not merely mistuned. Diagnose before turning anything; if it is only mistuned, turn `high` and never the base |

**Run 2's counts will be tiny, and this must be planned for rather than
discovered.** `is_ai = no` is the first row of the gate, so
`bc_start_toast_cooldown_effect` never runs for AI. Unlike every other `BC:`
marker, which counts the whole world, `BC: toast preempt` and `BC: toast rank2`
are **player-only** and will be single digits. A zero is weak evidence. Run 2 is
readable only if the player personally commands **at least three long battles**.

**Regression guard.** This design touches only the toast gate. `BC: fired` totals
and the `BC: moment` shares must be **unchanged** from Run 1. Movement there is an
accident, not a result.

**Static gates, both runs.** `python tools/ck3.py validate battle_chronicles
--strict` at 0 errors and the 2 known `namespace` warnings; `probe 'Compiling
source'` swept for `bc_`. No new parameters are introduced, so the
declared-but-unread compile failure does not apply — sweep anyway, because that
failure is silent at every call site.

## 9. What no run can settle

No log line can say that the toast the player saw was the turn of the battle.
Run 2's real verdict is a judgement on screen: did the extra message read as the
battle turning, or as one more line of noise?

**If it reads as noise, this design is wrong and the answer is not a smaller
cooldown.** It means the in-battle toast is the wrong surface for narrative
weight, and the effort belongs in the combat-end chronicle instead — one pop-up
that narrates the battle from the depth, style, ground, foe and wound already
recorded. That is the intended follow-on design either way; this outcome would
promote it from *next* to *instead*.
