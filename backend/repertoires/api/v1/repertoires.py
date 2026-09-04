from fastapi import APIRouter

router = APIRouter(prefix='/repertoires', tags=['Repertoires'])


@router.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
