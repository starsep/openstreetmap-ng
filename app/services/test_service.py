import logging
from datetime import datetime
from ipaddress import IPv4Address

from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.config import DEFAULT_LANGUAGE, TEST_ENV, TEST_USER_DOMAIN, TEST_USER_PASSWORD
from app.db import db_commit
from app.lib.auth_context import auth_context
from app.lib.password_hash import PasswordHash
from app.models.db.user import User
from app.models.str import PasswordStr
from app.models.user_role import UserRole
from app.models.user_status import UserStatus
from app.queries.user_query import UserQuery


class TestService:
    @staticmethod
    async def on_startup():
        """
        Prepare the test environment.

        Does nothing if not in test environment.
        """
        if not TEST_ENV:
            return

        with auth_context(None, ()):
            await TestService.create_user('admin', roles=(UserRole.administrator,))
            await TestService.create_user('moderator', roles=(UserRole.moderator,))
            await TestService.create_user('user1')
            await TestService.create_user('user2')

    # Additional safeguard against running this in production
    if TEST_ENV:

        @staticmethod
        async def create_user(
            name: str,
            *,
            status: UserStatus = UserStatus.active,
            language: str = DEFAULT_LANGUAGE,
            created_at: datetime | None = None,
            roles: tuple[UserRole, ...] = (),
        ) -> None:
            """
            Create a test user.
            """
            email = f'{name}@{TEST_USER_DOMAIN}'
            name_available = await UserQuery.check_display_name_available(name)
            password_hashed = PasswordHash.hash(PasswordStr(TEST_USER_PASSWORD))

            async with db_commit() as session:
                if name_available:
                    # create new user
                    user = User(
                        email=email,
                        display_name=name,
                        password_hashed=password_hashed,
                        created_ip=IPv4Address('127.0.0.1'),
                        status=status,
                        auth_provider=None,
                        auth_uid=None,
                        language=language,
                        activity_tracking=False,
                        crash_reporting=False,
                    )
                    if created_at is not None:
                        user.created_at = created_at
                    user.roles = roles
                    session.add(user)
                else:
                    # update existing user (happens after preloading real users)
                    stmt = select(User).options(load_only(User.id)).where(User.display_name == name).with_for_update()
                    user = (await session.execute(stmt)).scalar_one()
                    user.email = email
                    user.password_hashed = password_hashed
                    user.status = status
                    user.language = language
                    if created_at is not None:
                        user.created_at = created_at
                    user.roles = roles

            logging.info('Test user %r created', name)
