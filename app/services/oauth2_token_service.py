from base64 import urlsafe_b64encode
from hashlib import sha256

import cython
from sqlalchemy import delete, null, select

from app.db import db_commit
from app.lib.auth_context import auth_user
from app.lib.buffered_random import buffered_rand_urlsafe
from app.lib.crypto import hash_bytes
from app.lib.date_utils import utcnow
from app.lib.exceptions_context import raise_for
from app.limits import OAUTH2_SILENT_AUTH_QUERY_SESSION_LIMIT
from app.models.db.oauth2_application import OAuth2Application
from app.models.db.oauth2_token import OAuth2Token
from app.models.oauth2_code_challenge_method import OAuth2CodeChallengeMethod
from app.models.scope import Scope
from app.queries.oauth2_application_query import OAuth2ApplicationQuery
from app.queries.oauth2_token_query import OAuth2TokenQuery
from app.utils import extend_query_params

# TODO: limit number of access tokens per user+app


class OAuth2TokenService:
    @staticmethod
    async def authorize(
        *,
        init: bool,
        client_id: str,
        redirect_uri: str,
        scopes: tuple[Scope, ...],
        code_challenge_method: OAuth2CodeChallengeMethod | None,
        code_challenge: str | None,
        state: str | None,
    ) -> str | OAuth2Application:
        """
        Create a new authorization code.

        The code can be exchanged for an access token.

        In init=True mode, silent authentication is performed if the application is already authorized.
        When successful, a redirect url or an authorization code (prefixed with "oob;") is returned.
        Otherwise, the application instance is returned for the user to authorize it.

        In init=False mode, a redirect url or an authorization code (prefixed with "oob;") is returned.
        """
        app = await OAuth2ApplicationQuery.find_one_by_client_id(client_id)
        if app is None:
            raise_for().oauth_bad_app_token()
        if redirect_uri not in app.redirect_uris:
            raise_for().oauth_bad_redirect_uri()

        user_id = auth_user(required=True).id
        scopes_set = set(scopes)  # TODO: check app scopes
        if not scopes_set.issubset(app.scopes):
            raise_for().oauth_bad_scopes()

        # handle silent authentication
        if init:
            tokens = await OAuth2TokenQuery.find_many_authorized_by_user_app(
                user_id=user_id,
                app_id=app.id,
                limit=OAUTH2_SILENT_AUTH_QUERY_SESSION_LIMIT,
            )
            for token in tokens:
                # ignore different redirect uri
                if token.redirect_uri != redirect_uri:
                    continue
                # ignore different scopes
                if scopes_set.symmetric_difference(token.scopes):
                    continue
                # session found, auto-approve
                break
            else:
                # no session found, require manual approval
                return app

        authorization_code = buffered_rand_urlsafe(32)
        authorization_code_hashed = hash_bytes(authorization_code)

        async with db_commit() as session:
            token = OAuth2Token(
                user_id=user_id,
                application_id=app.id,
                token_hashed=authorization_code_hashed,
                scopes=scopes,
                redirect_uri=redirect_uri,
                code_challenge_method=code_challenge_method,
                code_challenge=code_challenge,
            )
            session.add(token)

        if token.is_oob:
            return f'oob;{authorization_code}'

        params = {'code': authorization_code}

        if state is not None:
            params['state'] = state

        return extend_query_params(redirect_uri, params)

    @staticmethod
    async def token(authorization_code: str, verifier: str | None) -> dict:
        """
        Exchange an authorization code for an access token.

        The access token can be used to make requests on behalf of the user.
        """
        authorization_code_hashed = hash_bytes(authorization_code)

        async with db_commit() as session:
            stmt = (
                select(OAuth2Token)
                .where(
                    OAuth2Token.token_hashed == authorization_code_hashed,
                    OAuth2Token.authorized_at == null(),
                )
                .with_for_update()
            )
            token = await session.scalar(stmt)
            if token is None:
                raise_for().oauth_bad_user_token()

            try:
                if token.code_challenge_method is None:
                    if verifier is not None:
                        raise_for().oauth2_challenge_method_not_set()
                elif token.code_challenge_method == OAuth2CodeChallengeMethod.plain:
                    if token.code_challenge != verifier:
                        raise_for().oauth2_bad_verifier(token.code_challenge_method)
                elif token.code_challenge_method == OAuth2CodeChallengeMethod.S256:
                    if token.code_challenge != _compute_s256(verifier):
                        raise_for().oauth2_bad_verifier(token.code_challenge_method)
                else:
                    raise NotImplementedError(  # noqa: TRY301
                        f'Unsupported OAuth2 code challenge method {token.code_challenge_method!r}'
                    )
            except Exception:
                # delete the token if the verification fails
                await session.delete(token)
                raise

            access_token = buffered_rand_urlsafe(32)
            access_token_hashed = hash_bytes(access_token)

            token.token_hashed = access_token_hashed
            token.authorized_at = utcnow()
            token.code_challenge_method = None
            token.code_challenge = None

        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'scope': token.scopes_str,
            'created_at': int(token.authorized_at.timestamp()),
            # TODO: id_token
        }

    @staticmethod
    async def revoke_by_token(access_token: str) -> None:
        """
        Revoke the given access token.
        """
        access_token_hashed = hash_bytes(access_token)
        async with db_commit() as session:
            stmt = delete(OAuth2Token).where(
                OAuth2Token.user_id == auth_user(required=True).id,
                OAuth2Token.token_hashed == access_token_hashed,
            )
            await session.execute(stmt)

    @staticmethod
    async def revoke_by_app(app_id: int) -> None:
        """
        Revoke all current user tokens for the given OAuth2 application.
        """
        async with db_commit() as session:
            stmt = delete(OAuth2Token).where(
                OAuth2Token.user_id == auth_user(required=True).id,
                OAuth2Token.application_id == app_id,
            )
            await session.execute(stmt)


@cython.cfunc
def _compute_s256(verifier: str) -> str:
    """
    Compute the S256 code challenge from the verifier.
    """
    verifier_bytes = verifier.encode()
    verifier_hashed = sha256(verifier_bytes).digest()
    verifier_base64 = urlsafe_b64encode(verifier_hashed).decode().rstrip('=')
    return verifier_base64
