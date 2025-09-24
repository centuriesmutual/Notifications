"""
Dropbox Advanced integration for file storage and management
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import dropbox
from dropbox.files import WriteMode, UploadSessionStartResult, UploadSessionCursor, CommitInfo
from dropbox.exceptions import ApiError, AuthError
from dropbox.sharing import SharedLinkSettings, RequestedVisibility

from app.config import get_settings

logger = logging.getLogger(__name__)


class DropboxManager:
    """Manages Dropbox Advanced operations for file storage and sharing"""
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize Dropbox manager with access token"""
        settings = get_settings()
        self.access_token = access_token or settings.dropbox_access_token
        self.dbx = dropbox.Dropbox(self.access_token)
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes
        self.chunk_size = 4 * 1024 * 1024  # 4MB chunks for large file uploads
        
    def test_connection(self) -> bool:
        """Test Dropbox API connection"""
        try:
            self.dbx.users_get_current_account()
            logger.info("Dropbox connection successful")
            return True
        except (AuthError, ApiError) as e:
            logger.error(f"Dropbox connection failed: {e}")
            return False
    
    def setup_client_folder(self, client_id: str) -> bool:
        """Create folder structure for new client"""
        try:
            folders = [
                f"/clients/{client_id}/messages",
                f"/clients/{client_id}/documents", 
                f"/clients/{client_id}/audit",
                f"/clients/{client_id}/templates"
            ]
            
            for folder in folders:
                try:
                    self.dbx.files_create_folder_v2(folder)
                    logger.info(f"Created folder: {folder}")
                except ApiError as e:
                    if "path/conflict/folder" not in str(e):
                        logger.error(f"Failed to create folder {folder}: {e}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Error setting up client folder for {client_id}: {e}")
            return False
    
    def upload_json(self, path: str, data: Dict[str, Any]) -> bool:
        """Upload JSON data to Dropbox"""
        try:
            json_data = json.dumps(data, indent=2, default=str)
            self.dbx.files_upload(
                json_data.encode('utf-8'),
                path,
                mode=WriteMode('overwrite')
            )
            logger.info(f"Uploaded JSON to: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload JSON to {path}: {e}")
            return False
    
    def download_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Download and parse JSON from Dropbox"""
        try:
            _, response = self.dbx.files_download(path)
            json_data = response.content.decode('utf-8')
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Failed to download JSON from {path}: {e}")
            return None
    
    def upload_file(self, file_data: bytes, path: str, filename: str) -> bool:
        """Upload file to Dropbox with chunked upload for large files"""
        try:
            file_size = len(file_data)
            full_path = f"{path}/{filename}"
            
            if file_size > self.chunk_size:
                return self._upload_large_file(file_data, full_path)
            else:
                return self._upload_small_file(file_data, full_path)
                
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            return False
    
    def _upload_small_file(self, file_data: bytes, path: str) -> bool:
        """Upload small file directly"""
        try:
            self.dbx.files_upload(
                file_data,
                path,
                mode=WriteMode('overwrite')
            )
            logger.info(f"Uploaded small file to: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload small file to {path}: {e}")
            return False
    
    def _upload_large_file(self, file_data: bytes, path: str) -> bool:
        """Upload large file using upload session"""
        try:
            # Start upload session
            session_start_result = self.dbx.files_upload_session_start(
                file_data[:self.chunk_size]
            )
            
            cursor = UploadSessionCursor(
                session_id=session_start_result.session_id,
                offset=len(file_data[:self.chunk_size])
            )
            
            # Upload remaining chunks
            offset = self.chunk_size
            while offset < len(file_data):
                chunk_size = min(self.chunk_size, len(file_data) - offset)
                chunk = file_data[offset:offset + chunk_size]
                
                if offset + chunk_size >= len(file_data):
                    # Final chunk
                    self.dbx.files_upload_session_finish(
                        chunk,
                        cursor,
                        CommitInfo(path=path)
                    )
                else:
                    # Intermediate chunk
                    self.dbx.files_upload_session_append_v2(
                        chunk,
                        cursor
                    )
                    cursor.offset += len(chunk)
                
                offset += chunk_size
            
            logger.info(f"Uploaded large file to: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload large file to {path}: {e}")
            return False
    
    def create_shared_link(self, path: str, password: Optional[str] = None, 
                          expires_at: Optional[datetime] = None) -> Optional[str]:
        """Create secure shared link for file"""
        try:
            settings = SharedLinkSettings(
                requested_visibility=RequestedVisibility.password if password else RequestedVisibility.team,
                link_password=password
            )
            
            shared_link = self.dbx.sharing_create_shared_link_with_settings(
                path=path,
                settings=settings,
                expires=expires_at
            )
            
            logger.info(f"Created shared link for: {path}")
            return shared_link.url
            
        except Exception as e:
            logger.error(f"Failed to create shared link for {path}: {e}")
            return None
    
    def list_folder(self, path: str) -> List[Dict[str, Any]]:
        """List contents of Dropbox folder"""
        try:
            result = self.dbx.files_list_folder(path)
            files = []
            
            for entry in result.entries:
                files.append({
                    'name': entry.name,
                    'path': entry.path_display,
                    'size': getattr(entry, 'size', 0),
                    'modified': getattr(entry, 'server_modified', None),
                    'is_folder': hasattr(entry, 'folder')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list folder {path}: {e}")
            return []
    
    def delete_file(self, path: str) -> bool:
        """Delete file from Dropbox"""
        try:
            self.dbx.files_delete_v2(path)
            logger.info(f"Deleted file: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False
    
    def get_file_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from Dropbox"""
        try:
            metadata = self.dbx.files_get_metadata(path)
            return {
                'name': metadata.name,
                'path': metadata.path_display,
                'size': getattr(metadata, 'size', 0),
                'modified': getattr(metadata, 'server_modified', None),
                'content_hash': getattr(metadata, 'content_hash', None)
            }
        except Exception as e:
            logger.error(f"Failed to get metadata for {path}: {e}")
            return None
    
    def setup_document_templates(self) -> bool:
        """Create shared templates for common insurance documents"""
        try:
            templates = {
                'enrollment_form': '/templates/enrollment-form.pdf',
                'claims_form': '/templates/claims-form.pdf', 
                'beneficiary_form': '/templates/beneficiary-form.pdf',
                'policy_document': '/templates/policy-document.pdf'
            }
            
            for template_name, path in templates.items():
                # Create template folder if it doesn't exist
                try:
                    self.dbx.files_create_folder_v2('/templates')
                except ApiError:
                    pass  # Folder already exists
                
                # Create template metadata
                template_data = {
                    'name': template_name,
                    'path': path,
                    'created_date': datetime.utcnow().isoformat(),
                    'description': f"Template for {template_name.replace('_', ' ').title()}"
                }
                
                self.upload_json(f"/templates/{template_name}.json", template_data)
                logger.info(f"Created template: {template_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup document templates: {e}")
            return False
    
    def archive_message(self, client_id: str, message_id: str, message_data: Dict[str, Any]) -> bool:
        """Archive message to client's message folder"""
        try:
            archive_path = f"/clients/{client_id}/messages/{message_id}.json"
            return self.upload_json(archive_path, message_data)
        except Exception as e:
            logger.error(f"Failed to archive message {message_id}: {e}")
            return False
    
    def get_client_metadata(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client metadata from Dropbox"""
        try:
            metadata_path = f"/clients/{client_id}/metadata.json"
            return self.download_json(metadata_path)
        except Exception as e:
            logger.error(f"Failed to get client metadata for {client_id}: {e}")
            return None
    
    def update_client_metadata(self, client_id: str, metadata: Dict[str, Any]) -> bool:
        """Update client metadata in Dropbox"""
        try:
            metadata_path = f"/clients/{client_id}/metadata.json"
            return self.upload_json(metadata_path, metadata)
        except Exception as e:
            logger.error(f"Failed to update client metadata for {client_id}: {e}")
            return False
