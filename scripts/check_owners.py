import fnmatch
import subprocess
import sys
from pathlib import Path


def parse(text: str) -> list[tuple[str, set[str]]]:
    rules = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pattern, *owners = line.split()
            rules.append((pattern, {o.lstrip("@").lower() for o in owners}))
    return rules


def matches(pattern: str, path: str) -> bool:
    if pattern == "*":
        return True
    pattern = pattern.lstrip("/")
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return fnmatch.fnmatchcase(path, pattern)


def owners(rules: list[tuple[str, set[str]]], path: str) -> set[str]:
    for pattern, who in reversed(rules):
        if matches(pattern, path):
            return who
    return set()


def violations(rules: list[tuple[str, set[str]]], author: str, paths: list[str]) -> list[str]:
    return [p for p in paths if author.lower() not in owners(rules, p)]


if __name__ == "__main__":
    author, base = sys.argv[1], sys.argv[2]
    rules = parse(Path(".github/CODEOWNERS").read_text(encoding="utf-8"))
    diff = ["git", "diff", "--name-only", "--no-renames", f"{base}...HEAD"]
    changed = subprocess.run(diff, capture_output=True, text=True, check=True).stdout.splitlines()
    bad = violations(rules, author, changed)
    for path in bad:
        print(f"{path}: owned by {', '.join(sorted(owners(rules, path)))}, not {author}. Ask the owner to make this change.")
    sys.exit(1 if bad else 0)
