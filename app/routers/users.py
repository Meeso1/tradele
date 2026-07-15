from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserResponse(BaseModel):
    id: str


@router.post("", response_model=CreateUserResponse, status_code=201)
def create_user(user_service: UserServiceDep) -> CreateUserResponse:
    """Create a new (anonymous) user and return its ID."""
    user_id = user_service.create()
    return CreateUserResponse(id=user_id)
