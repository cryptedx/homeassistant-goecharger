import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "custom_components" / "goecharger" / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
INTEGRATION_PREFIX = "custom_components/goecharger/"
RELEASE_RE = re.compile(r"^chore\(release\): v\d+\.\d+\.\d+")
HEADER_RE = re.compile(r"^([a-z]+)(?:\(([^)]+)\))?(!)?: .+")


@dataclass(frozen=True)
class ReleasePlan:
    version: str
    should_release: bool
    changed_files: bool
    bump: str | None = None


def parse_version(version):
    return tuple(int(part) for part in version.split("."))


def bump_version(version, bump):
    major, minor, patch = parse_version(version)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def is_release_commit(message):
    lines = message.splitlines()
    return bool(lines and RELEASE_RE.match(lines[0]))


def commit_bump(message, current_version):
    if is_release_commit(message):
        return None

    first_line = message.splitlines()[0]
    header = HEADER_RE.match(first_line)
    breaking = "BREAKING CHANGE:" in message or "BREAKING-CHANGE:" in message
    if header:
        breaking = breaking or bool(header.group(3))

    major, _, _ = parse_version(current_version)
    if breaking:
        return "major" if major else "minor"

    if not header:
        return None

    commit_type = header.group(1)
    scope = header.group(2)

    if commit_type == "feat":
        return "minor"
    if commit_type in {"fix", "perf"}:
        return "patch"
    if commit_type == "deps" or scope == "deps":
        return "patch"
    return None


def strongest_bump(bumps):
    order = {"patch": 1, "minor": 2, "major": 3}
    bumps = [bump for bump in bumps if bump]
    if not bumps:
        return None
    return max(bumps, key=order.get)


def integration_files_changed(paths):
    return any(path.startswith(INTEGRATION_PREFIX) for path in paths)


def plan_release(current_version, latest_tag, commit_messages, changed_paths):
    if latest_tag is None:
        return ReleasePlan(current_version, True, False)

    messages = [message for message in commit_messages if message.strip()]
    bump = strongest_bump(commit_bump(message, current_version) for message in messages)
    if bump is None and integration_files_changed(changed_paths):
        bump = "patch"

    if bump is None:
        return ReleasePlan(current_version, False, False)

    return ReleasePlan(bump_version(current_version, bump), True, True, bump)


def release_lines(messages):
    lines = []
    seen = set()
    for message in messages:
        lines = message.splitlines()
        if not lines:
            continue
        first_line = lines[0].strip()
        if not first_line or is_release_commit(first_line) or first_line in seen:
            continue
        seen.add(first_line)
        lines.append(f"- {first_line}")
    return "\n".join(lines) if lines else "- Automated release."


def update_changelog(changelog, version, release_date, messages):
    match = re.search(r"(?ms)^## Unreleased\n(?P<body>.*?)(?=^## |\Z)", changelog)
    if not match:
        raise ValueError("CHANGELOG.md must contain '## Unreleased'")

    body = match.group("body").strip()
    entry = body or release_lines(messages)
    replacement = f"## Unreleased\n\n## {version} - {release_date}\n\n{entry}\n\n"

    return changelog[: match.start()] + replacement + changelog[match.end() :].lstrip("\n")


def run_git(*args):
    return subprocess.run(
        ["git", *args],
        check=False,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def latest_tag():
    result = run_git("describe", "--tags", "--match", "v[0-9]*.[0-9]*.[0-9]*", "--abbrev=0")
    return result.stdout.strip() if result.returncode == 0 else None


def commit_messages_since(tag):
    if tag is None:
        return []
    result = run_git("log", "--format=%B%x1e", f"{tag}..HEAD")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return [message.strip() for message in result.stdout.split("\x1e") if message.strip()]


def changed_paths_since(tag):
    if tag is None:
        return []
    result = run_git("diff", "--name-only", f"{tag}..HEAD")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return [path.strip() for path in result.stdout.splitlines() if path.strip()]


def manifest_version():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]


def write_manifest_version(version):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["version"] = version
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def set_output(name, value):
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={str(value).lower() if isinstance(value, bool) else value}\n")


def main():
    current_version = manifest_version()
    tag = latest_tag()
    messages = commit_messages_since(tag)
    paths = changed_paths_since(tag)
    plan = plan_release(current_version, tag, messages, paths)

    if plan.changed_files:
        write_manifest_version(plan.version)
        changelog = CHANGELOG.read_text(encoding="utf-8")
        CHANGELOG.write_text(
            update_changelog(changelog, plan.version, date.today().isoformat(), messages),
            encoding="utf-8",
        )

    set_output("should_release", plan.should_release)
    set_output("changed", plan.changed_files)
    set_output("version", plan.version)
    set_output("tag", f"v{plan.version}")

    if plan.should_release:
        print(f"Release planned: v{plan.version}")
    else:
        print("No release-worthy changes.")


if __name__ == "__main__":
    main()
