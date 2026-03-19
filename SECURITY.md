# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.4.x   | ✅ Yes             |
| 0.3.x   | ⚠️ Security fixes only |
| < 0.3   | ❌ No              |

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

Instead, report vulnerabilities privately via one of these channels:

1. **GitHub Security Advisories** (preferred):
   → [Report a vulnerability](https://github.com/rodrigogobbo/denai/security/advisories/new)

2. **Email**: rodrigo.gobbo@outlook.com

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to expect

- **Acknowledgment** within 48 hours
- **Assessment** within 7 days
- **Fix release** within 30 days for critical issues

## Security Design

DenAI is designed to run **locally** on your machine. Key security features:

- **API key authentication** — Auto-generated on first run, required for all API calls
- **Rate limiting** — 60 requests/minute per IP
- **Command sandboxing** — Dangerous commands (`rm -rf`, `shutdown`, etc.) are blocked
- **Path sandboxing** — Tool access restricted to working directory and `~/.denai/`
- **SSRF protection** — `web_search` blocks requests to private IPs and internal networks
- **No telemetry** — Zero data leaves your machine
- **Local-only by default** — Binds to `127.0.0.1` unless `--share` is explicitly used

## Dependency Security

- Dependencies are monitored via [Dependabot](https://github.com/rodrigogobbo/denai/security/dependabot)
- Secret scanning and push protection are enabled
