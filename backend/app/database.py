"""PostgreSQL in deployment; isolated SQLite database for local demonstrations."""
import os
from sqlalchemy import create_engine, String, Text, Integer, UniqueConstraint
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool
from .settings import load_local_environment

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

def connection_url(value):
    """Accept provider URLs without requiring users to edit their passwords."""
    try:
        parsed = make_url(value)
    except ArgumentError:
        raise ValueError('Invalid database URL. Check the local or hosted environment settings.') from None
    if parsed.drivername in ('postgres', 'postgresql', 'postgresql+psycopg'):
        parsed = parsed.set(drivername='postgresql+psycopg')
        if parsed.host and parsed.host.endswith('.neon.tech'):
            mode = parsed.query.get('sslmode')
            if mode is None:
                parsed = parsed.update_query_dict({'sslmode': 'require'})
            elif mode not in ('require', 'verify-ca', 'verify-full'):
                raise ValueError('Neon connections must require TLS: use sslmode=require or a verification mode.')
    return parsed


def database(url=None):
    if url is None:
        load_local_environment()
    parsed = connection_url(url or os.getenv('DATABASE_URL', 'sqlite:///./carelink-demo.db'))
    if parsed.get_backend_name() == 'sqlite':
        engine = create_engine(parsed, connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)
    else:
        # Small reusable pool, with a liveness check after Neon has been idle.
        options = dict(connect_timeout=10, prepare_threshold=None)
        engine = create_engine(parsed, pool_pre_ping=True, pool_size=3,
                               max_overflow=2, connect_args=options)
        direct_url = os.getenv('DATABASE_URL_UNPOOLED') if url is None else None
        schema_url = connection_url(direct_url) if direct_url else parsed
        if schema_url.host and schema_url.host.endswith('.neon.tech') and '-pooler' in schema_url.host:
            engine.dispose()
            raise ValueError('Set DATABASE_URL_UNPOOLED to the direct Neon URL for initial table creation.')
        schema_engine = create_engine(schema_url, poolclass=NullPool, connect_args=options)
        try:
            # Initial schema only. Future schema upgrades require versioned migrations.
            Base.metadata.create_all(schema_engine)
        finally:
            schema_engine.dispose()
    return sessionmaker(engine, expire_on_commit=False)
