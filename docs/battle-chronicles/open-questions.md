# Battle Chronicles - open questions

Everything the mod does that no run has yet proven. This is the agenda for the
next run.

## Not yet verified in game

- The shieldbrother memory rendering, and that `[shieldbrother.GetFullName]`
  resolves.
- The 2026-08-14 localization fixes: that
  `[bc_named_commander.GetNicknameNoTooltip]` resolves inside the award toast
  (including in the liege branch, where the scope has moved), and that the 26
  new `nick_agot_*_desc` keys render on hover in the character sheet with no
  `Duplicate localization key` line in `error.log`.
- The nickname award **under its real gate**. The path itself is proven (see the
  2026-08-14 run) but no commander has yet banked three notable wins with
  `martial >= 14` and no nickname unaided. `"BC: nickname awarded"` is a permanent
  marker, so `probe 'BC:'` will report it the first time it happens.
- **The nemesis relation itself, on a character screen.** `BC: nemesis new` fired
  32 times and `BC: nemesis rung grudge` 26, so `bc_rivalry_set_relation_effect`
  runs and picks the right rung — but a marker only proves the effect was
  *reached*, not that the relation *landed*. Plan 4 targets
  `scope:bc_rivalry_foe`, saved from `var:bc_nemesis`, on the strength of an
  argument about shipped syntax: `set_relation_X = var:Y` has **zero** uses in
  vanilla or AGOT, while `has_relation_X = var:Y` ships. That argument is
  untested. Open a commander who took a `BC: nemesis new` and look for a grudge
  against the right man with the reason *"beat him on the field"*. If the marker
  fired and no relation exists, the target form is wrong and must be re-derived.
- The rivalry game rule rendering: **Battle Chronicles: Rivalry** with three
  readable options on the rules screen.
- **Whether a `combat_side` survives a day.** The dead-knight read is now deferred
  into `bc_chronicles.0093`. `BC: dk deferred` counting while
  `BC: dk deferred fired` is absent means the side object was freed and the read
  must be re-hung on the commander character. Both counting with
  `BC: dk found dead` still 0 means a day is not enough, or knights are not dying.
- **The wound, at last measurably.** `"BC: wound"` has never fired, and until
  2026-08-15 that was starvation — it had one call site on an arm that resolved
  once per run. It now also hangs off the major arm (~45/run).
  `BC: wound gates passed` counting with `BC: wound` 0 means the
  `var:bc_battle_size >= 3` read rejects; both 0 while `BC: moment major` counts
  means the five-row outer limit does.
- **That the SWING row rejects.** It was inert until the major arm started feeding
  it wins. Roughly a third of what now reaches `bc_wound_effect` is `swing up`,
  and nothing has yet proven the row turns those away.
- **The decisive rate at the new floor.** `>= 4` scored 1 in 44 battles. The
  binding constraint is call-site rarity, not the floor — only 10 of 233 moments
  ever request `decisive` and 7 request it too early. Both numbers should be
  re-measured together, never one alone.
- **The spike fragment.** `bc_banner_falls_ground`, invoked as
  `[bc_chronicle_subject.Custom('bc_banner_falls_ground')]` from
  `bc_banner_falls_toast_desc`. The next run must show a Banner Falls toast
  carrying a clause that names the ground, and `probe 'BC: ground'` must report
  a band for the same battle. **It is no longer the last clause on that toast**
  and looking for it there is how this check gets read as failed: the desc runs
  literal, ground, bond, scale, and the two shared clauses were wired onto all
  ten toasts by Plan B task 4. Read the markers and the toast together:

  | markers | toast | verdict |
  |---|---|---|
  | a band | ground clause present, matches band | shape proven — Plan B tasks 5-14 unblocked. Tasks 2, 3 and 4 shipped without it, under the plan's AMENDMENT: a clause APPENDED to a desc that keeps its literal fails to "no improvement", while the core sets tasks 5-14 write REPLACE the literal and fail to an empty toast. |
  | a band | no ground clause | **not a mechanism failure** — vanilla ships this exact shape. `court_poet_poetry_desc` (`localization/english/court_positions_2_l_english.yml:150`) is `"[court_poet_from_task.Custom('GeneratePoem_Outro_Rhyming')]"`, rendered by the `send_interface_toast` at `common/court_positions/tasks/00_court_poet_tasks.txt:94-98` against a scope saved earlier in that same file (`00_court_poet_tasks.txt:47`) — a saved scope, a bare `Custom`, in a toast desc. Eleven other vanilla toasts do the same. So a blank clause means the **anchor** or the **variable**, not the mechanism. **The retry that used to be needed here is not:** `bc_bond_clause` now renders on the same toast off the same anchor, and `bc_write_bond_effect` writes on every path, so a bond sentence present with the ground clause absent isolates the **variable**, and all three clauses absent at once isolates the **anchor**. **The two inferences do not rest on the same thing and only one of them is fragile.** The bond-present one rests on `bc_write_bond_effect` writing bare on the caller's current scope, which is the anchor only because `bc_battle_open_effect` is its sole caller — the paragraph named `NOTE ON SCOPE` in `bc_context_effects.txt` says that much, and the rest is that effect's own opening line, an unconditional `save_scope_as = bc_chronicle_subject`, which makes its current scope the anchor on every path. Give that effect a second caller on any other scope and characters other than the commander start carrying `bc_battle_bond`, so a rendered bond clause stops ruling out the failure the row below describes — the anchor resolving to somebody who is not the commander — and therefore stops vouching for the anchor. The all-three-absent one is unaffected by a second caller — a second caller adds a write elsewhere, it does not remove the one `bc_battle_open_effect` already performs on the commander — and fails only if that effect itself stops running on the anchor. Only if all three are absent, retry with `bc_commander`, saved on the same character fifteen lines above the toast (`bc_commander_phase_events.txt:65`; the toast is at `:80-85`). Do not abandon the design on this symptom. |
  | a band | ground clause present, wrong band | the arms read the variable off the wrong character — the anchor resolves but not to the commander who holds the scratch. |
  | `BC: ground missing` | no ground clause | not a spike failure — `combat.location` did not resolve at a phase event. Fix the read site in `bc_write_ground_effect` and run again. |
- **The widened eve.** `bc_chronicles.0011` now assembles three paragraphs and
  can offer eleven options — three unconditional and eight gated. Nothing static
  proves a `first_valid` picks the arm intended, or that an `option` `trigger`
  hides rather than greys.

  | markers | screen | verdict |
  |---|---|---|
  | `BC: ground <band>` (write-path marker, not the eve's own read) | a third paragraph naming that band | the write path and the eve's `scope:bc_eve_ground` read agreed — both work. A mismatch between the write-path band and the rendered paragraph is itself informative: the scope saved the province but a subsequent battle overwrote `BC: ground <band>` while the scope still points to the first one. |
  | `BC: ground` for **any named band** — rough, forest, jungle, winter, desert | third paragraph reads "The field is what it is" | `scope:bc_eve_ground` is saved but the band triggers do not match through it — check the scope's type, not the triggers. This is a real failure: all five have named arms and none of them should reach the fallback. Desert is the one band the DIAG run's Q5 terrain census never produced (0/137), so an absent `BC: ground desert` proves nothing either way. |
  | `BC: eve ground missing` | third paragraph reads "The field is what it is" | correct behaviour: the ground scope never saved, the fallback renders as designed. Not a trigger bug. The insert may be in the wrong branch of `bc_eve_offer_effect` if this counts while `BC: eve offered` counts equally. |
  | `BC: ground open` or unresolved province | third paragraph reads "The field is what it is" | correct: open is the only band that legitimately rides the fallback, and an unresolved province also reaches it. |
  | any | option d visible on open ground | the `trigger` is not gating; every option in the mod is then suspect |
  | `BC: eve option ground` counts | — | the option is reachable and taken. There is no "offered but not taken" marker. |
- **The `bc_ground_held` modifier on a character screen.** It is the fifth
  family-2 modifier and the first added since the cleanup rule was written. The
  run must show it appear when option d is taken and be **gone** by the next
  battle of the same war. If it is still there, `bc_cleanup_effect` did not run
  or did not reach the new line.
- **The sixteen new templates, one marker each.** Every one writes
  `BC: fired <key>`, so `probe 'BC: fired'` is a census of which gates are
  reachable. A template at **zero** is a gate that never opens, and the three
  worth suspecting first are `bc_dust_and_thirst` (the desert band scored 0/137
  and 0/360 in two censuses — a statement about where these campaigns were
  fought, not about the map), `bc_the_wine_at_noon` (drunkard is rare on a man
  trusted with a host) and `bc_the_practised_eye` (`strategist` **and** a
  15,000-man host at once). A template that **dominates** is the other failure:
  the six character-batch gates are the widest in the mod and the batch header
  names them as the first weights to cut.
- **That the new knight cases are seen at all.** The file header records
  `base = 40` behind narrow gates producing **zero** fires across a session
  against `knight_none` at 2000. All six shipped knight additions sit at 80. If
  the second and third batches are at zero while the shipped three fire, the
  base is the reason and not the gates.
- **That a pooled `random_valid` inside the eve's `first_valid` falls through
  when empty.** This is the one structural claim of the prose work, and vanilla
  `birth.9002` is the whole of the evidence. The test is cheap: fight on winter
  ground and read the third paragraph. **Winter or desert text = the nesting
  works.** "The field is what it is" on a battle whose markers say winter means
  the empty-pool fallthrough does *not* work the way `birth.9002` implies, and
  every pooled arm has to go back to a flat `triggered_desc` chain.
- **That the pools actually vary.** Three eves in one game should not print the
  same foe paragraph three times, and a knight with several battle memories
  should not have them all read identically. Uniform output with the structure
  in place means `random_valid` is being read as `first_valid`.
- **The style-branched nickname ladder.** `BC: nickname style UNMATCHED` is a
  permanent marker and **must stay at zero** — it counts a `var:bc_style_last`
  holding a value none of the six ladders claims, which is the seam's KIND
  vocabulary and the ladder having drifted apart.
- **The foe-relative award.** `probe 'BC: award'` reports which of the two
  currencies paid. The three markers `piety` / `prestige` / `no creed` partition
  the notable wins that reached the award; `nemesis` is a subset of the first
  two. A run where `BC: award no creed` dominates means most notable wins carry
  no BC moment — not that the award is broken. Separate the two causes by
  crossing it against `BC: bond nofoe`, which counts only the leaderless-enemy
  case. `BC: award piety` at zero while `BC: creed heathen` counts is the real
  failure: the read is landing on the wrong character.
