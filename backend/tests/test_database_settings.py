import os
from unittest.mock import patch

import pytest

from app.database import connection_url
from app.settings import load_local_environment


def test_neon_url_uses_existing_psycopg_driver_and_preserves_credentials():
    url = connection_url('postgresql://tester:p%40ss%2Fword@ep-demo-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
    assert url.drivername == 'postgresql+psycopg'
    assert url.password == 'p@ss/word'
    assert url.query['sslmode'] == 'require'
    assert url.query['channel_binding'] == 'require'


def test_neon_defaults_to_tls_but_does_not_weaken_certificate_verification():
    base = 'postgres://tester:example@ep-demo.aws.neon.tech/neondb'
    assert connection_url(base).query['sslmode'] == 'require'
    assert connection_url(base + '?sslmode=verify-full').query['sslmode'] == 'verify-full'


def test_neon_rejects_plaintext_connections():
    with pytest.raises(ValueError, match='must require TLS'):
        connection_url('postgresql://tester:example@ep-demo.aws.neon.tech/neondb?sslmode=disable')


def test_invalid_url_error_does_not_echo_the_secret():
    with pytest.raises(ValueError) as error:
        connection_url('not-a-url-private-password')
    assert 'private-password' not in str(error.value)


def test_local_env_precedence_and_process_override(tmp_path):
    (tmp_path / 'backend').mkdir()
    (tmp_path / '.env.local').write_text('CARELINK_TEST_VALUE=neon\nCARELINK_TEST_OTHER=root\n', encoding='utf-8')
    (tmp_path / 'backend' / '.env.local').write_text('CARELINK_TEST_VALUE=backend\n', encoding='utf-8')
    with patch.dict(os.environ, {}, clear=True):
        load_local_environment(tmp_path)
        assert os.environ['CARELINK_TEST_VALUE'] == 'backend'
        assert os.environ['CARELINK_TEST_OTHER'] == 'root'
        os.environ['CARELINK_TEST_VALUE'] = 'hosted'
        load_local_environment(tmp_path)
        assert os.environ['CARELINK_TEST_VALUE'] == 'hosted'
