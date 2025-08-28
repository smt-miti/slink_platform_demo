# URL Encoding Algorithms / Strategies

This table compares the strategies implemented in `strategies.py` and industry patterns frequently cited in URL shortener designs.  

| Strategy | How it works | Determinism | Uniqueness / Collisions | Predictability / Security | Operational notes | Pros | Cons | Good fit | Real-world example | Driver for choice |
|---|---|---|---|---|---|---|---|---|---|---|
| **SHA256Strategy** (in `strategies.py`) | `sha256(url)` → integer → **Base62** → **truncate to L** (retry with `counter` on rare collision). | Yes (same URL ⇒ same code) | Extremely low collision prob. after truncation; `counter` allows retry. | Mapping is public/predictable (no secret). | No secret mgmt; length normalized via `_safe_len` (clamps to 4–32; default 8). | Simple, idempotent; easy de-dupe by recompute. | Guessable relationships if L is short. | Idempotent create flow; stateless; low-ops demos. | Often used in internal systems needing **stable deterministic IDs** (e.g., deduplication pipelines). | Best when you need **idempotency** (same URL ⇒ same code) and low operational overhead. |
| **RandomStrategy** (in `strategies.py`) | Generate **L random Base62** chars via CSPRNG; rely on uniqueness check in storage. Default L=6 (clamped 4–32). | No | Collisions possible; resolve via **unique index + retry**. | High unpredictability; no URL→code relation. | Requires atomic insert-or-retry in DB/kv. | Simple, highly unpredictable; great for write throughput. | Non-idempotent; must handle retries. | High-throughput create path with robust storage guard. | Used in services where **non-guessability** is a must (e.g., private share links, Google Drive “unguessable” links). | Choose when **security/unpredictability** matters more than determinism; works well with strong DB uniqueness guarantees. |
| **Snowflake ID (Twitter/X)** | **64-bit time-sortable IDs**: 41 bits timestamp (ms since epoch) + 10 bits worker ID + 12-bit per-ms sequence; typically serialized in decimal then (optionally) Base62’d for shorter codes. | Yes (monotonic per node/time) | Collision-free within spec (per-node 4096 IDs/ms). | Not secret; time/order can be inferred from the ID. | Requires **time sync** and **worker ID** assignment; great sharding properties. | Massive scale, ordered IDs, no central DB hot-spot. | Leaks timing/order; needs infra (worker IDs, clock). | Large, distributed fleets; analytics that benefit from time-ordering. | Twitter/X (original Snowflake spec); adopted in distributed databases and ID services (e.g., Instagram, Discord IDs). | Choose when **global scale + ordering** is required (billions of IDs/day) and you need to avoid a central sequence bottleneck. |
| **Bitly-style sequential → Base62** | Assign an **increasing integer** (global or per-shard), then **Base62-encode** it to get a compact alias; ensure uniqueness via the counter. | Yes | Collision-free by construction (unique counter). | Not secret; short early IDs can be guessable. | Needs a scalable counter (DB auto-inc, ticket server, or sharded ranges). | Very fast, simple, short codes; great cache locality. | Requires careful sharding to avoid bottlenecks; sequential nature can expose volume. | Production shorteners; easy ops with good shard planning. | Bitly (classic design: incrementing counter → Base62) | Choose when **simplicity + performance** matter; works well when central counter scaling is solved (e.g., sharded DB, ticket servers). |

---

## Summary of Drivers
- **Idempotency required?** → SHA256/HMAC strategies.  
- **Security/unpredictability needed?** → Random strategy.  
- **Global ordering, massive scale?** → Snowflake IDs.  
- **Simplicity, proven in production?** → Bitly-style sequential Base62.  

---

---

## Code Length Considerations (Base62)

The size of the code space is given by **62^L**, where **L** is the code length and the alphabet consists of digits (0–9), lowercase (a–z), and uppercase (A–Z).  

### Capacity by Length
| Length (L) | Code space (62^L) | Approx. capacity | Notes |
|---:|---:|---:|---|
| 4 | 14,776,336 | ~14.8 million | Suitable only for small-scale or demo systems. |
| 5 | 916,132,832 | ~0.9 billion | Supports ~100M links with buffer. |
| 6 | 56,800,235,584 | ~56.8 billion | Common default for production-scale systems. |
| 7 | 3,521,614,606,208 | ~3.5 trillion | Enterprise scale. |
| 8 | 218,340,105,584,896 | ~218 trillion | Sufficient for internet-scale workloads. |

---

### Collision Probability

For **deterministic sequential codes**, collisions do not occur; the code space is exhausted sequentially and only lengthening is required once capacity is exceeded.  

For **random or truncated hash codes**, the **birthday paradox** applies. The probability of at least one collision after generating **M** codes in a space of size **N = 62^L** is approximately:

\[
P(collision) \approx 1 - e^{-M^2 / (2N)}
\]

**Illustrative examples:**

| Length (L) | Capacity (62^L) | M = 1M | M = 10M | M = 100M |
|---:|---:|---:|---:|---:|
| 6 | 56.8B | ~0.9% | ~81% | ~100% |
| 7 | 3.5T | ~0.014% | ~1.4% | ~96% |
| 8 | 218T | ~0.0002% | ~0.02% | ~2% |

---

### Recommendations

- **Sequential (Bitly-style):**  
  - Collisions do not occur.  
  - Codes remain as short as possible, growing in length only when capacity is exceeded.  
  - Recommended to enforce a minimum display length (e.g., 6 characters) to prevent short, easily guessable codes.  

- **Random / Truncated Hash (SHA256/HMAC):**  
  - Collision risk depends on code length.  
  - For ≤10M codes, **L = 7** is sufficient with low probability of collision.  
  - For ≥100M codes, **L = 9** recommended to keep probability below 1%.  
  - Collisions should be mitigated by enforcing uniqueness at the storage layer (e.g., unique index) and retrying on conflict.  

- **Snowflake IDs:**  
  - Collision-free within specification.  
  - Code length determined by 64-bit representation; typically 11 characters when Base62-encoded.  
  - Provides time-ordering rather than shortest possible length.  

---

### Practical Defaults
- **MVP or demo deployments:** 6-character minimum across all strategies.  
- **Production with sequential codes:** minimum length of 6, with growth as needed.  
- **Production with random/hash codes:** 8 characters recommended for up to 100M links.  
- **Internet-scale systems:** 9–11 characters, depending on growth horizon and chosen strategy.  
