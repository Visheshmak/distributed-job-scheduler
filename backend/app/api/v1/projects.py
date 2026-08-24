import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException
from app.models.organization import Organization, Project
from app.schemas.project import (
    OrganizationCreateRequest,
    OrganizationResponse,
    ProjectCreateRequest,
    ProjectResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_logic import get_current_user
from app.models.user import User

router = APIRouter(prefix="/projects", tags=["Organizations & Projects"])


@router.post("/organizations", response_model=ApiResponse[OrganizationResponse], status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = await session.scalar(select(Organization).where(Organization.slug == request.slug))
    if existing:
        raise DuplicateResourceException(f"Organization with slug '{request.slug}' already exists")

    org = Organization(name=request.name, slug=request.slug)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return ApiResponse(success=True, data=OrganizationResponse.model_validate(org))


@router.get("/organizations", response_model=ApiResponse[List[OrganizationResponse]])
async def list_organizations(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await session.execute(select(Organization).order_by(Organization.name.asc()))
    orgs = result.scalars().all()
    return ApiResponse(success=True, data=[OrganizationResponse.model_validate(o) for o in orgs])


@router.post("", response_model=ApiResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org = await session.get(Organization, request.organization_id)
    if not org:
        raise ResourceNotFoundException(f"Organization with ID '{request.organization_id}' not found")

    existing = await session.scalar(
        select(Project).where(Project.organization_id == request.organization_id, Project.slug == request.slug)
    )
    if existing:
        raise DuplicateResourceException(f"Project with slug '{request.slug}' already exists in this organization")

    proj = Project(
        organization_id=request.organization_id,
        name=request.name,
        slug=request.slug,
        description=request.description
    )
    session.add(proj)
    await session.commit()
    await session.refresh(proj)
    return ApiResponse(success=True, data=ProjectResponse.model_validate(proj))


@router.get("", response_model=ApiResponse[List[ProjectResponse]])
async def list_projects(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await session.execute(select(Project).order_by(Project.name.asc()))
    projects = result.scalars().all()
    return ApiResponse(success=True, data=[ProjectResponse.model_validate(p) for p in projects])


@router.get("/{project_id}", response_model=ApiResponse[ProjectResponse])
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj = await session.get(Project, project_id)
    if not proj:
        raise ResourceNotFoundException(f"Project with ID '{project_id}' not found")
    return ApiResponse(success=True, data=ProjectResponse.model_validate(proj))
