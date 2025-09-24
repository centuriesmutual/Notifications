"""
Advanced encryption utilities for the Centuries Mutual Home App
"""

import logging
import secrets
import base64
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.config import get_settings

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Advanced encryption manager for end-to-end security"""
    
    def __init__(self):
        self.settings = get_settings()
        self.backend = default_backend()
    
    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """Generate RSA key pair for asymmetric encryption"""
        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=self.backend
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return private_pem, public_pem
            
        except Exception as e:
            logger.error(f"Error generating key pair: {e}")
            raise
    
    def generate_symmetric_key(self, password: str, salt: bytes = None) -> bytes:
        """Generate symmetric key from password using PBKDF2"""
        try:
            if salt is None:
                salt = secrets.token_bytes(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self.backend
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key
            
        except Exception as e:
            logger.error(f"Error generating symmetric key: {e}")
            raise
    
    def encrypt_with_rsa(self, data: bytes, public_key_pem: bytes) -> bytes:
        """Encrypt data with RSA public key"""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem, backend=self.backend)
            
            encrypted = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return encrypted
            
        except Exception as e:
            logger.error(f"Error encrypting with RSA: {e}")
            raise
    
    def decrypt_with_rsa(self, encrypted_data: bytes, private_key_pem: bytes) -> bytes:
        """Decrypt data with RSA private key"""
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=self.backend
            )
            
            decrypted = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted
            
        except Exception as e:
            logger.error(f"Error decrypting with RSA: {e}")
            raise
    
    def encrypt_with_aes(self, data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """Encrypt data with AES-256-GCM"""
        try:
            # Generate random IV
            iv = secrets.token_bytes(12)  # 96-bit IV for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self.backend
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            return ciphertext, iv, encryptor.tag
            
        except Exception as e:
            logger.error(f"Error encrypting with AES: {e}")
            raise
    
    def decrypt_with_aes(self, ciphertext: bytes, key: bytes, iv: bytes, tag: bytes) -> bytes:
        """Decrypt data with AES-256-GCM"""
        try:
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Error decrypting with AES: {e}")
            raise
    
    def encrypt_message(self, message: str, recipient_public_key: bytes) -> Dict[str, str]:
        """Encrypt message for secure transmission"""
        try:
            # Generate random symmetric key
            symmetric_key = Fernet.generate_key()
            
            # Encrypt message with symmetric key
            fernet = Fernet(symmetric_key)
            encrypted_message = fernet.encrypt(message.encode())
            
            # Encrypt symmetric key with recipient's public key
            encrypted_key = self.encrypt_with_rsa(symmetric_key, recipient_public_key)
            
            return {
                "encrypted_message": base64.b64encode(encrypted_message).decode(),
                "encrypted_key": base64.b64encode(encrypted_key).decode(),
                "algorithm": "RSA-OAEP + AES-256-GCM"
            }
            
        except Exception as e:
            logger.error(f"Error encrypting message: {e}")
            raise
    
    def decrypt_message(self, encrypted_data: Dict[str, str], private_key: bytes) -> str:
        """Decrypt message from secure transmission"""
        try:
            # Decode base64 data
            encrypted_message = base64.b64decode(encrypted_data["encrypted_message"])
            encrypted_key = base64.b64decode(encrypted_data["encrypted_key"])
            
            # Decrypt symmetric key with private key
            symmetric_key = self.decrypt_with_rsa(encrypted_key, private_key)
            
            # Decrypt message with symmetric key
            fernet = Fernet(symmetric_key)
            decrypted_message = fernet.decrypt(encrypted_message)
            
            return decrypted_message.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting message: {e}")
            raise
    
    def create_secure_hash(self, data: str, salt: bytes = None) -> Tuple[str, bytes]:
        """Create secure hash with salt"""
        try:
            if salt is None:
                salt = secrets.token_bytes(32)
            
            # Create hash
            hash_obj = hashes.Hash(hashes.SHA256(), backend=self.backend)
            hash_obj.update(salt + data.encode())
            hash_digest = hash_obj.finalize()
            
            return base64.b64encode(hash_digest).decode(), salt
            
        except Exception as e:
            logger.error(f"Error creating secure hash: {e}")
            raise
    
    def verify_secure_hash(self, data: str, hash_value: str, salt: bytes) -> bool:
        """Verify secure hash"""
        try:
            computed_hash, _ = self.create_secure_hash(data, salt)
            return hash_value == computed_hash
            
        except Exception as e:
            logger.error(f"Error verifying secure hash: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def create_document_signature(self, document_data: bytes, private_key: bytes) -> str:
        """Create digital signature for document"""
        try:
            private_key_obj = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=self.backend
            )
            
            signature = private_key_obj.sign(
                document_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return base64.b64encode(signature).decode()
            
        except Exception as e:
            logger.error(f"Error creating document signature: {e}")
            raise
    
    def verify_document_signature(self, document_data: bytes, signature: str, public_key: bytes) -> bool:
        """Verify digital signature for document"""
        try:
            public_key_obj = serialization.load_pem_public_key(public_key, backend=self.backend)
            
            signature_bytes = base64.b64decode(signature)
            
            public_key_obj.verify(
                signature_bytes,
                document_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying document signature: {e}")
            return False


# Global encryption manager
encryption_manager = EncryptionManager()
