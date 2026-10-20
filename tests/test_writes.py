"""Write modes and secret sign-in: what each connection may run, and how it signs in.

    python3 -m unittest discover -s tests

No AWS calls.
"""

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib import client  # noqa: E402

READS = ["SELECT 1", "with x as (select 1) select * from x", "EXPLAIN SELECT 1", "SHOW search_path",
         "-- a comment\nSELECT 1", "/* block */ select 1"]
WRITES = ["INSERT INTO t VALUES (1)", "UPDATE t SET a = 1 WHERE b = 2", "DELETE FROM t WHERE a = 1",
          "CREATE TABLE t (a int)", "DROP TABLE t", "TRUNCATE t", "COPY t FROM 's3://b/k'", "GRANT SELECT ON t TO u",
          "-- looks harmless\nDROP TABLE t"]
ARN = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:dwh-AbCdEf"


class ValidateSqlTest(unittest.TestCase):
    def test_reject_allows_only_reads(self):
        for sql in READS:
            client.validate_sql(sql, "reject")
        for sql in WRITES:
            with self.assertRaises(ValueError, msg=sql):
                client.validate_sql(sql, "reject")

    def test_default_is_reject(self):
        with self.assertRaises(ValueError):
            client.validate_sql("DROP TABLE t")

    def test_writing_modes_allow_single_statements(self):
        for mode in ("accept", "ask", "auto"):
            for sql in READS + WRITES:
                client.validate_sql(sql, mode)

    def test_multi_statement_blocked_in_every_mode(self):
        for mode in client.WRITE_MODES:
            with self.assertRaises(ValueError, msg=mode):
                client.validate_sql("SELECT 1; DROP TABLE t", mode)

    def test_empty(self):
        with self.assertRaises(ValueError):
            client.validate_sql("  -- nothing\n", "accept")


class StatementArgsTest(unittest.TestCase):
    def test_serverless_as_iam_identity(self):
        args = client.statement_args("SELECT 1", {"workgroup": "wg", "database": "db"})
        self.assertEqual(args[-2:], ["--workgroup-name", "wg"])
        self.assertNotIn("--secret-arn", args)
        self.assertNotIn("--db-user", args)

    def test_serverless_as_secret_user(self):
        args = client.statement_args("SELECT 1", {"workgroup": "wg", "database": "db", "secret_arn": ARN})
        self.assertEqual(args[args.index("--secret-arn") + 1], ARN)

    def test_provisioned_as_db_user(self):
        args = client.statement_args("SELECT 1", {"cluster": "c", "db_user": "u", "database": "db"})
        self.assertEqual(args[args.index("--db-user") + 1], "u")
        self.assertNotIn("--secret-arn", args)

    def test_provisioned_secret_replaces_db_user(self):
        args = client.statement_args("SELECT 1", {"cluster": "c", "db_user": "u", "database": "db", "secret_arn": ARN})
        self.assertIn("--secret-arn", args)
        self.assertNotIn("--db-user", args)


class ResolveWriteModeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.orig = (client.CONFIG_DIR, client.CONFIG_FILE)
        client.CONFIG_DIR = Path(self.dir.name)
        client.CONFIG_FILE = client.CONFIG_DIR / "config.json"
        client.CONFIG_FILE.write_text(json.dumps({"default": "ro", "connections": {
            "ro": {"profile": "p", "workgroup": "wg", "database": "db"},
            "rw": {"profile": "p", "workgroup": "wg", "database": "db", "write_mode": "auto", "secret_arn": ARN},
            "bad": {"profile": "p", "workgroup": "wg", "database": "db", "write_mode": "yolo"},
            "prov": {"profile": "p", "cluster": "c", "database": "db", "secret_arn": ARN},
        }}))

    def tearDown(self):
        client.CONFIG_DIR, client.CONFIG_FILE = self.orig

    def resolve(self, *argv):
        parser = argparse.ArgumentParser()
        client.add_connection_args(parser)
        return client.resolve_config(parser.parse_args(list(argv)))

    def test_missing_write_mode_is_reject(self):
        self.assertEqual(self.resolve()["write_mode"], "reject")

    def test_connection_write_mode_and_secret(self):
        config = self.resolve("--connection", "rw")
        self.assertEqual((config["write_mode"], config["secret_arn"]), ("auto", ARN))

    def test_invalid_write_mode_exits(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.resolve("--connection", "bad")

    def test_provisioned_with_a_secret_needs_no_db_user(self):
        self.assertEqual(self.resolve("--connection", "prov")["cluster"], "c")

    def test_db_user_on_the_command_line_replaces_the_secret(self):
        config = self.resolve("--connection", "prov", "--db-user", "someone")
        self.assertEqual(config["db_user"], "someone")
        self.assertNotIn("secret_arn", config)


if __name__ == "__main__":
    unittest.main()
