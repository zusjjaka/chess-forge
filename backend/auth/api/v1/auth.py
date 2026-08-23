from core.config import get_settings
from db.session import get_db_session
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from models.user import User
from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user

router = APIRouter(prefix='/auth', tags=['Authentication'])

settings = get_settings()


@router.post(
    '/register',
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> RegisterResponse:
    service = AuthService(session)

    user = await service.register(
        email=data.email,
        password=data.password,
    )

    return RegisterResponse(
        id=user.id,
        email=user.email,
        status='pending_verification',
    )


@router.post(
    '/login',
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    service = AuthService(session)

    access_token, refresh_token = await service.login(
        email=data.email,
        password=data.password,
        ip_addr=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )

    response.set_cookie(
        key=settings.refresh_token_cookie.name,
        value=refresh_token,
        httponly=settings.refresh_token_cookie.httponly,
        secure=settings.refresh_token_cookie.secure,
        samesite=settings.refresh_token_cookie.samesite,
        path=settings.refresh_token_cookie.path,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post(
    '/tokens/refresh',
    response_model=TokenResponse,
)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    refresh_token = request.cookies.get(settings.refresh_token_cookie.name)

    if refresh_token is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token missing',
        )

    service = AuthService(session)

    access_token, new_refresh_token = await service.refresh(
        refresh_token=refresh_token,
        ip_addr=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )

    refresh_token_settings = settings.refresh_token_cookie

    response.set_cookie(
        key=refresh_token_settings.name,
        value=new_refresh_token,
        httponly=refresh_token_settings.httponly,
        secure=refresh_token_settings.secure,
        samesite=refresh_token_settings.samesite,
        path=refresh_token_settings.path,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    refresh_token = request.cookies.get(settings.refresh_token_cookie.name)

    if refresh_token is not None:
        service = AuthService(session)
        await service.logout(refresh_token)

    response.delete_cookie(
        key=settings.refresh_token_cookie.name,
        path=settings.refresh_token_cookie.path,
    )


@router.post(
    '/logout-all',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    service = AuthService(session)

    await service.logout_all(current_user.id)


@router.get(
    '/me',
    response_model=UserResponse,
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
