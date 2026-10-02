from collections.abc import AsyncGenerator
from datetime import datetime
import os
import uuid

from fastapi import Depends
from fastapi_users.db import (
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    inspect,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================
#
# Local development:
#     SQLite + aiosqlite
#
# Production:
#     PostgreSQL + asyncpg
#
# The DATABASE_URL environment variable is used automatically
# when deployed on Render.
#
# If DATABASE_URL is not provided, the application falls back
# to the local SQLite database.
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test.db",
)


# ============================================================
# POSTGRESQL URL COMPATIBILITY
# ============================================================
#
# Render may provide a URL beginning with:
#
#     postgresql://
# or
#     postgres://
#
# SQLAlchemy's async engine needs:
#
#     postgresql+asyncpg://
#
# Therefore, convert the URL automatically.
# ============================================================

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1,
    )


# ============================================================
# ASYNC DATABASE ENGINE
# ============================================================

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)


# ============================================================
# ASYNC SESSION MAKER
# ============================================================

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# ============================================================
# SQLALCHEMY BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# USER MODEL
# ============================================================

class User(
    SQLAlchemyBaseUserTableUUID,
    Base,
):
    posts: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# ============================================================
# POST MODEL
# ============================================================

class Post(Base):
    __tablename__ = "posts"

    # --------------------------------------------------------
    # Primary Key
    # --------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # --------------------------------------------------------
    # User Relationship
    # --------------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
    )

    # --------------------------------------------------------
    # Caption
    # --------------------------------------------------------

    caption: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # ImageKit / Media URL
    # --------------------------------------------------------

    url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # --------------------------------------------------------
    # File Type
    #
    # Examples:
    #     image
    #     video
    # --------------------------------------------------------

    file_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # --------------------------------------------------------
    # Original File Name
    # --------------------------------------------------------

    file_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # --------------------------------------------------------
    # ImageKit File ID
    #
    # This is extremely important for deletion.
    #
    # The URL is NOT enough to reliably delete a file from
    # ImageKit's Media Library.
    #
    # New posts store the ImageKit file ID here.
    #
    # Nullable=True keeps old posts compatible because posts
    # created before this column existed do not have an
    # ImageKit file ID.
    # --------------------------------------------------------

    imagekit_file_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # --------------------------------------------------------
    # Creation Timestamp
    # --------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # --------------------------------------------------------
    # Relationship Back To User
    # --------------------------------------------------------

    user: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
    )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

async def create_db_and_tables():
    """
    Create database tables if they do not already exist.

    For existing local SQLite databases, also make sure the
    imagekit_file_id column exists.

    NOTE:
    SQLAlchemy's create_all() only creates missing tables.
    It does NOT automatically add new columns to an existing
    table.
    """

    async with engine.begin() as conn:

        # ----------------------------------------------------
        # Create missing tables
        # ----------------------------------------------------

        await conn.run_sync(
            Base.metadata.create_all
        )

        # ----------------------------------------------------
        # Check whether imagekit_file_id already exists
        # ----------------------------------------------------

        def has_imagekit_file_id(sync_conn):
            columns = inspect(sync_conn).get_columns(
                "posts"
            )

            return any(
                column["name"] == "imagekit_file_id"
                for column in columns
            )

        column_exists = await conn.run_sync(
            has_imagekit_file_id
        )

        # ----------------------------------------------------
        # Add the column for older SQLite databases
        # ----------------------------------------------------

        if not column_exists:
            await conn.execute(
                text(
                    "ALTER TABLE posts "
                    "ADD COLUMN imagekit_file_id VARCHAR"
                )
            )


# ============================================================
# DATABASE SESSION DEPENDENCY
# ============================================================

async def get_async_session() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    """
    Provide an async SQLAlchemy session to FastAPI routes.
    """

    async with async_session_maker() as session:
        yield session


# ============================================================
# FASTAPI USERS DATABASE DEPENDENCY
# ============================================================

async def get_user_db(
    session: AsyncSession = Depends(
        get_async_session
    ),
):
    """
    Provide the FastAPI Users SQLAlchemy database adapter.
    """

    yield SQLAlchemyUserDatabase(
        session,
        User,
    )
