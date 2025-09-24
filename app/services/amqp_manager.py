"""
AMQP (RabbitMQ) messaging infrastructure for the Centuries Mutual Home App
"""

import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

import pika
from pika.exchange_type import ExchangeType
from pika.connection import ConnectionParameters
from pika.credentials import PlainCredentials

from app.config import get_settings

logger = logging.getLogger(__name__)


class AMQPManager:
    """Manages RabbitMQ AMQP messaging infrastructure"""
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """Initialize AMQP manager with connection parameters"""
        settings = get_settings()
        
        if connection_params:
            self.connection_params = connection_params
        else:
            credentials = PlainCredentials(
                settings.rabbitmq_username,
                settings.rabbitmq_password
            )
            self.connection_params = ConnectionParameters(
                host=settings.rabbitmq_host,
                port=settings.rabbitmq_port,
                virtual_host=settings.rabbitmq_vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
        
        self.connection = None
        self.channel = None
        self.daily_message_limit = settings.daily_message_limit
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()
            self.setup_infrastructure()
            logger.info("Connected to RabbitMQ successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def setup_infrastructure(self):
        """Declare exchanges and setup messaging infrastructure"""
        try:
            # Declare direct exchange for client-specific messages
            self.channel.exchange_declare(
                exchange='insurance.direct',
                exchange_type=ExchangeType.direct,
                durable=True
            )
            
            # Declare topic exchange for workflow messages
            self.channel.exchange_declare(
                exchange='insurance.workflow',
                exchange_type=ExchangeType.topic,
                durable=True
            )
            
            # Declare dead letter exchange for failed messages
            self.channel.exchange_declare(
                exchange='insurance.dlx',
                exchange_type=ExchangeType.direct,
                durable=True
            )
            
            logger.info("AMQP infrastructure setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup AMQP infrastructure: {e}")
            raise
    
    def create_client_queue(self, client_id: str, message_limit: Optional[int] = None) -> bool:
        """Create client-specific queue with daily message limit"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            limit = message_limit or self.daily_message_limit
            
            # Queue arguments for rate limiting and dead letter handling
            arguments = {
                'x-message-ttl': 86400000,  # 24 hours in milliseconds
                'x-max-length': limit,
                'x-overflow': 'reject-publish',
                'x-dead-letter-exchange': 'insurance.dlx',
                'x-dead-letter-routing-key': f'failed.{client_id}'
            }
            
            # Declare client queue
            self.channel.queue_declare(
                queue=f"client.{client_id}",
                durable=True,
                arguments=arguments
            )
            
            # Bind to direct exchange
            self.channel.queue_bind(
                exchange='insurance.direct',
                queue=f"client.{client_id}",
                routing_key=client_id
            )
            
            # Create dead letter queue for failed messages
            self.channel.queue_declare(
                queue=f"failed.{client_id}",
                durable=True
            )
            
            self.channel.queue_bind(
                exchange='insurance.dlx',
                queue=f"failed.{client_id}",
                routing_key=f'failed.{client_id}'
            )
            
            logger.info(f"Created queue for client {client_id} with limit {limit}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create queue for client {client_id}: {e}")
            return False
    
    def delete_client_queue(self, client_id: str) -> bool:
        """Delete client-specific queue"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            # Delete main queue
            self.channel.queue_delete(queue=f"client.{client_id}")
            
            # Delete dead letter queue
            self.channel.queue_delete(queue=f"failed.{client_id}")
            
            logger.info(f"Deleted queues for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete queues for client {client_id}: {e}")
            return False
    
    def publish_message(self, exchange: str, routing_key: str, message: Dict[str, Any], 
                       priority: int = 0) -> bool:
        """Publish message to exchange"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            # Prepare message properties
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                priority=priority,
                timestamp=int(datetime.utcnow().timestamp()),
                message_id=str(message.get('id', '')),
                content_type='application/json'
            )
            
            # Publish message
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message, default=str),
                properties=properties
            )
            
            logger.info(f"Published message to {exchange} with routing key {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def publish_client_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Publish message to client-specific queue"""
        return self.publish_message('insurance.direct', client_id, message)
    
    def publish_workflow_message(self, routing_key: str, message: Dict[str, Any]) -> bool:
        """Publish workflow message to topic exchange"""
        return self.publish_message('insurance.workflow', routing_key, message)
    
    def start_consuming(self, queue_name: str, callback: Callable, auto_ack: bool = False):
        """Start consuming messages from queue"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            # Set up consumer
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            
            logger.info(f"Started consuming from queue: {queue_name}")
            
            # Start consuming
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Failed to start consuming from {queue_name}: {e}")
            raise
    
    def stop_consuming(self):
        """Stop consuming messages"""
        try:
            if self.channel and self.channel.is_consuming:
                self.channel.stop_consuming()
            logger.info("Stopped consuming messages")
        except Exception as e:
            logger.error(f"Error stopping message consumption: {e}")
    
    def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Get queue information"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            return {
                'queue_name': queue_name,
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count
            }
        except Exception as e:
            logger.error(f"Failed to get queue info for {queue_name}: {e}")
            return None
    
    def purge_queue(self, queue_name: str) -> bool:
        """Purge all messages from queue"""
        try:
            if not self.channel:
                raise Exception("Not connected to RabbitMQ")
            
            self.channel.queue_purge(queue=queue_name)
            logger.info(f"Purged queue: {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {e}")
            return False
    
    def setup_workflow_queues(self):
        """Setup workflow-specific queues"""
        try:
            workflow_queues = [
                'enrollment.requests',
                'enrollment.completed',
                'claims.submitted',
                'claims.processed',
                'payments.due',
                'payments.completed'
            ]
            
            for queue in workflow_queues:
                self.channel.queue_declare(queue=queue, durable=True)
                
                # Bind to workflow exchange with appropriate routing key
                routing_key = queue.replace('.', '.')
                self.channel.queue_bind(
                    exchange='insurance.workflow',
                    queue=queue,
                    routing_key=routing_key
                )
            
            logger.info("Setup workflow queues completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup workflow queues: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ"""
        return self.connection is not None and not self.connection.is_closed
    
    def reconnect(self) -> bool:
        """Reconnect to RabbitMQ"""
        try:
            self.disconnect()
            return self.connect()
        except Exception as e:
            logger.error(f"Failed to reconnect to RabbitMQ: {e}")
            return False
