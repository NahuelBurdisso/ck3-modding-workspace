# Battle Chronicles — the toast slot becomes competitive

2026-08-20. Design only. Nothing here is implemented and **nothing here may be
implemented until the 11/16 rung run has been read** — see Section 7.

Companion documents: `../battle-chronicles/open-questions.md` (the agenda),
`../battle-chronicles/bench.md` (how to drive a run),
`2026-08-15-battle-chronicles-depth-design.md` (the ladder this builds on).

## 1. The problem

The mod's player-facing bandwidth is tiny and it is allocated by a timer.

444 templates exist. A commander's side averages **7.5 moments per battle**
(1175 moments ÷ 186 sides, run 2026-08-19), and the player sees about **4 toasts**
per 30-day battle after the flood cap shipped that same day. Which 4 is decided
by two things, neither of which is importance:

- `bc_toast_cooldown`, a 10-day character flag on the recipient, first-come
  first-served;
- CK3's weighted `chance` roll, which picks *which* template speaks.

So a rare hand-authored major moment is silently swallowed if a batch context
read fired three days earlier. The depth escalator shipped on 2026-08-19 raises a
moment's effective rung as a battle deepens, and the player has no way to
perceive that, because the rung has no influence on whether the moment is spoken.

The content is not the bottleneck. 434 of the 448 templates are batch-generated
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
across all 444 sites with `D:/ck3/_bcorder.py`:

    bc_commander_phase_events.txt   pairs: 238   out-of-order: 0   depth mismatches: 0
    bc_knight_phase_events.txt      pairs: 206   out-of-order: 0   depth mismatches: 0

Every `bc_record_moment_effect = { ... }` is followed by exactly one
`limit = { bc_can_toast_trigger = yes }`, and the toast `if` block sits exactly
one brace level deeper — i.e. inside the same enclosing scope. In knight
templates that scope is the `scope:combat_side.side_commander ?= { ... }` wrapper,
so the rank is written on, and read from, the toast's recipient. That script is
kept at the workspace root beside the other `_bc*` scanners because it guards an
invariant this design depends on; re-run it after any bulk edit to the phase-event
files.

Because the rank is on the scope the gate already evaluates on, the gate needs no
parameter, and **no template is edited.** Four files change, all of them
definitions.

## 4. The mechanism

### 4.1 Store the rank — `bc_ledger_effects.txt`

One line in each of `bc_record_effective_tier_effect`'s three arms, beside the
existing `debug_log`:

    set_variable = { name = bc_last_moment_rank value = 3 }   # decisive arm
    set_variable = { name = bc_last_moment_rank value = 2 }   # major arm
    set_variable = { name = bc_last_moment_rank value = 1 }   # else arm

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

`is_ai = no` stays the first row. Nothing below it evaluates for an AI commander.

### 4.3 Spend the budget, and mark the preemption — `bc_scripted_effects.txt`

    bc_start_toast_cooldown_effect = {
    	# BEFORE the flag is set, so the OLD state is still readable. If the base
    	# cooldown is already held at this instant, the gate can only have passed
    	# through the high arm — so this is an exact preemption counter, and the
    	# only one obtainable. A trigger cannot log.
    	if = {
    		limit = { has_character_flag = bc_toast_cooldown }
    		debug_log = "BC: toast preempt"
    	}
    	add_character_flag = { flag = bc_toast_cooldown days = 10 }
    	if = {
    		limit = { exists = var:bc_last_moment_rank }
    		if = {
    			limit = { var:bc_last_moment_rank >= 2 }
    			add_character_flag = { flag = bc_toast_cooldown_high days = <fitted, Section 7> }
    			debug_log = "BC: toast high"
    		}
    	}
    }

The nested `if` rather than two rows in one `limit`, for the reason in 4.2.

### 4.4 Clear the scratch — `bc_clear_scratch_effect`

    remove_variable = bc_last_moment_rank

**This is required, and not for the reason it first appears to be.** It is *not*
needed to stop a stale rank preempting: 3 proves the record always precedes the
read, so the gate always sees the current moment's rank. It is needed because
`bc_record_effective_tier_effect` runs for **every AI commander in the world** —
`is_ai = no` gates the toast, not the ledger — so without the clear,
`bc_last_moment_rank` accumulates as a permanent variable on every character who
has ever commanded.

### 4.5 Fix a stale number while in the file

`bc_ledger_effects.txt:271` reads "Eight of the eighteen call sites are pop-up
options." The real count is **465** — 238 commander + 206 knight + 21 in
`bc_events.txt`. The comment predates the 434-template batch. Correct it. A wrong
number in a design header is how the stale 4.2-moment mean survived three
separate rung fits.

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

Phase events roll every `COMBAT_EVENT_DAYS = 5`. With a separate high budget the
ceiling inside one high-cooldown window rises from 1 toast to 2.

At the 11/16 rungs' *target* split of 72/18/10, rank-2+ is 28% of moments, so the
player's side sees ~2.1 preemption candidates per 30-day battle against a cap of
`30 / high_days`. Expected outcome at `high = 20`: **+1 per battle**, total ~5
against a measured 4.

Two second-order effects, both accepted:

- **Volume is per-day, not per-battle.** A 60-day battle allows ~6 base and ~3
  high, so ~9 toasts. Long battles get proportionally more, by design.
- **Crescendo.** Depth escalates monotonically within a battle, so past rung 16
  *every* moment is rank 3 and the high budget becomes the binding constraint.
  The last toasts of a long battle will all be top-rank. This is thematically
  right, and it means "decisive" is a per-moment share, not a per-toast one — a
  long battle will feel decisive throughout, and should.

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
`BC: combat end cleanup` for the denominator, `BC: wound gates passed` nonzero
and near 55 — plus one number this design needs:

> **p = (major + decisive) ÷ total moments.**
> Rank-2+ moments per side per battle ≈ 7.5 × p, capped by `battle_days ÷ high_days`.
> **p ≥ 0.20 → `high = 20` days. p < 0.20 → `high = 10` days.**

Read the log only after `ck3.exe` has left `tasklist`; it is written live and a
mid-session read undercounts.

## 8. Verification — Run 2

| reading | verdict |
|---|---|
| `BC: toast preempt` > 0, screen shows 4-6 toasts per 30-day battle | **pass** |
| preempt 0, and `BC: moment major` + `decisive` also ~0 | not this feature — the rungs undershot. Re-fit and re-run 1 |
| preempt 0, `BC: toast high` > 0 | the base budget never collides. The feature is unnecessary, not broken — revert it |
| preempt 0, `BC: toast high` 0, moment counts healthy | the rank is not reaching the gate scope. Re-run `_bcorder.py` first |
| screen shows > 8 toasts per 30-day battle | `high` is too short. Turn `high` only, never the base |

**Run 2's counts will be tiny, and this must be planned for rather than
discovered.** `is_ai = no` is the first row of the gate, so
`bc_start_toast_cooldown_effect` never runs for AI. Unlike every other `BC:`
marker, which counts the whole world, `BC: toast preempt` and `BC: toast high`
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
