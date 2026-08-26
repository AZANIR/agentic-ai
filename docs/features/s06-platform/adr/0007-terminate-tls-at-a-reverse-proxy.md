---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0007 — TLS terminates at a reverse proxy

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The service has to answer over HTTPS. There are exactly two options: a certificate inside the
application, or a reverse proxy in front of it.

The question looks like infrastructure and has a direct teaching value: the reader has to see that
**the service knows nothing about TLS** — and why that is right.

## Decision drivers

- Certificates have to renew automatically; a manual renewal gets forgotten.
- Redirecting from an unencrypted connection is required by AC-08.
- Locally there is neither a domain nor a public certificate (C-3).
- An application that speaks TLS has to be restarted on every certificate renewal.

## Considered options

1. **A reverse proxy** that obtains the certificate automatically.
2. **TLS inside the application**, with certificate files.
3. **A proxy plus a separate certificate-authority client** as one more process.

## Decision outcome

**Chosen:** Option 1.

Option 2 mixes two jobs in one process: the service starts knowing about domains and expiry dates,
and renewing a certificate becomes restarting the service.

Option 3 is Option 1 taken apart into two pieces by hand. It makes sense where the proxy is already
in place and nobody is choosing it; here it is being chosen.

**Locally the same proxy runs** with an internal certificate. That matters: `smoke.sh` runs **the
same** list against localhost and against the domain, so the mechanics are checked locally. Exactly
one thing stays unverified — trust in the certificate from a public authority, and that is what
gets marked `NOT EVALUATED`.

## Consequences

**Positive**
- The application knows nothing about TLS; the certificate renews without restarting it.
- The same configuration file works locally and on the domain.
- The redirect and the security headers are two lines, not a library.

**Negative**
- One more container in the deployment.
- The local certificate is self-signed, so the client has either to accept it or to ignore it — and
  `smoke.sh` has to draw that distinction explicitly, rather than switching the check off silently.
