from collections.abc import Sequence

from anyio import create_task_group
from sqlalchemy import Select, select, text, union_all

from app.db import db
from app.lib.auth_context import auth_user
from app.lib.options_context import apply_options_context
from app.models.db.changeset import Changeset
from app.models.db.changeset_comment import ChangesetComment
from app.models.db.changeset_subscription import ChangesetSubscription


class ChangesetCommentQuery:
    @staticmethod
    async def is_subscribed(changeset_id: int) -> bool:
        """
        Check if the user is subscribed to the changeset.
        """
        async with db() as session:
            stmt = select(text('1')).where(
                ChangesetSubscription.changeset_id == changeset_id,
                ChangesetSubscription.user_id == auth_user().id,
            )
            return await session.scalar(stmt) is not None

    @staticmethod
    async def resolve_comments(
        changesets: Sequence[Changeset],
        *,
        limit_per_changeset: int | None,
        resolve_rich_text: bool = True,
    ) -> None:
        """
        Resolve comments for changesets.
        """
        changesets_: list[Changeset] = []
        id_comments_map: dict[int, list[ChangesetComment]] = {}
        for changeset in changesets:
            if changeset.comments is None:
                changesets_.append(changeset)
                id_comments_map[changeset.id] = changeset.comments = []

        if not changesets_:
            return

        async with db() as session:
            stmts: list[Select] = []

            for changeset in changesets_:
                stmt_ = select(ChangesetComment.id).where(
                    ChangesetComment.changeset_id == changeset.id,
                    ChangesetComment.created_at <= changeset.updated_at,
                )
                if limit_per_changeset is not None:
                    stmt_ = stmt_.order_by(ChangesetComment.created_at.desc())
                    stmt_ = stmt_.limit(limit_per_changeset)
                    stmt_ = select(stmt_.c.id).select_from(stmt_)
                stmts.append(stmt_)

            stmt = (
                select(ChangesetComment)
                .where(ChangesetComment.id.in_(union_all(*stmts).subquery().select()))
                .order_by(ChangesetComment.created_at.asc())
            )
            stmt = apply_options_context(stmt)
            comments: Sequence[ChangesetComment] = (await session.scalars(stmt)).all()

        current_changeset_id: int = 0
        current_comments: list[ChangesetComment] = []

        for comment in comments:
            changeset_id = comment.changeset_id
            if current_changeset_id != changeset_id:
                current_changeset_id = changeset_id
                current_comments = id_comments_map[changeset_id]
            current_comments.append(comment)

        if resolve_rich_text:
            async with create_task_group() as tg:
                for comment in comments:
                    tg.start_soon(comment.resolve_rich_text)