## Short-code Strategy Configuration

`slink_platform` supports multiple strategies for short-code generation. The active strategy is selected via `CODE_STRATEGY`.

**Supported values**
- `sha256` (default): Deterministic SHA-256 → Base62 → truncate to `CODE_LENGTH`
- `hmac-sha256`: Keyed deterministic HMAC-SHA256(secret, ...) → Base62 → truncate
- `random`: Random Base62 of length L (default 6 if not provided)
- `sequential` / `seq` / `bitly`: Bitly-like monotonically increasing integer → Base62

**Common settings**
- `CODE_LENGTH`: Default length for deterministic strategies (clamped to 4..32; default: 8)
- `CODE_SECRET`: Secret for `hmac-sha256`

**Sequential strategy settings**
- `SEQ_START`: Starting integer (default `3_500_000`). Prevents very short early codes.
- `CODE_MIN_LENGTH`: Minimum visible length (default `6`). Enforced via left-pad (e.g., `'0'`).
- `SHARD_PREFIX`: Optional string prefix (e.g., `'ap'` or a node/region tag).

**Examples**
```bash
# keep default deterministic behavior
export CODE_STRATEGY=sha256

# try random with explicit length 8 at call sites
export CODE_STRATEGY=random

# try sequential (Bitly-like) with sane public defaults
export CODE_STRATEGY=sequential
export SEQ_START=3500000
export CODE_MIN_LENGTH=6
export SHARD_PREFIX=

