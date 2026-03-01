# `argus-mcp secret`

Manage encrypted secrets used in configuration files. Secrets can be referenced
in config values using the `secret:<name>` syntax and are resolved at startup.

## Usage

```bash
argus-mcp secret [--provider PROVIDER] [--path PATH] {set,get,list,delete} ...
```

## Global Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--provider` | string | `file` | Storage provider: `env`, `file`, `keyring` |
| `--path` | path | `secrets.enc` | Path to encrypted file (file provider only) |

## Actions

### `set` — Store a Secret

```bash
# Interactive (prompts for value securely)
argus-mcp secret set my-api-key

# Inline value
argus-mcp secret set my-api-key sk-abc123
```

When no value is provided, the CLI prompts securely (input is hidden) using
`getpass`.

### `get` — Retrieve a Secret

```bash
argus-mcp secret get my-api-key
```

Prints the decrypted secret value to stdout.

### `list` — List Secret Names

```bash
argus-mcp secret list
```

Lists all stored secret names (values are not shown).

### `delete` — Remove a Secret

```bash
argus-mcp secret delete my-api-key
```

## Providers

### `file` (default)

Stores secrets in a Fernet-encrypted JSON file.

- **File**: `secrets.enc` (or `--path` override)
- **Master key**: `ARGUS_SECRET_KEY` environment variable
- **Encryption**: Fernet (AES-128-CBC + HMAC-SHA256)
- **File permissions**: `0600` (owner read/write only)
- **Writes**: Atomic (temp file + rename)
- **Requires**: `cryptography` package

```bash
# Generate a master key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set the key
export ARGUS_SECRET_KEY="your-generated-key"

# Store a secret
argus-mcp secret set my-api-key
```

### `env`

Maps secrets to environment variables.

- Secret `my-api-key` → env var `SECRET_MY_API_KEY`
- Convention: uppercased, hyphens to underscores, `SECRET_` prefix
- Read-only in practice (environment is not persisted)

```bash
export SECRET_MY_API_KEY=sk-abc123
argus-mcp secret --provider env get my-api-key
```

### `keyring`

Uses the OS keyring (macOS Keychain, GNOME Keyring, Windows Credential Locker).

- **Service name**: `argus-mcp`
- **Requires**: `keyring` package

```bash
argus-mcp secret --provider keyring set my-api-key
argus-mcp secret --provider keyring get my-api-key
```

## Using Secrets in Config

Reference stored secrets with the `secret:` prefix:

```yaml
backends:
  my-server:
    type: sse
    url: "http://localhost:8080/sse"
    headers:
      Authorization: "Bearer secret:my-api-key"

server:
  management:
    token: "secret:mgmt-token"
```

At startup, `secret:my-api-key` is resolved to the actual value from the
configured provider. Resolved values are automatically registered with the
log redaction filter — they will never appear in log files.

See [Secrets Management](../security/secrets.md) for architecture details.
