from collections.abc import Sequence

from shapely import Point
from sqlalchemy import func, null, or_, select

from db import DB
from limits import NEARBY_USERS_LIMIT, NEARBY_USERS_RADIUS_METERS
from models.db.user import User


class UserRepository:
    @staticmethod
    async def find_one_by_id(user_id: int) -> User | None:
        """
        Find a user by id.
        """

        async with DB() as session:
            return await session.get(User, user_id)

    @staticmethod
    async def find_one_by_display_name(display_name: str) -> User | None:
        """
        Find a user by display name.
        """

        async with DB() as session:
            stmt = select(User).where(User.display_name == display_name)

            return await session.scalar(stmt)

    @staticmethod
    async def find_one_by_display_name_or_email(display_name_or_email: str) -> User | None:
        """
        Find a user by display name or email.
        """

        async with DB() as session:
            stmt = select(User).where(
                or_(
                    User.display_name == display_name_or_email,
                    User.email == display_name_or_email,
                )
            )

            return await session.scalar(stmt)

    @staticmethod
    async def find_many_by_ids(user_ids: Sequence[int]) -> Sequence[User]:
        """
        Find users by ids.
        """

        async with DB() as session:
            stmt = select(User).where(User.id.in_(user_ids))

            return (await session.scalars(stmt)).all()

    @staticmethod
    async def find_many_nearby(
        point: Point,
        *,
        max_distance: float = NEARBY_USERS_RADIUS_METERS,
        limit: int | None = NEARBY_USERS_LIMIT,
    ) -> Sequence[User]:
        """
        Find nearby users.

        Users position is determined by their home point.
        """

        point_wkt = point.wkt

        async with DB() as session:
            stmt = (
                select(User)
                .where(
                    User.home_point != null(),
                    func.ST_DWithin(User.home_point, point_wkt, max_distance),
                )
                .order_by(func.ST_Distance(User.home_point, point_wkt))
            )

            if limit is not None:
                stmt = stmt.limit(limit)

            return (await session.scalars(stmt)).all()