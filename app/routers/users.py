from fastapi import APIRouter

from app.dependencies import UserServiceDep
from app.dtos.user_dtos import CreateUserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=CreateUserResponse, status_code=201)
def create_user(user_service: UserServiceDep) -> CreateUserResponse:
    """Create a new (anonymous) user and return its ID."""
    user_id = user_service.create()
    return CreateUserResponse(id=user_id)
