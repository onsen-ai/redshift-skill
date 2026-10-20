"""Config and connection selection: named connections, and configs from before them.

    python3 -m unittest discover -s tests

No AWS calls: only how the config file is read, chosen from and written.
"""

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import client  # noqa: E402
import setup  # noqa: E402

LEGACY = {"profile": "p1", "region": "eu-west-1", "workgroup": "wg1", "database": "dev", "python": "/usr/bin/python3"}
NAMED = {
    "default": "a",
    "connections": {
        "a": {"profile": "pa", "region": "eu-west-1", "workgroup": "wga", "database": "dba"},
        "b": {"profile": "pb", "region": "us-east-1", "cluster": "cb", "db_user": "ub", "database": "dbb"},
    },
    "python": "/usr/bin/python3",
}


def parse(*argv):
    parser = argparse.ArgumentParser()
    client.add_connection_args(parser)
    return parser.parse_args(list(argv))


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.orig = (client.CONFIG_DIR, client.CONFIG_FILE)
        client.CONFIG_DIR = Path(self.dir.name)
        client.CONFIG_FILE = client.CONFIG_DIR / "config.json"
        setup.CONFIG_FILE = client.CONFIG_FILE

    def tearDown(self):
        client.CONFIG_DIR, client.CONFIG_FILE = self.orig
        setup.CONFIG_FILE = client.CONFIG_FILE

    def write(self, config):
        client.CONFIG_FILE.write_text(json.dumps(config))

    def saved(self):
        return json.loads(client.CONFIG_FILE.read_text())

    # --- reading ---

    def test_legacy_config_reads_as_one_connection_named_main(self):
        self.write(LEGACY)
        config = client.load_config()
        self.assertEqual(config["default"], "main")
        self.assertEqual(config["connections"]["main"], {k: v for k, v in LEGACY.items() if k != "python"})
        self.assertEqual(config["python"], "/usr/bin/python3")

    def test_legacy_config_resolves_as_before(self):
        self.write(LEGACY)
        config = client.resolve_config(parse())
        self.assertEqual((config["profile"], config["workgroup"], config["database"]), ("p1", "wg1", "dev"))

    def test_legacy_file_is_not_rewritten_by_reading(self):
        self.write(LEGACY)
        client.resolve_config(parse())
        self.assertEqual(self.saved(), LEGACY)

    def test_no_config_still_works_ad_hoc(self):
        config = client.resolve_config(parse("--workgroup", "wg", "--database", "db", "--profile", "p"))
        self.assertEqual((config["workgroup"], config["database"], config["profile"]), ("wg", "db", "p"))

    def test_default_connection(self):
        self.write(NAMED)
        self.assertEqual(client.resolve_config(parse())["workgroup"], "wga")

    def test_named_connection(self):
        self.write(NAMED)
        config = client.resolve_config(parse("--connection", "b"))
        self.assertEqual((config["cluster"], config["db_user"], config["region"]), ("cb", "ub", "us-east-1"))

    def test_unknown_connection_exits(self):
        self.write(NAMED)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            client.resolve_config(parse("--connection", "nope"))

    def test_cli_overrides_the_connection(self):
        self.write(NAMED)
        config = client.resolve_config(parse("--connection", "a", "--database", "other", "--profile", "px"))
        self.assertEqual((config["database"], config["profile"], config["workgroup"]), ("other", "px", "wga"))

    def test_workgroup_on_the_command_line_replaces_a_provisioned_connection(self):
        self.write(NAMED)
        config = client.resolve_config(parse("--connection", "b", "--workgroup", "wgx"))
        self.assertEqual(config["workgroup"], "wgx")
        self.assertNotIn("cluster", config)
        self.assertNotIn("db_user", config)

    def test_cluster_on_the_command_line_replaces_a_serverless_connection(self):
        self.write(NAMED)
        config = client.resolve_config(parse("--connection", "a", "--cluster", "cx", "--db-user", "ux"))
        self.assertEqual((config["cluster"], config["db_user"]), ("cx", "ux"))
        self.assertNotIn("workgroup", config)

    # --- writing ---

    def test_save_connection_migrates_a_legacy_file_and_keeps_python(self):
        self.write(LEGACY)
        client.save_connection("new", {"profile": "pn", "workgroup": "wgn", "database": "dbn"})
        saved = self.saved()
        self.assertEqual(sorted(saved["connections"]), ["main", "new"])
        self.assertEqual(saved["default"], "main")
        self.assertEqual(saved["python"], "/usr/bin/python3")
        self.assertNotIn("workgroup", saved)

    def test_first_connection_becomes_the_default(self):
        client.save_connection("only", {"workgroup": "wg", "database": "db"})
        self.assertEqual(self.saved()["default"], "only")

    def test_set_default_when_asked(self):
        self.write(NAMED)
        client.save_connection("c", {"workgroup": "wgc", "database": "dbc"}, set_default=True)
        self.assertEqual(self.saved()["default"], "c")

    # --- setup.py --list / --set-default / --remove ---

    def manage(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            handled = setup.manage(list(argv))
        return handled, out.getvalue()

    def test_list(self):
        self.write(NAMED)
        handled, out = self.manage("--list")
        self.assertTrue(handled)
        self.assertIn("workgroup wga", out)
        self.assertIn("cluster cb as ub", out)
        self.assertIn("[default]", out.splitlines()[0])

    def test_list_legacy(self):
        self.write(LEGACY)
        _, out = self.manage("--list")
        self.assertIn("main", out)
        self.assertIn("workgroup wg1", out)

    def test_set_default(self):
        self.write(NAMED)
        self.manage("--set-default", "b")
        self.assertEqual(self.saved()["default"], "b")

    def test_remove_the_default_picks_another(self):
        self.write(NAMED)
        self.manage("--remove", "a")
        saved = self.saved()
        self.assertEqual(list(saved["connections"]), ["b"])
        self.assertEqual(saved["default"], "b")

    def test_remove_unknown_exits(self):
        self.write(NAMED)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.manage("--remove", "nope")

    def test_no_flags_runs_the_wizard(self):
        self.assertFalse(self.manage()[0])


if __name__ == "__main__":
    unittest.main()
