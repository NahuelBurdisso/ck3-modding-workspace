# Battle Chronicles — depth and scenarios, design

Written 2026-08-15, after the tiered-marker run and the session handoff
(`docs/2026-08-15-battle-chronicles-handoff.md`). It answers the handoff's job 1:
**add depth to the systems that already work, and a lot more cases and
scenarios.**

It does not touch job 2. Everything on the handoff's §3.1/§3.2 list needs a game
run or a human at a character screen, and this design is deliberately built to
need neither.

---

## 0. The problem, measured

The 2026-08-15 tiered-marker run: 44 combat ends, 233 moments, **5.3 per
battle**, drawn from **ten** phase-event templates each carrying **exactly one**
title and one description. A player who fights forty battles reads the same ten
paragraphs twenty-three times.

Every situational input except battle ratio is unread. A battle in a bog in
winter against a brother reads identically to a summer field battle against a
stranger.

## 1. Decisions taken before design

| question | answer |
|---|---|
| where does depth land | all four strands — prose, the eve, new moments, outcomes — sequenced, one spec |
| are new *outcomes* in scope | yes, sequenced last, non-lethal rule intact |
| what happens to measured pacing | **hold it.** Variety comes from branching inside existing keys, not from new keys competing for rolls |
| which inputs may be read | terrain, foe identity, size/odds, commander-vs-foe culture and faith, relation to the foe |
| which inputs are excluded | **war type** (`combat_war` is documented but has never run here — unverified scope risk) and **season** and **troop composition** (no readable path found) |
| mechanism | custom-loc fragments for the ten moments; hand-written `triggered_desc` for the eve |

The pacing answer is the load-bearing one. Handoff §2.4 established that the
tier ladder's real constraint is **call-site distribution**, not template count —
only 10 of 233 moments ever request `decisive` and 7 of those request it too
early. Adding templates spreads that distribution thinner, not richer.

## 2. Section 1 — how a moment learns its context

### The rule

**No new saved scope carries meaning.** `bc_ledger_effects.txt:41-51` records the
hazard: a saved scope cannot be unsaved, so `scope:bc_open_foe` can name a
previous battle's commander. Meaning goes in **scratch variables**, which
`bc_clear_scratch_effect` already strips at combat end.

### The change

`bc_battle_open_effect` — which already runs on the side commander at all ten
call sites, and already writes `bc_battle_foe` and `bc_battle_size` — gains:

- `bc_write_ground_effect = yes`, writing `var:bc_battle_ground` as a flag from a
  single ladder over AGOT's 23 terrain helpers, collapsed to six bands:
  `rough`, `forest`, `open`, `bog`, `mountain`, `frozen`. Each arm carries a
  `BC: ground <band>` marker.
- `save_scope_as = bc_chronicle_subject` on the side commander, as the one loc
  anchor common to all ten toasts.

**The write is unconditional, not write-if-unset.** This follows the doctrine
already stated at `bc_ledger_effects.txt:34-43`: a commander replaced mid-combat
is never cleared, so under write-if-unset his stale values would freeze
permanently rather than for one battle.

`bc_clear_scratch_effect` gains `remove_variable = bc_battle_ground`. **The
writer and the remover must ship in the same commit** — a remover without a
writer produces `Variable 'bc_battle_ground' is used but is never set` twice per
boot, the exact debt the 2026-08-15 run just finished retiring.

### Why the ladder lives in script and not in loc

Three reasons, and the third is the one that matters:

1. the 23-helper ladder is written once instead of being retyped in every arm
2. the flavour system then needs exactly one custom-loc `type` and no province
   scope
3. **a custom-loc arm cannot be instrumented.** There is no `debug_log` in
   localization. Putting the ladder in script is the only way the band
   distribution is ever measurable — and the terrain census (DIAG Q5) only ever
   measured the *world*, never what the *mod chose*.

### Why staleness is safe here

`scope:bc_chronicle_subject` can go stale between battles; nothing can unsave a
scope. But every arm it feeds tests a **scratch variable**, and scratch is wiped
at combat end. A stale subject therefore resolves to an arm's **fallback**, never
to wrong flavour. This inverts the `bc_open_foe` hazard rather than repeating it.

## 3. Section 2 — the prose fragments

New file `common/customizable_localization/bc_flavour.txt`. Additive; the
directory is vanilla (`00_journey_focus_custom_loc.txt` is the shape) and no
mod in the playset ships a file of that name.

**Note the divergence from the vanilla model file:** it tests `terrain = oasis`
directly. This mod forbids that — AGOT defines road variants as distinct terrain
types, and bare keys silently missed 424 and 51 provinces from the first live run
onward. BC arms never test terrain at all; they test `var:bc_battle_ground`,
which the script ladder wrote using AGOT's helpers.

### Shape

All definitions are `type = character`, called on the anchor:

```
bc_banner_falls_toast_desc:0 "[bc_chronicle_subject.Custom('bc_banner_falls_core')] [bc_chronicle_subject.Custom('bc_banner_falls_ground')]"
```

Three fragment classes:

| class | count | keyed on | shared or per-moment |
|---|---|---|---|
| core | 10 × 3 | nothing — `random_valid = yes` | per-moment |
| ground | 10 × 6 | `var:bc_battle_ground` | per-moment |
| foe | 6 | commander vs `var:bc_battle_foe` | shared |
| scale | 4 | `var:bc_battle_size` | shared |

Ground clauses are per-moment because the verb has to agree: a standard goes down
*in the mud*, a flank collapses *among the trees*. Foe and scale clauses are
moment-agnostic and shared.

Roughly **100 loc keys covering some hundreds of readings**, against 10 today.
Cost is additive, coverage is multiplicative.

### `Custom2` carries the two-character arms

`board_game_events_l_english.yml:114` ships
`Custom2('InsultNoun', SCOPE.sC('bg_opponent'))`. The foe class uses that form —
one call testing commander against foe — rather than a flattened set of
one-sided arms. Arms: nemesis, close kin, same culture, same faith / different
culture, different faith, stranger fallback.

### `random_valid = yes` is restricted to toasts

Vanilla uses it at `00_servants.txt:3`. It picks randomly among valid arms, which
is a repetition-killer needing no inputs at all.

**It must never appear on a memory or nickname description.** Those re-render
every time the player opens the window, so a random arm would make the same
remembered battle read differently each time it is looked at. Toasts fire once
and are safe. This is reasoned, not measured; the rule is cheap and the bug would
be very hard to attribute.

## 4. Section 3 — the eve

`bc_chronicles.0011` today: one intro desc, a two-way `first_valid` on nemesis vs
stranger, three options.

It fires **only for a human commanding in person** (`is_ai = no`) at
`var:bc_battle_size >= 3` behind a 90-day flag — 2 offers in 44 battles. So it is
rare but **100% seen**, the inverse of the moments, most of which happen to AI
commanders nobody watches.

### Changes

- **desc becomes three assembled paragraphs**, each its own small `first_valid`
  chain: the intro, a foe paragraph (nemesis / kin / countryman / heathen /
  stranger), a ground paragraph. Hand-written whole paragraphs, not fragments —
  this is the mod's showpiece and it is read every time it fires.
- **contextual options.** CK3 event options take a `trigger = { }` and are hidden
  when it fails. Two conditional options: one offered only on `rough`/`forest`
  ground, one offered only when facing the nemesis.

### What must not change

**No option may apply momentum.** The file's own header states it: the battle has
not started, the eve is about shape, not advantage. New options apply family-2
verb modifiers through `bc_add_verb_effect` or they apply nothing.

### The size gate stays at 3

Lowering it to 2 is **rate-safe** — the eve never calls
`bc_record_moment_effect`, so it cannot move moments-per-battle. It is an
*interrupt budget* question, not a pacing one. Recommendation: keep 3. Recorded
here so a future reader knows the lever exists and knows it is safe.

## 5. Section 4 — new moments, under a weight budget

The pacing decision forbids diluting the pool. It does not forbid new keys — it
forbids new *aggregate weight*.

### The invariant

```
sum of BC commander phase-event `base` = 440   (60+60+40+60+60+60+100)
sum of BC knight phase-event    `base` = 360   (150+150+60)
```

Any new key is funded by reducing existing bases so these totals are unchanged.
The invariant is auditable statically and belongs in a validator check.

### The honest limitation

Weight neutrality is **neutrality of declared base, not of realised rate.** The
pool weights only *valid* events, so a new key whose `is_valid` opens in
situations the old ones did not could still raise BC's aggregate valid weight.
The new keys proposed here are all *narrower* than the ones funding them, so the
expected drift is slightly downward — but this is a prediction, not a
measurement.

**Therefore section 4 is sequenced last and is the one strand that will
eventually need a run.** Sections 2, 3 and 5 do not.

### What the new keys are for

The measured defect worth attacking is that `decisive` is starved by call-site
timing, not by its floor. The new commander key is valid only late
(`exists = var:bc_battle_moments` nested over `var:bc_battle_moments >= 4`) and
requests `decisive`. That puts a decisive *request* where the ledger can actually
grant it, which is what §2.4 says the ladder is missing.

## 6. Section 5 — what a battle leaves behind

### Memories remember *how*, not only *where*

Today every notable battle leaves `bc_battle_memory_won` or `_lost`, naming the
province. `var:bc_battle_style` is already computed for every battle and the
memory ignores it.

**Implemented as distinct memory types, not as a variable on the memory.** The
caller already takes the type as a parameter
(`bc_battle_memory_effect = { TYPE = ... }`), so an if-ladder on
`var:bc_battle_style` in script picks among
`bc_battle_memory_won_<style>` / `_lost_<style>`.

This was chosen over storing the style on the memory because the memory desc
would then have to *print* a flag, which loc cannot do, and reading it from a
custom loc would need a `type = character_memory` that is **not known to exist**.
Distinct types need no new mechanism at all — each type carries its own static
description, and the flag comparison stays in script where `flag:` comparisons
are already the shipped idiom.

**The two `set_variable` calls must stay in one `random_memory` block.** The
existing effect identifies the just-created memory by
`NOT = { has_variable = battle_location }`. After the first `set_variable` that
test is false, so a *second* `random_memory` block with the same limit would find
an older memory or none. Anything added to the memory goes in the existing block.

### Outcome varies with who the foe was

On a notable win, the prestige/piety award reads the same commander-vs-foe
comparison the foe fragments use: beating a man of your own faith is worth
prestige, beating a heathen is worth piety. No new state — the comparison already
exists for the prose.

### What stays untouched

Non-lethal. No `death`, no maiming. `bc_wound_effect` is not widened by this
design; it is mid-measurement and handoff §3.1 owns it.

## 7. Section 6 — verification, with no game run

### The toolchain gap this design creates

`validate.py` collects top-level definitions from any `common/**/*.txt` and
checks loc files for BOM, header and duplicates. It does **not** check that a
custom-loc arm's `localization_key` exists, and it does **not** check that a
`[X.Custom('key')]` reference resolves.

This design multiplies loc keys roughly tenfold and **every one of those links
would be invisible to the toolchain** — the same failure class as
`flag:$PARAM$`: silently wrong, validate passes clean.

### So the tooling comes first

`ck3.py validate` gains three checks, and they land **before any fragment is
written**:

1. every `localization_key` inside a `common/customizable_localization/` arm
   resolves to a loc key defined in the mod
2. every `Custom('...')` / `Custom2('...', ...)` reference in the mod's loc
   resolves to a custom-loc definition in the mod
3. the phase-event base-weight totals match the section 4 invariant

`LOC_EXPECTED` is left alone — custom-loc definition keys are not themselves
localized, and adding the category would produce false warnings.

### The one unproven premise, and how it is retired cheaply

`.Custom()` appears **nowhere** in this mod today. The nearest existing form — a
saved scope inside a toast desc, `bc_l_english.yml:123` — is itself on the
README's *"Not yet verified in game"* list.

What *is* proven by eye, in the 2026-08-13 confirmation run, is reading a
variable from loc: `[ROOT.Var('battle_location').GetProvince.GetName]` renders.

So the first implementation step ships **one** fragment on **one** moment, with
the script-side band marker, and nothing else. That is the `bc_spike` discipline
this project already uses. The other ~100 keys are written only after that one
renders.

### New permanent markers

`BC: ground rough|forest|open|bog|mountain|frozen` — six, from the script ladder.
They give the band distribution the terrain census never measured for the mod's
own choices, and they are the only instrumentation the flavour system can have.

## 8. Sequencing

| # | strand | needs a run? |
|---|---|---|
| 1 | validator checks | no |
| 2 | context plumbing (ground variable, anchor, markers) | no |
| 3 | one proving fragment | **renders or it does not** — visible the first battle |
| 4 | the remaining prose fragments | no |
| 5 | the eve | no |
| 6 | outcomes | no |
| 7 | new moments under the weight budget | **yes, eventually** — realised-rate drift |

## 9. Risks

- **`.Custom()` is unproven in this mod.** Retired by step 3 above at the cost of
  one fragment.
- **`random_valid` re-render instability** on any surface that re-renders.
  Mitigated by rule, not by mechanism; a reviewer should check every use.
- **Weight-budget neutrality is predicted, not measured.** Section 4 only.
- **Custom-loc arms cannot be instrumented.** Accepted, and the reason the
  terrain ladder lives in script.
- **`type = character_memory` is not known to exist.** Avoided entirely by using
  distinct memory types.
