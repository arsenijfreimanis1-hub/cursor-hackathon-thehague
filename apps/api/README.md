# Rekentafel API

HTTP transport for Rekentafel MVP. Business logic uses a **FluxZero-inspired message bus**
(`src/flux/`) — commands and queries dispatched to handlers without HTTP coupling.

## FluxZero note

[FluxZero](https://fluxzero.io) is a JVM message-driven backend platform (Java/Kotlin SDK).
William's build docs reference Fastify; this user override targets FluxZero patterns.
The official SDK has no TypeScript runtime — this app mirrors FluxZero's handler model in
Node so frontends and shared packages stay in the pnpm monorepo. A future `apps/api-java`
FluxZero service can replace the in-process bus via HTTP/gRPC.

## Local dev

```bash
pnpm --filter @rekentafel/api dev
```

Requires `DATABASE_URL` and optionally `MOLLIE_API_KEY` (test mode).
