"""PostgreSQL in deployment; isolated SQLite database for local demonstrations."""
import os
from sqlalchemy import create_engine, String, Text, Integer, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20))
    condition: Mapped[str] = mapped_column(String(40), default='')
    enabled: Mapped[int] = mapped_column(Integer, default=1)

class SessionToken(Base):
    __tablename__ = 'sessions'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    expires: Mapped[str] = mapped_column(String(40))

class Connection(Base):
    __tablename__ = 'connections'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    patient: Mapped[str] = mapped_column(String(40), index=True)
    caregiver: Mapped[str] = mapped_column(String(40), index=True)
    state: Mapped[str] = mapped_column(String(20), default='pending')
    created: Mapped[str] = mapped_column(String(40))

class Record(Base):
    __tablename__ = 'records'
    __table_args__ = (UniqueConstraint('owner', 'kind', 'key'),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    key: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created: Mapped[str] = mapped_column(String(40))

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    actor: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(160))
    at: Mapped[str] = mapped_column(String(40))
    previous: Mapped[str] = mapped_column(Text, default='')

def database(url=None):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///./carelink-demo.db')
    engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {})
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
