# SkyShare — Capture. Share. Connect. 📸🎥

A simple photo/video sharing application built for development and testing.

**Current stack**
- Backend: FastAPI + FastAPI Users + SQLAlchemy async
- Database: SQLite for the current testing phase
- Media storage: ImageKit
- Frontend: Streamlit
- Authentication: JWT bearer tokens

**Credit:** Built by **Akash Kumar Saw**.

---

## 1. Project structure

```text
SkyShare/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── db.py
│   ├── images.py
│   ├── schemas.py
│   └── users.py
├── frontend/
│   └── streamlit_app.py
├── .env.example
├── .gitignore
├── .streamlit.example.toml
├── requirements.txt
└── README.md
```

---

## 2. Local setup

### Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Copy `.env.example` to `.env` and set at least:

```env
JWT_SECRET=your-testing-secret
IMAGEKIT_PRIVATE_KEY=your_imagekit_private_key
```

The SQLite database is created automatically on first backend startup.

---

## 3. Run the backend

From the project root:

```bash
uvicorn backend.app:app --reload --port 8000
```

API:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

---

## 4. Run the Streamlit frontend

In a second terminal:

```bash
streamlit run frontend/streamlit_app.py
```

If you use `.streamlit/secrets.toml`, create the folder and file:

```text
.streamlit/
└── secrets.toml
```

with:

```toml
API_URL = "http://127.0.0.1:8000"
```

The frontend supports:

- Account registration
- JWT login/logout
- Photo upload
- Video upload
- Captions
- Community feed
- Owner-only post deletion
- Responsive Streamlit layout
- Your creator credit in the UI

---

## 5. ImageKit

Create an ImageKit account and copy your server-side private key into `.env`:

```env
IMAGEKIT_PRIVATE_KEY=private_xxxxxxxxx
```

Do **not** put the private key into Streamlit secrets or browser-side code unless the backend is also running there. The Streamlit app sends media to the FastAPI backend, and the backend uploads it to ImageKit.

---

## 6. Streamlit deployment architecture for this phase

For this version, Streamlit is the frontend. The FastAPI API still needs to be reachable at a public URL.

```text
User Browser
     │
     ▼
Streamlit Cloud
     │
     │ HTTPS API requests
     ▼
FastAPI Backend
     │
     ├── SQLite (current testing setup)
     │
     └── ImageKit (media)
```

For local testing, Streamlit calls `http://127.0.0.1:8000`.

For Streamlit Cloud, set the Streamlit secret:

```toml
API_URL = "https://YOUR-BACKEND-URL"
```

The backend therefore cannot be reached through Streamlit Cloud alone; it needs its own reachable backend process/server.

---

## 7. Current testing vs later production work

This package intentionally keeps the current setup simple so you can finish testing features first.

Later, when moving to the React version, the planned upgrade is:

```text
React / Vite → FastAPI → PostgreSQL
                     ↓
                  ImageKit
```

At that stage, switch SQLite to PostgreSQL, use Alembic migrations, lock CORS to the React domain, move the production JWT secret to deployment secrets, add media cleanup, and deploy the React frontend separately.

