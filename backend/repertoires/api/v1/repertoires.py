import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)

from api.dependencies import (
    get_current_user_id,
    get_line_service,
    get_repertoire_service,
)
from schemas.line import (
    LineCreate,
    LineResponse,
    LineTreeReplaceRequest,
    LineUpdate,
)
from schemas.repertoire import (
    RepertoireCreate,
    RepertoireListResponse,
    RepertoireResponse,
    RepertoireUpdate,
)
from services.line import LineService
from services.repertoire import RepertoireService

router = APIRouter(
    prefix='/repertoires',
    tags=['repertoires'],
)


@router.get(
    '/health'
)
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@router.get(
    '',
    response_model=RepertoireListResponse,
)
async def get_repertoires(
        page: int = Query(1, ge=1),
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: RepertoireService = Depends(get_repertoire_service),
        ) -> RepertoireListResponse:
    items, current_page, pages = await service.list(
        user_id,
        page,
    )

    return RepertoireListResponse(
        items=[
            RepertoireResponse.model_validate(item)
            for item in items
        ],
        page=current_page,
        pages=pages,
    )


@router.post(
    '',
    response_model=RepertoireResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repertoire(
        data: RepertoireCreate,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: RepertoireService = Depends(get_repertoire_service),
        ) -> RepertoireResponse:
    repertoire = await service.create(
        user_id,
        data,
    )

    return RepertoireResponse.model_validate(repertoire)


@router.get(
    '/{repertoire_id}',
    response_model=RepertoireResponse,
)
async def get_repertoire(
        repertoire_id: uuid.UUID,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: RepertoireService = Depends(get_repertoire_service),
        ) -> RepertoireResponse:
    repertoire = await service.get(
        repertoire_id,
        user_id,
    )

    return RepertoireResponse.model_validate(repertoire)


@router.patch(
    '/{repertoire_id}',
    response_model=RepertoireResponse,
)
async def update_repertoire(
        repertoire_id: uuid.UUID,
        data: RepertoireUpdate,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: RepertoireService = Depends(get_repertoire_service),
        ) -> RepertoireResponse:
    repertoire = await service.update(
        repertoire_id,
        user_id,
        data,
    )

    return RepertoireResponse.model_validate(repertoire)


@router.delete(
    '/{repertoire_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_repertoire(
        repertoire_id: uuid.UUID,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: RepertoireService = Depends(get_repertoire_service),
        ) -> Response:
    await service.delete(
        repertoire_id,
        user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    '/{repertoire_id}/lines',
    response_model=LineResponse,
)
async def get_lines(
        repertoire_id: uuid.UUID,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> LineResponse:
    tree = await service.get_tree_response(
        repertoire_id,
        user_id,
    )

    return LineResponse.model_validate(tree)


@router.put(
    '/{repertoire_id}/lines',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def replace_lines(
        repertoire_id: uuid.UUID,
        data: LineTreeReplaceRequest,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> Response:
    await service.replace_tree(
        repertoire_id,
        user_id,
        data,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    '/{repertoire_id}/lines/{line_id}',
    response_model=LineResponse,
)
async def get_line(
        repertoire_id: uuid.UUID,
        line_id: uuid.UUID,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> LineResponse:
    tree = await service.get_line_response(
        repertoire_id,
        line_id,
        user_id,
    )

    return LineResponse.model_validate(tree)


@router.post(
    '/{repertoire_id}/lines/{line_id}',
    response_model=LineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_child_line(
        repertoire_id: uuid.UUID,
        line_id: uuid.UUID,
        data: LineCreate,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> LineResponse:
    line = await service.create_child(
        repertoire_id,
        line_id,
        user_id,
        data,
    )

    return LineResponse.model_validate({
        'id': line.id,
        'tag': line.tag,
        'moves': line.moves,
        'children': [],
    })


@router.patch(
    '/{repertoire_id}/lines/{line_id}',
    response_model=LineResponse,
)
async def update_line(
        repertoire_id: uuid.UUID,
        line_id: uuid.UUID,
        data: LineUpdate,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> LineResponse:
    line = await service.update(
        repertoire_id,
        line_id,
        user_id,
        data,
    )

    return LineResponse.model_validate({
        'id': line.id,
        'tag': line.tag,
        'moves': line.moves,
        'children': [],
    })


@router.delete(
    '/{repertoire_id}/lines/{line_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_line(
        repertoire_id: uuid.UUID,
        line_id: uuid.UUID,
        user_id: uuid.UUID = Depends(get_current_user_id),
        service: LineService = Depends(get_line_service),
        ) -> Response:
    await service.delete(
        repertoire_id,
        line_id,
        user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
