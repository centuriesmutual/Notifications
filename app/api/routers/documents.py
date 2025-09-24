"""
Document management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io

from app.models import DocumentCreate, DocumentResponse, DocumentType
from app.api.dependencies import DocumentDep
from app.services.document_manager import DocumentManager

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document(
    client_id: str = Form(...),
    document_type: str = Form(...),
    expires_hours: int = Form(24),
    file: UploadFile = File(...),
    document_manager: DocumentManager = DocumentDep
):
    """Upload document for client"""
    try:
        # Validate document type
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {document_type}"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Upload document
        result = document_manager.handle_document_upload(
            client_id=client_id,
            file_data=file_data,
            document_type=doc_type,
            filename=file.filename
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to upload document"
            )
        
        return {
            "message": "Document uploaded successfully",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "uploaded_at": result["uploaded_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/{client_id}/list", response_model=List[dict])
async def list_client_documents(
    client_id: str,
    document_manager: DocumentManager = DocumentDep
):
    """List all documents for a client"""
    try:
        documents = document_manager.list_client_documents(client_id)
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )


@router.get("/{client_id}/{document_id}/download")
async def download_document(
    client_id: str,
    document_id: str,
    document_manager: DocumentManager = DocumentDep
):
    """Download document for client"""
    try:
        document = document_manager.get_document(client_id, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Create streaming response
        file_data = document["file_data"]
        filename = document["filename"]
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading document: {str(e)}"
        )


@router.post("/{client_id}/{document_id}/share", response_model=dict)
async def create_document_share_link(
    client_id: str,
    document_id: str,
    expires_hours: int = 24,
    document_manager: DocumentManager = DocumentDep
):
    """Create shareable link for document"""
    try:
        share_info = document_manager.create_document_share_link(
            client_id=client_id,
            document_id=document_id,
            expires_hours=expires_hours
        )
        
        if not share_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create share link"
            )
        
        return {
            "message": "Share link created successfully",
            "shared_link": share_info["shared_link"],
            "password": share_info["password"],
            "expires_at": share_info["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating share link: {str(e)}"
        )


@router.delete("/{client_id}/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    client_id: str,
    document_id: str,
    document_manager: DocumentManager = DocumentDep
):
    """Delete document"""
    try:
        success = document_manager.delete_document(client_id, document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete document"
            )
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


@router.get("/templates", response_model=List[dict])
async def get_document_templates(
    document_manager: DocumentManager = DocumentDep
):
    """Get available document templates"""
    try:
        templates = document_manager.get_document_templates()
        return templates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document templates: {str(e)}"
        )


@router.post("/{client_id}/create-from-template", response_model=dict)
async def create_document_from_template(
    client_id: str,
    template_name: str,
    custom_data: dict,
    document_manager: DocumentManager = DocumentDep
):
    """Create document from template with custom data"""
    try:
        result = document_manager.create_document_from_template(
            client_id=client_id,
            template_name=template_name,
            custom_data=custom_data
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create document from template"
            )
        
        return {
            "message": "Document created from template successfully",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "uploaded_at": result["uploaded_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating document from template: {str(e)}"
        )
