from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import ApiKeyServiceDep, ServiceAccessDep, require_service_access
from app.dtos.api_key_dtos import ApiKeyResponse, CreateApiKeyRequest, CreateApiKeyResponse
from app.models.api_key import ApiKey
from app.services.api_key_service import AuthenticatingKeyDeactivationError

router = APIRouter(prefix="/api-keys", tags=["api-keys"], dependencies=[Depends(require_service_access)])


@router.post("", response_model=CreateApiKeyResponse, status_code=201)
def create_api_key(
    request: CreateApiKeyRequest,
    auth_context: ServiceAccessDep,
    api_key_service: ApiKeyServiceDep,
) -> CreateApiKeyResponse:
    """Create a new API key for the service account.

    The key value is returned once and never stored in plaintext. Present
    it via HTTP Basic auth - `authorization` contains the ready-to-use
    header value.
    """
    assert auth_context.api_key_id is not None  # service access requires API key auth
    api_key, secret = api_key_service.create_key(
        auth_context.user_id,
        request.name,
        created_by_key=auth_context.api_key_id,
    )
    assert secret is not None  # secrets are only omitted for hash-bootstrapped keys
    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        secret=secret,
        authorization=api_key_service.format_authorization_header(api_key.id, secret),
        created_at=api_key.created_at,
        created_by_key=api_key.created_by_key,
    )


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    auth_context: ServiceAccessDep,
    api_key_service: ApiKeyServiceDep,
) -> list[ApiKeyResponse]:
    """List the service account's API keys, active and deactivated."""
    return [_to_response(api_key) for api_key in api_key_service.list_keys(auth_context.user_id)]


@router.post("/{key_id}/deactivate", response_model=ApiKeyResponse)
def deactivate_api_key(
    key_id: str,
    auth_context: ServiceAccessDep,
    api_key_service: ApiKeyServiceDep,
) -> ApiKeyResponse:
    """Deactivate an API key. Keys are never deleted, only deactivated."""
    try:
        api_key = api_key_service.deactivate_key(
            auth_context.user_id,
            key_id,
            authenticating_key_id=auth_context.api_key_id,
        )
    except AuthenticatingKeyDeactivationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate the key that authenticated this request",
        ) from error

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    return _to_response(api_key)


def _to_response(api_key: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        created_by_key=api_key.created_by_key,
        created_at=api_key.created_at,
        deactivated_at=api_key.deactivated_at,
    )
