"""Browser OAuth with a short-lived, PKCE-bound handoff to the Android app.

Provider secrets and provider tokens stay on the server. No account is linked
by matching an email address; returning users are identified by provider/sub.
"""
import base64
from dataclasses import dataclass
import hashlib
import hmac
import os
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth import exceptions as google_errors
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
import httpx
from pydantic import Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from .database import SocialFlow, SocialIdentity, User
from .schemas import BaseModel
from .security import digest, password_hash


APP_CALLBACK = 'carelink://auth/callback'
PRIVATE_HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}


class SocialStart(BaseModel):
    code_challenge: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')


class SocialExchange(BaseModel):
    state: str = Field(min_length=32, max_length=128)
    code: str = Field(min_length=32, max_length=128)
    code_verifier: str = Field(pattern=r'^[A-Za-z0-9._~-]{43,128}$')


@dataclass(frozen=True)
class Provider:
    name: str
    client_id: str
    secret: str
    base: str
    version: str = ''

    @property
    def available(self):
        uri = urlsplit(self.base)
        valid_base = (uri.scheme == 'https' and uri.hostname and not uri.username
                      and not uri.password and not uri.query and not uri.fragment
                      and not uri.path)
        valid_version = self.name != 'facebook' or bool(re.fullmatch(r'v\d+\.\d+', self.version))
        return bool(self.client_id and self.secret and valid_base and valid_version)

    @property
    def callback(self):
        return f'{self.base}/auth/social/{self.name}/callback'


def provider_settings(name):
    if name not in ('google', 'facebook'):
        raise HTTPException(404, 'Sign-in option not found')
    base = (os.getenv('PUBLIC_API_URL') or os.getenv('RENDER_EXTERNAL_URL', '')).strip().rstrip('/')
    if name == 'google':
        return Provider(name, os.getenv('GOOGLE_CLIENT_ID', '').strip(),
                        os.getenv('GOOGLE_CLIENT_SECRET', '').strip(), base)
    return Provider(name, os.getenv('FACEBOOK_APP_ID', '').strip(),
                    os.getenv('FACEBOOK_APP_SECRET', '').strip(), base,
                    os.getenv('FACEBOOK_GRAPH_VERSION', '').strip())


def pkce_challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')


def authorization_url(config, state, nonce, verifier):
    params = dict(client_id=config.client_id, redirect_uri=config.callback,
                  response_type='code', state=state)
    if config.name == 'google':
        params.update(scope='openid email profile', nonce=nonce, prompt='select_account',
                      code_challenge=pkce_challenge(verifier), code_challenge_method='S256')
        endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
    else:
        params.update(scope='email,public_profile')
        endpoint = f'https://www.facebook.com/{config.version}/dialog/oauth'
    return endpoint + '?' + urlencode(params)


def _google_claims(token, client_id):
    transport = GoogleRequest()
    def bounded_request(*args, **kwargs):
        kwargs['timeout'] = 15
        return transport(*args, **kwargs)
    # The official library verifies signature, issuer, audience and expiry.
    claims = google_id_token.verify_oauth2_token(token, bounded_request, audience=client_id)
    if (claims.get('email_verified') is not True
            or not isinstance(claims.get('sub'), str)
            or not claims['sub']
            or not isinstance(claims.get('email'), str)
            or not claims['email']):
        raise ValueError('Unverified Google identity')
    return claims


def _google_identity(claims):
    return {'subject': claims['sub'], 'email': claims['email'], 'name': claims.get('name', '')}


def verify_google_token(token, client_id, nonce):
    claims = _google_claims(token, client_id)
    if (not isinstance(claims.get('nonce'), str)
            or not hmac.compare_digest(claims['nonce'], nonce)
            or (claims.get('azp') is not None and claims['azp'] != client_id)
            or claims.get('email_verified') is not True):
        raise ValueError('Unverified Google identity')
    return _google_identity(claims)


def verify_google_native_token(token, client_id):
    # Native SDK ID tokens are credentials sent directly over HTTPS. Verify the
    # server audience with Google's library; the Android authorized party can
    # differ from the Web client ID. Browser nonce/azp checks stay above.
    return _google_identity(_google_claims(token, client_id))


async def _facebook_identity(client, config, token):
    root = f'https://graph.facebook.com/{config.version}'
    inspected = await client.get(root + '/debug_token',
        params={'input_token': token},
        headers={'Authorization': f'Bearer {config.client_id}|{config.secret}'})
    inspected.raise_for_status()
    checked = inspected.json()['data']
    if (checked.get('is_valid') is not True
            or str(checked.get('app_id')) != config.client_id
            or checked.get('type') != 'USER'
            or not checked.get('user_id')
            or checked.get('expires_at', 0) <= time.time()
            or (checked.get('data_access_expires_at') and checked['data_access_expires_at'] <= time.time())):
        raise ValueError('Unverified Facebook identity')
    proof = hmac.new(config.secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    profile = await client.get(root + '/me',
        params={'fields': 'id,name,email', 'appsecret_proof': proof},
        headers={'Authorization': f'Bearer {token}'})
    profile.raise_for_status()
    result = profile.json()
    if str(result.get('id')) != str(checked['user_id']):
        raise ValueError('Facebook identity mismatch')
    return {'subject': str(result['id']), 'name': result.get('name', ''),
            'email': result.get('email', '')}


async def verify_facebook_native_token(config, token):
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        return await _facebook_identity(client, config, token)


async def fetch_identity(config, code, flow):
    """Fixed provider endpoints only; never accept an upstream URL from the app."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        fields = dict(client_id=config.client_id, client_secret=config.secret,
                      redirect_uri=config.callback, code=code)
        if config.name == 'google':
            response = await client.post('https://oauth2.googleapis.com/token', data={
                **fields, 'grant_type': 'authorization_code', 'code_verifier': flow.provider_verifier,
            })
            response.raise_for_status()
            token = response.json()['id_token']
            return await run_in_threadpool(verify_google_token, token, config.client_id, flow.nonce)
        root = f'https://graph.facebook.com/{config.version}'
        # Meta's documented server-side code exchange is an HTTPS GET.
        response = await client.get(root + '/oauth/access_token', params=fields)
        response.raise_for_status()
        token = response.json()['access_token']
        return await _facebook_identity(client, config, token)


def patient_for_identity(session, provider, identity):
    subject = identity.get('subject')
    if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
        raise ValueError('Invalid provider subject')
    linked = session.scalar(select(SocialIdentity).where(
        SocialIdentity.provider == provider, SocialIdentity.subject == subject))
    if linked:
        user = session.get(User, linked.user_id)
        if not user or not user.enabled or user.role != 'patient':
            raise HTTPException(403, 'account_unavailable')
        return user
    email = str(identity.get('email') or '').strip().lower()
    if email and (len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
        raise ValueError('Invalid provider email')
    # Facebook can withhold email. A reserved internal identifier is never used
    # as a deliverable email address or to match an existing email account.
    if not email:
        email = f'{provider}-{uuid.uuid4().hex}@identity.carelink.invalid'
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'email_in_use')
    name = str(identity.get('name') or '').strip()[:80] or 'CareLink member'
    user = User(id='CL-' + secrets.token_hex(8).upper(), email=email, name=name,
                password=password_hash(secrets.token_urlsafe(48)), role='patient')
    session.add(user)
    session.add(SocialIdentity(id=str(uuid.uuid4()), provider=provider,
                               subject=subject, user_id=user.id))
    session.flush()
    return user


def mobile_redirect(state, **fields):
    return RedirectResponse(APP_CALLBACK + '?' + urlencode({'state': state, **fields}),
                            status_code=303, headers=PRIVATE_HEADERS)


def register_social_routes(app, sessions, limiter, login_result):
    router = APIRouter(prefix='/auth', tags=['Sign-in'])

    def db():
        with sessions() as session:
            yield session

    @router.get('/providers')
    def providers():
        return {name: {'available': provider_settings(name).available,
                       'native_available': provider_settings(name).available}
                for name in ('google', 'facebook')}

    @router.post('/social/{provider}/start')
    def start(provider: str, data: SocialStart, request: Request, s=Depends(db)):
        limiter.check(('social.start', request.client.host), 20)
        config = provider_settings(provider)
        if not config.available:
            raise HTTPException(503, 'This sign-in option is not available yet. Please use email.')
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        s.execute(delete(SocialFlow).where(SocialFlow.expires <= int(time.time())))
        s.add(SocialFlow(state_digest=digest(state), provider=provider, challenge=data.code_challenge,
                        nonce=nonce, provider_verifier=verifier, expires=int(time.time()) + 600))
        s.commit()
        return JSONResponse({'authorization_url': authorization_url(config, state, nonce, verifier),
                             'state': state}, headers=PRIVATE_HEADERS)

    @router.get('/social/{provider}/callback')
    async def callback(provider: str, state: str = Query(min_length=32, max_length=128),
                       code: str | None = Query(default=None, max_length=4096),
                       error: str | None = Query(default=None, max_length=200), s=Depends(db)):
        config = provider_settings(provider)
        flow = s.get(SocialFlow, digest(state))
        if not config.available or not flow or flow.provider != provider:
            raise HTTPException(400, 'Sign-in expired or could not be verified. Please start again.')
        claimed = s.execute(update(SocialFlow).where(
            SocialFlow.state_digest == digest(state), SocialFlow.provider == provider,
            SocialFlow.status == 'pending', SocialFlow.expires > int(time.time())
        ).values(status='processing'))
        if claimed.rowcount != 1:
            raise HTTPException(400, 'Sign-in expired or was already completed.')
        s.commit()
        if error or not code:
            flow.status = 'failed'; s.commit()
            return mobile_redirect(state, error='cancelled')
        try:
            identity = await fetch_identity(config, code, flow)
            user = patient_for_identity(s, provider, identity)
            handoff = secrets.token_urlsafe(32)
            flow.user_id, flow.code_digest = user.id, digest(handoff)
            flow.status, flow.expires = 'ready', int(time.time()) + 90
            s.commit()
        except HTTPException as exc:
            s.rollback()
            flow = s.get(SocialFlow, digest(state)); flow.status = 'failed'; s.commit()
            return mobile_redirect(state, error=exc.detail)
        except (httpx.HTTPError, google_errors.GoogleAuthError, ValueError, KeyError, TypeError, IntegrityError):
            s.rollback()
            flow = s.get(SocialFlow, digest(state)); flow.status = 'failed'; s.commit()
            return mobile_redirect(state, error='unavailable')
        return mobile_redirect(state, code=handoff)

    @router.post('/social/exchange')
    def exchange(data: SocialExchange, request: Request, s=Depends(db)):
        limiter.check(('social.exchange', request.client.host), 30)
        flow = s.get(SocialFlow, digest(data.state))
        challenge = pkce_challenge(data.code_verifier)
        if (not flow or flow.status != 'ready' or flow.expires <= time.time()
                or not hmac.compare_digest(flow.challenge, challenge)
                or not hmac.compare_digest(flow.code_digest, digest(data.code))):
            raise HTTPException(400, 'Sign-in expired or could not be verified. Please start again.')
        user = s.get(User, flow.user_id)
        if not user or not user.enabled or user.role != 'patient':
            raise HTTPException(403, 'This account is unavailable.')
        claimed = s.execute(update(SocialFlow).where(
            SocialFlow.state_digest == digest(data.state), SocialFlow.status == 'ready',
            SocialFlow.expires > int(time.time()), SocialFlow.code_digest == digest(data.code)
        ).values(status='consumed', code_digest='', nonce='', provider_verifier=''))
        if claimed.rowcount != 1:
            raise HTTPException(400, 'Sign-in was already completed. Please start again.')
        # The one-time handoff and the new application session commit together.
        return JSONResponse(login_result(s, user), headers=PRIVATE_HEADERS)

    app.include_router(router)
