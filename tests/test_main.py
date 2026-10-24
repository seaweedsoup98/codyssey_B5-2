"""Required Mini Git behavior, edge cases, and a real REPL smoke test."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from main import Commit, MiniGit, find_ancestors, merge_sort, shortest_path, topological_log


ROOT = Path(__file__).resolve().parents[1]


class MiniGitTests(unittest.TestCase):
    def setUp(self):
        self.git = MiniGit()
        self.git.execute('INIT "Alice Smith"')

    def commit(self, message):
        result = self.git.execute(f'COMMIT "{message}"')
        self.assertTrue(result.startswith("["), result)
        return result.split(" ", 2)[1].rstrip("]")

    def test_init_sets_main_and_resets_repository(self):
        self.assertEqual(self.git.user, "Alice Smith")
        self.assertEqual(self.git.branches, {"main": None})
        self.commit("first")
        self.git.execute("BRANCH feature")
        response = self.git.execute("init Bob")
        self.assertIn("Current user: Bob", response)
        self.assertEqual(self.git.branches, {"main": None})
        self.assertEqual(self.git.commits, {})
        self.assertEqual(self.git.keyword_index, {})
        self.assertEqual(self.git.author_index, {})

    def test_new_hash_is_unique_even_after_reinitialization(self):
        first = self.commit("first")
        self.git.execute("INIT Bob")
        second = self.commit("second")
        self.assertNotEqual(first, second)

    def test_initialization_required(self):
        git = MiniGit()
        for command in ("COMMIT first", "BRANCH x", "LOG", "PATH a b", "SEARCH x"):
            with self.subTest(command=command):
                self.assertEqual(git.execute(command), "Repository not initialized.")

    def test_case_insensitive_commands_and_quoted_values(self):
        message = "Add Login Feature"
        hash_ = self.commit(message)
        self.assertIn(message, self.git.execute("lOg"))
        self.assertIn(hash_, self.git.execute('sEaRcH "LOGIN"'))
        self.assertIn(hash_, self.git.execute('SEARCH "login feature"'))
        self.assertIn(hash_, self.git.execute('SEARCH --author="Alice Smith"'))

    def test_branch_switch_and_parent_graph(self):
        root = self.commit("root")
        self.assertEqual(self.git.execute("BRANCH feature"), "Created branch: feature")
        self.git.execute("SWITCH feature")
        feature = self.commit("feature")
        self.git.execute("SWITCH main")
        main = self.commit("main")
        self.assertEqual(self.git.commits[feature].parents, (root,))
        self.assertEqual(self.git.commits[main].parents, (root,))
        self.assertEqual(self.git.branches["main"], main)
        self.assertEqual(self.git.branches["feature"], feature)
        self.assertEqual([c.hash for c in topological_log(self.git.commits)], [root, feature, main])

    def test_branch_errors(self):
        self.assertEqual(self.git.execute("BRANCH main"), "Branch already exists: main")
        self.assertEqual(self.git.execute("SWITCH missing"), "Unknown branch: missing")
        self.assertEqual(self.git.current_branch, "main")

    def test_log_parent_before_child_even_with_divergent_creation(self):
        root = self.commit("root")
        self.git.execute("BRANCH side")
        self.git.execute("SWITCH side")
        side = self.commit("side")
        self.git.execute("SWITCH main")
        latest = self.commit("main")
        log = self.git.execute("LOG")
        self.assertLess(log.index(root), log.index(side))
        self.assertLess(log.index(root), log.index(latest))
        for commit in self.git.commits.values():
            self.assertIn(commit.message, log)
            self.assertIn(commit.author, log)
            self.assertIn(commit.timestamp, log)

    def test_two_roots_yield_no_path(self):
        self.git.execute("BRANCH orphan")
        root1 = self.commit("root1")
        self.git.execute("SWITCH orphan")
        root2 = self.commit("root2")
        self.assertEqual(self.git.commits[root2].parents, ())
        self.assertEqual(self.git.execute(f"PATH {root1} {root2}"), "No path")

    def test_path_is_undirected_and_shortest(self):
        root = self.commit("root")
        self.git.execute("BRANCH side")
        current = self.commit("main")
        self.git.execute("SWITCH side")
        side = self.commit("side")
        self.assertEqual(self.git.execute(f"PATH {side} {current}"), f"Path: {side} -> {root} -> {current}")
        self.assertEqual(self.git.execute(f"PATH {root} {root}"), f"Path: {root}")

    def test_path_lexicographic_tie_break_with_multiple_parents(self):
        nodes = {
            "00000001": Commit("00000001", "a", "A", "t", ()),
            "00000002": Commit("00000002", "b", "A", "t", ()),
            "00000003": Commit("00000003", "c", "A", "t", ("00000001", "00000002")),
            "00000004": Commit("00000004", "d", "A", "t", ("00000001", "00000002")),
        }
        self.assertEqual(shortest_path(nodes, "00000003", "00000004"),
                         ["00000003", "00000001", "00000004"])
        self.assertEqual([c.hash for c in topological_log(nodes)],
                         ["00000001", "00000002", "00000003", "00000004"])

    def test_all_ancestors_without_duplicates(self):
        root = self.commit("root")
        middle = self.commit("middle")
        leaf = self.commit("leaf")
        self.assertEqual(find_ancestors(self.git.commits, leaf), {root, middle})
        self.assertIn(root, self.git.execute(f"ANCESTORS {leaf}"))
        self.assertEqual(self.git.execute(f"ANCESTORS {root}"), "No ancestors.")

    def test_ancestors_of_multi_parent_commit(self):
        commits = {
            "a": Commit("a", "a", "X", "t", ()),
            "b": Commit("b", "b", "X", "t", ("a",)),
            "c": Commit("c", "c", "X", "t", ("a",)),
            "d": Commit("d", "d", "X", "t", ("b", "c")),
        }
        self.assertEqual(find_ancestors(commits, "d"), {"a", "b", "c"})

    def test_long_ancestry_iterative(self):
        for i in range(1100):
            self.git.create_commit(f"commit{i}")
        target = self.git.branches["main"]
        self.assertEqual(len(find_ancestors(self.git.commits, target)), 1099)

    def test_index_token_normalization_and_deduplication(self):
        one = self.commit("Login login FEATURE")
        self.commit("feature only")
        self.assertEqual(self.git.keyword_index["login"], {one})
        self.assertEqual(len(self.git.keyword_index["feature"]), 2)
        self.assertIn(one, self.git.execute("SEARCH LOGIN"))
        self.assertEqual(self.git.execute('SEARCH "missing word"'), "No commits found.")
        self.assertEqual(self.git.execute('SEARCH "feature login"'), "No commits found.")

    def test_index_search_does_not_scan_entire_log(self):
        hash_ = self.commit("needle haystack")
        with patch("main.topological_log", side_effect=AssertionError("full scan")):
            self.assertIn(hash_, self.git.execute("SEARCH needle"))
            self.assertIn(hash_, self.git.execute('SEARCH --author="Alice Smith"'))

    def test_search_unknown_author(self):
        self.commit("a")
        self.assertEqual(self.git.execute("SEARCH --author=Nobody"), "No commits found.")

    def test_stable_merge_sort(self):
        values = [(2, "first"), (1, "early"), (2, "second"), (2, "third")]
        self.assertEqual(merge_sort(values, lambda pair: pair[0]),
                         [(1, "early"), (2, "first"), (2, "second"), (2, "third")])
        self.assertEqual(merge_sort([], lambda value: value), [])
        self.assertEqual(values[0], (2, "first"))  # no input mutation

    def test_date_and_author_sort_options(self):
        first = self.commit("first")
        self.git.user = "bob"  # Different authors are possible through the repository API.
        second = self.commit("second")
        self.git.commits[first] = replace(self.git.commits[first], timestamp="2026-10-25T00:00:00+00:00")
        self.git.commits[second] = replace(self.git.commits[second], timestamp="2026-10-24T00:00:00+00:00")
        by_date = self.git.execute("LOG --sort-by=DATE")
        by_author = self.git.execute("LOG --sort-by=author")
        self.assertLess(by_date.index(second), by_date.index(first))
        self.assertLess(by_author.index(first), by_author.index(second))

    def test_invalid_inputs_and_missing_hash(self):
        commands = ["INIT", 'INIT ""', "COMMIT", 'COMMIT ""', "COMMIT hello world",
                    "BRANCH", "BRANCH a b", "SWITCH", "LOG xyz", "LOG --sort-by=message",
                    "PATH x", "ANCESTORS", "SEARCH", "SEARCH --author=",
                    "SEARCH --whatever=foo", 'COMMIT "unterminated', "EXIT extra"]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.git.execute(command), "Invalid args")
        self.assertEqual(self.git.execute("PATH abc def"), "Unknown commit: abc")
        self.assertEqual(self.git.execute("ANCESTORS def"), "Unknown commit: def")
        self.assertEqual(self.git.execute("SWITCH unknown"), "Unknown branch: unknown")
        self.assertEqual(self.git.execute("WRONG"), "Unknown command: WRONG")

    def test_empty_log_search_and_exit(self):
        self.assertEqual(self.git.execute("LOG"), "No commits yet.")
        self.assertEqual(self.git.execute("SEARCH something"), "No commits found.")
        self.assertIsNone(self.git.execute("quit"))
        self.assertIsNone(self.git.execute("EXIT"))
        self.assertEqual(self.git.execute("   "), "")

    def test_real_repl(self):
        commands = 'init "Alice Smith"\ncommit "Initial commit"\nlog\nsearch initial\nquit\n'
        process = subprocess.run(
            [sys.executable, str(ROOT / "main.py")], input=commands,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, timeout=10, check=True,
        )
        self.assertEqual(process.stderr, "")
        self.assertIn("mini-git> ", process.stdout)
        self.assertIn("Initialized repository.", process.stdout)
        self.assertIn("Initial commit", process.stdout)
        self.assertIn("Found 1 commit(s):", process.stdout)


if __name__ == "__main__":
    unittest.main()
