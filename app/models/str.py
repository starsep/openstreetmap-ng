from typing import Annotated

from annotated_types import MaxLen, MinLen
from email_validator.rfc_constants import EMAIL_MAX_LENGTH
from pydantic import SecretStr

from app.limits import (
    DISPLAY_NAME_MAX_LENGTH,
    ELEMENT_TAGS_KEY_MAX_LENGTH,
    OAUTH_APP_URI_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
)
from app.validators.email import EmailStrValidator
from app.validators.url import UriValidator, UrlSafeValidator
from app.validators.whitespace import BoundaryWhitespaceValidator

Str255 = Annotated[str, MinLen(1), MaxLen(255)]

TagKeyStr = Annotated[str, MaxLen(ELEMENT_TAGS_KEY_MAX_LENGTH)]
TagValueStr = Annotated[str, MaxLen(255)]

DisplayNameStr = Annotated[
    str,
    MinLen(3),
    MaxLen(DISPLAY_NAME_MAX_LENGTH),
    UrlSafeValidator,
    BoundaryWhitespaceValidator,
]
EmailStr = Annotated[str, EmailStrValidator, MinLen(5), MaxLen(EMAIL_MAX_LENGTH)]
PasswordStr = Annotated[SecretStr, MinLen(PASSWORD_MIN_LENGTH), MaxLen(PASSWORD_MAX_LENGTH)]
RoleStr = Annotated[str, MaxLen(255)]

Uri = Annotated[str, UriValidator, MinLen(3), MaxLen(OAUTH_APP_URI_MAX_LENGTH)]
