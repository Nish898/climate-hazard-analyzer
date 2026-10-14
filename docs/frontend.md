# Frontend

React 18 + Vite, Chart.js (via react-chartjs-2), Leaflet (via react-leaflet), React Router 6. No UI framework: the look
comes from a small set of CSS design tokens.

## Pages (`src/pages/`)

| Route | Page | Content |
|---|---|---|
| `/` | `Analyzer.jsx` | Hero banner for the selected place, controls + map, insight, stat cards, event table, three charts |
| `/method` | `Method.jsx` | Heatwave definition, data cleaning, trend statistics |
| `/about` | `About.jsx` | Data source and limitations |

Unknown paths fall back to the Analyzer. The app is a single-page app, so the host must serve `index.html` for any path
(nginx and the Vercel/Netlify files in `frontend/` already do).

## Structure

```
src/
  main.jsx           entry: styles, global error handlers, error boundary
  App.jsx            router
  layouts/AppLayout  floating sidebar (collapsible; drawer on phones) + top bar
  pages/             Analyzer, Method, About (+ Analyzer.css)
  components/        Controls, MapPicker, InsightPanel, Charts, Dropdown, ToggleSwitch, icons
  hooks/             useClickOutside
  api.js             fetch wrappers: abortable, readable error messages
  logger.js          reports frontend errors to /api/client-log
  ErrorBoundary.jsx  keeps a render crash from blanking the whole page
  theme.css          colour tokens (light palette)
  index.css, App.css base styles, shell layout and shared primitives (card, btn, field, badge, table)
```

## Behaviour worth knowing

- **Results match what you see.** The Analyzer keeps the exact form that produced the displayed results, so the title and
  the CSV link never drift from the data while you edit fields.
- **Results are memoised.** `Charts` and `InsightPanel` use `React.memo`, so typing in the form does not re-render or re-animate
  them (typing 6 characters used to trigger 157 canvas redraws; it now triggers none).
- **Stale responses are ignored.** A new analysis or place search aborts the previous request.
- **Charts.** Years with under 80% valid data are drawn grey. Colours are read from the CSS tokens, because `<canvas>`
  cannot use CSS variables. The `Filler` plugin is registered for the filled intensity chart.
- **Errors.** API failures show plain messages (rate limit, provider down, timeout, offline). Unexpected frontend errors
  are reported to the backend log (see [logging.md](logging.md)).
- **Bundle.** Vendor libraries are split into separate chunks (`vite.config.js`).

## Styling

All colours come from `src/theme.css`; stylesheets never use literal colours for surfaces, text or borders. Brand
accents (burnt-sienna family) and the shadow colour are tokens too. The app is light-theme only.

## Development

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to localhost:8000
npm run build
```

`VITE_API_URL` sets the backend URL when the frontend is hosted separately from the API (empty = same origin).
