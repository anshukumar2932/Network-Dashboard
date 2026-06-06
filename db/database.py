from sqlalchemy.orm import sessionmaker

from db.models import engine

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)