"""Server-side Supabase-compatible JWT identity boundary."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, Protocol

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.config.settings import Settings
from app.security.errors import stable_http_error

_bearer_scheme = HTTPBearer(auto_error=False)
_credentials_dependency = Depends(_bearer_scheme)


class TokenVerifier(Protocol):
    """Callable seam for deterministic fixtures or a production verifier."""

    def __call__(self, token: str, settings: Settings | None = None) -> AuthenticatedUser: ...


class TokenVerificationError(ValueError):
    """Raised when a bearer token cannot be trusted as a user identity."""


class AuthenticatedUser(BaseModel):
    """Minimal identity accepted from a verified Supabase access token."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(min_length=1)
    email: str | None = None
    role: str = "authenticated"

    @classmethod
    def from_claims(cls, claims: Mapping[str, Any]) -> AuthenticatedUser:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise TokenVerificationError("verified token did not contain a subject")

        email = claims.get("email")
        if not isinstance(email, str):
            email = None
        role = claims.get("role", "authenticated")
        if not isinstance(role, str) or not role.strip():
            role = "authenticated"
        return cls(id=subject, email=email, role=role)


def verify_access_token(
    token: str,
    settings: Settings | None = None,
) -> AuthenticatedUser:
    """Verify a Supabase access JWT using a server-held signing secret.

    The key is never obtained from the browser and this function performs no
    network request.  Deployments using a different Supabase signing setup can
    inject an equivalent verifier into ``create_app``.
    """

    if not token or token.count(".") != 2:
        raise TokenVerificationError("token is not a compact JWT")
    if settings is None or settings.supabase_jwt_secret is None:
        raise TokenVerificationError("JWT verification is not configured")

    decode_kwargs: dict[str, Any] = {
        "algorithms": ["HS256"],
        "options": {"verify_aud": False},
    }
    if settings.supabase_jwt_issuer:
        decode_kwargs["issuer"] = settings.supabase_jwt_issuer
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret.get_secret_value(),
            **decode_kwargs,
        )
    except jwt.PyJWTError as error:
        raise TokenVerificationError("token verification failed") from error
    if not isinstance(claims, Mapping):
        raise TokenVerificationError("token claims are not an object")
    return AuthenticatedUser.from_claims(claims)


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else "req_unavailable"


def _auth_error(request: Request) -> HTTPException:
    return stable_http_error(
        status_code=401,
        code="UNAUTHENTICATED",
        message="Authentication is required to access this resource.",
        request_id=_request_id(request),
    )


def _invoke_verifier(
    verifier: Callable[..., AuthenticatedUser],
    token: str,
    settings: Settings,
) -> AuthenticatedUser:
    """Support both one-argument fixture verifiers and the typed two-arg seam."""

    try:
        signature = inspect.signature(verifier)
        positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        accepts_settings = len(positional) >= 2 or any(
            parameter.kind == inspect.Parameter.VAR_POSITIONAL
            for parameter in signature.parameters.values()
        )
    except (TypeError, ValueError):
        accepts_settings = True
    result = verifier(token, settings) if accepts_settings else verifier(token)
    if not isinstance(result, AuthenticatedUser):
        raise TokenVerificationError("token verifier returned an invalid identity")
    return result


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = _credentials_dependency,
) -> AuthenticatedUser:
    """Resolve a verified bearer identity without contacting Supabase."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _auth_error(request)
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise _auth_error(request)
    verifier = getattr(request.app.state, "token_verifier", verify_access_token)
    try:
        return _invoke_verifier(verifier, credentials.credentials, settings)
    except (TokenVerificationError, HTTPException, ValueError, TypeError):
        raise _auth_error(request) from None


_current_user_dependency = Depends(get_current_user)


async def require_admin(
    request: Request,
    current_user: AuthenticatedUser = _current_user_dependency,
) -> AuthenticatedUser:
    """Require an administrator role from an already verified identity claim."""

    if current_user.role.casefold() == "admin":
        return current_user
    raise stable_http_error(
        status_code=403,
        code="ADMIN_REQUIRED",
        message="Administrator access is required for this resource.",
        request_id=_request_id(request),
    )


__all__ = [
    "AuthenticatedUser",
    "TokenVerificationError",
    "TokenVerifier",
    "get_current_user",
    "require_admin",
    "verify_access_token",
]
