Frontend README — React
======================

Purpose
-------
This document helps a new frontend developer pick up and continue the frontend using React. It describes recommended tooling, scaffold steps, how to integrate with the existing Django backend, build/deploy, and common developer commands.

Project layout (existing)
-------------------------
- Django templates: [src/templates/main](src/templates/main)
- Static assets currently in: [src/static](src/static) and [staticfiles](staticfiles)
- Backend entrypoint: [src/manage.py](src/manage.py)

High-level options
-----------------------------
1. Standalone React SPA 
   - Create a separate `frontend/` folder at repo root using Vite.
   - Run the React dev server during development (`npm run dev`).
   - Backend remains at `http://localhost:8000`; enable CORS for the dev origin.
   - Production: build the SPA and serve it from a static host or integrate build into Django staticfiles.

2. Integrated build inside Django
   - Build the React app and copy the `dist` (or `build`) folder into Django static files.
   - Update Django `STATICFILES_DIRS` to include the built assets so `collectstatic` picks them up.

Recommended stack
-----------------
- Node.js LTS (>=18)
- Vite + React (fast dev server) or Create React App if you prefer CRA
- ESLint + Prettier for linting/formatting
- Vitest / Jest for unit tests

Scaffold a new frontend (Vite)
------------------------------
Run these commands from the repository root:

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

Development commands (inside `frontend`)
--------------------------------------
- Dev server: `npm run dev`
- Build for production: `npm run build`
- Preview build locally: `npm run preview`
- Add lint script (example): `npm run lint`

Environment variables
---------------------
- Vite: use `import.meta.env.VITE_API_BASE` for the backend base URL.
- Example `.env` (in `frontend`):

```env
VITE_API_BASE=http://localhost:8000/api
```

API & auth
-----------
- Put API wrappers in `src/services/api.js` (or `src/lib/api`).
- Use fetch/axios with the base URL from `import.meta.env.VITE_API_BASE`.
- For authentication tokens, store in secure cookies or `localStorage` (with caution); prefer HTTP-only cookies via backend when possible.

Django backend integration notes
--------------------------------
Option A — Separate SPA 
- Install and configure `django-cors-headers` in `src/settings.py`:

```python
INSTALLED_APPS += [
    'corsheaders',
]
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware'] + MIDDLEWARE
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',  # Vite default dev origin
]
```

Option B — Serve built assets via Django:
- Add this to `src/settings.py` (adjust paths):

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
STATICFILES_DIRS += [BASE_DIR / 'frontend' / 'dist']
```
- After building (`npm run build`), run `python manage.py collectstatic` to gather files.

Static asset references
-----------------------
- During integration via Option B, include the built `index.html` into your Django template or update `base.html` to reference bundled CSS/JS files.

Recommended folder conventions for `frontend`
-------------------------------------------
- `src/components/` — reusable UI components
- `src/pages/` — top-level route components
- `src/services/` — API wrappers and data fetching
- `src/hooks/` — custom hooks
- `src/assets/` — images and static assets

Testing, linting, CI
--------------------
- Add ESLint + Prettier config in `frontend/.eslintrc` and `frontend/.prettierrc`.
- Add unit tests using Vitest or Jest.
- Example npm scripts in `frontend/package.json`:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "lint": "eslint . --ext .js,.jsx",
  "test": "vitest"
}
```

Developer workflow
------------------
- Start backend: `python manage.py runserver` (from `src` folder / project root as appropriate).
- Start frontend: `cd frontend && npm run dev`.
- Open the SPA at the Vite dev URL (e.g., `http://localhost:5173`).

Troubleshooting
---------------
- If API calls 403/CORS: ensure `CORS_ALLOWED_ORIGINS` matches dev origin and `django-cors-headers` is installed.
- If static assets not found after build: confirm `STATICFILES_DIRS` includes build output and run `collectstatic`.

Next steps you can take now
--------------------------
1. Choose option A (separate SPA) or B (integrate build into Django).

Where to look in this repo
--------------------------
- Django templates: [src/templates/main](src/templates/main) //Html
- Static files:[src/static]  //css and js files
- Django settings: [src/app/settings.py](src/app/settings.py)
- Django manage script: [src/manage.py](src/manage.py)

