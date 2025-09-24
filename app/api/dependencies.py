"""
API dependencies for dependency injection
"""

from typing import Generator
from fastapi import Depends

from app.config import get_settings
from app.services import (
    DropboxManager,
    AMQPManager,
    DocumentManager,
    WebhookManager,
    ClientOnboarding,
    MessagePublisher,
    MessageConsumer
)

# Global service instances
_dropbox_manager = None
_amqp_manager = None
_document_manager = None
_webhook_manager = None
_client_onboarding = None
_message_publisher = None
_message_consumer = None


def get_dropbox_manager() -> DropboxManager:
    """Get Dropbox manager instance"""
    global _dropbox_manager
    if _dropbox_manager is None:
        _dropbox_manager = DropboxManager()
    return _dropbox_manager


def get_amqp_manager() -> AMQPManager:
    """Get AMQP manager instance"""
    global _amqp_manager
    if _amqp_manager is None:
        _amqp_manager = AMQPManager()
        _amqp_manager.connect()
    return _amqp_manager


def get_document_manager() -> DocumentManager:
    """Get document manager instance"""
    global _document_manager
    if _document_manager is None:
        dropbox_mgr = get_dropbox_manager()
        _document_manager = DocumentManager(dropbox_mgr)
    return _document_manager


def get_webhook_manager() -> WebhookManager:
    """Get webhook manager instance"""
    global _webhook_manager
    if _webhook_manager is None:
        dropbox_mgr = get_dropbox_manager()
        _webhook_manager = WebhookManager(dropbox_mgr)
    return _webhook_manager


def get_client_onboarding() -> ClientOnboarding:
    """Get client onboarding instance"""
    global _client_onboarding
    if _client_onboarding is None:
        dropbox_mgr = get_dropbox_manager()
        amqp_mgr = get_amqp_manager()
        _client_onboarding = ClientOnboarding(dropbox_mgr, amqp_mgr)
    return _client_onboarding


def get_message_publisher() -> MessagePublisher:
    """Get message publisher instance"""
    global _message_publisher
    if _message_publisher is None:
        dropbox_mgr = get_dropbox_manager()
        amqp_mgr = get_amqp_manager()
        _message_publisher = MessagePublisher(dropbox_mgr, amqp_mgr)
    return _message_publisher


def get_message_consumer() -> MessageConsumer:
    """Get message consumer instance"""
    global _message_consumer
    if _message_consumer is None:
        dropbox_mgr = get_dropbox_manager()
        _message_consumer = MessageConsumer(dropbox_mgr)
    return _message_consumer


# Dependency injection shortcuts
DropboxDep = Depends(get_dropbox_manager)
AMQPDep = Depends(get_amqp_manager)
DocumentDep = Depends(get_document_manager)
WebhookDep = Depends(get_webhook_manager)
ClientOnboardingDep = Depends(get_client_onboarding)
MessagePublisherDep = Depends(get_message_publisher)
MessageConsumerDep = Depends(get_message_consumer)
