from contextlib import asynccontextmanager
import os
import shutil
import tempfile
import uuid

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import (
    Post,
    User,
    create_db_and_tables,
    get_async_session,
)

from backend.images import imagekit

from backend.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)

from backend.users import (
    auth_backend,
    current_active_user,
    fastapi_users,
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="SkyShare API",
    description="Backend API for SkyShare — Capture. Share. Connect. 📸🎥",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# API KEY SECURITY
# ============================================================
# SkyShare's Streamlit frontend sends this secret with every
# backend request. Keep the value in environment variables only.
# Never hard-code the real production key in source code.

API_KEY = os.getenv("API_KEY")

# These endpoints are intentionally public because Render uses
# /health for health checks and the documentation is useful for
# development/testing. All actual application API routes require
# the API key.
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    """Require the shared SkyShare API key for application routes."""

    if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    if not API_KEY:
        # Fail closed in production if the secret was not configured.
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={
                "detail": "API_KEY is not configured on the server."
            },
        )

    provided_key = request.headers.get("X-API-Key")

    if not provided_key or provided_key != API_KEY:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=403,
            content={
                "detail": "Invalid or missing API key."
            },
        )

    return await call_next(request)


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(
        UserRead,
        UserCreate,
    ),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_verify_router(
        UserRead,
    ),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(
        UserRead,
        UserUpdate,
    ),
    prefix="/users",
    tags=["users"],
)


# ============================================================
# UPLOAD
# ============================================================

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Upload an image/video to ImageKit and create its
    corresponding SkyShare post in the database.

    Rollback behavior:
    - If the ImageKit upload succeeds but database creation fails,
      attempt to delete the newly uploaded ImageKit asset.
    """

    temp_file_path = None
    imagekit_file_id = None

    try:
        # --------------------------------------------------------
        # Validate file
        # --------------------------------------------------------

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required",
            )

        # --------------------------------------------------------
        # Save uploaded file temporarily
        # --------------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1],
        ) as temp_file:
            temp_file_path = temp_file.name

            shutil.copyfileobj(
                file.file,
                temp_file,
            )

        # --------------------------------------------------------
        # Upload to ImageKit
        # --------------------------------------------------------

        with open(
            temp_file_path,
            "rb",
        ) as media_file:

            upload_result = imagekit.files.upload(
                file=media_file,
                file_name=file.filename,
                tags=["backend-upload"],
            )

        # ImageKit's upload response contains the unique asset ID.
        imagekit_file_id = upload_result.file_id

        if not imagekit_file_id:
            raise RuntimeError(
                "ImageKit upload succeeded but no file ID was returned."
            )

        # --------------------------------------------------------
        # Determine media type
        # --------------------------------------------------------

        content_type = file.content_type or ""

        if content_type.startswith("video/"):
            file_type = "video"
        else:
            file_type = "image"

        # --------------------------------------------------------
        # Create database post
        # --------------------------------------------------------

        post = Post(
            user_id=user.id,
            caption=caption.strip(),
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name,
            imagekit_file_id=imagekit_file_id,
        )

        session.add(post)

        await session.commit()
        await session.refresh(post)

        return post

    except HTTPException:
        await session.rollback()
        raise

    except Exception as exc:
        await session.rollback()

        # --------------------------------------------------------
        # Important:
        # If ImageKit upload succeeded but DB creation failed,
        # remove the orphaned ImageKit asset.
        # --------------------------------------------------------

        if imagekit_file_id:
            try:
                imagekit.files.delete(imagekit_file_id)
            except Exception:
                # Do not hide the original error if cleanup fails.
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(exc)}",
        )

    finally:
        # --------------------------------------------------------
        # Remove local temporary file
        # --------------------------------------------------------

        if (
            temp_file_path
            and os.path.exists(temp_file_path)
        ):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

        try:
            await file.close()
        except Exception:
            pass


# ============================================================
# FEED
# ============================================================

@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    Return all posts in newest-first order.
    """

    result = await session.execute(
        select(Post).order_by(
            Post.created_at.desc()
        )
    )

    posts = result.scalars().all()

    # Fetch users once instead of querying once per post.
    result = await session.execute(
        select(User)
    )

    users = result.scalars().all()

    user_dict = {
        db_user.id: db_user.email
        for db_user in users
    }

    posts_data = []

    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": (
                    post.created_at.isoformat()
                    if post.created_at
                    else None
                ),
                "is_owner": post.user_id == user.id,
                "email": user_dict.get(
                    post.user_id,
                    "Unknown",
                ),
            }
        )

    return {
        "posts": posts_data,
    }


# ============================================================
# DELETE POST
# ============================================================

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    Delete a SkyShare post and its corresponding ImageKit asset.

    Order:
    1. Validate post ID.
    2. Find post.
    3. Verify ownership.
    4. Delete ImageKit asset when its file ID is available.
    5. Delete database record.
    """

    try:
        # --------------------------------------------------------
        # Validate UUID
        # --------------------------------------------------------

        try:
            post_uuid = uuid.UUID(post_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid post ID",
            )

        # --------------------------------------------------------
        # Find post
        # --------------------------------------------------------

        result = await session.execute(
            select(Post).where(
                Post.id == post_uuid
            )
        )

        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        # --------------------------------------------------------
        # Ownership check
        # --------------------------------------------------------

        if post.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this post",
            )

        # --------------------------------------------------------
        # Delete ImageKit asset
        # --------------------------------------------------------

        if post.imagekit_file_id:
            try:
                imagekit.files.delete(
                    post.imagekit_file_id
                )
            except Exception as exc:
                # Do NOT delete the DB record if ImageKit deletion
                # failed. This prevents the two systems from drifting.
                await session.rollback()

                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Could not delete the media from ImageKit. "
                        "The post was not deleted. "
                        f"ImageKit error: {str(exc)}"
                    ),
                )

        # --------------------------------------------------------
        # Delete database record
        # --------------------------------------------------------

        await session.delete(post)
        await session.commit()

        return {
            "success": True,
            "message": "Post and media deleted successfully",
        }

    except HTTPException:
        raise

    except Exception as exc:
        await session.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(exc)}",
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """
    Simple endpoint useful for local testing and deployment
    health checks.
    """

    return {
        "status": "ok",
        "service": "SkyShare API",
        "version": "1.0.0",
    }


