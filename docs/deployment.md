# Deployment (free tiers)

You need accounts for these; nothing here is done automatically.

## 1. Database: MongoDB Atlas (M0 free)

Create a cluster, a database user, and allow network access (0.0.0.0/0 for Render's free tier). Copy the
connection string for `MONGO_URI`.

## 2. Backend: Render (Docker web service)

- New Web Service from the GitHub repo, root directory `backend`, runtime Docker.
- Environment variables:
  - `MONGO_URI` = Atlas string
  - `ALLOW_MONGOMOCK_FALLBACK` = `false`
  - `CORS_ORIGINS` = your frontend URL (e.g. `https://your-app.vercel.app`)
  - Optional logging settings: `LOG_LEVEL`, `LOG_RETENTION_DAYS`, `LOG_MAX_MB`, `LOG_TO_FILE` (see [logging.md](logging.md)).
    On Render the filesystem is ephemeral and logs are read from the dashboard (stdout), so `LOG_TO_FILE=false` is sensible.
  - Keep secrets such as the Atlas string in the platform's environment settings, never in the repository.
- Render provides `PORT`; the Dockerfile honours it.
- Free instances sleep when idle, so the first request after a pause is slow.

## 3. Frontend: Vercel or Netlify

- Root directory `frontend`, build `npm run build`, output `dist`.
- Environment variable `VITE_API_URL` = the Render backend URL (no trailing slash).
- The app has client-side routes (`/method`, `/about`), so the host must serve `index.html` for unknown paths.
  `frontend/vercel.json` (Vercel) and `frontend/public/_redirects` (Netlify) already do this.

## 4. Verify

Open the frontend URL, run an analysis, and check `<backend-url>/api/health` (process) and `<backend-url>/api/ready` (database).
