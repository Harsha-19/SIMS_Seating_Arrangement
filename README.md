# SIMS Seating Arrangement

This repository is organized as a full-stack project with a dedicated Django backend and a separate React/Vite frontend.

## Structure

```text
project-root/
├── backend/
│   ├── api/
│   ├── core/
│   ├── scratch/
│   ├── scripts/
│   ├── seating/
│   ├── seating_data/
│   ├── .env
│   ├── .env.example
│   ├── db.sqlite3
│   ├── manage.py
│   ├── requirements.txt
│   ├── run_migrations.bat
│   └── runserver.bat
├── frontend/
│   ├── src/
│   ├── .env
│   ├── .env.example
│   └── package.json
├── README.md
└── .gitignore
```

## Backend

Install Python dependencies from the backend folder:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Start Django on port `8000`:

```powershell
python manage.py runserver 127.0.0.1:8000
```

Or use the helper batch file:

```powershell
.\runserver.bat
```

Apply migrations:

```powershell
.\run_migrations.bat
```

## Frontend

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Start Vite on port `5173`:

```powershell
npm run dev
```

Build the frontend:

```powershell
npm run build
```

## Environment

Backend configuration lives in `backend/.env`. Frontend API settings live in `frontend/.env`.

Default local development URLs:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

The frontend defaults to `/api` and Vite proxies API traffic to Django during development.
