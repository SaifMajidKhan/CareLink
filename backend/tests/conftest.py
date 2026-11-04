"""Keep ordinary tests isolated even when Neon credentials exist locally."""
import os

# app.main exposes an ASGI app at import time. Its bootstrap must never use Neon
# when collecting the normal unit/workflow tests.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('DATABASE_URL_UNPOOLED', None)
