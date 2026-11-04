import asyncio
import base64
import json
import time

from google.auth import jwt
import httpx
import pytest
from sqlalchemy import func, select

from app import native_auth, social_auth
from app.database import SocialIdentity, User
from test_social_auth import client, configured, signing_key


def google_token(signing_key, **changes):
    now = int(time.time())
    return jwt.encode(signing_key, {
        'iss': 'https://accounts.google.com', 'aud': 'test-google-client',
        'azp': 'test-android-client', 'sub': 'native-google-patient',
        'iat': now - 10, 'exp': now + 600,
        'email': 'native@example.test', 'email_verified': True,
        'name': 'Native Patient', **changes,
    }).decode()


def test_native_google_verifies_signed_server_audience_and_restores_same_identity(client, monkeypatch, signing_key):
    configured(monkeypatch)
    body = {'id_token': google_token(signing_key)}
    response = client.post('/auth/social/google/native', json=body)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    result = response.json()
    assert result['user']['role'] == 'patient'
    assert 'id_token' not in result and 'email' not in result['user']
    headers = {'Authorization': 'Bearer ' + result['token']}
    assert client.get('/me', headers=headers).json()['id'] == result['user']['id']
    again = client.post('/auth/social/google/native', json=body)
    assert again.json()['user']['id'] == result['user']['id']
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(SocialIdentity)) == 1


@pytest.mark.parametrize('changed', [
    {'aud': 'other-server'}, {'iss': 'https://attacker.example'},
    {'exp': 1}, {'email_verified': False}, {'sub': ''}, {'email': ''},
])
def test_native_google_rejects_invalid_claims_without_creating_users(client, monkeypatch, signing_key, changed):
    configured(monkeypatch)
    response = client.post('/auth/social/google/native', json={'id_token': google_token(signing_key, **changed)})
    assert response.status_code == 401
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_native_google_rejects_tampered_signature_and_client_supplied_identity(client, monkeypatch, signing_key):
    configured(monkeypatch)
    token = google_token(signing_key)
    header, body, signature = token.split('.')
    claims = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
    claims['sub'] = 'forged-user'
    changed = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    assert client.post('/auth/social/google/native', json={'id_token': f'{header}.{changed}.{signature}'}).status_code == 401
    assert client.post('/auth/social/google/native', json={'id_token': token, 'email': 'forged@example.test'}).status_code == 422


def test_native_google_collision_and_disabled_user_do_not_link_accounts(client, monkeypatch, signing_key):
    configured(monkeypatch)
    password = {'name': 'Existing', 'email': 'native@example.test', 'password': 'A-long-test-password'}
    client.post('/auth/register', json=password)
    assert client.post('/auth/social/google/native', json={'id_token': google_token(signing_key)}).status_code == 409
    token = google_token(signing_key, email='different@example.test', sub='different-subject')
    result = client.post('/auth/social/google/native', json={'id_token': token}).json()
    with client.app.state.sessions() as session:
        session.get(User, result['user']['id']).enabled = 0
        session.commit()
    assert client.post('/auth/social/google/native', json={'id_token': token}).status_code == 403


@pytest.mark.parametrize('changed', [{}, {'app_id': 'wrong-app'}, {'type': 'APP'},
    {'is_valid': False}, {'expires_at': 1}, {'data_access_expires_at': 1}])
def test_native_facebook_checks_meta_token_and_only_then_reads_profile(client, monkeypatch, changed):
    configured(monkeypatch)
    real_client = httpx.AsyncClient
    calls = []
    def respond(request):
        calls.append(request)
        if request.url.path.endswith('/debug_token'):
            return httpx.Response(200, json={'data': {
                'app_id': 'test-facebook-app', 'type': 'USER', 'is_valid': True,
                'user_id': 'native-fb-user', 'expires_at': int(time.time()) + 600, **changed,
            }})
        assert request.headers['Authorization'] == 'Bearer ' + 'native-fb-token' * 3
        assert 'appsecret_proof' in request.url.params
        return httpx.Response(200, json={'id': 'native-fb-user', 'name': 'Facebook Patient'})
    monkeypatch.setattr(social_auth.httpx, 'AsyncClient', lambda **kwargs:
        real_client(transport=httpx.MockTransport(respond), **kwargs))
    response = client.post('/auth/social/facebook/native', json={'access_token': 'native-fb-token' * 3})
    assert response.status_code == (401 if changed else 200)
    assert len(calls) == (1 if changed else 2)
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(User)) == (0 if changed else 1)


def test_native_endpoints_stay_disabled_without_provider_settings(client):
    assert client.post('/auth/social/google/native', json={'id_token': 'x' * 100}).status_code == 503
    assert client.post('/auth/social/facebook/native', json={'access_token': 'x' * 100}).status_code == 503
