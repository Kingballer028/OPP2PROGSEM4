from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL for PostgreSQL
DATABASE_URL = "postgresql://postgres:alpha@localhost/FitnessTracker"

# Create Engine
engine = create_engine(DATABASE_URL)

# Create SessionLocal for transaction sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()

# Dependency helper to inject DB session context in routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
