from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.schemas.common import ApiResponse
from app.services.auth_logic import AuthService, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, session: AsyncSession = Depends(get_db)):
    user = await AuthService.register_user(session, request)
    return ApiResponse(success=True, message="User registered successfully", data=user)


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(request: UserLoginRequest, session: AsyncSession = Depends(get_db)):
    token_resp = await AuthService.login(session, request)
    return ApiResponse(success=True, message="Login successful", data=token_resp)


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_profile(current_user: User = Depends(get_current_user)):
    user_dto = UserResponse.model_validate(current_user)
    return ApiResponse(success=True, data=user_dto)
