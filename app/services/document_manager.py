"""
Document management system for secure file sharing and handling
"""

import json
import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import get_settings
from app.models import DocumentCreate, DocumentResponse, DocumentType
from app.services.dropbox_manager import DropboxManager

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document storage, encryption, and secure sharing"""
    
    def __init__(self, dropbox_mgr: DropboxManager):
        """Initialize document manager with Dropbox manager"""
        self.dropbox = dropbox_mgr
        self.settings = get_settings()
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        try:
            # Use configured encryption key or generate from secret
            key_material = self.settings.encryption_key.encode()
            salt = b'centuries_mutual_salt'  # In production, use random salt
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key_material))
            return key
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            raise
    
    def encrypt_document(self, file_data: bytes) -> bytes:
        """Encrypt document data"""
        try:
            return self.cipher_suite.encrypt(file_data)
        except Exception as e:
            logger.error(f"Error encrypting document: {e}")
            raise
    
    def decrypt_document(self, encrypted_data: bytes) -> bytes:
        """Decrypt document data"""
        try:
            return self.cipher_suite.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Error decrypting document: {e}")
            raise
    
    def generate_secure_password(self, length: int = 12) -> str:
        """Generate secure password for document access"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_secure_document_link(self, client_id: str, document_path: str, 
                                  expires_hours: int = 24) -> Optional[Dict[str, str]]:
        """Create time-limited secure link for document access"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            password = self.generate_secure_password()
            
            # Create shared link with security settings
            shared_link = self.dropbox.create_shared_link(
                path=document_path,
                password=password,
                expires_at=expires_at
            )
            
            if not shared_link:
                logger.error(f"Failed to create shared link for {document_path}")
                return None
            
            # Log document access creation
            access_log = {
                'client_id': client_id,
                'document_path': document_path,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat(),
                'access_attempts': 0,
                'password_hash': hash(password)  # Store hash for verification
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/document_access_{uuid4().hex}.json",
                access_log
            )
            
            logger.info(f"Created secure document link for {document_path}")
            return {
                'shared_link': shared_link,
                'password': password,
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating secure document link: {e}")
            return None
    
    def handle_document_upload(self, client_id: str, file_data: bytes, 
                             document_type: DocumentType, filename: str) -> Optional[Dict[str, Any]]:
        """Handle client document uploads with encryption"""
        try:
            # Encrypt file data
            encrypted_data = self.encrypt_document(file_data)
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"document_{document_type.value}_{timestamp}_{filename}"
            upload_path = f"/clients/{client_id}/documents/{unique_filename}"
            
            # Upload to Dropbox
            if not self.dropbox.upload_file(encrypted_data, f"/clients/{client_id}/documents", unique_filename):
                logger.error(f"Failed to upload document {unique_filename}")
                return None
            
            # Create metadata record
            metadata = {
                'document_id': str(uuid4()),
                'client_id': client_id,
                'document_type': document_type.value,
                'original_filename': filename,
                'stored_filename': unique_filename,
                'file_size': len(file_data),
                'encrypted_size': len(encrypted_data),
                'uploaded_path': upload_path,
                'uploaded_at': datetime.utcnow().isoformat(),
                'encryption_method': 'AES-256-GCM',
                'access_count': 0,
                'is_encrypted': True
            }
            
            # Store metadata
            metadata_path = f"/clients/{client_id}/documents/metadata/{unique_filename}.json"
            if not self.dropbox.upload_json(metadata_path, metadata):
                logger.error(f"Failed to store document metadata for {unique_filename}")
                return None
            
            logger.info(f"Successfully uploaded document {unique_filename} for client {client_id}")
            return {
                'document_id': metadata['document_id'],
                'filename': unique_filename,
                'file_size': len(file_data),
                'uploaded_at': metadata['uploaded_at']
            }
            
        except Exception as e:
            logger.error(f"Error handling document upload: {e}")
            return None
    
    def get_document(self, client_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document with decryption"""
        try:
            # Find document metadata
            documents_folder = f"/clients/{client_id}/documents/metadata"
            metadata_files = self.dropbox.list_folder(documents_folder)
            
            document_metadata = None
            for file_info in metadata_files:
                if file_info['name'].endswith('.json'):
                    metadata = self.dropbox.download_json(file_info['path'])
                    if metadata and metadata.get('document_id') == document_id:
                        document_metadata = metadata
                        break
            
            if not document_metadata:
                logger.error(f"Document metadata not found for {document_id}")
                return None
            
            # Download encrypted file
            encrypted_data = self.dropbox.download_file(document_metadata['uploaded_path'])
            if not encrypted_data:
                logger.error(f"Failed to download document {document_id}")
                return None
            
            # Decrypt file
            decrypted_data = self.decrypt_document(encrypted_data)
            
            # Update access count
            document_metadata['access_count'] += 1
            document_metadata['last_accessed'] = datetime.utcnow().isoformat()
            
            metadata_path = f"/clients/{client_id}/documents/metadata/{document_metadata['stored_filename']}.json"
            self.dropbox.upload_json(metadata_path, document_metadata)
            
            logger.info(f"Retrieved document {document_id} for client {client_id}")
            return {
                'document_id': document_id,
                'filename': document_metadata['original_filename'],
                'file_data': decrypted_data,
                'file_size': document_metadata['file_size'],
                'document_type': document_metadata['document_type'],
                'uploaded_at': document_metadata['uploaded_at'],
                'access_count': document_metadata['access_count']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    def create_document_share_link(self, client_id: str, document_id: str, 
                                 expires_hours: int = 24) -> Optional[Dict[str, str]]:
        """Create shareable link for document"""
        try:
            # Get document metadata
            documents_folder = f"/clients/{client_id}/documents/metadata"
            metadata_files = self.dropbox.list_folder(documents_folder)
            
            document_metadata = None
            for file_info in metadata_files:
                if file_info['name'].endswith('.json'):
                    metadata = self.dropbox.download_json(file_info['path'])
                    if metadata and metadata.get('document_id') == document_id:
                        document_metadata = metadata
                        break
            
            if not document_metadata:
                logger.error(f"Document metadata not found for {document_id}")
                return None
            
            # Create secure shared link
            share_info = self.create_secure_document_link(
                client_id=client_id,
                document_path=document_metadata['uploaded_path'],
                expires_hours=expires_hours
            )
            
            if not share_info:
                return None
            
            # Update document metadata with share info
            document_metadata['shared_link'] = share_info['shared_link']
            document_metadata['share_expires_at'] = share_info['expires_at']
            document_metadata['last_shared'] = datetime.utcnow().isoformat()
            
            metadata_path = f"/clients/{client_id}/documents/metadata/{document_metadata['stored_filename']}.json"
            self.dropbox.upload_json(metadata_path, document_metadata)
            
            logger.info(f"Created share link for document {document_id}")
            return share_info
            
        except Exception as e:
            logger.error(f"Error creating share link for document {document_id}: {e}")
            return None
    
    def list_client_documents(self, client_id: str) -> List[Dict[str, Any]]:
        """List all documents for a client"""
        try:
            documents = []
            documents_folder = f"/clients/{client_id}/documents/metadata"
            metadata_files = self.dropbox.list_folder(documents_folder)
            
            for file_info in metadata_files:
                if file_info['name'].endswith('.json'):
                    metadata = self.dropbox.download_json(file_info['path'])
                    if metadata:
                        documents.append({
                            'document_id': metadata.get('document_id'),
                            'document_type': metadata.get('document_type'),
                            'original_filename': metadata.get('original_filename'),
                            'file_size': metadata.get('file_size'),
                            'uploaded_at': metadata.get('uploaded_at'),
                            'access_count': metadata.get('access_count', 0),
                            'last_accessed': metadata.get('last_accessed'),
                            'is_shared': bool(metadata.get('shared_link'))
                        })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents for client {client_id}: {e}")
            return []
    
    def delete_document(self, client_id: str, document_id: str) -> bool:
        """Delete document and its metadata"""
        try:
            # Find document metadata
            documents_folder = f"/clients/{client_id}/documents/metadata"
            metadata_files = self.dropbox.list_folder(documents_folder)
            
            document_metadata = None
            metadata_path = None
            for file_info in metadata_files:
                if file_info['name'].endswith('.json'):
                    metadata = self.dropbox.download_json(file_info['path'])
                    if metadata and metadata.get('document_id') == document_id:
                        document_metadata = metadata
                        metadata_path = file_info['path']
                        break
            
            if not document_metadata:
                logger.error(f"Document metadata not found for {document_id}")
                return False
            
            # Delete the encrypted file
            if not self.dropbox.delete_file(document_metadata['uploaded_path']):
                logger.error(f"Failed to delete document file {document_id}")
                return False
            
            # Delete metadata
            if not self.dropbox.delete_file(metadata_path):
                logger.error(f"Failed to delete document metadata {document_id}")
                return False
            
            # Create deletion audit log
            audit_log = {
                'action': 'document_deleted',
                'client_id': client_id,
                'document_id': document_id,
                'deleted_at': datetime.utcnow().isoformat(),
                'original_filename': document_metadata.get('original_filename'),
                'document_type': document_metadata.get('document_type')
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/document_deletion_{document_id}.json",
                audit_log
            )
            
            logger.info(f"Successfully deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    def get_document_templates(self) -> List[Dict[str, Any]]:
        """Get available document templates"""
        try:
            templates = []
            templates_folder = "/templates"
            template_files = self.dropbox.list_folder(templates_folder)
            
            for file_info in template_files:
                if file_info['name'].endswith('.json'):
                    template_data = self.dropbox.download_json(file_info['path'])
                    if template_data:
                        templates.append({
                            'name': template_data.get('name'),
                            'path': template_data.get('path'),
                            'description': template_data.get('description'),
                            'created_date': template_data.get('created_date')
                        })
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting document templates: {e}")
            return []
    
    def create_document_from_template(self, client_id: str, template_name: str, 
                                    custom_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create document from template with custom data"""
        try:
            # Get template
            template_data = self.dropbox.download_json(f"/templates/{template_name}.json")
            if not template_data:
                logger.error(f"Template {template_name} not found")
                return None
            
            # In a real implementation, you would:
            # 1. Download the template file
            # 2. Apply custom data (e.g., fill PDF forms, merge Word docs)
            # 3. Generate the final document
            # 4. Upload as new document
            
            # For now, create a placeholder document
            document_content = f"Document generated from template {template_name} with custom data: {json.dumps(custom_data)}"
            file_data = document_content.encode('utf-8')
            
            # Upload as new document
            result = self.handle_document_upload(
                client_id=client_id,
                file_data=file_data,
                document_type=DocumentType.POLICY_DOCUMENT,
                filename=f"{template_name}_generated.txt"
            )
            
            if result:
                logger.info(f"Created document from template {template_name} for client {client_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating document from template: {e}")
            return None
