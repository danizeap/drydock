"""Registry-hygiene tests: skill ids and command ids must not collide.

Regression guard for the v0.2.3 audit finding: a skill named `explore` and a
command file `explore.md` both registered as `drydock:explore`, producing
duplicate, ambiguous entries. The fix renamed the skill to `explore-mode`
(the same way `spec-sync` backs the `/drydock:sync` command). These tests keep
that class of collision from ever recurring, and keep each skill's frontmatter
`name:` honest against its directory.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
COMMANDS_DIR = ROOT / "commands"


def _frontmatter_name(skill_md: pathlib.Path):
    """Return the `name:` value from a SKILL.md YAML frontmatter block, or None."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    # frontmatter is the block between the first two `---` fences
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].splitlines():
        m = re.match(r"\s*name:\s*(\S+)\s*$", line)
        if m:
            return m.group(1)
    return None


def _skill_names():
    return {
        d.name: _frontmatter_name(d / "SKILL.md")
        for d in sorted(SKILLS_DIR.iterdir())
        if (d / "SKILL.md").is_file()
    }


def _command_ids():
    return {p.stem for p in COMMANDS_DIR.glob("*.md")}


def test_skills_and_commands_exist():
    # Guards against the tests silently passing on an empty glob.
    assert _skill_names(), "no skills discovered under skills/"
    assert _command_ids(), "no commands discovered under commands/"


def test_every_skill_has_a_frontmatter_name():
    missing = [d for d, name in _skill_names().items() if not name]
    assert not missing, f"skills missing a frontmatter `name:`: {missing}"


def test_skill_name_matches_its_directory():
    drift = {
        d: name for d, name in _skill_names().items() if name and name != d
    }
    assert not drift, (
        "skill frontmatter `name:` must equal its directory name "
        f"(a rename that touched one but not the other): {drift}"
    )


def test_no_skill_id_collides_with_a_command_id():
    skills = {name for name in _skill_names().values() if name}
    commands = _command_ids()
    collisions = skills & commands
    assert not collisions, (
        "skill id(s) collide with command id(s), producing duplicate "
        f"`drydock:<id>` registrations: {sorted(collisions)}. "
        "Rename the skill (e.g. `explore` -> `explore-mode`, as `spec-sync` "
        "backs `/drydock:sync`)."
    )
