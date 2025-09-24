"""
Webhook management system for document verification and audit tracking
"""

import json
import logging
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs

import httpx

from app.config import get_settings
from app.models import WebhookPayload
from app.services.dropbox_manager import DropboxManager

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages webhook processing for document verification and audit tracking"""
    
    def __init__(self, dropbox_mgr: DropboxManager):
        """Initialize webhook manager with Dropbox manager"""
        self.dropbox = dropbox_mgr
        self.settings = get_settings()
        self.webhook_secret = self.settings.webhook_secret
        self.base_url = self.settings.webhook_base_url
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature for security"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def process_dropbox_webhook(self, payload: Dict[str, Any]) -> bool:
        """Process Dropbox webhook payload"""
        try:
            webhook_type = payload.get('webhook_type')
            
            if webhook_type == 'file_shared':
                return self._handle_file_shared(payload)
            elif webhook_type == 'file_viewed':
                return self._handle_file_viewed(payload)
            elif webhook_type == 'file_downloaded':
                return self._handle_file_downloaded(payload)
            elif webhook_type == 'file_updated':
                return self._handle_file_updated(payload)
            else:
                logger.warning(f"Unknown webhook type: {webhook_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing Dropbox webhook: {e}")
            return False
    
    def _handle_file_shared(self, payload: Dict[str, Any]) -> bool:
        """Handle file shared webhook"""
        try:
            file_info = payload.get('file_info', {})
            file_path = file_info.get('path_display', '')
            
            # Extract client ID from path
            client_id = self._extract_client_id_from_path(file_path)
            if not client_id:
                logger.warning(f"Could not extract client ID from path: {file_path}")
                return False
            
            # Create audit log
            audit_log = {
                'action': 'file_shared',
                'client_id': client_id,
                'file_path': file_path,
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_payload': payload
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/webhook_file_shared_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                audit_log
            )
            
            logger.info(f"Processed file shared webhook for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling file shared webhook: {e}")
            return False
    
    def _handle_file_viewed(self, payload: Dict[str, Any]) -> bool:
        """Handle file viewed webhook"""
        try:
            file_info = payload.get('file_info', {})
            file_path = file_info.get('path_display', '')
            
            # Extract client ID from path
            client_id = self._extract_client_id_from_path(file_path)
            if not client_id:
                logger.warning(f"Could not extract client ID from path: {file_path}")
                return False
            
            # Create audit log
            audit_log = {
                'action': 'file_viewed',
                'client_id': client_id,
                'file_path': file_path,
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_payload': payload
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/webhook_file_viewed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                audit_log
            )
            
            # Update document access count if it's a document
            self._update_document_access_count(client_id, file_path)
            
            logger.info(f"Processed file viewed webhook for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling file viewed webhook: {e}")
            return False
    
    def _handle_file_downloaded(self, payload: Dict[str, Any]) -> bool:
        """Handle file downloaded webhook"""
        try:
            file_info = payload.get('file_info', {})
            file_path = file_info.get('path_display', '')
            
            # Extract client ID from path
            client_id = self._extract_client_id_from_path(file_path)
            if not client_id:
                logger.warning(f"Could not extract client ID from path: {file_path}")
                return False
            
            # Create audit log
            audit_log = {
                'action': 'file_downloaded',
                'client_id': client_id,
                'file_path': file_path,
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_payload': payload
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/webhook_file_downloaded_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                audit_log
            )
            
            logger.info(f"Processed file downloaded webhook for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling file downloaded webhook: {e}")
            return False
    
    def _handle_file_updated(self, payload: Dict[str, Any]) -> bool:
        """Handle file updated webhook"""
        try:
            file_info = payload.get('file_info', {})
            file_path = file_info.get('path_display', '')
            
            # Extract client ID from path
            client_id = self._extract_client_id_from_path(file_path)
            if not client_id:
                logger.warning(f"Could not extract client ID from path: {file_path}")
                return False
            
            # Create audit log
            audit_log = {
                'action': 'file_updated',
                'client_id': client_id,
                'file_path': file_path,
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_payload': payload
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/webhook_file_updated_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                audit_log
            )
            
            logger.info(f"Processed file updated webhook for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling file updated webhook: {e}")
            return False
    
    def _extract_client_id_from_path(self, file_path: str) -> Optional[str]:
        """Extract client ID from file path"""
        try:
            # Expected path format: /clients/{client_id}/...
            path_parts = file_path.split('/')
            if len(path_parts) >= 3 and path_parts[1] == 'clients':
                return path_parts[2]
            return None
        except Exception as e:
            logger.error(f"Error extracting client ID from path {file_path}: {e}")
            return None
    
    def _update_document_access_count(self, client_id: str, file_path: str) -> None:
        """Update document access count in metadata"""
        try:
            # Find document metadata file
            documents_folder = f"/clients/{client_id}/documents/metadata"
            metadata_files = self.dropbox.list_folder(documents_folder)
            
            for file_info in metadata_files:
                if file_info['name'].endswith('.json'):
                    metadata = self.dropbox.download_json(file_info['path'])
                    if metadata and metadata.get('uploaded_path') == file_path:
                        # Update access count
                        metadata['access_count'] = metadata.get('access_count', 0) + 1
                        metadata['last_accessed'] = datetime.utcnow().isoformat()
                        
                        # Save updated metadata
                        self.dropbox.upload_json(file_info['path'], metadata)
                        break
                        
        except Exception as e:
            logger.error(f"Error updating document access count: {e}")
    
    def send_webhook_notification(self, client_id: str, event_type: str, 
                                resource_id: str, metadata: Dict[str, Any]) -> bool:
        """Send webhook notification to external systems"""
        try:
            webhook_payload = {
                'event_type': event_type,
                'client_id': client_id,
                'resource_id': resource_id,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            
            # In a real implementation, you would send this to external webhook endpoints
            # For now, we'll just log it
            logger.info(f"Webhook notification: {webhook_payload}")
            
            # Archive webhook notification
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/webhook_notification_{event_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                webhook_payload
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
    
    def get_webhook_audit_logs(self, client_id: str, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get webhook audit logs for a client"""
        try:
            audit_logs = []
            audit_folder = f"/clients/{client_id}/audit"
            audit_files = self.dropbox.list_folder(audit_folder)
            
            for file_info in audit_files:
                if file_info['name'].startswith('webhook_'):
                    if event_type and event_type not in file_info['name']:
                        continue
                    
                    audit_data = self.dropbox.download_json(file_info['path'])
                    if audit_data:
                        audit_logs.append({
                            'filename': file_info['name'],
                            'timestamp': audit_data.get('timestamp'),
                            'action': audit_data.get('action'),
                            'data': audit_data
                        })
            
            # Sort by timestamp (newest first)
            audit_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            return audit_logs
            
        except Exception as e:
            logger.error(f"Error getting webhook audit logs: {e}")
            return []
    
    def process_custom_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> bool:
        """Process custom webhook to external system"""
        try:
            async with httpx.AsyncClient() as client:
                response = client.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent webhook to {webhook_url}")
                    return True
                else:
                    logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing custom webhook to {webhook_url}: {e}")
            return False
    
    def setup_webhook_endpoints(self) -> Dict[str, str]:
        """Setup webhook endpoints for different event types"""
        try:
            endpoints = {
                'document_shared': f"{self.base_url}/webhooks/document/shared",
                'document_viewed': f"{self.base_url}/webhooks/document/viewed",
                'document_downloaded': f"{self.base_url}/webhooks/document/downloaded",
                'message_sent': f"{self.base_url}/webhooks/message/sent",
                'client_registered': f"{self.base_url}/webhooks/client/registered"
            }
            
            # Store endpoint configuration
            self.dropbox.upload_json("/webhook_endpoints.json", endpoints)
            
            logger.info("Webhook endpoints configured")
            return endpoints
            
        except Exception as e:
            logger.error(f"Error setting up webhook endpoints: {e}")
            return {}
    
    def validate_webhook_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate webhook payload structure"""
        try:
            required_fields = ['event_type', 'timestamp']
            
            for field in required_fields:
                if field not in payload:
                    logger.error(f"Missing required field in webhook payload: {field}")
                    return False
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                logger.error("Invalid timestamp format in webhook payload")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating webhook payload: {e}")
            return False
    
    def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook processing statistics"""
        try:
            # This would typically query a database or cache
            # For now, return basic stats
            return {
                'total_webhooks_processed': 0,
                'successful_webhooks': 0,
                'failed_webhooks': 0,
                'last_webhook_processed': None,
                'webhook_types': {
                    'file_shared': 0,
                    'file_viewed': 0,
                    'file_downloaded': 0,
                    'file_updated': 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting webhook statistics: {e}")
            return {}
