"""Behavioral tests for the secrets-path guardrail (secrets-protection-hook spec)."""
import pytest

import protect_secrets as ps

SECRET_PATHS = [
    ".env",
    ".env.local",
    ".env.production",
    "config/prod.env",
    ".envrc",
    "key.pem",
    "server.key",
    "id_rsa",
    "/home/u/.ssh/id_ed25519",
    "keys/id_ecdsa",
    "deploy.ppk",
    "certs/app.p12",
    "certs/app.pfx",
    "store.jks",
    "a/b/credentials.json",
    "secrets.yaml",
    "secret.toml",
    "service-account.json",
    "gcp\\service_account_prod.json",
]

OK_PATHS = [
    ".env.example",
    ".env.template",
    "dir/.env.sample",
    "notes.txt",
    "src/app.py",
    "README.md",
    "envrc.md",
    "my.envelope",
    "keystore.md",
]

BASH_BLOCK = [
    "echo KEY=x > .env",
    "echo x >> .env",
    "echo x >.env",
    "cat tmp | tee server.key",
    "cp template .env",
    "mv a.txt .env",
    "printf '%s' secret > config/prod.env",
]

BASH_OK = [
    "cat .env",
    "grep KEY .env",
    "echo hi > notes.txt",
    "ls -la",
    "cp .env backup-notes.txt",
]


@pytest.mark.parametrize("path", SECRET_PATHS)
def test_secret_path_blocked(path):
    assert ps.check("Write", {"file_path": path}) is not None, path


@pytest.mark.parametrize("path", OK_PATHS)
def test_non_secret_path_allowed(path):
    assert ps.check("Write", {"file_path": path}) is None, path


@pytest.mark.parametrize("cmd", BASH_BLOCK)
def test_bash_write_to_secret_blocked(cmd):
    assert ps.check("Bash", {"command": cmd}) is not None, cmd


@pytest.mark.parametrize("cmd", BASH_OK)
def test_bash_non_secret_allowed(cmd):
    assert ps.check("Bash", {"command": cmd}) is None, cmd
