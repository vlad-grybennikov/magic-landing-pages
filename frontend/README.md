# Magic Landing Pages frontend

Next.js App Router frontend for the voice-driven page builder, originally
scaffolded with `create-next-app`. The builder sends commands to the FastAPI
orchestrator. Published pages are read from MongoDB by the Next.js server.

## Local development

Run these commands from `frontend/`:

```bash
npm ci
npm run dev
```

Open [localhost:3000](http://localhost:3000). Start the orchestrator separately
with `make dev-api` from the repository root. Page generation also requires
the backend's configured model services and MongoDB.

Optional overrides go in `frontend/.env.local`:

| Variable | Default / purpose |
|---|---|
| `NEXT_PUBLIC_ORCHESTRATOR_URL` | `http://localhost:8000` |
| `MONGODB_URI` | `mongodb://localhost:27017` |
| `MONGODB_DB` | `vlp-local`; match the orchestrator's `MONGO_DB` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Optional Google web client ID; match the orchestrator's `GOOGLE_CLIENT_ID` when enabling sign-in |
| `NEXT_PUBLIC_SITE_HOST` | Optional published-page host; defaults to the browser's host |

## Routes and rendering

- `/`: builder, implemented in `src/app/page.tsx`.
- `/preview`: iframe preview receiving draft content from the builder.
- `/sections` and `/sections/[pack]`: section and layout-pack previews.
- `/[...slug]`: published-page lookup and rendering.

Shared section components render both the preview and published pages.
The builder uses Inter. Generated pages use their selected font pairing,
with Open Sans as the CSS fallback; fonts are loaded through `next/font`.

## Checks and production build

```bash
npx tsc --noEmit
npm run lint
npm run build
npm start
```

The repository's Docker Compose configuration runs the frontend alongside
the orchestrator, MongoDB, and Ollama.
