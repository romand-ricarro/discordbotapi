import os
import json
import uuid
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("api_key_manager")

class APIKeyManager:
    def __init__(self, keys_file="api_keys.json"):
        self.keys_file = keys_file
        self.keys = {}  # key -> {'owner': name, 'created': timestamp, 'expires': timestamp}
        self.load_keys()
        
    def load_keys(self):
        """Load API keys from file or environment."""
        # Always load the main key from environment
        main_key = os.getenv("API_KEY")
        if main_key:
            expiry = time.time() + 90 * 24 * 3600  # 90 days from now
            self.keys[main_key] = {
                'owner': 'admin',
                'created': time.time(),
                'expires': expiry,
                'description': 'Primary API Key'
            }
            
        # Try to load additional keys from file
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r') as f:
                    stored_keys = json.load(f)
                    # Merge with existing keys
                    self.keys.update(stored_keys)
                    
                    # Log the loaded keys (partially obscured)
                    for key in stored_keys:
                        masked_key = key[:5] + "..." + key[-5:] if len(key) > 10 else "***"
                        logger.info(f"Loaded API key: {masked_key} for {stored_keys[key].get('owner', 'unknown')}")
        except Exception as e:
            logger.error(f"Error loading API keys: {str(e)}")
            
    def save_keys(self):
        """Save API keys to file."""
        try:
            # Don't save the main key from environment
            main_key = os.getenv("API_KEY")
            keys_to_save = {k: v for k, v in self.keys.items() if k != main_key}
            
            with open(self.keys_file, 'w') as f:
                json.dump(keys_to_save, f, indent=2)
                
            logger.info(f"Saved {len(keys_to_save)} API keys to {self.keys_file}")
        except Exception as e:
            logger.error(f"Error saving API keys: {str(e)}")
            
    def validate_key(self, key):
        """Validate if an API key is valid and not expired."""
        if key in self.keys:
            key_data = self.keys[key]
            # Check if expired
            if key_data.get('expires') and time.time() > key_data['expires']:
                logger.warning(f"Expired API key used: {key[:5]}...")
                return False
            return True
        return False
        
    def create_key(self, owner, description=None, expires_days=90):
        """Create a new API key."""
        # Generate a new random key
        new_key = str(uuid.uuid4())
        
        # Calculate expiry time
        expiry = time.time() + expires_days * 24 * 3600
        expiry_date = datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')
        
        # Store the key
        self.keys[new_key] = {
            'owner': owner,
            'created': time.time(),
            'expires': expiry,
            'description': description or f"API Key for {owner}"
        }
        
        # Save the updated keys
        self.save_keys()
        
        # Log the key creation
        logger.info(f"Created new API key for {owner}, expires on {expiry_date}")
        
        return {
            'key': new_key,
            'owner': owner,
            'expires': expiry_date,
            'description': description
        }
        
    def revoke_key(self, key):
        """Revoke an API key."""
        if key in self.keys:
            owner = self.keys[key].get('owner', 'unknown')
            del self.keys[key]
            self.save_keys()
            logger.info(f"Revoked API key for {owner}")
            return True
        return False
        
    def get_keys_info(self):
        """Get information about all API keys (without revealing the full keys)."""
        keys_info = []
        for key, data in self.keys.items():
            # Mask the key for security
            masked_key = key[:5] + "..." + key[-5:] if len(key) > 10 else "***"
            
            # Format dates
            created_date = datetime.fromtimestamp(data.get('created', 0)).strftime('%Y-%m-%d %H:%M:%S')
            expires_date = datetime.fromtimestamp(data.get('expires', 0)).strftime('%Y-%m-%d %H:%M:%S')
            
            keys_info.append({
                'key_preview': masked_key,
                'owner': data.get('owner', 'unknown'),
                'created': created_date,
                'expires': expires_date,
                'description': data.get('description', ''),
                'is_expired': time.time() > data.get('expires', 0)
            })
            
        return keys_info
        
    def rotate_key(self, old_key, expires_days=90):
        """Rotate an API key by creating a new one and revoking the old one."""
        if old_key not in self.keys:
            return None
            
        # Get owner and description
        owner = self.keys[old_key].get('owner', 'unknown')
        description = self.keys[old_key].get('description', f"API Key for {owner}")
        
        # Create new key
        new_key_info = self.create_key(owner, description, expires_days)
        
        # Revoke old key
        self.revoke_key(old_key)
        
        logger.info(f"Rotated API key for {owner}")
        
        return new_key_info