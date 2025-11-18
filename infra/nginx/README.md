# Nginx / Reverse Proxy

Stores nginx (or Traefik) configs for routing subdomains to the right app containers.

## Plan
- Base config with TLS termination + HTTP/2
- `bets.dock108.ai`, `crypto.dock108.ai`, etc. mapped to the relevant Next.js services
- `/api` upstream → FastAPI service, with sticky sessions disabled (stateless)
- Logging tuned for guardrail audits
