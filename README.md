# Centuries Mutual Home App – Enterprise Integration Architecture

## Overview

This is a comprehensive enterprise-level notifications system built with Dropbox Advanced and AMQP messaging infrastructure. The system provides secure document management, real-time messaging, and audit capabilities for insurance clients.

## Architecture

### High-Level Architecture

```
Mobile/Web Frontend <-> API Gateway (Auth, Routing) <-> Dropbox Advanced (Storage Backend)
                                                                 |
                                                                 - Webhooks
                                                                 - Audit Logs
                                                                 - Shared Links

Client Devices (Push/Email/SMS) <-> (AMQP 0.1) RabbitMQ
  - Notifications
  - Confirmation View
  - Daily Limits    - Message Queue
                     - Daily Limits  > Message Archive (Dropbox Folders)
```

### Key Components

- **Dropbox Advanced**: Unlimited API calls, file storage, webhooks, audit logs
- **RabbitMQ**: AMQP messaging with persistent queues and delivery guarantees
- **FastAPI**: High-performance API with automatic documentation
- **PostgreSQL**: Reliable data persistence
- **Redis**: Caching and session management
- **Nginx**: Reverse proxy with SSL termination and rate limiting

## Features

### Core Functionality
- ✅ Client onboarding and management
- ✅ Secure document upload and sharing
- ✅ Real-time messaging with rate limiting
- ✅ Webhook processing for document verification
- ✅ End-to-end encryption
- ✅ Comprehensive audit logging
- ✅ RESTful API with OpenAPI documentation

### Security Features
- ✅ JWT-based authentication
- ✅ Role-based access control
- ✅ End-to-end encryption (AES-256-GCM + RSA-OAEP)
- ✅ Digital signatures for documents
- ✅ Rate limiting and DDoS protection
- ✅ Secure webhook verification

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Dropbox Advanced/Enterprise account
- Domain name with SSL certificate (for production)

### 1. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp config.env.example .env
```

Edit `.env` with your configuration:

```bash
# Dropbox Configuration
DROPBOX_ACCESS_TOKEN=your_dropbox_access_token_here
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=notifications_db

# Security Configuration
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key-here
WEBHOOK_SECRET=your-webhook-secret-here

# Application Configuration
WEBHOOK_BASE_URL=https://your-domain.com
```

### 2. Start the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check health
curl http://localhost:8000/health
```

### 3. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

## API Endpoints

### Client Management
- `POST /clients/register` - Register new client
- `GET /clients/{client_id}/status` - Get client status
- `POST /clients/{client_id}/complete-onboarding` - Complete onboarding

### Message Management
- `POST /messages/send` - Send message to client
- `POST /messages/send-bulk` - Send multiple messages
- `GET /messages/{client_id}/stats` - Get message statistics

### Document Management
- `POST /documents/upload` - Upload document
- `GET /documents/{client_id}/list` - List client documents
- `GET /documents/{client_id}/{document_id}/download` - Download document
- `POST /documents/{client_id}/{document_id}/share` - Create share link

### Webhook Management
- `POST /webhooks/dropbox` - Process Dropbox webhooks
- `GET /webhooks/{client_id}/audit` - Get webhook audit logs

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp config.env.example .env
# Edit .env with your configuration

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Type checking
mypy app/

# Linting
flake8 app/
```

## Production Deployment

### 1. SSL Certificate Setup

```bash
# Create SSL directory
mkdir ssl

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem -out ssl/cert.pem

# For production, use Let's Encrypt or your CA
```

### 2. Environment Configuration

Update `.env` with production values:

```bash
DEBUG=false
LOG_LEVEL=INFO
WEBHOOK_BASE_URL=https://your-production-domain.com
```

### 3. Deploy

```bash
# Build and start services
docker-compose -f docker-compose.yml up -d

# Scale workers if needed
docker-compose up -d --scale worker=3
```

### 4. Monitoring

```bash
# View logs
docker-compose logs -f

# Monitor resources
docker stats

# Health checks
curl https://your-domain.com/health
```

## Configuration

### Dropbox Setup

1. Create a Dropbox App at https://www.dropbox.com/developers/apps
2. Generate access token with appropriate permissions
3. Configure webhook URL: `https://your-domain.com/webhooks/dropbox`

### RabbitMQ Configuration

The system uses the following exchanges and queues:

- **Exchanges**:
  - `insurance.direct` - Direct exchange for client-specific messages
  - `insurance.workflow` - Topic exchange for workflow messages
  - `insurance.dlx` - Dead letter exchange for failed messages

- **Queues**:
  - `client.{client_id}` - Client-specific message queues
  - `enrollment.*` - Enrollment workflow queues
  - `claims.*` - Claims workflow queues
  - `payments.*` - Payment workflow queues

### Rate Limiting

- **API Endpoints**: 10 requests/second per IP
- **Webhook Endpoints**: 5 requests/second per IP
- **Daily Message Limit**: 10 messages per client (configurable)

## Security Considerations

### Encryption

- **Document Storage**: AES-256-GCM encryption
- **Message Transmission**: RSA-OAEP + AES-256-GCM
- **Password Hashing**: bcrypt with salt
- **JWT Tokens**: HS256 with configurable expiration

### Access Control

- **Authentication**: JWT-based with role separation
- **Authorization**: Role-based access control (client/admin)
- **Rate Limiting**: Per-IP and per-client limits
- **Audit Logging**: Comprehensive activity tracking

### Network Security

- **HTTPS Only**: SSL/TLS termination at Nginx
- **Security Headers**: HSTS, XSS protection, content type validation
- **CORS**: Configurable cross-origin resource sharing
- **Firewall**: Restrict access to management interfaces

## Monitoring and Logging

### Health Checks

- Application health: `/health`
- Database connectivity
- RabbitMQ connectivity
- Dropbox API connectivity

### Logging

- **Application Logs**: Structured logging with JSON format
- **Access Logs**: Nginx access and error logs
- **Audit Logs**: All client actions and system events
- **Error Tracking**: Comprehensive error logging and monitoring

### Metrics

- Message processing rates
- Document access patterns
- Client activity metrics
- System performance indicators

## Troubleshooting

### Common Issues

1. **Dropbox Connection Failed**
   - Verify access token is valid
   - Check network connectivity
   - Ensure app has required permissions

2. **RabbitMQ Connection Issues**
   - Verify credentials in environment
   - Check if RabbitMQ is running
   - Review connection parameters

3. **Database Connection Problems**
   - Verify PostgreSQL is running
   - Check database credentials
   - Ensure database exists

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug output
docker-compose up
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is proprietary software for Centuries Mutual. All rights reserved.

## Support

For technical support or questions, please contact the development team or create an issue in the project repository.
