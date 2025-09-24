"""
Client management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.models import ClientCreate, ClientResponse
from app.api.dependencies import ClientOnboardingDep
from app.services.client_onboarding import ClientOnboarding

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_client(
    client_data: ClientCreate,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Register a new client"""
    try:
        result = onboarding.register_client(client_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register client"
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Client registered successfully",
                "client_id": result["client_id"],
                "status": result["status"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering client: {str(e)}"
        )


@router.post("/{client_id}/complete-onboarding", status_code=status.HTTP_200_OK)
async def complete_onboarding(
    client_id: str,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Complete client onboarding process"""
    try:
        success = onboarding.complete_onboarding(client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to complete onboarding"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Onboarding completed successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing onboarding: {str(e)}"
        )


@router.get("/{client_id}/status", response_model=dict)
async def get_client_status(
    client_id: str,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Get client status and information"""
    try:
        status_info = onboarding.get_client_status(client_id)
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting client status: {str(e)}"
        )


@router.post("/{client_id}/reset-limits", status_code=status.HTTP_200_OK)
async def reset_daily_limits(
    client_id: str,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Reset daily message limits for client"""
    try:
        success = onboarding.reset_daily_limits(client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reset daily limits"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Daily limits reset successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting daily limits: {str(e)}"
        )


@router.post("/{client_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_client(
    client_id: str,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Deactivate client account"""
    try:
        success = onboarding.deactivate_client(client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate client"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Client deactivated successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deactivating client: {str(e)}"
        )


@router.post("/{client_id}/reactivate", status_code=status.HTTP_200_OK)
async def reactivate_client(
    client_id: str,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Reactivate client account"""
    try:
        success = onboarding.reactivate_client(client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reactivate client"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Client reactivated successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating client: {str(e)}"
        )


@router.put("/{client_id}/update", status_code=status.HTTP_200_OK)
async def update_client_info(
    client_id: str,
    updates: dict,
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Update client information"""
    try:
        success = onboarding.update_client_info(client_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update client information"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Client information updated successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating client information: {str(e)}"
        )


@router.get("/", response_model=List[dict])
async def get_all_clients(
    onboarding: ClientOnboarding = ClientOnboardingDep
):
    """Get list of all clients"""
    try:
        clients = onboarding.get_all_clients()
        return clients
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting clients: {str(e)}"
        )
