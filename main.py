"""B5-2 Mini Git: commit metadata and graph algorithms in a simple REPL."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import shlex


@dataclass(frozen=True)
class Commit:
    """One immutable node in the commit directed acyclic graph (DAG)."""

    hash: str
    message: str
    author: str
    timestamp: str
    parents: tuple[str, ...]


def merge_sort(items, key):
    """Return a stable sorted copy without Python's built-in sorting APIs."""
    if len(items) < 2:
        return items[:]

    middle = len(items) // 2
    left = merge_sort(items[:middle], key)
    right = merge_sort(items[middle:], key)
    merged = []
    i = j = 0

    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    return merged + left[i:] + right[j:]


def topological_log(commits):
    """Use Kahn's algorithm so every parent precedes its children."""
    remaining_parents = {hash_: len(commit.parents) for hash_, commit in commits.items()}
    children = {hash_: [] for hash_ in commits}

    for hash_, commit in commits.items():
        for parent in commit.parents:
            children[parent].append(hash_)

    ready = deque(hash_ for hash_ in commits if remaining_parents[hash_] == 0)
    result = []

    while ready:
        hash_ = ready.popleft()
        result.append(commits[hash_])
        for child in children[hash_]:
            remaining_parents[child] -= 1
            if remaining_parents[child] == 0:
                ready.append(child)

    return result


def shortest_path(commits, start, end):
    """BFS on undirected parent edges; smallest lexical shortest path wins."""
    neighbors = {hash_: set() for hash_ in commits}
    for hash_, commit in commits.items():
        for parent in commit.parents:
            neighbors[hash_].add(parent)
            neighbors[parent].add(hash_)

    queue = deque([start])
    previous = {start: None}
    while queue:
        current = queue.popleft()
        if current == end:
            break
        for neighbor in merge_sort(list(neighbors[current]), key=lambda value: value):
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)

    if end not in previous:
        return None

    path = []
    current = end
    while current is not None:
        path.append(current)
        current = previous[current]
    return path[::-1]


def find_ancestors(commits, hash_):
    """Iterative DFS following parents, excluding the target commit itself."""
    found = set()
    stack = list(commits[hash_].parents)
    while stack:
        parent = stack.pop()
        if parent not in found:
            found.add(parent)
            stack.extend(commits[parent].parents)
    return found


class MiniGit:
    """In-memory repository state plus a single-command CLI dispatcher."""

    def __init__(self):
        self.next_number = 0
        self.user = None
        self.current_branch = None
        self.branches = {}
        self.commits = {}
        self.keyword_index = {}
        self.author_index = {}

    def initialize(self, user):
        """Reset the repository without reusing hashes from this REPL session."""
        self.user = user
        self.current_branch = "main"
        self.branches = {"main": None}
        self.commits = {}
        self.keyword_index = {}
        self.author_index = {}
        return f"Initialized repository.\nCurrent branch: main\nCurrent user: {user}"

    def create_commit(self, message):
        """Add a child of the current branch tip and update both inverted indexes."""
        self.next_number += 1
        hash_ = f"{self.next_number:08x}"
        parent = self.branches[self.current_branch]
        parents = (parent,) if parent is not None else ()
        commit = Commit(
            hash_, message, self.user,
            datetime.now(timezone.utc).isoformat(timespec="microseconds"), parents,
        )
        self.commits[hash_] = commit
        self.branches[self.current_branch] = hash_

        for word in set(message.lower().split()):
            self.keyword_index.setdefault(word, set()).add(hash_)
        self.author_index.setdefault(self.user, set()).add(hash_)
        return f"[{self.current_branch} {hash_}] {message}"

    def search_keyword(self, query):
        """Intersect posting lists first; check phrase order only in candidates."""
        words = query.lower().split()
        matching = self.keyword_index.get(words[0], set()).copy()
        for word in words[1:]:
            matching.intersection_update(self.keyword_index.get(word, set()))

        phrase = " ".join(words)
        selected = [
            self.commits[hash_] for hash_ in matching
            if phrase in " ".join(self.commits[hash_].message.lower().split())
        ]
        return merge_sort(selected, key=lambda commit: commit.hash)

    @staticmethod
    def format_commits(commits):
        """Show the required identifying fields for every commit."""
        if not commits:
            return "No commits found."
        return "\n".join(
            f"commit {commit.hash} ({commit.author}, {commit.timestamp})\n"
            f"  {commit.message}"
            for commit in commits
        )

    def execute(self, line):
        """Parse and execute one line; return text or None to exit the REPL."""
        try:
            parts = shlex.split(line)
        except ValueError:
            return "Invalid args"
        if not parts:
            return ""

        command, *args = parts
        command = command.upper()
        if command in ("EXIT", "QUIT"):
            return None if not args else "Invalid args"
        if command == "INIT":
            return self.initialize(args[0]) if len(args) == 1 and args[0].strip() else "Invalid args"
        if command not in ("BRANCH", "SWITCH", "COMMIT", "LOG", "PATH", "ANCESTORS", "SEARCH"):
            return f"Unknown command: {command}"
        if self.current_branch is None:
            return "Repository not initialized."

        if command == "BRANCH":
            if len(args) != 1 or not args[0].strip():
                return "Invalid args"
            if args[0] in self.branches:
                return f"Branch already exists: {args[0]}"
            self.branches[args[0]] = self.branches[self.current_branch]
            return f"Created branch: {args[0]}"

        if command == "SWITCH":
            if len(args) != 1:
                return "Invalid args"
            if args[0] not in self.branches:
                return f"Unknown branch: {args[0]}"
            self.current_branch = args[0]
            return f"Switched to branch: {args[0]}"

        if command == "COMMIT":
            return self.create_commit(args[0]) if len(args) == 1 and args[0].strip() else "Invalid args"

        if command == "LOG":
            if not args:
                selected = topological_log(self.commits)
            elif len(args) == 1 and args[0].lower() in ("--sort-by=date", "--sort-by=author"):
                field = args[0].split("=", 1)[1].lower()
                key = (lambda commit: commit.timestamp) if field == "date" else (lambda commit: commit.author.lower())
                selected = merge_sort(list(self.commits.values()), key)
            else:
                return "Invalid args"
            return self.format_commits(selected) if selected else "No commits yet."

        if command == "PATH":
            if len(args) != 2:
                return "Invalid args"
            for hash_ in args:
                if hash_ not in self.commits:
                    return f"Unknown commit: {hash_}"
            path = shortest_path(self.commits, args[0], args[1])
            return "Path: " + " -> ".join(path) if path else "No path"

        if command == "ANCESTORS":
            if len(args) != 1:
                return "Invalid args"
            if args[0] not in self.commits:
                return f"Unknown commit: {args[0]}"
            hashes = merge_sort(list(find_ancestors(self.commits, args[0])), key=lambda hash_: hash_)
            return "\n".join(f"- {hash_}: {self.commits[hash_].message}" for hash_ in hashes) if hashes else "No ancestors."

        if len(args) != 1 or not args[0].strip():  # SEARCH
            return "Invalid args"
        if args[0].lower().startswith("--author="):
            author = args[0].split("=", 1)[1]
            if not author:
                return "Invalid args"
            matching = self.author_index.get(author, set())
            selected = merge_sort(
                [self.commits[hash_] for hash_ in matching], key=lambda commit: commit.hash
            )
        elif args[0].startswith("--"):
            return "Invalid args"
        else:
            selected = self.search_keyword(args[0])
        if not selected:
            return "No commits found."
        return f"Found {len(selected)} commit(s):\n" + self.format_commits(selected)


def main():
    """Repeat input → execute → output until EXIT, QUIT, or end of input."""
    git = MiniGit()
    while True:
        try:
            line = input("mini-git> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        result = git.execute(line)
        if result is None:
            break
        if result:
            print(result)


if __name__ == "__main__":
    main()
