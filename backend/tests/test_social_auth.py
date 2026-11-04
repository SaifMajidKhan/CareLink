import asyncio
import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt
import httpx
import pytest
from sqlalchemy import func, select

from app.database import SocialFlow, SocialIdentity, User
from app.main import create_app
from app import social_auth
from app.security import digest


VERIFIER = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
CHALLENGE = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'


@pytest.fixture
def client(tmp_path, monkeypatch):
    for key in ('PUBLIC_API_URL', 'RENDER_EXTERNAL_URL', 'GOOGLE_CLIENT_ID',
                'GOOGLE_CLIENT_SECRET', 'FACEBOOK_APP_ID', 'FACEBOOK_APP_SECRET',
                'FACEBOOK_GRAPH_VERSION'):
        monkeypatch.delenv(key, raising=False)
    return TestClient(create_app('sqlite:///' + str(tmp_path / 'auth.db')))


def configured(monkeypatch):
    for key, value in {
        'PUBLIC_API_URL': 'https://api.example.test',
        'GOOGLE_CLIENT_ID': 'test-google-client', 'GOOGLE_CLIENT_SECRET': 'test-secret',
        'FACEBOOK_APP_ID': 'test-facebook-app', 'FACEBOOK_APP_SECRET': 'test-secret',
        'FACEBOOK_GRAPH_VERSION': 'v24.0',
    }.items():
        monkeypatch.setenv(key, value)


def start(client, provider='google'):
    response = client.post(f'/auth/social/{provider}/start', json={'code_challenge': CHALLENGE})
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    return response.json()


def finish(client, started, provider='google'):
    response = client.get(f'/auth/social/{provider}/callback',
        params={'state': started['state'], 'code': 'upstream-test-code'}, follow_redirects=False)
    assert response.status_code == 303, response.text
    url = urlsplit(response.headers['location'])
    assert url.scheme == 'carelink' and url.netloc == 'auth' and url.path == '/callback'
    params = {key: value[0] for key, value in parse_qs(url.query).items()}
    assert 'token' not in params
    return params


async def identity(*args):
    return {'subject': 'provider-patient-1', 'email': 'member@example.test', 'name': 'Member'}


def test_unconfigured_providers_cannot_pretend_to_sign_in(client):
    assert client.get('/auth/providers').json() == {
        'google': {'available': False, 'native_available': False},
        'facebook': {'available': False, 'native_available': False}}
    assert client.post('/auth/social/google/start', json={'code_challenge': CHALLENGE}).status_code == 503
    assert client.post('/auth/social/unknown/start', json={'code_challenge': CHALLENGE}).status_code == 404


@pytest.mark.parametrize('provider', ['google', 'facebook'])
def test_social_sign_in_handoff_is_one_time_and_patient_only(client, monkeypatch, provider):
    configured(monkeypatch)
    monkeypatch.setattr(social_auth, 'fetch_identity', identity)
    first = start(client, provider)
    params = parse_qs(urlsplit(first['authorization_url']).query)
    assert params['redirect_uri'] == [f'https://api.example.test/auth/social/{provider}/callback']
    if provider == 'google':
        assert params['code_challenge_method'] == ['S256'] and 'nonce' in params
    handoff = finish(client, first, provider)
    response = client.post('/auth/social/exchange', json={**handoff, 'code_verifier': VERIFIER})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['user']['role'] == 'patient'
    assert client.get('/me', headers={'Authorization': 'Bearer ' + result['token']}).status_code == 200
    assert client.post('/auth/social/exchange', json={**handoff, 'code_verifier': VERIFIER}).status_code == 400
    assert client.get(f'/auth/social/{provider}/callback', params={
        'state': first['state'], 'code': 'replayed-code'}, follow_redirects=False).status_code == 400
    # A new sign-in with the same provider subject returns the same account.
    second = finish(client, start(client, provider), provider)
    again = client.post('/auth/social/exchange', json={**second, 'code_verifier': VERIFIER})
    assert again.json()['user']['id'] == result['user']['id']
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(SocialIdentity)) == 1


def test_pkce_wrong_state_expiry_and_open_redirect_are_rejected(client, monkeypatch):
    configured(monkeypatch)
    monkeypatch.setattr(social_auth, 'fetch_identity', identity)
    assert social_auth.pkce_challenge(VERIFIER) == CHALLENGE
    assert client.post('/auth/social/google/start', json={
        'code_challenge': CHALLENGE, 'redirect_uri': 'https://attacker.example'}).status_code == 422
    first = start(client)
    assert client.get('/auth/social/google/callback', params={
        'state': 'x' * 43, 'code': 'code'}, follow_redirects=False).status_code == 400
    handoff = finish(client, first)
    assert client.post('/auth/social/exchange', json={**handoff, 'code_verifier': 'x' * 43}).status_code == 400
    assert client.post('/auth/social/exchange', json={**handoff, 'code_verifier': VERIFIER}).status_code == 200
    expired = start(client)
    with client.app.state.sessions() as session:
        session.get(SocialFlow, digest(expired['state'])).expires = int(time.time()) - 1
        session.commit()
    assert client.get('/auth/social/google/callback', params={
        'state': expired['state'], 'code': 'code'}, follow_redirects=False).status_code == 400


def test_email_collision_never_links_or_takes_over_existing_account(client, monkeypatch):
    configured(monkeypatch)
    monkeypatch.setattr(social_auth, 'fetch_identity', identity)
    original = client.post('/auth/register', json={'name': 'Existing Member',
        'email': 'member@example.test', 'password': 'Existing-password-123'}).json()
    failed = finish(client, start(client))
    assert failed['error'] == 'email_in_use' and 'code' not in failed
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(SocialIdentity)) == 0
        assert session.get(User, original['user']['id']).name == 'Existing Member'


def test_cancelled_provider_and_disabled_account_fail_closed(client, monkeypatch):
    configured(monkeypatch)
    monkeypatch.setattr(social_auth, 'fetch_identity', identity)
    cancelled = start(client)
    response = client.get('/auth/social/google/callback', params={
        'state': cancelled['state'], 'error': 'access_denied'}, follow_redirects=False)
    assert parse_qs(urlsplit(response.headers['location']).query)['error'] == ['cancelled']
    ready = finish(client, start(client))
    with client.app.state.sessions() as session:
        flow = session.get(SocialFlow, digest(ready['state']))
        session.get(User, flow.user_id).enabled = 0
        session.commit()
    assert client.post('/auth/social/exchange', json={**ready, 'code_verifier': VERIFIER}).status_code == 403


def test_registration_validation_and_normalization(client):
    body = {'name': 'Member', 'email': 'member@example.test', 'password': 'short'}
    response = client.post('/auth/register', json=body)
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'] == ['body', 'password']
    body['password'] = 'A-long-test-password'
    body['email'] = '  MEMBER@EXAMPLE.TEST  '
    assert client.post('/auth/register', json=body).status_code == 201
    assert client.post('/auth/login', json={
        'email': 'member@example.test', 'password': body['password']}).status_code == 200
    for email in ['bad@name@host.com', 'invalid address@example.com', 'bad-email']:
        assert client.post('/auth/register', json={**body, 'email': email}).status_code == 422
    assert client.post('/auth/register', json={**body, 'name': '   '}).status_code == 422


@pytest.fixture
def signing_key(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    def request(*args, **kwargs):
        return SimpleNamespace(status=200, data=json.dumps({'test-key': public}).encode())
    monkeypatch.setattr(social_auth, 'GoogleRequest', lambda: request)
    return crypt.RSASigner.from_string(private, key_id='test-key')


@pytest.mark.parametrize('changed', [{}, {'aud': 'wrong-client'}, {'iss': 'https://attacker.example'},
    {'exp': 1}, {'nonce': 'wrong-nonce'}, {'email_verified': False}, {'azp': 'other-client'}])
def test_google_verification_uses_signature_audience_issuer_expiry_and_nonce(signing_key, changed):
    now = int(time.time())
    claims = {'iss': 'https://accounts.google.com', 'aud': 'test-client', 'sub': 'google-subject',
              'iat': now - 10, 'exp': now + 600, 'nonce': 'expected-nonce',
              'email': 'google@example.test', 'email_verified': True, **changed}
    token = jwt.encode(signing_key, claims).decode()
    if not changed:
        assert social_auth.verify_google_token(token, 'test-client', 'expected-nonce')['subject'] == 'google-subject'
    else:
        with pytest.raises((ValueError, social_auth.google_errors.GoogleAuthError)):
            social_auth.verify_google_token(token, 'test-client', 'expected-nonce')


def test_google_rejects_forged_signature(signing_key):
    now = int(time.time())
    token = jwt.encode(signing_key, {'iss': 'https://accounts.google.com', 'aud': 'test-client',
        'sub': 'real-subject', 'iat': now - 10, 'exp': now + 600, 'nonce': 'nonce',
        'email': 'google@example.test', 'email_verified': True}).decode()
    header, body, signature = token.split('.')
    # Change signed claims while keeping the genuine signature.
    import base64
    claims = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
    claims['sub'] = 'forged-subject'
    changed = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    with pytest.raises(ValueError):
        social_auth.verify_google_token(f'{header}.{changed}.{signature}', 'test-client', 'nonce')


@pytest.mark.parametrize('changed', [{}, {'app_id': 'wrong-app'}, {'expires_at': 1},
    {'type': 'APP'}, {'is_valid': False}, {'data_access_expires_at': 1}])
def test_facebook_checks_token_app_user_expiry_and_proof(monkeypatch, changed):
    real_client = httpx.AsyncClient
    requests = []
    def respond(request):
        requests.append(request)
        if request.url.path.endswith('/oauth/access_token'):
            return httpx.Response(200, json={'access_token': 'test-provider-token'})
        if request.url.path.endswith('/debug_token'):
            return httpx.Response(200, json={'data': {'is_valid': True, 'type': 'USER',
                'app_id': 'test-facebook-app', 'user_id': 'fb-user',
                'expires_at': int(time.time()) + 600, **changed}})
        assert request.headers['Authorization'] == 'Bearer test-provider-token'
        assert 'appsecret_proof' in request.url.params
        return httpx.Response(200, json={'id': 'fb-user', 'name': 'Member'})
    monkeypatch.setattr(social_auth.httpx, 'AsyncClient', lambda **kwargs:
        real_client(transport=httpx.MockTransport(respond), **kwargs))
    config = social_auth.Provider('facebook', 'test-facebook-app', 'test-secret',
        'https://api.example.test', 'v24.0')
    operation = social_auth.fetch_identity(config, 'test-code', SimpleNamespace())
    if changed:
        with pytest.raises(ValueError): asyncio.run(operation)
        assert len(requests) == 2
    else:
        result = asyncio.run(operation)
        assert result['subject'] == 'fb-user' and result['email'] == ''
