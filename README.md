# Universal Import Service

Universal Import Service is a tenant-aware CSV and Excel import platform with a FastAPI backend and a React frontend. It is designed for operator-friendly imports: the user selects a tenant, provides database connection details, uploads a file, and the backend resolves the correct import profile automatically.

## Highlights

- Tenant-based import profiles
- Backend-managed schema, mapping, transforms, and validation
- CSV and Excel import support
- Background job execution with progress tracking
- Row-level correction workbook generation
- Re-import flow that ignores the helper `Error` column
- Premium React operator console
- Structured database connection input instead of raw SQLAlchemy driver strings

## Architecture

The project has two main parts:

- `app/`
  FastAPI backend, import engine, profile matching, storage, validation, and job tracking
- `frontend/`
  React + Vite operator console

Key backend areas:

- `app/main.py`
  FastAPI app setup, startup initialization, CORS, exception wiring
- `app/api/v1/routes/`
  REST endpoints for imports, jobs, profiles, health, and error file download
- `app/import_engine/`
  Import pipeline, profile defaults, parsing, validation, transformation, duplicate handling, and error workbook creation
- `app/models/`
  SQLAlchemy models for import jobs and import profiles
- `app/db/`
  Job metadata DB session and target DB connection helpers

Key frontend areas:

- `frontend/src/App.tsx`
  Main operator dashboard
- `frontend/src/api.ts`
  API client helpers
- `frontend/src/styles.css`
  Premium SaaS-style UI theme

## Current operator workflow

The standard UI flow is:

1. Enter tenant ID
2. Choose database type
3. Fill database connection fields
4. Upload CSV or Excel file
5. Start import

The backend then:

- inspects the uploaded file
- resolves the best matching tenant import profile
- applies mapping and transformations
- validates rows
- filters duplicates
- inserts valid rows into the destination DB
- creates an error workbook for failed rows when needed

## Import profiles

Import profiles are the core of the simplified UX. They let the backend own schema logic while the UI stays minimal.

Each profile can define:

- tenant ID
- profile name
- description
- default profile status
- filename match hints
- required headers
- sheet mapping
- model definitions

The backend currently seeds a default profile for `tenant_a` called `default_users`.

That seeded profile expects headers like:

- `Email Address`
- `Age`
- `Department`
- `Full Name`

It maps to the `users` table and applies:

- `email` lowercasing
- `Full Name` split into `first_name` and `last_name`

## Correction workbook flow

If an import contains invalid rows:

1. The UI shows that an error workbook is available
2. The user downloads it from the job details panel
3. The workbook preserves the original input columns
4. One extra column, `Error`, is appended
5. The user fixes the invalid rows and re-uploads the workbook

On re-import:

- the backend ignores the helper `Error` column
- corrected rows are processed normally

## API endpoints

- `GET /api/v1/health`
  Health check
- `POST /api/v1/imports`
  Direct JSON import job creation
- `POST /api/v1/imports/upload`
  File upload import flow
- `GET /api/v1/import/status/{job_id}`
  Single job status
- `GET /api/v1/jobs`
  Recent jobs for a tenant
- `GET /api/v1/import/errors/{job_id}`
  Download correction workbook
- `GET /api/v1/profiles/{tenant_id}`
  List import profiles for a tenant

## Database connection input

The UI no longer expects raw SQLAlchemy URLs by default.

Instead, users enter structured fields:

- database type
- host
- port
- database name
- username
- password

For SQLite:

- file path only

The backend converts those values into supported sync SQLAlchemy URLs:

- PostgreSQL -> `postgresql+psycopg2`
- MySQL -> `mysql+pymysql`
- SQL Server -> `mssql+pyodbc`
- SQLite -> `sqlite:///...`

This is why raw async driver strings like `postgresql+asyncpg` are rejected.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENV` | `dev` | Environment label |
| `APP_NAME` | `Universal Import Service` | API/service name |
| `APP_VERSION` | `1.0.0` | Service version |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_V1_PREFIX` | `/api/v1` | API route prefix |
| `JOB_DB_URL` | `sqlite:///./import_jobs.db` | Metadata DB for jobs and profiles |
| `STORAGE_ROOT` | `./storage` | Uploaded file storage root |
| `ERROR_ROOT` | `./errors` | Error workbook storage root |
| `REDIS_URL` | empty | Celery broker/backend URL |
| `USE_CELERY` | `false` | Enable Celery workers |
| `MAX_CONCURRENT_IMPORTS_PER_TENANT` | `3` | Per-tenant concurrency limit |
| `DEFAULT_CHUNK_SIZE` | `2000` | Row chunk size |
| `MAX_UPLOAD_SIZE_MB` | `25` | Max upload size |
| `MAX_ERRORS_PER_JOB` | `5000` | Max exported errors |
| `MAX_ROWS_PER_FILE` | `100000` | Max rows allowed per file |
| `ALLOWED_FILE_EXTENSIONS` | `.csv,.xlsx,.xls` | Supported file types |
| `ALLOWED_DB_SCHEMES` | `sqlite,postgresql,...` | Allowed SQLAlchemy schemes |
| `API_KEYS` | empty | Optional API keys |
| `ALLOWED_ORIGINS` | `*` | CORS allowlist |

## Local setup

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend health URL:

`http://127.0.0.1:8000/api/v1/health`

### Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Frontend URL:

`http://127.0.0.1:5173`

## Local smoke test

Use:

```bash
powershell -ExecutionPolicy Bypass -File .\test_import.ps1
```

That script:

- resets the local demo DB
- creates a sample CSV
- uploads it
- checks job completion
- confirms the simplified flow works

## What has been validated

The codebase has already been checked for the main happy path:

- backend compile passes
- frontend production build passes
- health endpoint works
- profile listing works
- upload flow works
- job status and job listing work
- error workbook download works
- corrected workbook re-import works
- unsupported DB schemes are rejected early
- unrelated files are rejected when no profile matches

## Current boundaries

- relationship resolution is still a placeholder/no-op
- profile creation and editing is not yet exposed in an admin UI
- Alembic migrations are not set up yet
- the repository currently seeds only a default demo tenant profile

## Recommended next steps

- add profile management UI for admins
- add automated pytest coverage
- add Alembic migrations
- support saved database connections per tenant
- add authentication/session UX in the frontend

## GitHub push steps

After Git is initialized locally, you can push with:

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
