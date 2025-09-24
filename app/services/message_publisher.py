"""
Message publishing system for the Centuries Mutual Home App
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from uuid import uuid4

from app.config import get_settings
from app.models import MessageCreate, MessageType
from app.services.dropbox_manager import DropboxManager
from app.services.amqp_manager import AMQPManager

logger = logging.getLogger(__name__)


class MessageLimitExceededException(Exception):
    """Exception raised when daily message limit is exceeded"""
    pass


class MessagePublisher:
    """Handles message publishing with rate limiting and archiving"""
    
    def __init__(self, dropbox_mgr: DropboxManager, amqp_mgr: AMQPManager):
        """Initialize message publisher with managers"""
        self.dropbox = dropbox_mgr
        self.amqp = amqp_mgr
        self.settings = get_settings()
    
    def send_client_message(self, client_id: str, message_data: MessageCreate) -> Optional[Dict[str, Any]]:
        """Send message to client with rate limiting and archiving"""
        try:
            # Check daily limit first
            if not self.check_message_limit(client_id):
                raise MessageLimitExceededException(f"Daily limit exceeded for client {client_id}")
            
            # Prepare message payload
            message = {
                'id': str(uuid4()),
                'type': message_data.message_type.value,
                'content': message_data.content,
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'attachments': message_data.attachments or [],
                'metadata': message_data.metadata or {}
            }
            
            # Archive to Dropbox first
            archive_path = f"/clients/{client_id}/messages/{message['id']}.json"
            if not self.dropbox.upload_json(archive_path, message):
                logger.error(f"Failed to archive message {message['id']}")
                return None
            
            # Publish to AMQP
            if not self.amqp.publish_client_message(client_id, message):
                logger.error(f"Failed to publish message {message['id']}")
                return None
            
            # Update message counter
            self.increment_message_counter(client_id)
            
            logger.info(f"Successfully sent message {message['id']} to client {client_id}")
            return {
                'message_id': message['id'],
                'client_id': client_id,
                'status': 'sent',
                'timestamp': message['timestamp']
            }
            
        except MessageLimitExceededException as e:
            logger.warning(str(e))
            raise
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            return None
    
    def send_workflow_message(self, routing_key: str, message_type: str, 
                            content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Send workflow message to topic exchange"""
        try:
            message = {
                'id': str(uuid4()),
                'type': message_type,
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'routing_key': routing_key,
                'metadata': metadata or {}
            }
            
            # Archive workflow message
            archive_path = f"/workflow/messages/{message['id']}.json"
            if not self.dropbox.upload_json(archive_path, message):
                logger.error(f"Failed to archive workflow message {message['id']}")
                return None
            
            # Publish to workflow exchange
            if not self.amqp.publish_workflow_message(routing_key, message):
                logger.error(f"Failed to publish workflow message {message['id']}")
                return None
            
            logger.info(f"Successfully sent workflow message {message['id']} with routing key {routing_key}")
            return {
                'message_id': message['id'],
                'routing_key': routing_key,
                'status': 'sent',
                'timestamp': message['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error sending workflow message: {e}")
            return None
    
    def check_message_limit(self, client_id: str) -> bool:
        """Check if client has exceeded daily message limit"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            today = date.today().isoformat()
            
            # Reset counter if it's a new day
            if metadata.get('last_reset') != today:
                metadata['message_count_today'] = 0
                metadata['last_reset'] = today
                self.dropbox.update_client_metadata(client_id, metadata)
            
            current_count = metadata.get('message_count_today', 0)
            daily_limit = self.settings.daily_message_limit
            
            return current_count < daily_limit
            
        except Exception as e:
            logger.error(f"Error checking message limit for client {client_id}: {e}")
            return False
    
    def increment_message_counter(self, client_id: str) -> bool:
        """Increment daily message counter for client"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                logger.error(f"Client metadata not found for {client_id}")
                return False
            
            metadata['message_count_today'] = metadata.get('message_count_today', 0) + 1
            metadata['last_message_sent'] = datetime.utcnow().isoformat()
            
            return self.dropbox.update_client_metadata(client_id, metadata)
            
        except Exception as e:
            logger.error(f"Error incrementing message counter for client {client_id}: {e}")
            return False
    
    def get_message_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get message statistics for client"""
        try:
            metadata = self.dropbox.get_client_metadata(client_id)
            if not metadata:
                return None
            
            return {
                'client_id': client_id,
                'messages_today': metadata.get('message_count_today', 0),
                'daily_limit': self.settings.daily_message_limit,
                'last_reset': metadata.get('last_reset'),
                'last_message_sent': metadata.get('last_message_sent'),
                'remaining_messages': max(0, self.settings.daily_message_limit - metadata.get('message_count_today', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting message stats for client {client_id}: {e}")
            return None
    
    def send_bulk_messages(self, messages: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Send multiple messages in batch"""
        results = {
            'successful': [],
            'failed': [],
            'limit_exceeded': []
        }
        
        for message_data in messages:
            try:
                client_id = message_data['client_id']
                
                # Check limit for each client
                if not self.check_message_limit(client_id):
                    results['limit_exceeded'].append({
                        'client_id': client_id,
                        'error': 'Daily limit exceeded'
                    })
                    continue
                
                # Create message
                message = MessageCreate(
                    client_id=client_id,
                    message_type=MessageType(message_data['type']),
                    content=message_data['content'],
                    attachments=message_data.get('attachments', []),
                    metadata=message_data.get('metadata', {})
                )
                
                result = self.send_client_message(client_id, message)
                if result:
                    results['successful'].append(result)
                else:
                    results['failed'].append({
                        'client_id': client_id,
                        'error': 'Failed to send message'
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'client_id': message_data.get('client_id', 'unknown'),
                    'error': str(e)
                })
        
        logger.info(f"Bulk message send completed: {len(results['successful'])} successful, "
                   f"{len(results['failed'])} failed, {len(results['limit_exceeded'])} limit exceeded")
        
        return results
    
    def send_notification(self, client_id: str, notification_type: str, 
                         content: str, priority: int = 0) -> Optional[Dict[str, Any]]:
        """Send high-priority notification to client"""
        try:
            message = {
                'id': str(uuid4()),
                'type': 'system_alert',
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'client_id': client_id,
                'notification_type': notification_type,
                'priority': priority,
                'metadata': {}
            }
            
            # Archive notification
            archive_path = f"/clients/{client_id}/messages/{message['id']}.json"
            self.dropbox.upload_json(archive_path, message)
            
            # Publish with priority
            if not self.amqp.publish_client_message(client_id, message):
                logger.error(f"Failed to publish notification {message['id']}")
                return None
            
            logger.info(f"Successfully sent notification {message['id']} to client {client_id}")
            return {
                'message_id': message['id'],
                'client_id': client_id,
                'status': 'sent',
                'timestamp': message['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error sending notification to client {client_id}: {e}")
            return None
    
    def resend_failed_message(self, message_id: str, client_id: str) -> bool:
        """Resend a previously failed message"""
        try:
            # Get archived message
            archive_path = f"/clients/{client_id}/messages/{message_id}.json"
            message = self.dropbox.download_json(archive_path)
            
            if not message:
                logger.error(f"Failed message not found: {message_id}")
                return False
            
            # Update timestamp
            message['timestamp'] = datetime.utcnow().isoformat()
            message['retry_count'] = message.get('retry_count', 0) + 1
            
            # Re-archive with updated info
            self.dropbox.upload_json(archive_path, message)
            
            # Republish
            success = self.amqp.publish_client_message(client_id, message)
            
            if success:
                logger.info(f"Successfully resent message {message_id}")
            else:
                logger.error(f"Failed to resend message {message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error resending message {message_id}: {e}")
            return False
