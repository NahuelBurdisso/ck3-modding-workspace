"""Regression tests for the checks in ck3lib.validate OTHER than citations.

WHY THIS FILE EXISTS. `validate --strict` is the acceptance gate for every mod
in this workspace - `workflow.md` says to run it before every launch, and every
commit message in the tree quotes its output as proof. Until this file, one of
its checks was tested. `test_citations.py` covers `_check_citations` and
`_citation_files` in depth; the BOM check, the brace check, the descriptor
check, the structure allowlist, the loc checks, the ground partition and the
two customizable-localization resolvers had nothing at all behind them. The
gate that proves the mod correct was itself unproven.

WHAT THAT COST, CONCRETELY. Adding a `.gitattributes` to a mod root took the
battle_chronicles baseline from 2 warnings to 3, because `_check_structure`
enumerates git's metadata one name at a time and nobody had added that one.
Nothing failed; a number in a commit message moved. A number moving is how this
project has found most of its defects, and it is a slower instrument than a red
test.

WHAT IS PINNED AND WHAT IS NOT. These are behaviour tests against the real
functions, not against a fixture of their output. Where a check has a boundary -
a version that matches versus one that does not, a language in KNOWN_LANGS
versus one outside it - BOTH SIDES ARE WRITTEN, because a check that fires on
everything passes every one-sided test. Where a constant drives a loop
(REQUIRED_DESCRIPTOR_KEYS, BC_GROUND_BASES) the test reads the constant rather
than restating it, so growing the constant cannot leave a silent hole. NO COUNT
OF TESTS IS ASSERTED ANYWHERE, and no test asserts a position in an issue list
except where the check's own contract is an order.

Run it with `python tools/tests/test_validate.py`. Stdlib unittest, no pytest,
for the reason test_citations.py gives.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import validate as V  # noqa: E402
from ck3lib.paths import Config  # noqa: E402

BOM = "\ufeff"

GOOD_DESCRIPTOR = 'name="T"\nversion="1"\nsupported_version="1.19"\ntags={"Fixes"}\n'


class ValidateTestCase(unittest.TestCase):
    """Builds a throwaway mod tree per test and runs the real checks on it."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ck3_val_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, relpath: str, text: str) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def cfg(self, supported_version: str = "1.19") -> Config:
        # game_dir points at a directory that does not exist, so `game_root`
        # resolves and every `is_file()` against it is False. That is what makes
        # the vanilla-override INFO line absent from these fixtures rather than
        # dependent on what happens to be installed.
        return Config(
            game_dir=self.root / "nonexistent_game",
            user_dir=self.root / "nonexistent_user",
            workshop_dir=self.root / "nonexistent_workshop",
            workspace_dir=self.root,
            app_id="1158310",
            base_mod_id="0",
            supported_version=supported_version,
        )

    def run_check(self, fn, *args) -> list[str]:
        """Every issue one check emitted, as `LEVEL path:line: message`."""
        issues: list[V.Issue] = []
        fn(*args, issues)
        return [issue.format() for issue in issues]

    def assertOneMatching(self, found: list[str], needle: str) -> str:
        hits = [line for line in found if needle in line]
        self.assertEqual(
            len(hits), 1, f"expected exactly one issue containing {needle!r}, got {found}"
        )
        return hits[0]

    def assertNoneMatching(self, found: list[str], needle: str) -> None:
        hits = [line for line in found if needle in line]
        self.assertEqual(hits, [], f"expected no issue containing {needle!r}, got {found}")


class TestDescriptor(ValidateTestCase):
    """descriptor.mod: the file CK3 refuses to load a mod without."""

    def test_a_missing_descriptor_is_an_error_and_stops_the_check(self) -> None:
        found = self.run_check(V._check_descriptor, self.root, self.cfg())
        self.assertEqual(found, ["ERROR descriptor.mod: missing descriptor.mod at mod root"])

    def test_every_required_key_is_checked(self) -> None:
        # DERIVED FROM THE CONSTANT, not restated. Adding a key to
        # REQUIRED_DESCRIPTOR_KEYS without checking it would otherwise leave
        # this test green over a hole.
        self.write("descriptor.mod", "")
        found = self.run_check(V._check_descriptor, self.root, self.cfg())
        for key in V.REQUIRED_DESCRIPTOR_KEYS:
            self.assertOneMatching(found, f"missing required key `{key}`")

    def test_a_complete_descriptor_is_silent(self) -> None:
        self.write("descriptor.mod", GOOD_DESCRIPTOR)
        self.assertEqual(self.run_check(V._check_descriptor, self.root, self.cfg()), [])

    def test_a_supported_version_behind_the_game_warns(self) -> None:
        self.write("descriptor.mod", GOOD_DESCRIPTOR.replace('"1.19"', '"1.18"'))
        found = self.run_check(V._check_descriptor, self.root, self.cfg("1.19"))
        self.assertOneMatching(found, "supported_version=1.18 but installed game is 1.19")

    def test_a_wildcard_supported_version_does_not_warn(self) -> None:
        # THE SILENT PARTNER for the test above. Mods declare `1.*` routinely,
        # and a version check that fired on those would be turned off within a
        # day of anyone using it.
        self.write("descriptor.mod", GOOD_DESCRIPTOR.replace('"1.19"', '"1.*"'))
        found = self.run_check(V._check_descriptor, self.root, self.cfg("1.19"))
        self.assertNoneMatching(found, "supported_version")

    def test_a_backslash_in_path_is_an_error(self) -> None:
        self.write("descriptor.mod", GOOD_DESCRIPTOR + 'path="D:\\ck3\\mods\\t"\n')
        found = self.run_check(V._check_descriptor, self.root, self.cfg())
        self.assertOneMatching(found, "path= contains backslashes")

    def test_a_forward_slash_path_is_silent(self) -> None:
        self.write("descriptor.mod", GOOD_DESCRIPTOR + 'path="D:/ck3/mods/t"\n')
        found = self.run_check(V._check_descriptor, self.root, self.cfg())
        self.assertNoneMatching(found, "path=")


class TestStructure(ValidateTestCase):
    """What may sit at a mod root without the game silently ignoring it."""

    def test_an_unrecognised_entry_warns(self) -> None:
        self.write("notes.txt", "")
        found = self.run_check(V._check_structure, self.root)
        self.assertOneMatching(found, "notes.txt: not a directory CK3 loads")

    def test_the_git_and_editor_entries_are_allowed(self) -> None:
        # `.gitattributes` IS THE ONE THAT COST SOMETHING. Adding it to
        # battle_chronicles took the acceptance baseline from 2 warnings to 3,
        # and nothing went red - a number in a commit message moved instead.
        # The others are here so that a rewrite of the allowlist that drops one
        # of them fails on the name it dropped.
        for name in (".gitattributes", ".gitignore", "README.md", "descriptor.mod", "thumbnail.png"):
            self.write(name, "")
        (self.root / ".vscode").mkdir()
        (self.root / ".git").mkdir()
        (self.root / "tests").mkdir()
        self.assertEqual(self.run_check(V._check_structure, self.root), [])

    def test_every_scan_dir_is_allowed(self) -> None:
        # DERIVED FROM THE CONSTANT for the reason the descriptor keys are: a
        # directory added to SCAN_DIRS must not start warning at a mod root.
        for name in V.SCAN_DIRS:
            (self.root / name).mkdir()
        self.assertEqual(self.run_check(V._check_structure, self.root), [])


class TestScriptFile(ValidateTestCase):
    """Braces, which CK3 answers by truncating the rest of the file in silence."""

    def check_script(self, relpath: str, text: str) -> tuple[list[str], list]:
        path = self.write(relpath, text)
        issues: list[V.Issue] = []
        defs = V._check_script_file(relpath, path, issues)
        return [issue.format() for issue in issues], defs

    def test_a_balanced_file_is_silent(self) -> None:
        found, _ = self.check_script("common/a.txt", "a = {\n\tb = yes\n}\n")
        self.assertEqual(found, [])

    def test_an_unclosed_brace_reports_the_difference(self) -> None:
        found, _ = self.check_script("common/a.txt", "a = {\n\tb = yes\n")
        self.assertOneMatching(found, "unbalanced braces: 1 `{` vs 0 `}` (diff 1)")

    def test_a_stray_closing_brace_reports_its_line(self) -> None:
        found, _ = self.check_script("common/a.txt", "a = yes\n}\n")
        self.assertOneMatching(found, "common/a.txt:2: closing brace with no matching opening brace")

    def test_top_level_definitions_come_back_for_script_directories(self) -> None:
        _, defs = self.check_script("common/a.txt", "first = {\n}\nsecond = {\n}\n")
        self.assertEqual(defs, [("first", 1), ("second", 3)])

    def test_every_directory_the_check_names_yields_definitions(self) -> None:
        # ONE FIXTURE PER PREFIX. The test above covers `common/` alone, so
        # dropping `events/` or `history/` from the tuple was a silent
        # narrowing: definitions in those trees would stop being collected and
        # the duplicate-key check would stop seeing them, with nothing red.
        for prefix in ("common", "events", "history"):
            _, defs = self.check_script(f"{prefix}/a.txt", "only = {\n}\n")
            self.assertEqual(defs, [("only", 1)], prefix)

    def test_a_directory_the_check_does_not_name_yields_nothing(self) -> None:
        # The other side of the same boundary: a tuple widened to everything
        # passes the test above and this one is what notices.
        _, defs = self.check_script("gfx/a.txt", "only = {\n}\n")
        self.assertEqual(defs, [])

    def test_an_unreadable_file_is_an_error_and_yields_no_definitions(self) -> None:
        # THE ONLY ARM OF THIS FUNCTION THAT CANNOT BE REACHED BY WRITING A
        # FIXTURE, so it is reached by making the read fail. It matters because
        # the alternative to reporting is a file the gate skipped in silence,
        # which is the failure mode the whole module exists to end.
        path = self.write("common/a.txt", "a = {\n}\n")
        issues: list[V.Issue] = []
        with mock.patch.object(V, "read_text", side_effect=OSError("boom")):
            defs = V._check_script_file("common/a.txt", path, issues)
        self.assertEqual(defs, [])
        self.assertOneMatching([i.format() for i in issues], "common/a.txt: unreadable: boom")

    def test_no_definitions_come_back_from_gui(self) -> None:
        # A .gui carries no top-level `key = {` the duplicate check can use, and
        # collecting them would report a collision between two windows that are
        # allowed to share a name. THE BRACE CHECK STILL RUNS on it, which is
        # the half worth having, so this asserts the split and not just silence.
        found, defs = self.check_script("gui/a.gui", "window = {\n")
        self.assertEqual(defs, [])
        self.assertOneMatching(found, "unbalanced braces")


class TestLocFile(ValidateTestCase):
    """Localization, where a missing BOM costs the whole file with no message."""

    def write_loc(self, relpath: str, text: str, bom: bool = True) -> tuple[list[str], list[str]]:
        path = self.write(relpath, (BOM if bom else "") + text)
        issues: list[V.Issue] = []
        keys = V._check_loc_file(relpath, path, issues)
        return [issue.format() for issue in issues], keys

    def test_a_well_formed_file_is_silent_and_yields_its_keys(self) -> None:
        found, keys = self.write_loc(
            "localization/english/a_l_english.yml",
            'l_english:\n bc_one:0 "One"\n bc_two:0 "Two"\n',
        )
        self.assertEqual(found, [])
        self.assertEqual(sorted(keys), ["bc_one", "bc_two"])

    def test_a_missing_bom_is_an_error_on_line_one(self) -> None:
        found, _ = self.write_loc(
            "localization/english/a_l_english.yml", 'l_english:\n bc_one:0 "One"\n', bom=False
        )
        self.assertOneMatching(found, ":1: missing UTF-8 BOM; CK3 will ignore the entire file")

    def test_a_filename_without_the_language_suffix_stops_the_check(self) -> None:
        # It returns early, so the missing header below it is NOT reported. That
        # is deliberate - every later message would be noise about a file CK3
        # will not open - and it is asserted so a rewrite cannot quietly make
        # the filename error non-fatal.
        found, keys = self.write_loc("localization/english/a.yml", "nothing here\n")
        self.assertEqual(found, ["ERROR localization/english/a.yml: filename must end with `_l_<language>.yml`"])
        self.assertEqual(keys, [])

    def test_an_unknown_language_in_the_filename_warns(self) -> None:
        found, _ = self.write_loc(
            "localization/klingon/a_l_klingon.yml", 'l_klingon:\n bc_one:0 "One"\n'
        )
        self.assertOneMatching(found, "unknown language `klingon` in filename")

    def test_every_known_language_is_accepted(self) -> None:
        # DERIVED FROM THE CONSTANT. A language dropped from KNOWN_LANGS would
        # start warning on a file that has always been correct.
        for lang in sorted(V.KNOWN_LANGS):
            found, _ = self.write_loc(
                f"localization/{lang}/a_l_{lang}.yml", f'l_{lang}:\n bc_one:0 "One"\n'
            )
            self.assertEqual(found, [], f"{lang} warned")

    def test_a_file_with_no_language_folder_has_nothing_to_disagree_with(self) -> None:
        # `localization/a_l_english.yml` splits into two parts, so there IS no
        # folder to compare and `folder_lang` stays None. Loosening the length
        # test to `> 1` makes `parts[1]` the FILENAME, which never equals a
        # language and false-errors on a legal layout. Both directions of that
        # boundary are pinned - the wrong-folder case below is the other one.
        found, keys = self.write_loc(
            "localization/a_l_english.yml", 'l_english:\n bc_one:0 "One"\n'
        )
        self.assertEqual(found, [])
        self.assertEqual(keys, ["bc_one"])

    def test_a_file_in_the_wrong_language_folder_is_an_error(self) -> None:
        found, _ = self.write_loc(
            "localization/english/a_l_spanish.yml", 'l_spanish:\n bc_one:0 "One"\n'
        )
        self.assertOneMatching(found, "file is `_l_spanish` but sits in localization/english/")

    def test_a_missing_header_is_an_error(self) -> None:
        found, _ = self.write_loc("localization/english/a_l_english.yml", ' bc_one:0 "One"\n')
        self.assertOneMatching(found, "missing `l_<language>:` header line")

    def test_a_header_disagreeing_with_the_filename_is_an_error(self) -> None:
        found, _ = self.write_loc(
            "localization/english/a_l_english.yml", 'l_spanish:\n bc_one:0 "One"\n'
        )
        self.assertOneMatching(found, "header is `l_spanish:` but filename says `_l_english`")

    def test_a_malformed_entry_reports_its_line(self) -> None:
        found, _ = self.write_loc(
            "localization/english/a_l_english.yml", 'l_english:\n bc_one:0 One\n'
        )
        self.assertOneMatching(found, "a_l_english.yml:2: malformed entry")

    def test_a_duplicate_key_warns_and_names_the_first_line(self) -> None:
        found, keys = self.write_loc(
            "localization/english/a_l_english.yml",
            'l_english:\n bc_one:0 "One"\n bc_one:0 "Again"\n',
        )
        self.assertOneMatching(found, "duplicate loc key `bc_one` (first at line 2)")
        self.assertEqual(keys, ["bc_one"])


class Source:
    """The one attribute `_check_ground_partition` reads off a playset source."""

    def __init__(self, root: Path) -> None:
        self.root = root


class TestGroundPartition(ValidateTestCase):
    """The six ground bands must cover every AGOT base terrain exactly once."""

    def bands(self, names: list[str]) -> None:
        body = "".join(f"\tagot_is_{name}_terrain = yes\n" for name in names)
        self.write(V.BC_GROUND_FILE, "bc_ground = {\n" + body + "}\n")

    def ground(self, sources: list[Source] | None = None) -> list[str]:
        with mock.patch.object(V, "playset_sources", return_value=sources or []):
            return self.run_check(V._check_ground_partition, self.cfg(), self.root)

    def agot(self, names: list[str], at: str = "agot_source", body: str = "") -> Source:
        source_root = self.root / at
        path = source_root / V.AGOT_TERRAIN_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(f"agot_is_{name}_terrain = {{\n}}\n" for name in names) + body,
            encoding="utf-8",
        )
        return Source(source_root)

    def test_a_mod_without_the_file_is_skipped_entirely(self) -> None:
        # This check is mod-specific and runs against every mod in the
        # workspace. A mod that has no ground bands must produce nothing at all,
        # not even the SKIPPED warning - agot_conflict_merge and bc_spike both
        # validate at 0/0 and this is what keeps them there.
        self.assertEqual(self.ground(), [])

    def test_a_missing_base_is_an_error(self) -> None:
        self.bands([n for n in V.BC_GROUND_BASES if n != "taiga"])
        found = self.ground()
        self.assertOneMatching(found, "terrain `taiga` is in no ground band")

    def test_a_helper_that_is_not_a_base_is_an_error(self) -> None:
        self.bands(V.BC_GROUND_BASES + ["majorroad"])
        found = self.ground()
        self.assertOneMatching(found, "`agot_is_majorroad_terrain` is not a base terrain helper")

    def test_a_base_in_two_bands_is_an_error(self) -> None:
        self.bands(V.BC_GROUND_BASES + ["taiga"])
        found = self.ground()
        self.assertOneMatching(found, "terrain `taiga` is in more than one ground band")

    def test_a_complete_partition_with_no_playset_skips_loudly(self) -> None:
        # THE SKIP IS THE ASSERTION. A machine with no playset configured must
        # say the AGOT-side check did not happen, because a silent skip reads
        # exactly like a pass and this half exists for the case nobody watches.
        self.bands(V.BC_GROUND_BASES)
        found = self.ground()
        self.assertOneMatching(found, "SKIPPED the AGOT-side check")

    def test_a_complete_partition_against_a_matching_agot_is_silent(self) -> None:
        self.bands(V.BC_GROUND_BASES)
        source = self.agot(V.BC_GROUND_BASES + sorted(V.BC_GROUND_NON_BASES))
        self.assertEqual(self.ground([source]), [])

    def test_a_terrain_agot_added_is_an_error(self) -> None:
        self.bands(V.BC_GROUND_BASES)
        source = self.agot(V.BC_GROUND_BASES + ["saltmarsh"])
        found = self.ground([source])
        self.assertOneMatching(found, "AGOT ships `agot_is_saltmarsh_terrain`, which is in no ground band")

    def test_a_terrain_agot_dropped_is_an_error(self) -> None:
        self.bands(V.BC_GROUND_BASES)
        source = self.agot([n for n in V.BC_GROUND_BASES if n != "glacier"])
        found = self.ground([source])
        self.assertOneMatching(found, "band uses `agot_is_glacier_terrain`, which AGOT no longer defines")

    def test_the_cross_cutting_helpers_are_not_read_as_agot_bases(self) -> None:
        # BC_GROUND_NON_BASES exists because the AGOT file defines road and
        # location-validity helpers alongside the terrain ones. Without the
        # subtraction each of them errors as an unbanded terrain, which is a
        # false failure on a correct mod.
        self.bands(V.BC_GROUND_BASES)
        source = self.agot(V.BC_GROUND_BASES + sorted(V.BC_GROUND_NON_BASES))
        found = self.ground([source])
        for name in V.BC_GROUND_NON_BASES:
            self.assertNoneMatching(found, name)

    def test_a_helper_agot_only_mentions_is_not_read_as_shipped(self) -> None:
        # THE TWO SIDES USE TWO DIFFERENT PATTERNS AND MUST KEEP DOING SO. The
        # mod side scans with TERRAIN_HELPER_RE, which matches a bare mention,
        # because a ground band is nothing but mentions. The AGOT side scans
        # with TERRAIN_DEF_RE, which matches only `agot_is_x_terrain = {` at
        # column zero, because AGOT's terrain file also USES its helpers inside
        # the bodies of other triggers. Point the AGOT side at the loose
        # pattern and every such use reads as a terrain AGOT ships, which
        # errors on a mod that is correct.
        self.bands(V.BC_GROUND_BASES)
        source = self.agot(
            V.BC_GROUND_BASES,
            body="agot_terrain_is_watery = {\n\tagot_is_saltmarsh_terrain = yes\n}\n",
        )
        self.assertEqual(self.ground([source]), [])

    def test_the_last_source_shipping_the_file_is_the_one_read(self) -> None:
        # THE LOOKUP HAS NO `break` ON PURPOSE. playset_sources yields in load
        # order, so when two enabled sources both carry AGOT's terrain file the
        # later one is what the game loads, and this check has to agree with
        # the game. The earlier source here still defines a terrain that was
        # since removed; stopping at the first hit reports a mod that matches
        # the file actually loaded as wrong.
        self.bands(V.BC_GROUND_BASES)
        stale = self.agot(V.BC_GROUND_BASES + ["saltmarsh"], at="agot_old")
        current = self.agot(V.BC_GROUND_BASES, at="agot_new")
        self.assertEqual(self.ground([stale, current]), [])


class TestValidateMod(ValidateTestCase):
    """The whole run: what only fires once the per-file results are combined."""

    def setUp(self) -> None:
        super().setUp()
        self.write("descriptor.mod", GOOD_DESCRIPTOR)

    def validate(self, strict: bool = False) -> list[str]:
        return [i.format() for i in V.validate_mod(self.cfg(), self.root, strict=strict)]

    def test_a_folder_that_does_not_exist_reports_once_and_stops(self) -> None:
        missing = self.root / "no_such_mod"
        issues = V.validate_mod(self.cfg(), missing, strict=True)
        self.assertEqual([i.message for i in issues], ["mod folder does not exist"])

    def test_a_minimal_clean_mod_is_silent(self) -> None:
        self.write("common/scripted_effects/a.txt", "bc_a = {\n}\n")
        self.assertEqual(self.validate(strict=True), [])

    def test_the_same_key_defined_twice_warns_and_names_the_first_site(self) -> None:
        self.write("common/scripted_effects/a.txt", "bc_a = {\n}\n")
        self.write("common/scripted_effects/b.txt", "bc_a = {\n}\n")
        found = self.validate()
        self.assertOneMatching(found, "`bc_a` also defined in common/scripted_effects/a.txt:1")

    def test_a_custom_call_with_no_definition_in_this_mod_is_an_error(self) -> None:
        self.write(
            "localization/english/a_l_english.yml",
            BOM + 'l_english:\n bc_line:0 "[dude.Custom(\'bc_missing\')]"\n',
        )
        found = self.validate()
        self.assertOneMatching(
            found, "`Custom('bc_missing')` has no customizable_localization definition in this mod"
        )

    def test_a_custom_call_that_resolves_is_silent(self) -> None:
        self.write("common/customizable_localization/c.txt", "bc_there = {\n}\n")
        self.write(
            "localization/english/a_l_english.yml",
            BOM + 'l_english:\n bc_line:0 "[dude.Custom(\'bc_there\')]"\n',
        )
        self.assertNoneMatching(self.validate(), "Custom(")

    def test_a_foreign_custom_call_is_not_resolved_at_all(self) -> None:
        # A call naming a vanilla or AGOT definition cannot be resolved from the
        # mod root and must not error. THE PREFIX IS WHAT DECIDES, and this is
        # the test that stops the resolver being widened to everything.
        self.write(
            "localization/english/a_l_english.yml",
            BOM + 'l_english:\n bc_line:0 "[dude.Custom(\'agot_something\')]"\n',
        )
        self.assertNoneMatching(self.validate(), "Custom(")

    def test_an_arm_naming_a_loc_key_this_mod_lacks_is_an_error(self) -> None:
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttext = {\n\t\tlocalization_key = bc_absent\n\t}\n}\n",
        )
        found = self.validate()
        self.assertOneMatching(found, "`localization_key = bc_absent` has no loc entry in this mod")

    def test_an_arm_that_resolves_is_silent(self) -> None:
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttext = {\n\t\tlocalization_key = bc_present\n\t}\n}\n",
        )
        self.write(
            "localization/english/a_l_english.yml", BOM + 'l_english:\n bc_present:0 "Here"\n'
        )
        self.assertNoneMatching(self.validate(), "localization_key")

    def test_a_definition_with_no_unguarded_arm_is_an_error(self) -> None:
        # THE FAILURE THIS CATCHES IS SILENT AT BOTH ENDS. If every arm is
        # guarded and no trigger matches, CK3 renders the definition as the
        # empty string - which is exactly what a definition that does not exist
        # renders as, and exactly what a correct optional clause renders as. The
        # mod's convention is therefore an unguarded LAST arm, empty if the
        # clause is meant to be optional, so that "nothing to say" is written
        # down rather than inferred from a gap.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        self.assertOneMatching(self.validate(), "`bc_there` has no unguarded `text` arm")

    def test_a_definition_whose_unguarded_arm_is_last_is_silent(self) -> None:
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        self.assertNoneMatching(self.validate(), "arm")

    def test_an_arm_below_the_unguarded_arm_is_unreachable(self) -> None:
        # CK3 takes the FIRST matching arm, and an unguarded arm matches always,
        # so everything below it is dead. Dead prose in this mod is worse than
        # dead code: the comments are the design record, and an arm nobody can
        # ever see still reads as shipped.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        self.assertOneMatching(self.validate(), "unreachable: `bc_there` has an unguarded arm above it")

    def test_random_valid_suspends_the_order_rule_and_not_the_fallback_rule(self) -> None:
        # BOTH HALVES IN ONE TEST because the pair is the behaviour. Under
        # `random_valid = yes` CK3 pools every valid arm instead of taking the
        # first, so no arm is dead and the ordering complaint would be wrong.
        # The fallback rule survives regardless: an empty pool still renders
        # nothing, and that is what the unguarded arm is there to prevent.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_pooled = {\n\ttype = character\n\trandom_valid = yes\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n}\n"
            "bc_empty_pool = {\n\ttype = character\n\trandom_valid = yes\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        found = self.validate()
        self.assertNoneMatching(found, "unreachable")
        self.assertOneMatching(found, "`bc_empty_pool` has no unguarded `text` arm")

    def test_a_trigger_nested_below_the_arm_is_not_the_arm_s_guard(self) -> None:
        # `trigger` appears inside arms for a second reason - as the key of a
        # nested block such as `trigger_if` fields, or inside a `limit` - and a
        # substring test on the arm body reads those as guards. That reading
        # turns the fallback rule off for exactly the arms most likely to be
        # complicated, which is the wrong half to stop checking. Only a
        # `trigger` at the arm's OWN depth guards it.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n"
            "\t\tfoo = { trigger = { always = yes } }\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        self.assertNoneMatching(self.validate(), "arm")

    def test_two_unguarded_arms_kill_everything_below_the_first_of_them(self) -> None:
        # THE SHAPE A SECOND FALLBACK ACTUALLY TAKES. Nobody writes two
        # fallbacks on purpose; one arrives when a guarded arm is edited and its
        # trigger goes with it, and the arms between the two then look fine from
        # either end. The dead run starts at the FIRST unguarded arm, so the
        # second fallback is itself dead - measuring from the last one reports
        # nothing at all on the one file where the mistake is easiest to make.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n"
            "\ttext = {\n\t\ttrigger = { always = yes }\n\t\tlocalization_key = bc_p\n\t}\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        found = [issue for issue in self.validate() if "unreachable" in issue]
        self.assertEqual(len(found), 2, found)

    def test_a_block_that_is_not_a_text_arm_is_not_counted_as_one(self) -> None:
        # A definition may carry depth-1 blocks that are not arms, and counting
        # one as an arm makes the verdict depend on a key the check never
        # examined: here it would call a block BELOW the fallback a dead arm,
        # which is a complaint about the wrong thing in the wrong place.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttype = character\n"
            "\ttext = {\n\t\tlocalization_key = bc_p\n\t}\n"
            "\tsome_other_block = {\n\t\ttrigger = { always = yes }\n\t}\n}\n",
        )
        self.write("localization/english/a_l_english.yml", BOM + 'l_english:\n bc_p:0 "Here"\n')
        self.assertNoneMatching(self.validate(), "arm")

    def test_a_definition_outside_the_custom_loc_directory_is_not_shape_checked(self) -> None:
        # The rule is a property of customizable_localization, not of the word
        # `text`. A scripted effect with a guarded `text` block in it is not a
        # definition with a missing fallback.
        self.write(
            "common/scripted_effects/e.txt",
            "bc_effect = {\n\ttext = {\n\t\ttrigger = { always = yes }\n\t}\n}\n",
        )
        self.assertNoneMatching(self.validate(), "arm")

    def test_the_missing_localization_warning_is_strict_only(self) -> None:
        # BOTH SIDES IN ONE TEST because the pair IS the behaviour: the same
        # tree has to be silent without --strict and loud with it. Split in two,
        # a check that never fires passes the first half and a check that always
        # fires passes the second.
        self.write("common/traits/t.txt", "bc_trait = {\n}\n")
        self.assertNoneMatching(self.validate(strict=False), "has no localization key")
        self.assertOneMatching(
            self.validate(strict=True), "`bc_trait` has no localization key in this mod"
        )

    def test_a_script_value_macro_is_not_expected_to_have_localization(self) -> None:
        # `@name = 3` is a script-value macro, not a definition anyone can name
        # in a tooltip. Without the `@` guard every macro in a LOC_EXPECTED
        # directory warns under --strict.
        self.write("common/traits/t.txt", "@bc_macro = 3\nbc_trait = {\n}\n")
        self.assertNoneMatching(self.validate(strict=True), "@bc_macro")

    # THE LIST IS WRITTEN OUT, NOT READ BACK OUT OF V.LOC_EXPECTED. The first
    # version of the test below took its fixtures from the constant, which puts
    # the same set on both sides: dropping `common/decisions` also dropped the
    # fixture that would have caught it, and both single-drop mutants survived.
    # This is the trap the extension list in test_sweep_backticks.py records,
    # walked into again three commits later. NO NUMBER IS GIVEN for the length.
    LISTED_LOC_EXPECTED = (
        "common/character_interactions",
        "common/decisions",
        "common/traits",
    )

    def test_every_category_that_expects_localization_is_checked(self) -> None:
        # One definition per listed category, one warning per listed category.
        for i, category in enumerate(self.LISTED_LOC_EXPECTED):
            self.write(f"{category}/f{i}.txt", f"bc_def{i} = {{\n}}\n")
        found = self.validate(strict=True)
        for i in range(len(self.LISTED_LOC_EXPECTED)):
            self.assertOneMatching(found, f"`bc_def{i}` has no localization key in this mod")

    def test_the_literal_category_list_is_the_one_the_module_declares(self) -> None:
        # What the literal buys, beyond killing the single drops: a category
        # added to LOC_EXPECTED without a fixture beside it fails HERE, naming
        # the line to edit, rather than being checked by no test at all.
        self.assertEqual(V.LOC_EXPECTED, set(self.LISTED_LOC_EXPECTED))

    def test_a_category_outside_the_list_is_not_expected_to_have_localization(self) -> None:
        # The widening side. A LOC_EXPECTED holding every category passes the
        # test above; this is what notices, and common/scripted_effects is the
        # case that matters - nothing in it is ever named in a tooltip.
        self.write("common/scripted_effects/e.txt", "bc_effect = {\n}\n")
        self.assertNoneMatching(self.validate(strict=True), "has no localization key")

    def test_every_scanned_extension_is_read(self) -> None:
        # ONE FIXTURE PER EXTENSION the file loop names, each carrying a brace
        # error, so a dropped extension fails on the file it stopped opening.
        # Written out rather than derived: the tuple is inline in validate_mod
        # and reading it back out would put the same list on both sides.
        for ext in (".txt", ".gui", ".gfx", ".asset", ".info"):
            self.write(f"common/scripted_effects/x{ext}", "bc_a = {\n")
        found = self.validate()
        for ext in (".txt", ".gui", ".gfx", ".asset", ".info"):
            self.assertOneMatching(found, f"x{ext}: unbalanced braces")

    def test_an_unscanned_extension_is_not_read(self) -> None:
        # `.shader`, NOT `.json`: the walk itself filters to SCRIPT_EXTS, so a
        # .json never reaches this loop at all and asserting on one says
        # nothing about the loop's own tuple. `.shader` and `.mod` are the two
        # extensions the walk yields and this loop declines, which makes them
        # the only fixtures that can see it widened.
        self.write("common/scripted_effects/x.shader", "bc_a = {\n")
        self.assertNoneMatching(self.validate(), "x.shader")

    def test_a_custom2_call_resolves_like_a_custom_call(self) -> None:
        # `.Custom2('name')` is the two-scope form and names the same kind of
        # definition. Dropping the optional `2` from the pattern stops every
        # one of them being checked, which is silent by construction: a missing
        # definition renders as nothing at all in game.
        self.write(
            "localization/english/a_l_english.yml",
            BOM + 'l_english:\n bc_line:0 "[dude.Custom2(\'bc_missing\', other)]"\n',
        )
        self.assertOneMatching(
            self.validate(),
            "`Custom('bc_missing')` has no customizable_localization definition in this mod",
        )

    def test_a_comment_touching_an_arm_key_is_not_read_as_part_of_it(self) -> None:
        # `localization_key = bc_present# note` is legal script with no space
        # before the comment. `\S+` captures `bc_present#` and false-errors on
        # a key that is present, which is why the pattern excludes `#`.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_there = {\n\ttext = {\n\t\tlocalization_key = bc_present# note\n\t}\n}\n",
        )
        self.write(
            "localization/english/a_l_english.yml", BOM + 'l_english:\n bc_present:0 "Here"\n'
        )
        self.assertNoneMatching(self.validate(), "localization_key")

    def test_two_arms_are_each_reported_on_their_own_line(self) -> None:
        # THE LINE NUMBER IS THE WHOLE POINT OF THE MESSAGE. _scan_matches
        # derives it by counting newlines BEFORE the match and adding one, and
        # neither half of that had a test: dropping the `+ 1` reports every
        # issue one line high, and counting the whole file instead of the
        # prefix reports every issue at the last line. Both leave the message
        # text intact, so every other test here stays green over either. TWO
        # ARMS, NOT ONE, because a single arm cannot tell a per-match count
        # from a whole-file count.
        self.write(
            "common/customizable_localization/c.txt",
            "bc_one = {\n\ttext = {\n\t\tlocalization_key = bc_absent_a\n\t}\n}\n"
            "bc_two = {\n\ttext = {\n\t\tlocalization_key = bc_absent_b\n\t}\n}\n",
        )
        found = self.validate()
        self.assertOneMatching(found, "c.txt:3: `localization_key = bc_absent_a`")
        self.assertOneMatching(found, "c.txt:8: `localization_key = bc_absent_b`")

    def test_a_file_that_vanilla_also_ships_is_reported_as_an_override(self) -> None:
        # THE ONLY INFO-LEVEL LINE THE VALIDATOR EMITS, and nothing reached it:
        # every other fixture here points game_dir at a directory that does not
        # exist precisely so this branch stays out of the way. It is worth a
        # line because an accidental override of a vanilla file is how a mod
        # breaks something it never mentions.
        rel = "common/scripted_effects/a.txt"
        game_copy = self.root / "nonexistent_game" / "game" / rel
        game_copy.parent.mkdir(parents=True, exist_ok=True)
        game_copy.write_text("vanilla = {\n}\n", encoding="utf-8")
        self.write(rel, "bc_a = {\n}\n")
        self.assertOneMatching(self.validate(), f"overrides 1 vanilla file(s); first: {rel}")

    def test_a_mod_overriding_nothing_says_nothing(self) -> None:
        self.write("common/scripted_effects/a.txt", "bc_a = {\n}\n")
        self.assertNoneMatching(self.validate(), "overrides")


class TestSummarize(ValidateTestCase):
    """The counts every commit message in this tree quotes."""

    def test_each_level_is_counted_separately(self) -> None:
        issues = [
            V.Issue(V.ERROR, "a", None, "x"),
            V.Issue(V.WARN, "b", None, "y"),
            V.Issue(V.WARN, "c", None, "z"),
        ]
        self.assertEqual(V.summarize(issues), {V.ERROR: 1, V.WARN: 2, V.INFO: 0})

    def test_every_level_is_present_even_at_zero(self) -> None:
        # The caller formats `N errors, M warnings` off this dict without a
        # `.get`, so a level missing from an empty summary is a KeyError on the
        # happy path - the one path that must never raise.
        self.assertEqual(V.summarize([]), {V.ERROR: 0, V.WARN: 0, V.INFO: 0})


class TestAgainstTheRealMod(unittest.TestCase):
    """The fixtures above prove the checks fire. This proves they agree with the tree."""

    def test_battle_chronicles_is_at_its_documented_baseline(self) -> None:
        # THE BASELINE IS 0 ERRORS AND 2 WARNINGS, both of them the `namespace`
        # false positive that `_check_script_file` cannot avoid: three event
        # files legitimately share one namespace and the duplicate-definition
        # check has no way to know it. The number is asserted HERE, once, so
        # that a commit message quoting it is quoting a tested fact.
        # THE MOD FOLDER IS NOT THE ONLY THING THIS DEPENDS ON. The warning
        # count is 2 only when the playset resolves AGOT; on a checkout with no
        # playset `_check_ground_partition` emits its SKIPPED warning as a third
        # and the assertion goes red for a reason that is not a regression.
        # Both preconditions are therefore checked, and each skips rather than
        # fails.
        from ck3lib.paths import load_config
        from ck3lib.sources import playset_sources

        root = Path(__file__).resolve().parents[2]
        mod = root / "mods" / "battle_chronicles"
        if not mod.is_dir():
            self.skipTest("battle_chronicles is not in this checkout")
        cfg = load_config()
        if not any((s.root / V.AGOT_TERRAIN_FILE).is_file() for s in playset_sources(cfg)):
            self.skipTest(f"no enabled source provides {V.AGOT_TERRAIN_FILE}")
        counts = V.summarize(V.validate_mod(cfg, mod, strict=True))
        self.assertEqual(counts[V.ERROR], 0)
        self.assertEqual(counts[V.WARN], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
