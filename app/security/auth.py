"""
Authentication and authorization for the Centuries Mutual Home App
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()
settings = get_settings()


class AuthManager:
    """Manages authentication and authorization"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_hours = settings.jwt_expiration_hours
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.access_token_expire_hours)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
    
    def create_client_token(self, client_id: str, permissions: list[str] = None) -> str:
        """Create token for client access"""
        data = {
            "sub": client_id,
            "type": "client",
            "permissions": permissions or ["read", "write"]
        }
        return self.create_access_token(data)
    
    def create_admin_token(self, admin_id: str, permissions: list[str] = None) -> str:
        """Create token for admin access"""
        data = {
            "sub": admin_id,
            "type": "admin",
            "permissions": permissions or ["admin", "read", "write", "delete"]
        }
        return self.create_access_token(data)


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        payload = auth_manager.verify_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_client(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """Get current client ID from token"""
    if current_user.get("type") != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client access required"
        )
    
    return current_user.get("sub")


async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """Get current admin ID from token"""
    if current_user.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user.get("sub")


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented based on your permission system
            # For now, just return the function
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis or similar
    
    def is_allowed(self, client_id: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if client is within rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) >= limit:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


# Global rate limiter
rate_limiter = RateLimiter()


def require_rate_limit(limit: int = 100, window: int = 3600):
    """Decorator to require rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented based on your rate limiting needs
            # For now, just return the function
            return await func(*args, **kwargs)
        return wrapper
    return decorator
