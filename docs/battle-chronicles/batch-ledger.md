# Battle Chronicles - batch ledger

The 2026-08-17 content session, one row per batch. Extracted from the mod
README, where it was 492 KB inside a single section and made the file
unreadable. Split into parts because the table alone still exceeds a single
read.

## Content session, 2026-08-17 (no run — static verification only)

Two hundred and twenty batches, one per row of the table below, none of which needed a
runtime answer. The measured problem they
answer is one number: **ten moment templates produced 233 firings in 44
battles**, so a player who fights one war reads the same ten sentences over and
over. Design: `../../docs/specs/2026-08-17-battle-chronicles-cases-design.md`.

**The rate limiter is the cooldown, not the weights.**
`bc_chronicle_ready_commander_trigger` fails while `bc_chronicle_recent` is
live, so a blocked roll is not a Battle Chronicles roll at all — it goes to
vanilla's `commander_none`. A template that fires in a slot an old one already
owned therefore buys variety at no rate cost. The honest half: an even battle on
open ground with an unremarkable commander used to match nothing, and now does.

## Parts

- `batch-ledger-1.md` - 76 rows
- `batch-ledger-2.md` - 24 rows
- `batch-ledger-3.md` - 21 rows
- `batch-ledger-4.md` - 20 rows
- `batch-ledger-5.md` - 67 rows
- `batch-ledger-6.md` - 12 rows


**All six ground bands are now gated on as well as narrated.**
`bc_scripted_triggers.txt` wrapped four of six with a note to add the rest when
something needed them; `bc_the_broken_ground_holds` and `bc_the_green_closes_in`
are that something, and the wrapper set now matches `bc_ground_triggers.txt` one
for one.

**The two new foe triggers are not a ladder.** `bc_foe_is_countryman_trigger`
and `bc_foe_is_heathen_trigger` each test one property of the man opposite, so
unlike the arms of `bc_write_bond_effect` they are not mutually exclusive — a
foe can be both, and both templates can be valid on the same roll. The bond
*clause* still picks one, because that is a ladder; the *gates* are not.

**Every (KIND, SWING) pair the seam defines is now reached.** Plan 1 recorded
`entrenched`/`down`, `wild`/`up` and `ordered`/`down` as unreachable; later
content batches reached the first two, and this session's knight trait batch
reached the third. The pair census and the modifier reach counts in
`bc_ledger_effects.txt` are re-counted mechanically at the end of every batch —
plan 1's eighteen call sites are now **four hundred and sixty-five**, its "3, 3, 4 and 3"
are 78, 78, 77 and 39, and the fall-through set is one hundred and ninety-three sites rather than
five. The table's *behaviour* is unchanged; only its comments went wrong, and wrong in the
direction that invites a bad fix, which is why the counting command is now
written into the comment that carries the numbers.

**Template totals are now commander 238, knight 206.** Weight against vanilla's
`commander_none` at 1000: roughly 400 (the calibrated seven) + 300 + 180 + 70
+ 90 + 110 + 100 + 70 + 60 + 120 + 120 + 80 + 120 + 100 + 100 + 50 + 60 + 100 + 100 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50 + 50; on the knight side, two hundred and six templates against
`knight_none`'s 2000 — two hundred and five at 80 and `bc_knight_pulls_him_out` at 60,
held below the rest because it is the one knight moment that writes something
permanent.
If a sweep shows the original seven crowded out, **the character batch is the
first to cut** — it is the newest and the least measured.

**Pooling is `random_valid`, and it is vanilla in three separate shapes.**
`00_animal_custom_loc.txt` for a customizable_localization; `birth.9002`
(`events/birth_events.txt:3515-3614`) for a `random_valid` nested inside a
`first_valid` with a bare fallback below it, which is the pattern the eve now
uses and which only works because an empty pool is *not valid* and `first_valid`
moves past it; `chariot_race_ongoing_jp.0400` for bare untriggered `desc` lines
inside a pool. The memory types were already built this way and simply had
one-line pools.

**`validate` was wrong about pools and was fixed in the same session.** Its
arm-shape check demanded an unguarded `text` arm from every
customizable_localization definition including `random_valid` ones — but under
pooling an unguarded arm is valid on *every* render, so it competes with the
real prose and takes its share, and for `bc_bond_clause`'s empty-string fallback
that means deleting a clause that was available. The rule mandated a defect. It
is now suspended for pooled definitions, and the obligation moves to the mod,
which writes its fallback arm as a bare `trigger_if` — true when its limit is
false, so it is valid on exactly the absent and unknown-value paths.
