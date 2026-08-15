# Playbook

How to build a CK3 mod here without burning days. `gotchas.md` holds the facts
this method exists to work around; `workflow.md` holds the commands. This file is
the method itself, written after the Battle Chronicles spike proved it.

## The governing constraint

**A restart costs about seven minutes.** A large AGOT stack loads slowly, and
almost nothing about script logic can be hot-reloaded. Every decision below
follows from that one number.

The failure mode is testing one fact per run. Three runs to learn three things is
twenty minutes of loading screens, and it is how a day disappears.

## Spike before you build

Before writing a feature, write a **probe mod** that answers every open question
about that feature in a single battle, a single reign, a single run.

`mods/bc_spike` is the worked example: thirteen probes in one mod, each writing
one `debug_log` marker, all answered from one battle. The mod it de-risked
(`mods/battle_chronicles`) was then written with no unknowns left in it.

How to build one:

1. **List the unknowns first, as a numbered comment block at the top of the
   file.** P1 mod loads, P2 event fires, P3 scope reachable, and so on. If you
   cannot number it, you do not know what you are testing.
2. **One marker per probe, all sharing a greppable prefix.**
   `BC_SPIKE: P4 terrain = other but readable`. Include the *negative* branch
   too — an `else` that logs `P4 FAILED ...` distinguishes "the check was
   false" from "the code never ran", and that distinction is most of debugging
   here.
3. **Turn the weights up absurdly.** `chance = { base = 100000 }`. You are not
   testing pacing, you are testing whether the hook exists at all.
4. **Chain the probes** so one run covers the dependent ones: probe A locks
   itself out with a modifier and probe B requires that modifier, so B firing
   proves both B and the lockout.
5. **Exaggerate values** so a result cannot be mistaken for noise:
   `advantage = 20`, not `advantage = 3`.
6. **Keep the probe mod.** It is the regression suite and the reference for
   working syntax. Do not fold it into the real mod.

## Reading a run

**Never from stdout.** Even in `-debug_mode` the captured stream is
`[Checksum Builder]` spam, and that spam is not a file manifest — mods that are
definitely loaded never appear in it.

Everything is in `<user dir>/logs/`:

| File | What it is good for |
|---|---|
| `debug.log` | every `debug_log` line, plus the real mod manifest `<Name>\|mod/<file>.mod\|Enabled` |
| `error.log` | names the file behind every complaint; the best single proof a mod parsed |
| `game.log` | rarely needed |

`debug.log` reaches tens of megabytes in one session, so tailing it is useless.
The question is always *how many times did marker X fire*:

    python tools/ck3.py probe 'BC_SPIKE'

It strips timestamps and source prefixes and prints counts per distinct message.
A marker at 41 hits and a marker at 1 hit mean very different things — 41 is
"fires for every knight in the world", 1 is "fires for the player only".

## Prove the negative before you debug the positive

When something does not work, the first question is not *why*, it is *did my
code run at all*. Two cheap instruments:

- **A load canary.** Override one localization key with an obvious string and
  look for it on screen. Pick a key the HUD actually draws — `PAUSED_BY_PLAYER`,
  not `PAUSED`. A canary on a key nothing renders is a permanent false negative
  and will send you hunting a loading bug that does not exist.
- **`error.log` naming your file.** Even a complaint is proof of life.

Only once the code is proven to run is it worth asking why it behaves wrongly.

## Do not out-think the environment

The single most expensive bug in this workspace's history was **deploying to the
wrong user directory**. Four plausible hypotheses were investigated first —
absolute paths, `dependencies={}`, junction traversal, a mod-count cap — and all
four were wrong. The mod was in a folder the game never reads.

The lesson generalises: before theorising about the engine, verify that the file
you edited is the file the engine loads. `python tools/ck3.py doctor` and the
`Mounted Data:` lines in `debug.log` answer it directly.

## Do not merge what does not merge

CK3's merge rules are per-construct and not written down anywhere obvious:

- Files at a vanilla relative path **replace** the vanilla file wholesale.
- `common/defines/` merges per key.
- `common/combat_phase_events/`, `common/modifiers/` and friends merge per key
  across files — this is why the whole mod is additive new files.
- on_action `events = { }` merges; **on_action `effect = { }` does not**, and the
  winner is decided by alphabetical filename inside `common/on_action`.

Default to hooking through the additive construct, always. Naming a file `zz_*`
wins a race you should not be running.

## Isolate before you blame your mod

A crash or an error during a 60-mod playset is not evidence about your mod. Run
the same save with your mod disabled. Two independent techniques from one
session:

- Compare `crashes/*/exception.txt` fault addresses. Identical addresses with and
  without your mod means it is not your mod. Only comparable within one Windows
  boot — ASLR rebases per boot.
- Compare file sizes across autosaves. A save far smaller than its neighbours is
  truncated, and `continue_game.json` may be pointing at it.

## Write script that does not cost frames

CK3 runs script far more often than it looks. Four rules, in order of how much
they matter:

- **Never nest an unbounded iterator inside a per-character pulse.**
  `every_living_character` inside `yearly_playable_pulse` is quadratic across
  thousands of characters. Filter to the smallest scope first, then iterate.
- **Order triggers cheapest-first, and use `trigger_if`.** Boolean early-out does
  *not* apply while the game is building a tooltip — it evaluates every child so
  it can render every line. `trigger_if = { limit = { ... } ... }` is the only
  way to actually skip work there.
- **Script values recalculate every UI frame** they are displayed in. A script
  value with iterators in it, shown in a tooltip, is a frame-rate bug.
- **`ai_check_interval = 0`** on a decision only the player can take. Otherwise
  every AI ruler re-evaluates it forever.
- 1.19 added `(any_)ruler` as a pre-filtered iterator, and made `(any_)dynasty`
  iterate only active dynasties by default. Prefer them over the wide versions.

## Order of work

1. Design doc in `docs/specs/`, with a **risks and unknowns** section. That
   section is the probe list.
2. Probe mod. One run. Update the design doc's risk section with RESOLVED and the
   evidence.
3. Real mod, written against proven syntax only. Anything still unproven gets a
   comment saying so and a note in the README, so the next run knows what to
   watch.
4. `validate`, `conflicts`, deploy, play.

Write down what cost you an hour, in `gotchas.md`, the day it costs you.
