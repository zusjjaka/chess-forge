from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from api.dependencies import (
    get_current_user_id,
    get_training_service,
)
from core.constants import PAGE_SIZE
from models.session import TrainingSessionStatus
from schemas.session import (
    TrainingMoveRequest,
    TrainingMoveResponse,
    TrainingSessionCreate,
    TrainingSessionListItem,
    TrainingSessionListResponse,
    TrainingSessionResponse,
)
from services.training import TrainingService

router = APIRouter(
    prefix='/training',
    tags=['Training'],
)


@router.get(
    '/sessions',
    response_model=TrainingSessionListResponse,
)
async def list_sessions(
        page: int = Query(
            default=1,
            ge=1,
        ),
        status_filter: TrainingSessionStatus | None = Query(
            default=None,
            alias='status',
        ),
        user_id: UUID = Depends(get_current_user_id),
        service: TrainingService = Depends(
            get_training_service,
        ),
        ) -> TrainingSessionListResponse:

    limit = PAGE_SIZE
    offset = (page - 1) * limit

    sessions = await service.list_sessions(
        user_id=user_id,
        status=status_filter,
        offset=offset,
        limit=limit,
    )

    total = await service.count_sessions(
        user_id=user_id,
        status=status_filter,
    )

    items = [
        TrainingSessionListItem(
            id=session.id,
            status=session.status,
            created_at=session.created_at,
        )
        for session in sessions
    ]

    return TrainingSessionListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
    )


@router.post(
    '/sessions',
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
        data: TrainingSessionCreate,
        user_id: UUID = Depends(get_current_user_id),
        service: TrainingService = Depends(
            get_training_service,
        ),
        ) -> TrainingSessionResponse:

    session = await service.create_session(
        user_id=user_id,
        data=data,
    )

    return TrainingSessionResponse(
        id=session.id,
        repertoire_id=session.repertoire_id,
        line_id=session.start_line_id,
        status=session.status,
        repertoire_version=session.repertoire_revision,
        current_ply=session.current_ply,
        created_at=session.created_at,
        ended_at=session.ended_at,
        error_line_id=session.error_line_id,
        error_ply=session.error_ply,
    )


@router.get(
    '/sessions/{session_id}',
    response_model=TrainingSessionResponse,
)
async def get_session(
        session_id: UUID,
        user_id: UUID = Depends(get_current_user_id),
        service: TrainingService = Depends(
            get_training_service,
        ),
        ) -> TrainingSessionResponse:

    session = await service.get_session(
        user_id=user_id,
        session_id=session_id,
    )

    return TrainingSessionResponse(
        id=session.id,
        repertoire_id=session.repertoire_id,
        line_id=session.start_line_id,
        status=session.status,
        repertoire_version=session.repertoire_revision,
        current_ply=session.current_ply,
        created_at=session.created_at,
        ended_at=session.ended_at,
        error_line_id=session.error_line_id,
        error_ply=session.error_ply,
    )


@router.post(
    '/sessions/{session_id}/moves',
    response_model=TrainingMoveResponse,
)
async def make_move(
        session_id: UUID,
        data: TrainingMoveRequest,
        user_id: UUID = Depends(get_current_user_id),
        service: TrainingService = Depends(
            get_training_service,
        ),
        ) -> TrainingMoveResponse:

    return await service.make_move(
        user_id=user_id,
        session_id=session_id,
        move=data.move,
    )
