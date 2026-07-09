"""PowerShell write-target extraction + PowerShell-tool guard coverage.

Ported from the tested secpho reference (drydock_deny_guards). The false-block
traps are load-bearing for a security tool: file CONTENT is never a write
target, and for copy/move/rename the destination is the 2nd positional.
"""
import _drydock_common as common
import packet_guard as pg
import protect_secrets as ps

SID = "session-abcdef123456"


def T(command):
    return common.powershell_write_targets(command)


# --- extractor units (ported from the reference ExtractorUnit) --------------
def test_param_and_positional_forms():
    assert T("Set-Content -Path .env -Value x") == [".env"]
    assert T("Set-Content .env x") == [".env"]
    assert T("Set-Content -Path:.env x") == [".env"]


def test_value_param_is_content_not_a_path():
    assert T("Set-Content -Path a.txt -Value b.env") == ["a.txt"]


def test_positional_after_explicit_path_is_not_a_target():
    # 'credentials.json' binds to -Value in real PowerShell; blocking it is wrongful.
    assert T("Set-Content -Path:notes.txt credentials.json") == ["notes.txt"]


def test_copy_move_rename_take_destination():
    assert T("Copy-Item src.txt dst.txt") == ["dst.txt"]
    assert T("Move-Item a b -Force") == ["b"]
    assert T("Rename-Item old.txt new.env") == ["new.env"]


def test_separators_reset_parsing():
    assert T("git status ; Set-Content .env x") == [".env"]


def test_unparseable_yields_nothing():
    assert T("Set-Content 'unbalanced") == []


def test_no_cmdlet_yields_nothing():
    assert T("git commit -m 'Set-Content .env'") == []


def test_valueless_switch_before_path_does_not_hide_it():
    """Regression (verifier fail-open): a common-parameter switch (-Verbose/
    -Debug) before the positional path must NOT consume the path token. The
    earlier 'unknown -Param eats the next token' heuristic let this slip."""
    assert T("Set-Content -Verbose .env x") == [".env"]
    assert T("Set-Content -Debug .env -Value x") == [".env"]
    assert T("Copy-Item -Verbose config.json .env") == [".env"]
    assert T("Add-Content -Verbose .env x") == [".env"]
    assert T("Out-File -Verbose .env.local") == [".env.local"]
    # and end-to-end through the secrets guard
    assert ps.check("PowerShell", {"command": "Set-Content -Verbose .env 'K=V'"}) is not None
    assert ps.check("PowerShell", {"command": "Copy-Item -Debug cfg.json .env"}) is not None


def test_known_value_param_still_skips_its_value():
    # -Encoding/-ItemType take a value that must not be read as a path
    assert T("Set-Content -Encoding utf8 -Path notes.txt x") == ["notes.txt"]
    assert T("New-Item -ItemType File -Path .env.production") == [".env.production"]


def test_out_file_and_new_item():
    assert T('"K=V" | Out-File .env.local') == [".env.local"]
    assert T("New-Item -ItemType File -Path .env.production") == [".env.production"]


# --- command_write_targets dispatch -----------------------------------------
def test_dispatch_bash_ignores_ps_cmdlets():
    # Set-Content via the Bash tool is nonsense and must not be extracted
    assert common.command_write_targets("Set-Content -Path .env -Value x", "Bash") == []


def test_dispatch_powershell_unions_posix_and_native():
    assert ".env" in common.command_write_targets("echo x > .env", "PowerShell")
    assert ".env" in common.command_write_targets("Set-Content -Path .env -Value x", "PowerShell")


# --- protect_secrets over the PowerShell tool -------------------------------
def test_ps_native_secret_writes_denied():
    for cmd in ('Set-Content -Path .env -Value "K=V"',
                "Set-Content .env 'K=V'",
                "Set-Content -Path:.env 'K=V'",
                '"K=V" | Out-File .env.local',
                "New-Item -ItemType File -Path .env.production",
                "Copy-Item config.json .env",
                "Move-Item temp.txt -Destination secrets.yaml"):
        assert ps.check("PowerShell", {"command": cmd}) is not None, cmd


def test_ps_benign_and_content_allowed():
    for cmd in ("Set-Content notes.txt 'hello'",
                "Set-Content -Path notes.txt -Value credentials.json",  # content, not path
                "Set-Content -Path .env.example -Value 'K='",           # allow-listed template
                "New-Item -ItemType Directory build",
                "echo hello"):
        assert ps.check("PowerShell", {"command": cmd}) is None, cmd


# --- packet_guard over the PowerShell tool ----------------------------------
def _make_project(root):
    (root / "sdd-plus" / "protocols").mkdir(parents=True)
    (root / "sdd-plus" / "changes").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# a\n", encoding="utf-8")
    return root


def _pg(root, cmd):
    return pg.classify({"tool_name": "PowerShell", "session_id": SID, "cwd": str(root),
                        "tool_input": {"command": cmd}})


def test_ps_high_risk_write_denied(tmp_path):
    root = _make_project(tmp_path)
    out = _pg(root, f'Set-Content -Path "{root / "migrations" / "0003.sql"}" -Value "x"')
    assert out[0] == "deny"


def test_ps_fixture_write_suppressed(tmp_path):
    root = _make_project(tmp_path)
    out = _pg(root, f'Set-Content -Path "{root / "tests" / "fixtures" / "seed.sql"}" -Value "y"')
    assert out[0] == "silent"
