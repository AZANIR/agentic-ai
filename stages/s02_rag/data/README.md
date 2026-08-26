# Stage 2 data

`kb/` is the NovaShop knowledge base. Every file carries metadata: `title` and `access`
(`public` or `internal`).

The set is picked so the checks are deterministic rather than lucky:

| Document | Its role in the checks |
|---|---|
| `returns-policy.md` | The target of AC-01: it wins on the literal returns question |
| `internal-refund-thresholds.md` | **The AC-05 trap:** it deliberately contains the same words as a shopper's question about the refund amount, and would win on closeness. It has to be cut out by the filter — and `returns-policy` has to stay in the results while that happens |
| `internal-escalation.md` | The second internal document: proves the filter does not depend on one file |
| `empty.md`, `tiny.md` | AC-08b: indexing does not fall over, the documents are named, and the rest of the base is still searchable |
| the rest | Filler, so that top-k has something to choose between |

If you change `internal-refund-thresholds.md`, check that it **still wins** on closeness without
the filter. Otherwise AC-05 starts checking a coincidence rather than a mechanism.

The knowledge-base documents themselves are the shop's Ukrainian-language corpus and are
fixtures, not lesson prose: the checks match their wording literally, and the AC-05 trap only
works because the trap document shares words with the question.
