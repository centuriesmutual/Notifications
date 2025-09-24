"""
Webhook management API endpoints
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse

from app.models import WebhookPayload
from app.api.dependencies import WebhookDep
from app.services.webhook_manager import WebhookManager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/dropbox", status_code=status.HTTP_200_OK)
async def process_dropbox_webhook(
    request: Request,
    webhook_manager: WebhookManager = WebhookDep
):
    """Process Dropbox webhook"""
    try:
        # Get request body
        body = await request.body()
        
        # Get signature header
        signature = request.headers.get("X-Dropbox-Signature", "")
        
        # Verify signature
        if not webhook_manager.verify_webhook_signature(body, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse JSON payload
        import json
        payload = json.loads(body.decode('utf-8'))
        
        # Process webhook
        success = webhook_manager.process_dropbox_webhook(payload)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process webhook"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook processed successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/notify", status_code=status.HTTP_200_OK)
async def send_webhook_notification(
    client_id: str,
    event_type: str,
    resource_id: str,
    metadata: Dict[str, Any],
    webhook_manager: WebhookManager = WebhookDep
):
    """Send webhook notification to external systems"""
    try:
        success = webhook_manager.send_webhook_notification(
            client_id=client_id,
            event_type=event_type,
            resource_id=resource_id,
            metadata=metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send webhook notification"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Webhook notification sent successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending webhook notification: {str(e)}"
        )


@router.post("/custom", status_code=status.HTTP_200_OK)
async def process_custom_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    webhook_manager: WebhookManager = WebhookDep
):
    """Process custom webhook to external system"""
    try:
        # Validate payload
        if not webhook_manager.validate_webhook_payload(payload):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload"
            )
        
        success = webhook_manager.process_custom_webhook(webhook_url, payload)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process custom webhook"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Custom webhook processed successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing custom webhook: {str(e)}"
        )


@router.get("/{client_id}/audit", response_model=List[dict])
async def get_webhook_audit_logs(
    client_id: str,
    event_type: str = None,
    webhook_manager: WebhookManager = WebhookDep
):
    """Get webhook audit logs for a client"""
    try:
        logs = webhook_manager.get_webhook_audit_logs(client_id, event_type)
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting webhook audit logs: {str(e)}"
        )


@router.get("/endpoints", response_model=Dict[str, str])
async def get_webhook_endpoints(
    webhook_manager: WebhookManager = WebhookDep
):
    """Get configured webhook endpoints"""
    try:
        endpoints = webhook_manager.setup_webhook_endpoints()
        return endpoints
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting webhook endpoints: {str(e)}"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_webhook_statistics(
    webhook_manager: WebhookManager = WebhookDep
):
    """Get webhook processing statistics"""
    try:
        stats = webhook_manager.get_webhook_statistics()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting webhook statistics: {str(e)}"
        )
