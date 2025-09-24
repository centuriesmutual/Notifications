"""
Message management API endpoints
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import JSONResponse

from app.models import MessageCreate, MessageResponse, MessageType
from app.api.dependencies import MessagePublisherDep, MessageConsumerDep
from app.services.message_publisher import MessagePublisher, MessageLimitExceededException
from app.services.message_consumer import MessageConsumer

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/send", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    publisher: MessagePublisher = MessagePublisherDep
):
    """Send message to client"""
    try:
        result = publisher.send_client_message(message_data.client_id, message_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send message"
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Message sent successfully",
                "message_id": result["message_id"],
                "client_id": result["client_id"],
                "timestamp": result["timestamp"]
            }
        )
    except MessageLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


@router.post("/send-bulk", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_bulk_messages(
    messages: List[Dict[str, Any]],
    publisher: MessagePublisher = MessagePublisherDep
):
    """Send multiple messages in batch"""
    try:
        results = publisher.send_bulk_messages(messages)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Bulk message send completed",
                "results": results
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending bulk messages: {str(e)}"
        )


@router.post("/send-notification", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_notification(
    client_id: str,
    notification_type: str,
    content: str,
    priority: int = 0,
    publisher: MessagePublisher = MessagePublisherDep
):
    """Send high-priority notification to client"""
    try:
        result = publisher.send_notification(client_id, notification_type, content, priority)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send notification"
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Notification sent successfully",
                "message_id": result["message_id"],
                "client_id": result["client_id"],
                "timestamp": result["timestamp"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/workflow", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_workflow_message(
    routing_key: str,
    message_type: str,
    content: str,
    metadata: Dict[str, Any] = None,
    publisher: MessagePublisher = MessagePublisherDep
):
    """Send workflow message to topic exchange"""
    try:
        result = publisher.send_workflow_message(routing_key, message_type, content, metadata)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send workflow message"
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Workflow message sent successfully",
                "message_id": result["message_id"],
                "routing_key": result["routing_key"],
                "timestamp": result["timestamp"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending workflow message: {str(e)}"
        )


@router.get("/{client_id}/stats", response_model=dict)
async def get_message_stats(
    client_id: str,
    publisher: MessagePublisher = MessagePublisherDep
):
    """Get message statistics for client"""
    try:
        stats = publisher.get_message_stats(client_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting message stats: {str(e)}"
        )


@router.post("/{message_id}/resend", status_code=status.HTTP_200_OK)
async def resend_failed_message(
    message_id: str,
    client_id: str,
    publisher: MessagePublisher = MessagePublisherDep
):
    """Resend a previously failed message"""
    try:
        success = publisher.resend_failed_message(message_id, client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to resend message"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Message resent successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resending message: {str(e)}"
        )


@router.get("/processing/stats", response_model=dict)
async def get_processing_stats(
    consumer: MessageConsumer = MessageConsumerDep
):
    """Get message processing statistics"""
    try:
        stats = consumer.get_message_processing_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting processing stats: {str(e)}"
        )
