from fastapi import APIRouter, HTTPException, status

from app.dependencies import AuthServiceDep, UserServiceDep
from app.dtos.auth_dtos import IssueTokenRequest, IssueTokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=IssueTokenResponse)
def issue_token(
    request: IssueTokenRequest,
    user_service: UserServiceDep,
    auth_service: AuthServiceDep,
) -> IssueTokenResponse:
    """Issue a signed access token asserting the given user ID.

    This performs no real authentication - it just mints a token for a
    user ID that must already exist, as a stand-in until a real auth flow
    (e.g. Auth0) is added.
    """
    if not user_service.exists(request.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return IssueTokenResponse(access_token=auth_service.create_access_token(request.user_id))
