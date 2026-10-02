# ☁️ SkyShare

### Capture. Share. Connect. 📸🎥

**SkyShare** is a full-stack photo and video sharing platform built to provide a simple, visual space where users can create accounts, upload media, browse a community feed, and manage their own posts.

This project is the **v1 production release** of SkyShare, built with a Python/FastAPI backend, PostgreSQL, ImageKit, and a Streamlit frontend.

---

## ✨ Features

- 🔐 User registration and JWT authentication
- 👤 Authenticated user sessions
- 📸 Image uploads
- 🎥 Video uploads
- 📝 Captions for posts
- 🏠 Community feed with newest posts first
- 👤 Post ownership information
- 🗑️ Delete your own posts
- ☁️ Cloud media storage through ImageKit
- 🗄️ PostgreSQL database for production
- 🔒 Protected API using a private API key
- 🔑 JWT-based user authorization
- ♻️ ImageKit cleanup when posts are deleted
- 🧹 Rollback handling for failed uploads
- ❤️ Clean, simple Streamlit interface
- 🚀 Production deployment with Render + Streamlit Community Cloud

---

## 🏗️ Architecture

```text
                         ┌─────────────────────────┐
                         │   Streamlit Community   │
                         │         Cloud           │
                         │       Frontend          │
                         └────────────┬────────────┘
                                      │
                              HTTPS + API Key
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │         Render          │
                         │       FastAPI API       │
                         └───────┬─────────┬───────┘
                                 │         │
                       PostgreSQL│         │ImageKit
                                 │         │
                                 ▼         ▼
                         ┌───────────┐  ┌───────────┐
                         │ PostgreSQL│  │  ImageKit │
                         │ Database  │  │   Media   │
                         └───────────┘  └───────────┘
```

### Request flow

```text
User
 │
 ▼
Streamlit Frontend
 │
 │ X-API-Key
 │ Authorization: Bearer <JWT>
 ▼
FastAPI Backend
 │
 ├── Authentication
 ├── Authorization
 ├── Post management
 │
 ├──────────────► PostgreSQL
 │
 └──────────────► ImageKit
```

---

## 🛠️ Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| Python | Application language |
| Streamlit | Frontend/UI |
| Requests | HTTP API communication |
| python-dotenv | Local environment configuration |

### Backend

| Technology | Purpose |
|---|---|
| Python | Backend language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| FastAPI Users | Authentication and user management |
| SQLAlchemy | ORM |
| Pydantic | Data validation |
| python-multipart | File/form uploads |

### Database

| Technology | Purpose |
|---|---|
| PostgreSQL | Production database |
| SQLite | Local development/testing |
| asyncpg | Async PostgreSQL driver |
| aiosqlite | Async SQLite driver |

### Media Storage

| Technology | Purpose |
|---|---|
| ImageKit | Image/video storage and delivery |

### Development & Deployment

| Tool | Purpose |
|---|---|
| uv | Python package and project management |
| Git | Version control |
| GitHub | Source code hosting |
| Render | FastAPI + PostgreSQL deployment |
| Streamlit Community Cloud | Frontend deployment |

---

## 📁 Project Structure

```text
skyshare_v1/
│
├── backend/
│   ├── __init__.py
│   ├── app.py              # FastAPI application and API routes
│   ├── db.py               # Database models and SQLAlchemy setup
│   ├── images.py           # ImageKit configuration
│   ├── schemas.py          # Pydantic/FastAPI schemas
│   └── users.py            # Authentication and user configuration
│
├── frontend/
│   ├── streamlit_app.py    # Streamlit application
│   └── skyshare_logo.png   # SkyShare branding
│
├── .env                    # Local environment variables
├── .gitignore
├── .python-version
├── .streamlit.example.toml
├── main.py
├── pyproject.toml
├── requirements.txt
├── uv.lock
└── README.md
```

> `.env`, databases, virtual environments, and other sensitive/local files are excluded from Git through `.gitignore`.

---

## 🔐 Authentication

SkyShare uses **JWT authentication** through FastAPI Users.

### Authentication endpoints

```text
POST /auth/register
POST /auth/jwt/login
POST /auth/reset-password
POST /auth/verify
```

### User endpoint

```text
GET /users/me
```

Authenticated requests use:

```http
Authorization: Bearer <access_token>
```

---

## 🔌 API

### Health

```http
GET /health
```

Returns the API health status.

Example:

```json
{
  "status": "ok",
  "service": "SkyShare API",
  "version": "1.0.0"
}
```

### Feed

```http
GET /feed
```

Returns posts in newest-first order.

### Upload

```http
POST /upload
```

Accepts:

- image/video file
- caption

The media is uploaded to ImageKit and the post metadata is stored in PostgreSQL.

### Delete Post

```http
DELETE /posts/{post_id}
```

A user can delete only their own post.

The backend also removes the corresponding ImageKit asset.

---

## 🗄️ Data Model

The main entities in the current v1 database are:

```text
User
 │
 └──< Post
```

A `Post` contains information such as:

```text
id
user_id
caption
url
file_type
file_name
imagekit_file_id
created_at
```

The `imagekit_file_id` is stored so that the corresponding cloud media can be deleted when a post is removed.

---

## 🔒 API Security

SkyShare v1 uses two complementary security mechanisms.

### 1. API Key

The Streamlit frontend sends a private API key with requests:

```http
X-API-Key: <API_KEY>
```

The same secret is stored as an environment variable on Render and as a Streamlit secret.

### 2. JWT Authentication

User-specific operations additionally use JWT authentication:

```http
Authorization: Bearer <JWT>
```

This gives the application two layers:

```text
API Key
   ↓
Trusted application client

JWT
   ↓
Authenticated SkyShare user
```

> The API key must never be committed to GitHub or exposed in client-side code.

---

## ⚙️ Environment Variables

### Backend — Render

```env
DATABASE_URL=...
IMAGEKIT_PRIVATE_KEY=...
IMAGE_PUBLIC_KEY=...
IMAGEKIT_URL=...
JWT_SECRET=...
API_KEY=...
```

### Frontend — Streamlit Community Cloud

```toml
API_URL = "https://your-skyshare-api.onrender.com"
API_KEY = "your-private-api-key"
```

### Local development

Create a `.env` file:

```env
DATABASE_URL=sqlite+aiosqlite:///./test.db

IMAGEKIT_PRIVATE_KEY=...
IMAGE_PUBLIC_KEY=...
IMAGEKIT_URL=...

JWT_SECRET=...
API_KEY=...

API_URL=http://127.0.0.1:8000
```

Never commit `.env` to GitHub.

---

## 🚀 Local Development

### 1. Clone the repository

```bash
git clone https://github.com/aako-aakash/skyshare-v1.git
cd skyshare-v1
```

### 2. Install dependencies

If you use `uv`:

```bash
uv sync
```

Or install from the requirements file:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create:

```text
.env
```

and add the required variables.

### 4. Start the FastAPI backend

```bash
uv run uvicorn backend.app:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start Streamlit

Open another terminal:

```bash
uv run streamlit run frontend/streamlit_app.py
```

The Streamlit application will open in your browser.

---

## ☁️ Production Deployment

SkyShare v1 uses the following production architecture:

```text
Streamlit Community Cloud
        │
        ▼
Render FastAPI
        │
        ├── Render PostgreSQL
        │
        └── ImageKit
```

### Backend

The FastAPI backend is deployed on **Render**.

Production server command:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

### Database

The production application uses PostgreSQL.

The Render service receives the database connection through:

```env
DATABASE_URL
```

### Frontend

The Streamlit frontend is deployed through **Streamlit Community Cloud**.

It communicates with the deployed FastAPI backend using:

```env
API_URL
```

---

## 🔄 Upload Reliability

SkyShare includes cleanup logic to prevent orphaned media.

The upload flow is:

```text
Upload file
     │
     ▼
Temporary local file
     │
     ▼
Upload to ImageKit
     │
     ▼
Receive ImageKit file ID
     │
     ▼
Create PostgreSQL post
     │
     ├── Success ──► Keep media + database record
     │
     └── Failure ──► Delete ImageKit asset
```

This keeps the database and media storage synchronized as much as possible.

---

## 🗑️ Post Deletion

Deleting a post follows this flow:

```text
User requests deletion
        │
        ▼
Validate post ID
        │
        ▼
Find post
        │
        ▼
Verify ownership
        │
        ▼
Delete ImageKit asset
        │
        ▼
Delete database record
        │
        ▼
Success
```

If ImageKit deletion fails, the database post is preserved instead of silently creating an inconsistent state.

---

## 🎯 Current Scope — v1

SkyShare v1 intentionally focuses on the core media-sharing experience:

- Authentication
- User accounts
- Photo sharing
- Video sharing
- Captions
- Community feed
- Post ownership
- Post deletion
- Cloud media storage
- Production deployment

The following are **not implemented in v1**:

- Likes
- Comments
- Followers/following
- Notifications
- Messaging
- Stories
- Reels
- Search
- Bookmarks
- Recommendation systems
- AI-powered features

These can be introduced in future versions.

---

## 🗺️ Future Roadmap

Potential future improvements for SkyShare include:

```text
v2
├── React + TypeScript frontend
├── Modern responsive UI
├── Profile pages
├── My Posts
├── Likes
├── Comments
├── Follow / Following
├── Search
├── Notifications
├── Bookmarks
└── Improved media experience

Future
├── AI captions
├── AI image tagging
├── Content recommendations
├── Real-time notifications
├── Messaging
└── Advanced media processing
```

---

## 📌 Project Status

**SkyShare v1 — Production MVP**

The current release demonstrates a complete full-stack workflow:

```text
Authentication
      ↓
Frontend
      ↓
FastAPI API
      ↓
PostgreSQL
      +
ImageKit
      ↓
Production Deployment
```

The project is intentionally kept focused so that the foundation can be extended into a larger social-media platform in future versions.

---

## 👨‍💻 Credits

### Built by **Akash Kumar Saw**

**Computer Science Engineer | AI & ML**

- GitHub: [@aako-aakash](https://github.com/aako-aakash)
- LinkedIn: [Akash Kumar Saw](https://www.linkedin.com/in/aako-aakash/)

### SkyShare

> **Capture. Share. Connect. 📸🎥**

Designed, developed, and deployed by **AAKASH**.

---

## 📄 License

This project is currently maintained as a personal/project portfolio application.

See the repository for the applicable licensing terms.
