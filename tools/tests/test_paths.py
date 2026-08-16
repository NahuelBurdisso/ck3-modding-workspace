"""Regression tests for tools/ck3lib/paths.py.

WHAT A PATH BUG COSTS HERE. This module is the only place that knows where the
game, the user directory and the workshop are, and every other tool asks it
rather than guessing. A wrong answer does not raise: `iter_files` over a
directory that is not there yields nothing, so a validator run reports a clean
mod because it read no files, and an index build reports forty-eight sources
scanned and zero definitions found. `Config.check` exists to turn that silence
into a message, which makes it the one function here that has to be right.

`version_matches` IS NOT A VERSION COMPARISON and reads like a broken one until
that is said out loud. It answers whether a mod's DECLARED support covers the
installed build, so it compares only the segments both strings have and treats
`*` on either side as agreement. `1.19` covers `1.19.0.6`; that is the intended
answer, not a truncation bug.

Run it with `python tools/tests/test_paths.py`. Stdlib unittest, no pytest, for
the reason test_citations.py gives in its own header.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import paths as P  # noqa: E402


def config(**overrides: object) -> P.Config:
    fields: dict[str, object] = {
        "game_dir": Path("/g"),
        "user_dir": Path("/u"),
        "workshop_dir": Path("/w"),
        "workspace_dir": Path("/ws"),
        "app_id": "1158310",
        "base_mod_id": "0",
        "supported_version": "1.19",
    }
    fields.update(overrides)
    return P.Config(**fields)  # type: ignore[arg-type]


class TestDerivedPaths(unittest.TestCase):
    def test_the_game_root_is_the_game_folder_and_not_the_install_folder(self) -> None:
        # THE DISTINCTION IS THE WHOLE PROPERTY. `game/` is what mirrors a mod's
        # own layout - common/, events/, localization/ - so every lookup that
        # compares a mod file against vanilla resolves through here. Point it one
        # level up and every such lookup misses silently.
        self.assertEqual(config().game_root, Path("/g/game"))

    def test_the_four_user_directory_paths_hang_off_user_dir(self) -> None:
        cfg = config()
        self.assertEqual(cfg.mod_dir, Path("/u/mod"))
        self.assertEqual(cfg.dlc_load, Path("/u/dlc_load.json"))
        self.assertEqual(cfg.game_logs, Path("/u/logs"))
        self.assertEqual(cfg.exe, Path("/g/binaries/ck3.exe"))

    def test_the_workspace_paths_hang_off_workspace_dir(self) -> None:
        # `mods_src` IS GIT-TRACKED AND `mod_dir` IS NOT, and they are the two
        # halves of the deploy step. Swapping them writes generated files into
        # the repo and tracked sources into the game's mod folder.
        cfg = config()
        self.assertEqual(cfg.mods_src, Path("/ws/mods"))
        self.assertEqual(cfg.index_db, Path("/ws/index/ck3.sqlite3"))
        self.assertEqual(cfg.run_logs, Path("/ws/logs"))

    def test_loc_languages_defaults_to_english_and_spanish(self) -> None:
        self.assertEqual(config().loc_languages, ("english", "spanish"))


class TestCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "game" / "game").mkdir(parents=True)
        (self.root / "user").mkdir()
        (self.root / "workshop").mkdir()

    def good(self, **overrides: object) -> P.Config:
        fields: dict[str, object] = {
            "game_dir": self.root / "game",
            "user_dir": self.root / "user",
            "workshop_dir": self.root / "workshop",
        }
        fields.update(overrides)
        return config(**fields)

    def test_a_complete_installation_reports_nothing(self) -> None:
        self.assertEqual(self.good().check(), [])

    def test_each_missing_directory_is_named_separately(self) -> None:
        # ALL THREE ARE REPORTED, not the first. An operator who has just moved
        # a drive has all three wrong, and a check that stops at the first one
        # costs three runs to learn that.
        problems = config(
            game_dir=self.root / "nope",
            user_dir=self.root / "nope",
            workshop_dir=self.root / "nope",
        ).check()
        self.assertEqual(len(problems), 3)
        self.assertTrue(any(p.startswith("game_dir invalid") for p in problems))
        self.assertTrue(any(p.startswith("user_dir invalid") for p in problems))
        self.assertTrue(any(p.startswith("workshop_dir invalid") for p in problems))

    def test_a_game_dir_without_its_game_folder_is_reported(self) -> None:
        # THE COMMON MISCONFIGURATION, and the one that fails most quietly: the
        # install path is right, so nothing looks wrong, and every vanilla
        # lookup below it resolves to a directory that does not exist.
        problems = self.good(game_dir=self.root / "user").check()
        self.assertEqual(len(problems), 1)
        self.assertIn("game_dir invalid", problems[0])

    def test_the_message_names_the_path_that_was_looked_for(self) -> None:
        problems = self.good(game_dir=self.root / "nope").check()
        self.assertIn(str(self.root / "nope" / "game"), problems[0])


class TestLoadConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "ck3.config.json"
        real = P.CONFIG_FILE
        P.CONFIG_FILE = self.file
        self.addCleanup(lambda: setattr(P, "CONFIG_FILE", real))
        env = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(env)))

    def write(self, **overrides: object) -> None:
        raw: dict[str, object] = {
            "game_dir": "C:/g",
            "user_dir": "C:/u",
            "workshop_dir": "C:/w",
            "workspace_dir": "C:/ws",
            "app_id": "1158310",
            "base_mod_id": "0",
            "supported_version": "1.19",
        }
        raw.update(overrides)
        self.file.write_text(json.dumps(raw), encoding="utf-8")

    def test_directory_keys_are_paths_and_the_rest_are_left_alone(self) -> None:
        # THE JSON HOLDS STRINGS AND EVERY CALLER USES `/` ON THE RESULT. Leave
        # one as a string and the failure is a TypeError three modules away.
        self.write()
        cfg = P.load_config()
        for value in (cfg.game_dir, cfg.user_dir, cfg.workshop_dir, cfg.workspace_dir):
            self.assertIsInstance(value, Path)
        self.assertEqual(cfg.app_id, "1158310")
        self.assertEqual(cfg.supported_version, "1.19")

    def test_an_environment_variable_in_a_path_is_expanded(self) -> None:
        # The checked-in config spells the user directory through a variable so
        # it is the same file on every machine. Unexpanded, it becomes a
        # directory literally named with the variable, which `check` then
        # reports as missing - true, but not the reason.
        os.environ["CK3_TEST_HOME"] = str(Path(self.tmp.name) / "home")
        self.write(user_dir="$CK3_TEST_HOME/Documents")
        self.assertEqual(
            P.load_config().user_dir, Path(self.tmp.name) / "home" / "Documents"
        )

    def test_loc_languages_becomes_a_tuple_because_the_config_is_frozen(self) -> None:
        # A frozen dataclass with a list in it is only shallowly immutable, and
        # this one is passed to every tool in the tree.
        self.write(loc_languages=["english"])
        self.assertEqual(P.load_config().loc_languages, ("english",))

    def test_a_config_without_loc_languages_keeps_the_default(self) -> None:
        self.write()
        self.assertEqual(P.load_config().loc_languages, ("english", "spanish"))


class TestVersionMatches(unittest.TestCase):
    def test_identical_versions_match(self) -> None:
        self.assertTrue(P.version_matches("1.19.0.6", "1.19.0.6"))

    def test_a_shorter_declaration_matches_a_longer_build(self) -> None:
        # `1.19` IS A CLAIM ABOUT TWO SEGMENTS and says nothing about the rest,
        # so it covers every 1.19.x. This is how AGOT and most of vanilla's own
        # mods declare support, and treating it as a mismatch would report the
        # whole playset as out of date on every patch.
        self.assertTrue(P.version_matches("1.19", "1.19.0.6"))
        self.assertTrue(P.version_matches("1.19.0.6", "1.19"))

    def test_a_wildcard_on_either_side_matches_that_segment(self) -> None:
        self.assertTrue(P.version_matches("1.*", "1.19.0.6"))
        self.assertTrue(P.version_matches("*.*.*", "1.19.0.6"))
        self.assertTrue(P.version_matches("1.19", "1.*"))

    def test_a_difference_in_any_compared_segment_is_a_mismatch(self) -> None:
        self.assertFalse(P.version_matches("1.18", "1.19"))
        self.assertFalse(P.version_matches("1.*.7", "1.19.6"))

    def test_a_missing_version_on_either_side_is_treated_as_matching(self) -> None:
        # A mod with no `supported_version` has declared nothing, and reporting
        # a mod as incompatible on the strength of a field it never filled in is
        # noise in a report whose only job is to be short enough to read.
        self.assertTrue(P.version_matches("", "1.19"))
        self.assertTrue(P.version_matches("1.19", ""))


class TestToPdxPath(unittest.TestCase):
    def test_backslashes_become_forward_slashes(self) -> None:
        # CK3 REJECTS MIXED SEPARATORS IN `path=`, and a rejected .mod file is
        # not an error in the launcher - the mod simply does not appear.
        self.assertEqual(P.to_pdx_path(Path("D:\\ck3\\mods\\bc")), "D:/ck3/mods/bc")

    def test_a_path_that_is_already_posix_is_unchanged(self) -> None:
        self.assertEqual(P.to_pdx_path(Path("mods/bc")), "mods/bc")


if __name__ == "__main__":
    unittest.main(verbosity=2)
