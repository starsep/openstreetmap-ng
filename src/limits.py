from datetime import timedelta
from math import inf

_KB = 1024
_MB = 1024 * _KB

AVATAR_MAX_RATIO = 2
AVATAR_MAX_MEGAPIXELS = 2 * _MB  # 2 MP (e.g., 1448x1448)
AVATAR_MAX_FILE_SIZE = 1 * _MB

CACHE_DEFAULT_EXPIRE = timedelta(days=3)

CHANGESET_OPEN_TIMEOUT = timedelta(days=1)
CHANGESET_IDLE_TIMEOUT = timedelta(hours=1)
CHANGESET_COMMENT_BODY_MAX_LENGTH = 5_000  # NOTE: value TBD
CHANGESET_QUERY_DEFAULT_LIMIT = 100
CHANGESET_QUERY_MAX_LIMIT = 100

# Q95: 1745, Q99: 3646, Q99.9: 10864, Q100: 636536
DIARY_BODY_MAX_LENGTH = 100_000  # NOTE: value TBD
DIARY_COMMENT_BODY_MAX_LENGTH = 5_000  # NOTE: value TBD

ELEMENT_MAX_TAGS = 123  # TODO:
ELEMENT_WAY_MAX_NODES = 2_000
ELEMENT_RELATION_MAX_MEMBERS = 32_000

FAST_PASSWORD_CACHE_EXPIRE = timedelta(hours=8)

FIND_LIMIT = 100

ISSUE_COMMENT_BODY_MAX_LENGTH = 5_000  # NOTE: value TBD

LANGUAGE_CODE_MAX_LENGTH = 10

MAIL_PROCESSING_TIMEOUT = timedelta(minutes=1)
MAIL_UNPROCESSED_EXPONENT = 2  # 1 min, 2 mins, 4 mins, etc.
MAIL_UNPROCESSED_EXPIRE = timedelta(days=3)  # TODO: expire index

MAP_QUERY_AREA_MAX_SIZE = 0.25  # in square degrees
MAP_QUERY_LEGACY_NODES_LIMIT = 50_000

MESSAGE_BODY_MAX_LENGTH = 50_000  # NOTE: value TBD

NEARBY_USERS_LIMIT = 30
NEARBY_USERS_RADIUS_METERS = 50_000

NOMINATIM_CACHE_EXPIRE = timedelta(days=30)

NOTE_COMMENT_BODY_MAX_LENGTH = 2_000
NOTE_FRESHLY_CLOSED_TIMEOUT = timedelta(days=7)
NOTE_QUERY_AREA_MAX_SIZE = 25  # in square degrees
NOTE_QUERY_DEFAULT_LIMIT = 100
NOTE_QUERY_DEFAULT_CLOSED = 7  # open + max 7 days closed
NOTE_QUERY_LEGACY_MAX_LIMIT = 10_000

OAUTH_APP_NAME_MAX_LENGTH = 64  # TODO:
OAUTH1_NONCE_MAX_LENGTH = 255
OAUTH1_TIMESTAMP_EXPIRE = timedelta(days=2)
OAUTH1_TIMESTAMP_VALIDITY = timedelta(days=1)
OAUTH2_SILENT_AUTH_QUERY_SESSION_LIMIT = 10

# TODO: check pwned passwords
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 255  # TODO:

POLICY_LEGACY_IMAGERY_BLACKLISTS = [
    '.*\\.google(apis)?\\..*/.*',
    'http://xdworld\\.vworld\\.kr:8080/.*',
    '.*\\.here\\.com[/:].*',
    '.*\\.mapy\\.cz.*',
]

REPORT_BODY_MAX_LENGTH = 50_000  # NOTE: value TBD

TRACE_TAG_MAX_LENGTH = 40
TRACE_TAGS_LIMIT = 10

TRACE_FILE_MAX_SIZE = 50 * _MB
TRACE_FILE_UNCOMPRESSED_MAX_SIZE = 80 * _MB
TRACE_FILE_ARCHIVE_MAX_FILES = 10
TRACE_FILE_COMPRESS_ZSTD_THREADS = 1
TRACE_FILE_COMPRESS_ZSTD_LEVEL = (
    # useful: zstd -f -b11 -e19 test_trace.gpx
    (0.25 * _MB, 19),
    (1.00 * _MB, 15),
    (inf, 13),
)

TRACE_POINT_QUERY_AREA_MAX_SIZE = 0.25  # in square degrees
TRACE_POINT_QUERY_DEFAULT_LIMIT = 5_000
TRACE_POINT_QUERY_MAX_LIMIT = 5_000
TRACE_POINT_QUERY_LEGACY_MAX_SKIP = 45_000
TRACE_POINT_QUERY_CURSOR_EXPIRE = timedelta(hours=1)

URL_MAX_LENGTH = 2 * _KB  # TODO:

USER_BLOCK_BODY_MAX_LENGTH = 50_000  # NOTE: value TBD
USER_LANGUAGES_LIMIT = 10
USER_DESCRIPTION_MAX_LENGTH = 100_000  # NOTE: value TBD

USER_PREF_BULK_SET_LIMIT = 150

USER_TOKEN_ACCOUNT_CONFIRM_EXPIRE = timedelta(days=30)  # TODO: delete unconfirmed accounts
USER_TOKEN_EMAIL_CHANGE_EXPIRE = timedelta(days=1)
USER_TOKEN_EMAIL_REPLY_EXPIRE = timedelta(days=2 * 365)  # 2 years
USER_TOKEN_SESSION_EXPIRE = timedelta(days=365)  # 1 year

XML_PARSE_MAX_SIZE = 50 * _MB  # the same as CGImap

HTTP_BODY_MAX_SIZE = max(TRACE_FILE_MAX_SIZE, XML_PARSE_MAX_SIZE) + 5 * _MB  # MAX + 5 MB
HTTP_COMPRESSED_BODY_MAX_SIZE = HTTP_BODY_MAX_SIZE // 2