"""Regression tests for tools/ck3lib/sources.py.

THE MODULE THAT DECIDES WHAT GETS READ AT ALL. `iter_files` is the front door of
the validator and the index: a file it does not yield is a file nothing in this
workspace has ever looked at, and the report that comes back says the mod is
clean. Every failure mode here is a false negative, which is why the tests below
spend more effort on what is SKIPPED than on what is returned.

LOAD ORDER IS THE OTHER HALF. CK3 resolves a relative path by letting the LAST
enabled source that provides it win, so `playset_sources` returning the right
sources in the wrong order gives every override answer backwards - and an
override answer that is backwards still looks like an answer.

WHAT THESE TESTS DO NOT NEED. No game install and no user directory: every
fixture is a temp tree with a `Config` pointed at it. The one thing that cannot
be faked is a real playset, so nothing here asserts anything about the machine's
own dlc_load.json.

Run it with `python tools/tests/test_sources.py`. Stdlib unittest, no pytest,
for the reason test_citations.py gives in its own header.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ck3lib import sources as S  # noqa: E402
from ck3lib.paths import Config  # noqa: E402


class SourcesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.user = self.root / "user"
        self.workspace = self.root / "ws"
        (self.user / "mod").mkdir(parents=True)
        self.cfg = Config(
            game_dir=self.root / "game",
            user_dir=self.user,
            workshop_dir=self.root / "workshop",
            workspace_dir=self.workspace,
            app_id="1158310",
            base_mod_id="0",
            supported_version="1.19",
        )

    def write(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def mod_file(self, stem: str, body: str) -> Path:
        return self.write(self.user / "mod" / f"{stem}.mod", body)

    def set_enabled(self, *rels: str) -> None:
        self.write(self.user / "dlc_load.json", json.dumps({"enabled_mods": list(rels)}))


class TestIterFiles(SourcesTestCase):
    def test_a_content_file_is_yielded_with_a_posix_relative_path(self) -> None:
        # THE RELATIVE PATH IS THE IDENTITY OF A FILE across sources - it is what
        # the override comparison joins on - so a backslash in it makes a mod's
        # file and vanilla's file two different files on Windows and one file
        # everywhere else.
        target = self.write(self.root / "m" / "common" / "traits" / "x.txt", "a = b")
        self.assertEqual(list(S.iter_files(self.root / "m")), [("common/traits/x.txt", target)])

    def test_a_file_outside_the_scanned_directories_is_not_yielded(self) -> None:
        # A MOD ROOT HOLDS MORE THAN CONTENT: descriptor.mod, thumbnails, a .git
        # directory, whatever the author left there. The scan is a whitelist so
        # that none of it reaches a validator that would report on it.
        self.write(self.root / "m" / "descriptor.mod", 'name="M"')
        self.write(self.root / "m" / "notes" / "todo.txt", "later")
        self.assertEqual(list(S.iter_files(self.root / "m")), [])

    def test_an_unknown_extension_is_not_yielded(self) -> None:
        self.write(self.root / "m" / "gfx" / "a.png", "not script")
        self.write(self.root / "m" / "gfx" / "b.gfx", "script")
        self.assertEqual(
            [rel for rel, _ in S.iter_files(self.root / "m")], ["gfx/b.gfx"]
        )

    def test_the_extension_match_is_case_blind(self) -> None:
        # Vanilla ships mixed casing and Windows does not care, so a scan that
        # does would drop real files on the one platform this runs on.
        self.write(self.root / "m" / "events" / "a.TXT", "a = b")
        self.assertEqual([rel for rel, _ in S.iter_files(self.root / "m")], ["events/a.TXT"])

    def test_the_scan_recurses_to_any_depth(self) -> None:
        self.write(self.root / "m" / "common" / "a" / "b" / "c" / "d.txt", "a = b")
        self.assertEqual(
            [rel for rel, _ in S.iter_files(self.root / "m")], ["common/a/b/c/d.txt"]
        )

    def test_a_missing_top_level_directory_is_skipped_rather_than_raising(self) -> None:
        # No mod has all thirteen. A scan that insisted would run on nothing.
        self.write(self.root / "m" / "events" / "a.txt", "a = b")
        self.assertEqual([rel for rel, _ in S.iter_files(self.root / "m")], ["events/a.txt"])

    def test_a_root_that_does_not_exist_yields_nothing_and_does_not_raise(self) -> None:
        # THE SILENT FAILURE THIS MODULE'S TESTS EXIST FOR. A mis-resolved root
        # comes back as an empty scan, which reads downstream as a clean mod.
        # Nothing here can fix that; `Config.check` is where it is caught.
        self.assertEqual(list(S.iter_files(self.root / "gone")), [])

    def test_an_explicit_extension_set_replaces_the_default(self) -> None:
        self.write(self.root / "m" / "events" / "a.txt", "a = b")
        self.write(self.root / "m" / "localization" / "a.yml", "l_english:")
        self.assertEqual(
            [rel for rel, _ in S.iter_files(self.root / "m", {".yml"})],
            ["localization/a.yml"],
        )

    def test_an_empty_extension_set_means_every_file_not_no_file(self) -> None:
        # THE READING IS NOT OBVIOUS AND THE CALLERS DEPEND ON IT. `if exts and`
        # makes an empty set fall through the filter entirely, so `set()` asks
        # for everything. A caller that meant "nothing" would get the opposite,
        # so this is pinned rather than left to be rediscovered.
        self.write(self.root / "m" / "gfx" / "a.png", "binary")
        self.assertEqual([rel for rel, _ in S.iter_files(self.root / "m", set())], ["gfx/a.png"])


class TestReadModFile(SourcesTestCase):
    def test_a_pointer_file_that_is_not_there_is_none_rather_than_an_error(self) -> None:
        # dlc_load.json outlives the mods it names, so a stale entry is normal
        # and must not abort the whole playset scan.
        self.assertIsNone(S.read_mod_file(self.cfg, self.user / "mod" / "gone.mod", 1))

    def test_a_pointer_file_with_no_path_is_none(self) -> None:
        # Without `path` there is nothing to scan; a Source built on it would
        # resolve to the user directory itself and scan the whole playset.
        self.assertIsNone(S.read_mod_file(self.cfg, self.mod_file("a", 'name="A"'), 1))

    def test_a_relative_path_resolves_against_the_user_directory(self) -> None:
        # EVERY LOCAL MOD SPELLS IT THIS WAY - `path="mod/thing"` - because that
        # is what the launcher writes. Resolving it against the process's own
        # working directory would make the answer depend on where ck3.py was run
        # from.
        mod = self.mod_file("a", 'name="A"\npath="mod/a"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual(source.root, self.user / "mod/a")

    def test_an_absolute_path_is_left_alone(self) -> None:
        mod = self.mod_file("a", f'name="A"\npath="{(self.root / "elsewhere").as_posix()}"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual(source.root, self.root / "elsewhere")

    def test_a_remote_file_id_makes_it_a_workshop_source(self) -> None:
        mod = self.mod_file("a", 'name="A"\npath="mod/a"\nremote_file_id="123"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual((source.kind, source.mod_id), (S.WORKSHOP, "123"))

    def test_no_remote_file_id_makes_it_a_local_source(self) -> None:
        mod = self.mod_file("a", 'name="A"\npath="mod/a"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual((source.kind, source.mod_id), (S.LOCAL, None))

    def test_a_nameless_pointer_falls_back_to_its_own_filename(self) -> None:
        source = S.read_mod_file(self.cfg, self.mod_file("ugc_123", 'path="mod/a"'), 1)
        assert source is not None
        self.assertEqual(source.name, "ugc_123")

    def test_the_mods_own_descriptor_is_preferred_over_the_pointer(self) -> None:
        # THE TWO DISAGREE IN PRACTICE. The pointer is written by the launcher
        # and the descriptor by the author, and the version fields drift apart;
        # the one inside the mod is the one the game reads.
        mod = self.mod_file("a", 'name="A"\npath="mod/a"')
        inner = self.write(self.user / "mod" / "a" / "descriptor.mod", 'name="A"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual(source.descriptor, inner)

    def test_the_pointer_is_the_descriptor_when_the_mod_has_none(self) -> None:
        mod = self.mod_file("a", 'name="A"\npath="mod/a"')
        source = S.read_mod_file(self.cfg, mod, 1)
        assert source is not None
        self.assertEqual(source.descriptor, mod)

    def test_absent_version_fields_come_back_empty_rather_than_none(self) -> None:
        # `version_matches` takes strings and reads an empty one as "undeclared".
        # A None here would be a TypeError inside the compatibility report.
        source = S.read_mod_file(self.cfg, self.mod_file("a", 'path="mod/a"'), 1)
        assert source is not None
        self.assertEqual((source.version, source.supported_version), ("", ""))


class TestEnabledMods(SourcesTestCase):
    def test_a_missing_dlc_load_is_an_empty_list(self) -> None:
        self.assertEqual(S.enabled_mods(self.cfg), [])

    def test_the_enabled_list_is_returned_in_file_order(self) -> None:
        # FILE ORDER IS LOAD ORDER. dlc_load.json is not sorted and must not be:
        # the position in this list is what decides which mod wins a collision.
        self.set_enabled("mod/z.mod", "mod/a.mod")
        self.assertEqual(S.enabled_mods(self.cfg), ["mod/z.mod", "mod/a.mod"])

    def test_a_dlc_load_without_the_key_is_an_empty_list(self) -> None:
        self.write(self.user / "dlc_load.json", json.dumps({"enabled_dlcs": []}))
        self.assertEqual(S.enabled_mods(self.cfg), [])


class TestPlaysetSources(SourcesTestCase):
    def test_vanilla_comes_first_and_therefore_loses_every_collision(self) -> None:
        self.mod_file("a", 'name="A"\npath="mod/a"')
        self.set_enabled("mod/a.mod")
        sources = S.playset_sources(self.cfg)
        self.assertEqual([s.kind for s in sources], [S.VANILLA, S.LOCAL])
        self.assertEqual(sources[0].root, self.cfg.game_root)
        self.assertEqual(sources[0].order, 0)

    def test_vanilla_can_be_left_out(self) -> None:
        self.mod_file("a", 'name="A"\npath="mod/a"')
        self.set_enabled("mod/a.mod")
        self.assertEqual([s.kind for s in S.playset_sources(self.cfg, include_vanilla=False)], [S.LOCAL])

    def test_the_mods_keep_the_order_of_the_enabled_list(self) -> None:
        self.mod_file("a", 'name="A"\npath="mod/a"')
        self.mod_file("b", 'name="B"\npath="mod/b"')
        self.set_enabled("mod/b.mod", "mod/a.mod")
        self.assertEqual([s.name for s in S.playset_sources(self.cfg, False)], ["B", "A"])
        self.assertEqual([s.order for s in S.playset_sources(self.cfg, False)], [1, 2])

    def test_an_unreadable_entry_is_dropped_without_renumbering_the_rest(self) -> None:
        # THE GAP IN THE ORDERS IS DELIBERATE AND HARMLESS. Only the relative
        # order matters, and keeping the index from the enabled list means a
        # stale entry cannot silently promote everything behind it.
        self.mod_file("b", 'name="B"\npath="mod/b"')
        self.set_enabled("mod/gone.mod", "mod/b.mod")
        sources = S.playset_sources(self.cfg, include_vanilla=False)
        self.assertEqual([(s.name, s.order) for s in sources], [("B", 2)])


class TestWorkspaceMods(SourcesTestCase):
    def test_a_workspace_without_a_mods_directory_is_empty(self) -> None:
        self.assertEqual(S.workspace_mods(self.cfg), [])

    def test_a_directory_without_a_descriptor_is_not_a_mod(self) -> None:
        # `mods/` collects work in progress and scratch directories, and a
        # descriptor is what distinguishes a mod from a folder.
        (self.workspace / "mods" / "scratch").mkdir(parents=True)
        self.assertEqual(S.workspace_mods(self.cfg), [])

    def test_every_descriptor_bearing_directory_is_a_local_source(self) -> None:
        self.write(self.workspace / "mods" / "bc" / "descriptor.mod", 'name="Battle Chronicles"')
        sources = S.workspace_mods(self.cfg)
        self.assertEqual([(s.kind, s.name) for s in sources], [(S.LOCAL, "Battle Chronicles")])
        self.assertEqual(sources[0].root, self.workspace / "mods" / "bc")

    def test_a_nameless_descriptor_falls_back_to_the_directory_name(self) -> None:
        self.write(self.workspace / "mods" / "bc" / "descriptor.mod", 'version="1.0"')
        self.assertEqual([s.name for s in S.workspace_mods(self.cfg)], ["bc"])

    def test_the_directories_are_read_in_sorted_order(self) -> None:
        # Not load order - these are authored, not enabled - but a stable list
        # is what makes a report diffable between runs.
        for name in ("z", "a"):
            self.write(self.workspace / "mods" / name / "descriptor.mod", f'name="{name}"')
        self.assertEqual([s.name for s in S.workspace_mods(self.cfg)], ["a", "z"])

    def test_a_workspace_mod_sorts_after_every_enabled_one(self) -> None:
        # THE ORDER IS 10000 SO IT WINS. What is being authored here has to
        # override what is installed, or an override check run against our own
        # mod reports the mod it is overriding as the winner.
        self.write(self.workspace / "mods" / "bc" / "descriptor.mod", 'name="BC"')
        self.assertEqual([s.order for s in S.workspace_mods(self.cfg)], [10_000])


class TestSourceLabel(SourcesTestCase):
    def test_a_workshop_source_is_labelled_with_its_id(self) -> None:
        # THE ID IS WHAT MAKES THE LABEL UNIQUE. Two subscriptions can share a
        # name, and a collision report that names both of them the same thing
        # cannot be acted on.
        source = S.Source(kind=S.WORKSHOP, name="AGOT", root=Path("."), order=1, mod_id="123")
        self.assertEqual(source.label, "AGOT [123]")

    def test_a_local_source_is_labelled_with_its_name_alone(self) -> None:
        source = S.Source(kind=S.LOCAL, name="Battle Chronicles", root=Path("."), order=1)
        self.assertEqual(source.label, "Battle Chronicles")


if __name__ == "__main__":
    unittest.main(verbosity=2)
