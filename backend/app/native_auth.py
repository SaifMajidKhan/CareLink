"""Exchange native SDK credentials for a normal CareLink patient session.

Provider claims supplied by the phone are never used as identity. Google tokens
are cryptographically verified; Facebook tokens are inspected by Meta first.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from google.auth import exceptions as google_errors
import httpx
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from .schemas import BaseModel
from .social_auth import (PRIVATE_HEADERS, patient_for_identity, provider_settings,
                          verify_google_native_token, verify_facebook_native_token)


class GoogleNativeCredential(BaseModel):
    id_token: str = Field(min_length=40, max_length=16384, repr=False)


class FacebookNativeCredential(BaseModel):
    access_token: str = Field(min_length=20, max_length=16384, repr=False)


def register_native_routes(app, sessions, limiter, login_result):
    router = APIRouter(prefix='/auth/social', tags=['Native sign-in'])

    def db():
        with sessions() as session:
            yield session

    def configured(provider, request):
        limiter.check(('native.' + provider, request.client.host), 20)
        config = provider_settings(provider)
        if not config.available:
            raise HTTPException(503, 'This sign-in option is not available yet. Please use email.')
        return config

    def finish(session, provider, identity):
        try:
            patient = patient_for_identity(session, provider, identity)
            return JSONResponse(login_result(session, patient), headers=PRIVATE_HEADERS)
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, 'This account could not be connected. Try your existing sign-in method.') from None
        except (ValueError, KeyError, TypeError):
            session.rollback()
            raise HTTPException(401, 'Sign-in could not be verified. Please try again.') from None
        except HTTPException as error:
            session.rollback()
            if error.detail == 'email_in_use':
                raise HTTPException(409, 'An account already uses this email. Sign in with your existing method.') from None
            if error.detail == 'account_unavailable':
                raise HTTPException(403, 'This account is unavailable. Please contact support.') from None
            raise

    @router.post('/google/native')
    async def google(data: GoogleNativeCredential, request: Request, s=Depends(db)):
        config = configured('google', request)
        try:
            identity = await run_in_threadpool(verify_google_native_token, data.id_token, config.client_id)
        except (google_errors.GoogleAuthError, ValueError, KeyError, TypeError):
            raise HTTPException(401, 'Google sign-in could not be verified. Please try again.') from None
        return finish(s, 'google', identity)

    @router.post('/facebook/native')
    async def facebook(data: FacebookNativeCredential, request: Request, s=Depends(db)):
        config = configured('facebook', request)
        try:
            identity = await verify_facebook_native_token(config, data.access_token)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise HTTPException(401, 'Facebook sign-in could not be verified. Please try again.') from None
        return finish(s, 'facebook', identity)

    app.include_router(router)
