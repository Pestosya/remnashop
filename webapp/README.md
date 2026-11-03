# Personal cabinet (Telegram Mini App)

A small React + TypeScript SPA that talks to the public API under
`/api/v1/public`. FastAPI serves the build at `/app` (see `src/web/spa.py`).

## Why it is served from the backend

The session lives in httpOnly cookies set by `POST /auth/telegram/webapp`.
Telegram's WebView drops third-party cookies, so hosting the cabinet on a
different origin than the API would require switching authentication to bearer
tokens. Same-origin keeps the existing auth untouched.

## Running it

The Docker image builds this automatically — there is nothing to do for a normal
deploy. For local work:

```bash
npm install
npm run dev
```

`npm run dev` proxies `/api` to `http://localhost:8000`; override with
`VITE_API_TARGET`.

### Previewing without Telegram or a backend

Logging in needs signed Telegram `initData`, so a plain browser normally only
reaches the "open from the bot" screen. Append `?demo=1` to swap the API layer
for the fixtures in `src/demo.ts` and browse every screen offline:

    http://localhost:5173/app/?demo=1

Demo mode is opt-in through the query string only, so a real Mini App session
is never affected. Use it for design review and screenshots; it does not
exercise auth, payments or the Telegram bridge.

```bash
npm run build      # type-checks, then emits dist/
npm run typecheck  # types only
```

## Website sign-in (buyers without Telegram)

Outside Telegram the cabinet shows email sign-up / sign-in (`/auth/register`, `/auth/login`)
and then asks for the 6-digit code from the email (`/auth/email/request-verification`,
`/auth/email/confirm`): the backend lets only verified web accounts buy. That needs
`EMAIL_ENABLED=true` and the `EMAIL_*` SMTP settings. Purchases made there send
`return_to_site`, so the payment page returns to `/app/?paid=1` on the same site instead of
the bot. The landing (`landing/`, served at `/`) links to `/app/` and `/app/store?plan=<code>`.

## Enabling it in production

```env
WEB_ENABLED=true
WEB_CABINET_URL="https://your-domain.example/app"
APP_API_KEY="..."      # required when WEB_ENABLED=true
APP_JWT_SECRET="..."   # required when WEB_ENABLED=true
```

The bot's menu already renders a WebApp button for `WEB_CABINET_URL` when
`WEB_ENABLED` is on, so no code change is needed to surface it.

## Keeping types in sync

`src/types.ts` mirrors `src/web/schemas/*.py` by hand — the backend disables its
OpenAPI document (`openapi_url=None`), so nothing is generated. When a schema
changes on the Python side, update the interface here too.
