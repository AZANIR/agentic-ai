---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---

# 0005 — Pin MCP to a minor line, not a floor

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead
- **Amends:** repository ADR 0001 (extras carry floors, not pins)

## Context

Repository ADR 0001 says: versions in extras are **floors**, not pins. The reason was a good one:
a false pin on an unverified package is worse than an honest floor.

The SAD §11 risk ("the MCP library's API will change") fired **before the first line of the
stage's code was written**. The extra said `mcp>=1.2`; the install gave **2.0.0**, and in it:

    mcp.server.fastmcp        -> the module does not exist
    FastMCP                   -> renamed to MCPServer
    tool.inputSchema          -> tool.input_schema
    result.isError            -> result.is_error
    result.structuredContent  -> result.structured_content

That is, the entry point the source article starts from disappeared, and every field the client
reads was renamed. The floor `>=1.2` described an API that no longer exists.

## Considered options

1. **A pin to the minor line:** `mcp>=2.0,<3`.
2. **Keep the floor** `>=1.2` and write the code against 2.0 — that is, lie in the metadata.
3. **An exact pin** `==2.0.0`.

## Decision outcome

**Chosen:** Option 1.

Option 2 is out immediately: the floor `>=1.2` asserts that the code works with 1.2, and it does
not. This is not pedantry — a reader who ends up with 1.9 installed will get a
`ModuleNotFoundError` with no hint whatsoever that the cause is the version.

Option 3 is more reliable and more expensive than needed: an exact pin breaks on every patch and
turns the course into pin-maintenance work. A minor line is the boundary at which the library
itself promises not to break the API.

**The exception is limited to this package.** The other extras stay floors: their APIs have been
stable for years. MCP is a young protocol whose specification changed enough that it became the
news of the source article itself. Treating it like `numpy` would mean ignoring what it says
about itself.

## Consequences

**Positive**
- `pip install -e ".[s04]"` gives a library the code actually works with.
- The release of 3.0 will break the install **loudly**, rather than with a silent
  `ModuleNotFoundError` deep inside the code.
- The lesson can show concrete names and fields without adding "depending on the version".

**Negative**
- One package lives by a different rule from the rest. Recorded here so that the next reader does
  not conclude it was an oversight.
- Moving to 3.0 becomes a piece of work of its own rather than a consequence of the next
  `pip install`. That is the point.
