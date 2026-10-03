from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import (
    TrainingSessionInvalidatedError,
    TrainingSessionNotActiveError,
    TrainingSessionNotFoundError,
)
from grpc_client.client import RepertoireGrpcClient
from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)
from repositories.session import TrainingSessionRepository
from repositories.stat import LineTrainingStatsRepository
from schemas.session import (
    TrainingMoveResponse,
    TrainingSessionCreate,
)
from services.selection import TrainingSelector


class TrainingService:
    def __init__(
            self,
            session: AsyncSession,
            repertoire_client: RepertoireGrpcClient,
            ) -> None:
        self._session = session
        self._session_repository = TrainingSessionRepository(
            session,
        )
        self._stats_repository = LineTrainingStatsRepository(
            session,
        )
        self._repertoire_client = repertoire_client
        self._selector = TrainingSelector()

    async def create_session(
            self,
            user_id: UUID,
            data: TrainingSessionCreate,
            ) -> TrainingSession:

        tree = await self._repertoire_client.get_training_tree(
            user_id=user_id,
            repertoire_id=data.repertoire_id,
            start_line_id=data.line_id,
        )

        stats = await self._stats_repository.get_many(
            user_id=user_id,
            line_keys=[
                (
                    line.id,
                    line.analytic_version,
                )
                for line in tree.lines
            ],
        )

        selected_path = self._selector.select(
            tree.lines,
            stats,
        )

        selected_path_data = [
            {
                'line_id': str(line.id),
                'moves_count': len(line.moves),
                'analytic_version': line.analytic_version,
            }
            for line in selected_path.lines
        ]

        training_session = TrainingSession(
            user_id=user_id,
            repertoire_id=data.repertoire_id,
            start_line_id=selected_path.lines[0].id,
            current_ply=0,
            repertoire_revision=tree.repertoire_revision,
            selected_moves=selected_path.moves,
            selected_path=selected_path_data,
            status=TrainingSessionStatus.ACTIVE,
        )

        await self._session_repository.add(
            training_session,
        )

        await self._session.commit()
        await self._session.refresh(
            training_session,
        )

        return training_session

    async def get_session(
            self,
            user_id: UUID,
            session_id: UUID,
            ) -> TrainingSession:

        training_session = await self._session_repository.get(
            session_id=session_id,
            user_id=user_id,
        )

        if training_session is None:
            raise TrainingSessionNotFoundError

        return training_session

    async def list_sessions(
            self,
            user_id: UUID,
            *,
            status: TrainingSessionStatus | None,
            offset: int,
            limit: int,
            ) -> list[TrainingSession]:

        return await self._session_repository.list_by_user(
            user_id=user_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def count_sessions(
            self,
            user_id: UUID,
            *,
            status: TrainingSessionStatus | None,
            ) -> int:

        return await self._session_repository.count_by_user(
            user_id=user_id,
            status=status,
        )

    async def make_move(
            self,
            user_id: UUID,
            session_id: UUID,
            move: str,
            ) -> TrainingMoveResponse:

        training_session = await self._session_repository.get(
            session_id=session_id,
            user_id=user_id,
        )

        if training_session is None:
            raise TrainingSessionNotFoundError

        if (
            training_session.status
            != TrainingSessionStatus.ACTIVE
        ):
            raise TrainingSessionNotActiveError

        current_revision = (
            await self._repertoire_client.get_repertoire_revision(
                user_id=user_id,
                repertoire_id=training_session.repertoire_id,
            )
        )

        repertoire_revision = training_session.repertoire_revision

        await self._session.rollback()

        if current_revision != repertoire_revision:
            await self._invalidate_session(
                user_id=user_id,
                session_id=session_id,
            )

            raise TrainingSessionInvalidatedError

        async with self._session.begin():
            training_session = (
                await self._session_repository.get(
                    session_id=session_id,
                    user_id=user_id,
                    for_update=True,
                )
            )

            if training_session is None:
                raise TrainingSessionNotFoundError

            if (
                training_session.status
                != TrainingSessionStatus.ACTIVE
            ):
                raise TrainingSessionNotActiveError

            expected_move = (
                training_session.selected_moves[
                    training_session.current_ply
                ]
            )

            if move != expected_move:
                await self._handle_failure(
                    training_session,
                )

                return TrainingMoveResponse(
                    correct=False,
                    current_ply=training_session.current_ply,
                    status=training_session.status,
                )

            await self._handle_successful_move(
                training_session,
            )

            return TrainingMoveResponse(
                correct=True,
                current_ply=training_session.current_ply,
                status=training_session.status,
            )

    async def _invalidate_session(
            self,
            user_id: UUID,
            session_id: UUID,
            ) -> None:

        async with self._session.begin():
            training_session = (
                await self._session_repository.get(
                    session_id=session_id,
                    user_id=user_id,
                    for_update=True,
                )
            )

            if training_session is None:
                raise TrainingSessionNotFoundError

            if (
                training_session.status
                != TrainingSessionStatus.ACTIVE
            ):
                return

            training_session.status = (
                TrainingSessionStatus.INVALIDATED
            )
            training_session.ended_at = datetime.now(
                UTC,
            )

    async def _handle_successful_move(
            self,
            training_session: TrainingSession,
            ) -> None:

        training_session.current_ply += 1

        if (
            training_session.current_ply
            == len(training_session.selected_moves)
        ):
            training_session.status = (
                TrainingSessionStatus.PASSED
            )
            training_session.ended_at = datetime.now(
                UTC,
            )

            await self._record_all_successes(
                training_session,
            )

    async def _handle_failure(
            self,
            training_session: TrainingSession,
            ) -> None:

        error_line_id = self._find_line_for_ply(
            training_session,
            training_session.current_ply,
        )

        training_session.status = (
            TrainingSessionStatus.FAILED
        )
        training_session.error_line_id = error_line_id
        training_session.error_ply = (
            training_session.current_ply
        )
        training_session.error_line_analytic_version = (
            self._get_line_version(
                training_session,
                error_line_id,
            )
        )
        training_session.ended_at = datetime.now(
            UTC,
        )

        await self._record_failure(
            training_session,
            error_line_id,
        )

        for line_id in self._get_passed_line_ids(
            training_session,
            error_line_id,
        ):
            await self._record_success(
                training_session,
                line_id,
            )

    @staticmethod
    def _find_line_for_ply(
            training_session: TrainingSession,
            ply: int,
            ) -> UUID:

        current_ply = 0

        for item in training_session.selected_path:
            line_id = UUID(
                str(item['line_id']),
            )

            moves_count = int(
                item['moves_count'],
            )

            if ply < current_ply + moves_count:
                return line_id

            current_ply += moves_count

        raise RuntimeError(
            'Unable to determine error line',
        )

    @staticmethod
    def _get_passed_line_ids(
            training_session: TrainingSession,
            error_line_id: UUID,
            ) -> list[UUID]:

        result: list[UUID] = []

        for item in training_session.selected_path:
            line_id = UUID(
                str(item['line_id']),
            )

            if line_id == error_line_id:
                break

            result.append(line_id)

        return result

    async def _record_all_successes(
            self,
            training_session: TrainingSession,
            ) -> None:

        for item in training_session.selected_path:
            line_id = UUID(
                str(item['line_id']),
            )

            await self._record_success(
                training_session,
                line_id,
            )

    async def _record_success(
            self,
            training_session: TrainingSession,
            line_id: UUID,
            ) -> None:

        await self._stats_repository.increment_success(
            user_id=training_session.user_id,
            line_id=line_id,
            line_analytic_version=self._get_line_version(
                training_session,
                line_id,
            ),
        )

    async def _record_failure(
            self,
            training_session: TrainingSession,
            line_id: UUID,
            ) -> None:

        await self._stats_repository.increment_failure(
            user_id=training_session.user_id,
            line_id=line_id,
            line_analytic_version=self._get_line_version(
                training_session,
                line_id,
            ),
        )

    @staticmethod
    def _get_line_version(
            training_session: TrainingSession,
            line_id: UUID,
            ) -> int:

        for item in training_session.selected_path:
            if UUID(str(item['line_id'])) == line_id:
                return int(item['analytic_version'])

        raise RuntimeError(
            'Line not found in selected path',
        )
