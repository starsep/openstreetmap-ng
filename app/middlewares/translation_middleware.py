import logging
import re
from functools import lru_cache

import cython
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import DEFAULT_LANGUAGE
from app.lib.auth_context import auth_user
from app.lib.locale import normalize_locale
from app.lib.translation import translation_context
from app.limits import LANGUAGE_CODE_MAX_LENGTH
from app.middlewares.request_context_middleware import get_request

# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language#language
# limit to matches only supported by our translation files: config/locale
_accept_language_re = re.compile(r'(?P<lang>[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{1,8})?|\*)(?:;q=(?P<q>[0-9.]+))?')


class TranslationMiddleware:
    """
    Wrap requests in translation context.
    """

    __slots__ = ('app',)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        lang = _get_request_language()
        with translation_context(lang):
            await self.app(scope, receive, send)


@cython.cfunc
def _get_request_language() -> str:
    user = auth_user()
    if user is not None:
        return user.language

    accept_language = get_request().headers.get('Accept-Language')
    if accept_language:
        return _parse_accept_language(accept_language)

    return DEFAULT_LANGUAGE


@lru_cache(maxsize=512)
def _parse_accept_language(accept_language: str) -> str:
    """
    Parse the accept language header.

    Returns the most preferred and supported language.

    >>> _parse_accept_language('en-US;q=0.8,*;q=0.5,pl,es;q=0.9')
    'pl'
    """
    current_q: cython.double = 0
    current_lang: str = DEFAULT_LANGUAGE

    for match in _accept_language_re.finditer(accept_language):
        q_str: str | None = match['q']
        q_num: cython.double
        if q_str is None:
            q_num = 1
        else:
            try:
                q_num = float(q_str)
            except ValueError:
                logging.debug('Invalid accept language q-factor %r', q_str)
                continue

        if q_num <= current_q:
            continue

        lang: str = match['lang']

        if len(lang) > LANGUAGE_CODE_MAX_LENGTH:
            logging.debug('Accept language code is too long %d', len(lang))
            continue

        if lang == '*':
            lang = DEFAULT_LANGUAGE
        else:
            lang_normal = normalize_locale(lang)
            if lang_normal is None:
                lang_prefix = lang.partition('-')[0]
                lang_normal = normalize_locale(lang_prefix)
                if lang_normal is None:
                    logging.debug('Unsupported accept language %r', lang)
                    continue
            lang = lang_normal

        current_q = q_num
        current_lang = lang

    return current_lang
