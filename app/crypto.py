"""State token encryption and decryption using AES-GCM."""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os


def get_secret_key() -> bytes:
    """Get the secret key from environment variable."""
    key_str = os.getenv("STATE_SECRET_KEY")
    if not key_str:
        raise ValueError("STATE_SECRET_KEY environment variable is required")
    
    # If it's base64 encoded, decode it; otherwise use it directly as bytes
    try:
        # Try to decode as base64 first
        key = base64.urlsafe_b64decode(key_str)
        if len(key) == 32:
            return key
    except Exception:
        pass
    
    # If not base64 or wrong length, use the string directly
    key_bytes = key_str.encode('utf-8')
    if len(key_bytes) < 32:
        # Pad to 32 bytes if needed
        key_bytes = key_bytes.ljust(32, b'\0')
    elif len(key_bytes) > 32:
        # Truncate to 32 bytes
        key_bytes = key_bytes[:32]
    
    return key_bytes


def encrypt_state(state: Dict[str, Any], secret_key: bytes) -> str:
    """
    Encrypt a state dictionary into a base64-encoded token.
    
    Args:
        state: The state dictionary to encrypt
        secret_key: 32-byte secret key for AES-256-GCM
        
    Returns:
        Base64-encoded encrypted state token
    """
    # Serialize state to JSON
    json_data = json.dumps(state, sort_keys=True).encode('utf-8')
    
    # Generate a random 96-bit (12-byte) nonce for GCM
    nonce = os.urandom(12)
    
    # Encrypt using AES-GCM
    aesgcm = AESGCM(secret_key)
    ciphertext = aesgcm.encrypt(nonce, json_data, None)
    
    # Combine nonce and ciphertext, then base64 encode
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
    
    return token


def decrypt_state(token: str, secret_key: bytes) -> Dict[str, Any]:
    """
    Decrypt a base64-encoded state token back into a dictionary.
    
    Args:
        token: Base64-encoded encrypted state token
        secret_key: 32-byte secret key for AES-256-GCM
        
    Returns:
        The decrypted state dictionary
        
    Raises:
        ValueError: If decryption fails (invalid token or key)
    """
    try:
        # Decode from base64
        data = base64.urlsafe_b64decode(token.encode('utf-8'))
        
        # Extract nonce (first 12 bytes) and ciphertext (rest)
        nonce = data[:12]
        ciphertext = data[12:]
        
        # Decrypt using AES-GCM
        aesgcm = AESGCM(secret_key)
        json_data = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Deserialize JSON back to dictionary
        state = json.loads(json_data.decode('utf-8'))
        
        return state
    except Exception as e:
        raise ValueError(f"Failed to decrypt state token: {str(e)}") from e

