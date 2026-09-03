from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)

from api.dependencies import (
    get_auth_service,
    get_current_user,
    get_email_verification_service,
    get_password_reset_service,
    get_unverified_current_user,
)
from core.config import get_settings
from exceptions import RefreshTokenInvalidError
from models.user import User
from schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from schemas.email import EmailVerificationData
from services.auth import AuthService
from services.verification_code import (
    EmailVerificationService,
    PasswordResetService,
)

router = APIRouter(prefix='/auth', tags=['Authentication'])

settings = get_settings()


@router.post(
    '/register',
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: RegisterRequest,
                   service: AuthService = Depends(get_auth_service)
                   ) -> RegisterResponse:
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
async def login(data: LoginRequest,
                request: Request,
                response: Response,
                service: AuthService = Depends(get_auth_service)
                ) -> TokenResponse:
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
        expires_in=int(settings.access_token_lifetime.total_seconds()),
    )


@router.post(
    '/tokens/refresh',
    response_model=TokenResponse,
)
async def refresh(request: Request,
                  response: Response,
                  service: AuthService = Depends(get_auth_service)
                  ) -> TokenResponse:
    refresh_token = request.cookies.get(settings.refresh_token_cookie.name)

    if refresh_token is None:
        raise RefreshTokenInvalidError

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
        expires_in=int(settings.access_token_lifetime.total_seconds()),
    )


@router.post(
    '/logout',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(request: Request,
                 response: Response,
                 service: AuthService = Depends(get_auth_service)
                 ) -> None:
    refresh_token = request.cookies.get(settings.refresh_token_cookie.name)

    if refresh_token is not None:
        await service.logout(refresh_token)

    response.delete_cookie(
        key=settings.refresh_token_cookie.name,
        path=settings.refresh_token_cookie.path,
    )


@router.post(
    '/logout-all',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(current_user: User = Depends(get_current_user),
                     service: AuthService = Depends(get_auth_service)
                     ) -> None:
    await service.logout_all(current_user.id)


@router.get(
    '/me',
    response_model=UserResponse,
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    '/email/approval',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def approve_email(
    data: EmailVerificationData,
    current_user: User = Depends(get_unverified_current_user),
    service: EmailVerificationService = Depends(get_email_verification_service),
) -> None:
    await service.verify(
        user_id=current_user.id,
        code=data.code,
    )


@router.post(
    '/password/reset/request',
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(data: PasswordResetRequest,
                                 service: AuthService = Depends(get_auth_service)
                                 ) -> None:
    await service.request_password_reset(
        email=data.email,
    )


@router.post(
    '/password/reset/confirm',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    service: PasswordResetService = Depends(get_password_reset_service),
) -> None:
    await service.reset(
        email=data.email,
        code=data.code,
        password=data.password,
    )
