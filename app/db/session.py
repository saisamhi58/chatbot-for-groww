"""Database session management."""

from app.models.database import SessionLocal, engine, Base


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()
