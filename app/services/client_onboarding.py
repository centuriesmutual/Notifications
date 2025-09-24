"""
Client onboarding workflow for the Centuries Mutual Home App
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from uuid import uuid4

from app.config import get_settings
from app.models import ClientCreate, ClientResponse
from app.services.dropbox_manager import DropboxManager
from app.services.amqp_manager import AMQPManager

logger = logging.getLogger(__name__)


class ClientOnboarding:
    """Handles client registration and onboarding workflow"""
    
    def __init__(self, dropbox_mgr: DropboxManager, amqp_mgr: AMQPManager):
        """Initialize client onboarding with managers"""
        self.dropbox = dropbox_mgr
        self.amqp = amqp_mgr
        self.settings = get_settings()
    
    def register_client(self, client_data: ClientCreate) -> Optional[Dict[str, Any]]:
        """Register new client with full onboarding process"""
        try:
            client_id = client_data.client_id
            
            # Step 1: Create Dropbox client folder structure
            if not self.dropbox.setup_client_folder(client_id):
                logger.error(f"Failed to setup Dropbox folders for client {client_id}")
                return None
            
            # Step 2: Create AMQP client queue
            if not self.amqp.create_client_queue(client_id):
                logger.error(f"Failed to create AMQP queue for client {client_id}")
                return None
            
            # Step 3: Store client metadata
            metadata = {
                'client_id': client_id,
                'email': client_data.email,
                'phone': client_data.phone,
                'first_name': client_data.first_name,
                'last_name': client_data.last_name,
                'registered_date': datetime.utcnow().isoformat(),
                'last_reset': date.today().isoformat(),
                'message_count_today': 0,
                'is_active': True,
                'onboarding_completed': False,
                'custom_metadata': client_data.metadata
            }
            
            if not self.dropbox.update_client_metadata(client_id, metadata):
                logger.error(f"Failed to store client metadata for {client_id}")
                return None
            
            # Step 4: Send welcome message
            welcome_message = {
                'id': str(uuid4()),
                'type': 'enrollment_notification',
                'content': f"Welcome to Centuries Mutual, {client_data.first_name}! Your account has been created successfully.",
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'attachments': []
            }
            
            if not self.amqp.publish_client_message(client_id, welcome_message):
                logger.warning(f"Failed to send welcome message to client {client_id}")
            
            # Step 5: Archive welcome message
            self.dropbox.archive_message(client_id, welcome_message['id'], welcome_message)
            
            logger.info(f"Successfully registered client {client_id}")
            return {
                'client_id': client_id,
                'status': 'registered',
                'message': 'Client registered successfully',
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error registering client {client_data.client_id}: {e}")
            return None
    
    def complete_onboarding(self, client_id: str) -> bool:
        """Mark client onboarding as completed"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            metadata['onboarding_completed'] = True
            metadata['onboarding_completed_date'] = datetime.utcnow().isoformat()
            
            if not self.dropbox.update_client_metadata(client_id, metadata):
                logger.error(f"Failed to update onboarding status for {client_id}")
                return False
            
            # Send onboarding completion notification
            completion_message = {
                'id': str(uuid4()),
                'type': 'system_alert',
                'content': 'Your onboarding process has been completed. You can now access all features.',
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'attachments': []
            }
            
            self.amqp.publish_client_message(client_id, completion_message)
            self.dropbox.archive_message(client_id, completion_message['id'], completion_message)
            
            logger.info(f"Onboarding completed for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing onboarding for client {client_id}: {e}")
            return False
    
    def setup_document_templates(self) -> bool:
        """Create shared templates for common insurance documents"""
        try:
            return self.dropbox.setup_document_templates()
        except Exception as e:
            logger.error(f"Error setting up document templates: {e}")
            return False
    
    def get_client_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client onboarding status and metadata"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                return None
            
            # Get queue information
            queue_info = self.amqp.get_queue_info(f"client.{client_id}")
            
            return {
                'client_id': client_id,
                'onboarding_completed': metadata.get('onboarding_completed', False),
                'registered_date': metadata.get('registered_date'),
                'message_count_today': metadata.get('message_count_today', 0),
                'daily_limit': self.settings.daily_message_limit,
                'is_active': metadata.get('is_active', True),
                'queue_info': queue_info
            }
            
        except Exception as e:
            logger.error(f"Error getting client status for {client_id}: {e}")
            return None
    
    def reset_daily_limits(self, client_id: str) -> bool:
        """Reset daily message limits for client"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            today = date.today().isoformat()
            if metadata.get('last_reset') != today:
                metadata['message_count_today'] = 0
                metadata['last_reset'] = today
                
                if not self.dropbox.update_client_metadata(client_id, metadata):
                    logger.error(f"Failed to reset daily limits for {client_id}")
                    return False
                
                logger.info(f"Reset daily limits for client {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting daily limits for client {client_id}: {e}")
            return False
    
    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate client account"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            metadata['is_active'] = False
            metadata['deactivated_date'] = datetime.utcnow().isoformat()
            
            if not self.dropbox.update_client_metadata(client_id, metadata):
                logger.error(f"Failed to deactivate client {client_id}")
                return False
            
            # Send deactivation notification
            deactivation_message = {
                'id': str(uuid4()),
                'type': 'system_alert',
                'content': 'Your account has been deactivated. Please contact support for assistance.',
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'attachments': []
            }
            
            self.amqp.publish_client_message(client_id, deactivation_message)
            self.dropbox.archive_message(client_id, deactivation_message['id'], deactivation_message)
            
            logger.info(f"Deactivated client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating client {client_id}: {e}")
            return False
    
    def reactivate_client(self, client_id: str) -> bool:
        """Reactivate client account"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            metadata['is_active'] = True
            metadata['reactivated_date'] = datetime.utcnow().isoformat()
            
            if not self.dropbox.update_client_metadata(client_id, metadata):
                logger.error(f"Failed to reactivate client {client_id}")
                return False
            
            # Send reactivation notification
            reactivation_message = {
                'id': str(uuid4()),
                'type': 'system_alert',
                'content': 'Your account has been reactivated. Welcome back!',
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'attachments': []
            }
            
            self.amqp.publish_client_message(client_id, reactivation_message)
            self.dropbox.archive_message(client_id, reactivation_message['id'], reactivation_message)
            
            logger.info(f"Reactivated client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reactivating client {client_id}: {e}")
            return False
    
    def update_client_info(self, client_id: str, updates: Dict[str, Any]) -> bool:
        """Update client information"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            # Update allowed fields
            allowed_fields = ['email', 'phone', 'first_name', 'last_name', 'custom_metadata']
            for field, value in updates.items():
                if field in allowed_fields:
                    metadata[field] = value
            
            metadata['updated_date'] = datetime.utcnow().isoformat()
            
            if not self.dropbox.update_client_metadata(client_id, metadata):
                logger.error(f"Failed to update client info for {client_id}")
                return False
            
            logger.info(f"Updated client info for {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating client info for {client_id}: {e}")
            return False
    
    def get_all_clients(self) -> list[Dict[str, Any]]:
        """Get list of all clients"""
        try:
            # List all client folders
            clients_folder = self.dropbox.list_folder('/clients')
            clients = []
            
            for item in clients_folder:
                if item.get('is_folder') and item['name'].startswith('client_'):
                    client_id = item['name']
                    status = self.get_client_status(client_id)
                    if status:
                        clients.append(status)
            
            return clients
            
        except Exception as e:
            logger.error(f"Error getting all clients: {e}")
            return []
