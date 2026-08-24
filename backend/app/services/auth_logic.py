import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, UnauthorizedException, ForbiddenException
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse

security_scheme = HTTPBearer(auto_error=False)


class AuthService:

    @staticmethod
    async def register_user(session: AsyncSession, request: UserRegisterRequest) -> UserResponse:
        existing = await session.scalar(select(User).where(User.email == request.email))
        if existing:
            raise DuplicateResourceException(f"User with email '{request.email}' already exists")

        user = User(
            email=request.email,
            password_hash=get_password_hash(request.password),
            full_name=request.full_name,
            role=request.role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def login(session: AsyncSession, request: UserLoginRequest) -> TokenResponse:
        user = await session.scalar(select(User).where(User.email == request.email))
        if not user or not verify_password(request.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        access_token = create_access_token(
            subject=str(user.id),
            claims={"email": user.email, "role": user.role.value, "name": user.full_name}
        )
        return TokenResponse(
            access_token=access_token,
            expires_in=60 * 24 * 60,
            user=UserResponse.model_validate(user)
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise UnauthorizedException("Authentication token required")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Malformed token payload")
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        raise UnauthorizedException(f"Invalid authentication token: {str(e)}")

    user = await session.get(User, user_id)
    if not user:
        raise UnauthorizedException("User no longer exists")
    return user


def require_role(required_role: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user  # Admin has access to all roles
        if current_user.role != required_role:
            raise ForbiddenException(f"Role '{required_role.value}' required to perform this action")
        return current_user
    return role_checker
