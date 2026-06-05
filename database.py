from sqlalchemy.orm import sessionmaker

from models import engine

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)