"""
Message consumer system for the Centuries Mutual Home App
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable

import pika

from app.config import get_settings
from app.services.dropbox_manager import DropboxManager

logger = logging.getLogger(__name__)


class MessageConsumer:
    """Handles message consumption and processing"""
    
    def __init__(self, dropbox_mgr: DropboxManager):
        """Initialize message consumer with Dropbox manager"""
        self.dropbox = dropbox_mgr
        self.settings = get_settings()
        self.is_consuming = False
    
    def process_message(self, channel: pika.channel.Channel, method: pika.spec.Basic.Deliver, 
                       properties: pika.spec.BasicProperties, body: bytes) -> None:
        """Process incoming AMQP messages"""
        try:
            message = json.loads(body.decode('utf-8'))
            client_id = message.get('client_id')
            message_id = message.get('id')
            
            logger.info(f"Processing message {message_id} for client {client_id}")
            
            # Process based on message type
            message_type = message.get('type')
            
            if message_type == 'document_request':
                self.handle_document_request(message)
            elif message_type == 'claim_update':
                self.handle_claim_update(message)
            elif message_type == 'payment_reminder':
                self.handle_payment_reminder(message)
            elif message_type == 'enrollment_notification':
                self.handle_enrollment_notification(message)
            elif message_type == 'beneficiary_update':
                self.handle_beneficiary_update(message)
            elif message_type == 'system_alert':
                self.handle_system_alert(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
            
            # Store delivery confirmation
            confirmation = {
                'message_id': message_id,
                'client_id': client_id,
                'processed': datetime.utcnow().isoformat(),
                'status': 'delivered',
                'message_type': message_type
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/delivery-{message_id}.json",
                confirmation
            )
            
            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Successfully processed message {message_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message JSON: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject and requeue for retry
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def handle_document_request(self, message: Dict[str, Any]) -> None:
        """Handle document request messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            
            logger.info(f"Processing document request for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'document_request_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/document_request_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling document request: {e}")
    
    def handle_claim_update(self, message: Dict[str, Any]) -> None:
        """Handle claim update messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            
            logger.info(f"Processing claim update for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'claim_update_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/claim_update_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling claim update: {e}")
    
    def handle_payment_reminder(self, message: Dict[str, Any]) -> None:
        """Handle payment reminder messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            
            logger.info(f"Processing payment reminder for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'payment_reminder_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/payment_reminder_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling payment reminder: {e}")
    
    def handle_enrollment_notification(self, message: Dict[str, Any]) -> None:
        """Handle enrollment notification messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            
            logger.info(f"Processing enrollment notification for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'enrollment_notification_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/enrollment_notification_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling enrollment notification: {e}")
    
    def handle_beneficiary_update(self, message: Dict[str, Any]) -> None:
        """Handle beneficiary update messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            
            logger.info(f"Processing beneficiary update for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'beneficiary_update_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/beneficiary_update_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling beneficiary update: {e}")
    
    def handle_system_alert(self, message: Dict[str, Any]) -> None:
        """Handle system alert messages"""
        try:
            client_id = message['client_id']
            content = message['content']
            notification_type = message.get('notification_type', 'general')
            
            logger.info(f"Processing system alert for client {client_id}: {content}")
            
            # Create audit log
            audit_log = {
                'action': 'system_alert_processed',
                'client_id': client_id,
                'message_id': message['id'],
                'notification_type': notification_type,
                'timestamp': datetime.utcnow().isoformat(),
                'content': content
            }
            
            self.dropbox.upload_json(
                f"/clients/{client_id}/audit/system_alert_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling system alert: {e}")
    
    def process_workflow_message(self, channel: pika.channel.Channel, method: pika.spec.Basic.Deliver,
                                properties: pika.spec.BasicProperties, body: bytes) -> None:
        """Process workflow messages from topic exchange"""
        try:
            message = json.loads(body.decode('utf-8'))
            routing_key = method.routing_key
            message_id = message.get('id')
            
            logger.info(f"Processing workflow message {message_id} with routing key {routing_key}")
            
            # Process based on routing key
            if routing_key.startswith('enrollment.'):
                self.handle_enrollment_workflow(message, routing_key)
            elif routing_key.startswith('claims.'):
                self.handle_claims_workflow(message, routing_key)
            elif routing_key.startswith('payments.'):
                self.handle_payments_workflow(message, routing_key)
            else:
                logger.warning(f"Unknown workflow routing key: {routing_key}")
            
            # Archive workflow message
            self.dropbox.upload_json(
                f"/workflow/processed/{message_id}.json",
                {
                    'message': message,
                    'routing_key': routing_key,
                    'processed_at': datetime.utcnow().isoformat(),
                    'status': 'processed'
                }
            )
            
            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Successfully processed workflow message {message_id}")
            
        except Exception as e:
            logger.error(f"Error processing workflow message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def handle_enrollment_workflow(self, message: Dict[str, Any], routing_key: str) -> None:
        """Handle enrollment workflow messages"""
        try:
            logger.info(f"Processing enrollment workflow: {routing_key}")
            
            # Create workflow audit log
            audit_log = {
                'action': 'enrollment_workflow_processed',
                'routing_key': routing_key,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': message.get('content', '')
            }
            
            self.dropbox.upload_json(
                f"/workflow/audit/enrollment_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling enrollment workflow: {e}")
    
    def handle_claims_workflow(self, message: Dict[str, Any], routing_key: str) -> None:
        """Handle claims workflow messages"""
        try:
            logger.info(f"Processing claims workflow: {routing_key}")
            
            # Create workflow audit log
            audit_log = {
                'action': 'claims_workflow_processed',
                'routing_key': routing_key,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': message.get('content', '')
            }
            
            self.dropbox.upload_json(
                f"/workflow/audit/claims_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling claims workflow: {e}")
    
    def handle_payments_workflow(self, message: Dict[str, Any], routing_key: str) -> None:
        """Handle payments workflow messages"""
        try:
            logger.info(f"Processing payments workflow: {routing_key}")
            
            # Create workflow audit log
            audit_log = {
                'action': 'payments_workflow_processed',
                'routing_key': routing_key,
                'message_id': message['id'],
                'timestamp': datetime.utcnow().isoformat(),
                'content': message.get('content', '')
            }
            
            self.dropbox.upload_json(
                f"/workflow/audit/payments_{message['id']}.json",
                audit_log
            )
            
        except Exception as e:
            logger.error(f"Error handling payments workflow: {e}")
    
    def get_message_processing_stats(self) -> Dict[str, Any]:
        """Get message processing statistics"""
        try:
            # This would typically query a database or cache
            # For now, return basic stats
            return {
                'total_processed': 0,  # Would be calculated from audit logs
                'successful': 0,
                'failed': 0,
                'last_processed': None
            }
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
