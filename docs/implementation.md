Create UI and backend corresponding to the database that has been created and as per the specification present in
  docs/CoachLink Spec.dc.html


Tech Stack to be used 
    Backend (server/)
    - Python 3.12+ with FastAPI
    - SQLAlchemy 2.0 (async) + PostgreSQL (SQLite in-memory for tests)
    - Alembic for migrations
    - uv for dependency management
    - Auth via JWT (access + refresh tokens), pydantic-settings for config
    - Tooling: pytest, ruff (lint/format), mypy (strict mode)

    Frontend (web/)
    - React 19 + TypeScript + Vite
    - Tailwind CSS (with the Elevionix design-system theme)
    - TanStack Query for server state, Zustand for auth state, React Router for routing
    - Axios for API calls, with types generated from the backend's OpenAPI spec

Use Elevionix Design System theme for UI which is present at web/elevionix-design-system

For UI reference /Users/ajsingh/Developer/etl/projects/coachlink/docs/CoachLink Standalone.html, if you want to refer how the screens should look like
