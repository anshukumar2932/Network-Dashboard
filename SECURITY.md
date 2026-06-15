# Security Measures

## Authentication

| Measure | Detail |
|---|---|
| Password hashing | `werkzeug.security.generate_password_hash` (pbkdf2:sha256) |
| Login rate limit | 10 POST requests per minute on `/` |
| CAPTCHA | 6-char alphanumeric image CAPTCHA on every login attempt |
| Force password change | New users default to `must_change_password=True`; blocked from all routes except `/change-password` until changed |

### Credential limits

| Field | Min length | Max length | Storage |
|---|---|---|---|
| Username | — | **No limit enforced** | `String` (unbounded) in SQLite |
| Password | 4 characters | **No limit enforced** | `String` (unbounded), stored as pbkdf2 hash (~200 chars) |

> **Recommendation:** Add `maxlength="64"` on username inputs and `minlength="8" maxlength="128"` on password inputs (forms + server-side validation) to prevent abuse.

---

## Transport Encryption (TLS/HTTPS)

| Setting | Env Variable | Purpose |
|---|---|---|
| `SSL_CERTFILE` | Path to certificate file | Enables HTTPS when both cert and key are set |
| `SSL_KEYFILE` | Path to private key file | Enables HTTPS when both cert and key are set |

### Behavior

- When `SSL_CERTFILE` and `SSL_KEYFILE` are set and files exist, the server starts with TLS enabled
- In production (`DEBUG=false`), `SESSION_COOKIE_SECURE=True` is set automatically (cookies only sent over HTTPS)
- HTTP requests are redirected to HTTPS (301) when TLS is active
- Falls back to plain HTTP if cert/key files are missing or invalid

### Generating self-signed certificates (development only)

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

Set in `.env`:
```
SSL_CERTFILE=cert.pem
SSL_KEYFILE=key.pem
```

---

## Session Security

| Setting | Value | Purpose |
|---|---|---|
| `SESSION_COOKIE_HTTPONLY` | `True` | Prevents JavaScript from reading the session cookie (XSS mitigation) |
| `SESSION_COOKIE_SAMESITE` | `Lax` | Blocks cross-origin cookie submission (CSRF mitigation) |
| `SESSION_COOKIE_SECURE` | `True` in production | Cookies only sent over HTTPS (set automatically when `DEBUG=false`) |
| `PERMANENT_SESSION_LIFETIME` | 3600 seconds (1 hour) | Auto-logout after inactivity |
| Session timeout check | `@app.before_request` | Forces logout and clears session if `last_activity` exceeds 1 hour |

---

## CSRF Protection

Destructive API routes require **one of**:

| Header | Value | Used by |
|---|---|---|
| `X-CSRF-Token` | Session-generated hex token (64 chars) | Browser frontend (auto-injected via `<meta>` tag) |
| `X-API-Key` | Environment variable `API_KEY` | External API clients / scripts |

Protected routes:
- `GET /api/ping/now` — triggers a full network scan
- `GET /api/ping/now` (sidebar "Add All") — also protected
- `POST /api/dashboard-state` — saves layout, positions, collapse state
- `DELETE /api/devices/delete/<ip>` — removes a device

### How it works

1. On login, a CSRF token is generated (`secrets.token_hex(32)`) and stored in the session
2. The token is injected into `<meta name="csrf-token">` via Jinja2 context processor
3. Frontend JavaScript reads the meta tag and sends it as `X-CSRF-Token` header on protected fetch calls
4. Server compares the header value against `session["csrf_token"]`

---

## Rate Limiting

| Scope | Limit | Target |
|---|---|---|
| Default | 200 requests/day, 50/hour | All routes unless exempt |
| Login (`POST /`) | 10 per minute | Brute-force protection |
| `/api/*` routes | Exempt from default limits | Polling-friendly (dashboard auto-refreshes every 28s) |
| `/dashboard` | Exempt | Paginated page loads |
| `/links` | Exempt | Paginated page loads |

---

## Security Headers

Applied to every response via `@app.after_request`:

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking (no iframe embedding) |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter in older browsers |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer leakage |
| `Cache-Control` | `no-store, no-cache, must-revalidate, max-age=0` | Applied to API and HTML responses |
| `Pragma` | `no-cache` | HTTP/1.0 cache busting |

---

## API Access Control

| Layer | Mechanism |
|---|---|
| Browser session | `@login_required` (Flask-Login session cookie) on all routes |
| Destructive APIs | `@require_api_key` on top of `@login_required` — requires either `X-API-Key` or `X-CSRF-Token` |
| External clients | Set `X-API-Key` header to the `API_KEY` environment variable |
| API rate limit exempt | All `/api/*` routes exempt from default rate limits for real-time polling |

---

## Monitor Health System

| Component | Detail |
|---|---|
| `monitor_status` dict | Tracks `last_run`, `last_success`, `running`, `last_duration`, `last_up`, `last_down`, `last_device_count` |
| `/api/monitor-status` | Returns monitor status as JSON (requires `@login_required`) |
| `/api/health` | Public health check: returns `{database, scheduler, monitor, last_run}` |
| SocketIO heartbeat | Emits `monitor_heartbeat` event after each successful ping cycle |
| Frontend banner | Three-state banner: OK (green), Running (yellow), Offline (red with glow) |
| Polling | Frontend polls `/api/monitor-status` every 30 seconds |
| Watchdog | JavaScript checks heartbeat age every 10 seconds; shows alert if > 10 minutes |
| Offline detection | Banner shows "MONITORING OFFLINE" when no successful scan for 10+ minutes |

---

## Input Handling

| Area | Detail |
|---|---|
| SQL injection | SQLAlchemy ORM — parameterized queries, no raw SQL |
| XSS (templates) | Jinja2 auto-escaping enabled by default |
| XSS (tooltip/innerHTML) | `node-tooltip` uses `pointer-events: none` to prevent interaction |
| Form validation | Server-side validation on login, password change, device CRUD, link CRUD |
| Sort/filter params | Allowlisted against valid column names (`app.py:486`) |

---

## Environment & Secrets

| Item | Location | Notes |
|---|---|---|
| `SECRET_KEY` | `.env` file | Flask session signing key |
| `API_KEY` | `.env` file | External API authentication |
| `DATABASE_URL` | `.env` file | Database connection string |
| `SSL_CERTFILE` | `.env` file | TLS certificate path (optional) |
| `SSL_KEYFILE` | `.env` file | TLS private key path (optional) |
| `.env` | Git-ignored | Listed in `.gitignore` |

---

## Network Topology Events

| Event | Method | Why |
|---|---|---|
| Hover | `cy.on('mouseover'/'mouseout', 'node', ...)` | Native Cytoscape events |
| Click | `cy.on('tap', 'node/edge', ...)` | Native Cytoscape events |
| Right-click | `cy.on('cxttap', 'node', ...)` | Native Cytoscape event (no DOM hit-testing) |
| Double-click | Double-tap timer on `cy.on('tap', 'node', ...)` | 300ms threshold, no DOM `dblclick` event |
| Context menu | Fixed-position overlay, closed on outside click | `pointer-events: none` on tooltip |

---

## Known Gaps / Recommendations

1. **No max length on username or password** — Add server-side validation (`len()`) and HTML `maxlength` attributes
2. **No CSRF token rotation** — Token is static per session; consider rotating on sensitive actions
3. **No Content-Security-Policy header** — Recommended for production to prevent XSS
4. **Password minimum is only 4 chars** — Industry recommendation is 8+ characters
5. **No account lockout** — Only rate limiting; no permanent lockout after N failed attempts
6. **Self-signed certs for dev** — Use Let's Encrypt for production deployments
