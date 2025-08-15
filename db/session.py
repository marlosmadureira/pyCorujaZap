from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from contextlib import contextmanager

load_dotenv()
# Pega a URL do PostgreSQL nas variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Cria engine
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Cria sessão
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

@contextmanager
def get_session():

    session = SessionLocal()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()

    finally:
        session.close()