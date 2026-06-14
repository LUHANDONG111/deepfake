# Deepfake Video Detection System

Flask + SQLite API service with a Vue 3 administration console for visual deepfake video detection.

## Project Layout

```text
backend/   Flask API, SQLite models, detection pipeline, tests, migrations
frontend/  Vue 3 + Vite + Element Plus administration console
```

## Features

- Account login with JWT Bearer authentication
- Admin-created users with `admin` and `user` roles
- MP4 upload, detection progress polling, result review, CSV report download
- Personal history for normal users
- Global task and user management for administrators
- SQLite persistence with Flask-Migrate support

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The backend runs at http://127.0.0.1:5000.

The system does not create a default administrator. On the first deployment, open the frontend and create the first administrator account from the initialization form. After any user exists, the initialization endpoint closes automatically.

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The Vue console runs at http://127.0.0.1:5173 and calls the Flask API on http://127.0.0.1:5000.

To point the frontend at a different API host:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:5000"
npm run dev
```

## Environment Variables

- `JWT_SECRET_KEY`: JWT signing secret; falls back to `SECRET_KEY`
- `DATABASE_URL`: SQLAlchemy database URL
- `UPLOAD_FOLDER`: uploaded MP4 storage directory
- `REPORT_FOLDER`: generated CSV report directory
- `MODEL_PATH`: model weights path

## Database Migrations

The app includes Flask-Migrate support:

```powershell
cd backend
flask --app app:create_app db migrate -m "describe change"
flask --app app:create_app db upgrade
```

For compatibility with the existing MVP SQLite database, startup also adds the `task_sessions.user_id` column when it is missing. Old anonymous tasks are assigned to the first administrator created during initial setup.

## Tests

```powershell
cd backend
python -m pytest
cd ..\frontend
npm run build
```

The Xception classifier remains exposed through a replaceable classifier interface; place future model-loading code in `inference/classifier.py` without changing the API or UI.
