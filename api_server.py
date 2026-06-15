# api_server.py - Complete AWS-ready version with enhanced monitoring
import asyncio
import logging
import threading
from typing import Dict, Optional, Any, Callable, List
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime
import discord
import os

from api_key_manager import APIKeyManager
from activity_logger import ActivityLogger
from rate_limiter import RateLimiter

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

# Model definitions
class ChannelMessageRequest(BaseModel):
    channel_id: str
    message: str

class DirectMessageRequest(BaseModel):
    user_id: str
    message: str

class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool = False

class EmbedFooter(BaseModel):
    text: str
    icon_url: Optional[str] = None

class EmbedAuthor(BaseModel):
    name: str
    url: Optional[str] = None
    icon_url: Optional[str] = None

class EmbedRequest(BaseModel):
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    color: Optional[str] = Field(None, description="Color in hex format (e.g., 'FF5733')")
    image: Optional[str] = None
    thumbnail: Optional[str] = None
    footer: Optional[EmbedFooter] = None
    author: Optional[EmbedAuthor] = None
    fields: Optional[List[EmbedField]] = None

class APIKeyRequest(BaseModel):
    owner: str
    description: Optional[str] = None
    expires_days: int = 90

class APIServer:
    def __init__(self, bot_instance):
        """Initialize the API server with a reference to the Discord bot."""
        self.app = FastAPI(title="Discord Bot API", version="1.0.0")
        self.bot = bot_instance
        self.bot_loop = None
        
        # Initialize the API key manager
        self.api_key_manager = APIKeyManager()

        # Initialize the activity logger
        self.activity_logger = ActivityLogger()
        
        # Initialize the rate limiter
        self.rate_limiter = RateLimiter()
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Cache for static files to avoid repeated file reads
        self._static_cache = {}
        
        def read_static_file(filepath: str, is_binary: bool = False) -> str:
            """Read and cache static files."""
            if filepath in self._static_cache:
                return self._static_cache[filepath]
                
            try:
                mode = 'rb' if is_binary else 'r'
                encoding = None if is_binary else 'utf-8'
                
                with open(filepath, mode, encoding=encoding) as f:
                    content = f.read()
                    
                # Cache the content
                self._static_cache[filepath] = content
                return content
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
                return ""
        
        # Root endpoint - API information
        @self.app.get("/")
        async def root():
            """Root endpoint - API information"""
            return {
                "message": "Discord Bot API is running",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/health",
                    "simple_health": "/health",
                    "docs": "/docs",
                    "web_interface": "/",
                    "api_base": "/api"
                },
                "status": "online",
                "timestamp": datetime.now().isoformat()
            }

        # Simple health check for AWS Load Balancers
        @self.app.get("/health")
        async def simple_health():
            """Simple health check for load balancers"""
            return {"status": "ok", "timestamp": datetime.now().isoformat()}

        # Static file routes - using direct string responses to avoid content-length issues
        @self.app.get("/web", include_in_schema=False)
        async def serve_index():
            """Serve the main HTML page."""
            content = read_static_file("static/index.html")
            if not content:
                return HTMLResponse(content="<h1>Web interface not found</h1><p>Please ensure static/index.html exists</p>")
            return HTMLResponse(content=content)

        @self.app.get("/css/styles.css", include_in_schema=False)  
        async def serve_styles():
            """Serve the CSS file."""
            content = read_static_file("static/css/styles.css")
            return PlainTextResponse(content=content, media_type="text/css")

        @self.app.get("/js/script.js", include_in_schema=False)
        async def serve_script():
            """Serve the JavaScript file."""
            content = read_static_file("static/js/script.js")
            return PlainTextResponse(content=content, media_type="application/javascript")
        
        # API key dependency with rate limiting
        async def verify_api_key(
            response: Response,
            x_api_key: str = Header(None),
            request: Request = None
        ):
            if not x_api_key or not self.api_key_manager.validate_key(x_api_key):
                logger.warning(f"Invalid API key attempt: {x_api_key[:5] if x_api_key else 'None'}...")
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            # Get endpoint for rate limiting
            endpoint = None
            if request and request.url.path.startswith('/api/'):
                # Extract endpoint name from path like /api/channel-message -> channel-message
                parts = request.url.path.split('/')
                if len(parts) >= 3:
                    endpoint = parts[2]  # Get the endpoint name
            
            # Check if this is an admin key
            is_admin = self.api_key_manager.keys.get(x_api_key, {}).get('owner') == 'admin'
            
            # Check rate limit
            is_limited, remaining, reset_in = self.rate_limiter.is_rate_limited(x_api_key, endpoint, is_admin)
            
            # Add rate limit headers
            rate_limit_headers = self.rate_limiter.get_headers(x_api_key, endpoint, is_admin)
            for header, value in rate_limit_headers.items():
                response.headers[header] = value
            
            if is_limited:
                # Log the rate limit
                key_owner = self.api_key_manager.keys.get(x_api_key, {}).get('owner', 'unknown')
                self.activity_logger.log_activity(
                    "rate_limited",
                    key_owner,
                    {"endpoint": endpoint or "global", "reset_in": reset_in},
                    success=False
                )
                
                # If rate limited, raise HTTP 429 Too Many Requests
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {int(reset_in)} seconds."
                )
            
            return x_api_key
        
        # Enhanced health check with comprehensive monitoring
        @self.app.get("/api/health")
        async def health_check():
            """Enhanced health check endpoint for AWS monitoring"""
            bot_status = "unknown"
            bot_latency = None
            bot_guilds = 0
            bot_users = 0
            
            try:
                if self.bot and hasattr(self.bot, 'bot'):
                    if self.bot.bot.is_ready():
                        bot_status = "connected"
                        bot_latency = round(self.bot.bot.latency * 1000, 2)  # Convert to ms
                        bot_guilds = len(self.bot.bot.guilds)
                        bot_users = len(self.bot.bot.users)
                    elif self.bot.bot.is_closed():
                        bot_status = "disconnected"
                    else:
                        bot_status = "connecting"
                else:
                    bot_status = "not_initialized"
            except Exception as e:
                bot_status = f"error: {str(e)}"
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "discord-bot-api",
                "version": "1.0.0",
                "environment": getattr(config, 'ENVIRONMENT', 'production'),
                "bot": {
                    "status": bot_status,
                    "latency_ms": bot_latency,
                    "guilds": bot_guilds,
                    "users": bot_users
                },
                "api": {
                    "total_keys": len(self.api_key_manager.keys),
                    "active_keys": len([k for k in self.api_key_manager.keys.values() if not k.get('revoked', False)])
                }
            }

        # Detailed bot status endpoint
        @self.app.get("/api/bot/status")
        async def bot_status(api_key: str = Depends(verify_api_key)):
            """Get detailed bot status information"""
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Log this activity
            self.activity_logger.log_activity(
                "bot_status",
                key_owner,
                {}
            )
            
            try:
                if not self.bot or not hasattr(self.bot, 'bot'):
                    return {
                        "status": "not_initialized",
                        "ready": False,
                        "guilds": 0,
                        "users": 0,
                        "latency": None
                    }
                
                bot = self.bot.bot
                
                return {
                    "status": "connected" if bot.is_ready() else "disconnected",
                    "ready": bot.is_ready(),
                    "guilds": len(bot.guilds),
                    "users": len(bot.users),
                    "latency_ms": round(bot.latency * 1000, 2) if bot.latency else None,
                    "user": {
                        "id": str(bot.user.id) if bot.user else None,
                        "name": bot.user.name if bot.user else None,
                        "discriminator": bot.user.discriminator if bot.user else None
                    },
                    "uptime": str(datetime.now() - bot.ready_time) if hasattr(bot, 'ready_time') and bot.ready_time else None
                }
            except Exception as e:
                logger.error(f"Error getting bot status: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "ready": False
                }
        
        @self.app.post("/api/channel-message")
        async def send_channel_message(
            request: ChannelMessageRequest,
            api_key: str = Depends(verify_api_key)
        ):
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            logger.info(f"Received request to send message to channel {request.channel_id}")
            if not self.bot_loop:
                logger.error("Bot event loop not available")
                
                # Log the failed activity
                self.activity_logger.log_activity(
                    "channel_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": "Bot not initialized"},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail="Bot not initialized")
                
            try:
                # Log the activity attempt
                self.activity_logger.log_activity(
                    "channel_message",
                    key_owner,
                    {
                        "channel_id": request.channel_id, 
                        "message_preview": request.message[:50] + "..." if len(request.message) > 50 else request.message
                    }
                )
                
                # Submit coroutine to bot's event loop and wait for result
                future = asyncio.run_coroutine_threadsafe(
                    self.bot.send_channel_message(request.channel_id, request.message),
                    self.bot_loop
                )
                # Wait for the result with a timeout
                result = future.result(timeout=10)
                
                if not result.get("success", False):
                    logger.error(f"Error sending message: {result.get('error', 'Unknown error')}")
                    
                    # Log the failed activity
                    self.activity_logger.log_activity(
                        "channel_message",
                        key_owner,
                        {"channel_id": request.channel_id, "error": result.get('error', 'Unknown error')},
                        success=False
                    )
                    
                    raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
                
                return result
            except asyncio.TimeoutError:
                logger.error("Timeout while sending message to channel")
                
                # Log the timeout
                self.activity_logger.log_activity(
                    "channel_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": "Timeout"},
                    success=False
                )
                
                raise HTTPException(status_code=504, detail="Timeout while processing request")
            except Exception as e:
                logger.exception(f"Error processing channel message request: {str(e)}")
                
                # Log the exception
                self.activity_logger.log_activity(
                    "channel_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": str(e)},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.app.post("/api/direct-message")
        async def send_direct_message(
            request: DirectMessageRequest,
            api_key: str = Depends(verify_api_key)
        ):
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            logger.info(f"Received request to send DM to user {request.user_id}")
            if not self.bot_loop:
                logger.error("Bot event loop not available")
                
                # Log the failed activity
                self.activity_logger.log_activity(
                    "direct_message",
                    key_owner,
                    {"user_id": request.user_id, "error": "Bot not initialized"},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail="Bot not initialized")
                
            try:
                # Log the activity attempt
                self.activity_logger.log_activity(
                    "direct_message",
                    key_owner,
                    {
                        "user_id": request.user_id, 
                        "message_preview": request.message[:50] + "..." if len(request.message) > 50 else request.message
                    }
                )
                
                # Submit coroutine to bot's event loop and wait for result
                future = asyncio.run_coroutine_threadsafe(
                    self.bot.send_direct_message(request.user_id, request.message),
                    self.bot_loop
                )
                # Wait for the result with a timeout
                result = future.result(timeout=10)
                
                if not result.get("success", False):
                    logger.error(f"Error sending DM: {result.get('error', 'Unknown error')}")
                    
                    # Log the failed activity
                    self.activity_logger.log_activity(
                        "direct_message",
                        key_owner,
                        {"user_id": request.user_id, "error": result.get('error', 'Unknown error')},
                        success=False
                    )
                    
                    raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
                
                return result
            except asyncio.TimeoutError:
                logger.error("Timeout while sending DM")
                
                # Log the timeout
                self.activity_logger.log_activity(
                    "direct_message",
                    key_owner,
                    {"user_id": request.user_id, "error": "Timeout"},
                    success=False
                )
                
                raise HTTPException(status_code=504, detail="Timeout while processing request")
            except Exception as e:
                logger.exception(f"Error processing direct message request: {str(e)}")
                
                # Log the exception
                self.activity_logger.log_activity(
                    "direct_message",
                    key_owner,
                    {"user_id": request.user_id, "error": str(e)},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.app.post("/api/embed-message")
        async def send_embed_message(
            request: EmbedRequest,
            api_key: str = Depends(verify_api_key)
        ):
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            logger.info(f"Received request to send embed message to channel {request.channel_id}")
            if not self.bot_loop:
                logger.error("Bot event loop not available")
                
                # Log the failed activity
                self.activity_logger.log_activity(
                    "embed_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": "Bot not initialized"},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail="Bot not initialized")
                
            try:
                # Log the activity attempt
                self.activity_logger.log_activity(
                    "embed_message",
                    key_owner,
                    {
                        "channel_id": request.channel_id, 
                        "title": request.title,
                        "description_preview": request.description[:50] + "..." if request.description and len(request.description) > 50 else request.description
                    }
                )
                
                # Convert Pydantic model to dict
                embed_data = request.dict(exclude_none=True)
                
                # Submit coroutine to bot's event loop and wait for result
                future = asyncio.run_coroutine_threadsafe(
                    self.bot.send_embed_message(request.channel_id, embed_data),
                    self.bot_loop
                )
                # Wait for the result with a timeout
                result = future.result(timeout=10)
                
                if not result.get("success", False):
                    logger.error(f"Error sending embed: {result.get('error', 'Unknown error')}")
                    
                    # Log the failed activity
                    self.activity_logger.log_activity(
                        "embed_message",
                        key_owner,
                        {"channel_id": request.channel_id, "error": result.get('error', 'Unknown error')},
                        success=False
                    )
                    
                    raise HTTPException(status_code=400, detail=result.get("error", "Failed to send embed"))
                
                return result
            except asyncio.TimeoutError:
                logger.error("Timeout while sending embed message to channel")
                
                # Log the timeout
                self.activity_logger.log_activity(
                    "embed_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": "Timeout"},
                    success=False
                )
                
                raise HTTPException(status_code=504, detail="Timeout while processing request")
            except Exception as e:
                logger.exception(f"Error processing embed message request: {str(e)}")
                
                # Log the exception
                self.activity_logger.log_activity(
                    "embed_message",
                    key_owner,
                    {"channel_id": request.channel_id, "error": str(e)},
                    success=False
                )
                
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.app.get("/api/keys")
        async def get_api_keys(api_key: str = Depends(verify_api_key)):
            """Get information about all API keys."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key
            if not self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin':
                # Log the failed activity
                self.activity_logger.log_activity(
                    "view_keys",
                    key_owner,
                    {"error": "Not admin"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
                
            # Log this activity
            self.activity_logger.log_activity(
                "view_keys",
                key_owner,
                {}
            )
            
            return {"keys": self.api_key_manager.get_keys_info()}

        @self.app.post("/api/keys")
        async def create_api_key(
            request: APIKeyRequest,
            api_key: str = Depends(verify_api_key)
        ):
            """Create a new API key."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key
            if not self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin':
                # Log the failed activity
                self.activity_logger.log_activity(
                    "create_key",
                    key_owner,
                    {"requested_for": request.owner, "error": "Not admin"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Log the activity
            self.activity_logger.log_activity(
                "create_key",
                key_owner,
                {"created_for": request.owner, "expires_days": request.expires_days}
            )
            
            new_key = self.api_key_manager.create_key(
                request.owner,
                request.description,
                request.expires_days
            )
            
            return new_key

        @self.app.delete("/api/keys/{key}")
        async def revoke_api_key(
            key: str,
            api_key: str = Depends(verify_api_key)
        ):
            """Revoke an API key."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key
            if not self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin':
                # Log the failed activity
                self.activity_logger.log_activity(
                    "revoke_key",
                    key_owner,
                    {"key": key[:5] + "..." if len(key) > 5 else key, "error": "Not admin"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if key == api_key:
                # Log the failed activity
                self.activity_logger.log_activity(
                    "revoke_key",
                    key_owner,
                    {"key": key[:5] + "..." if len(key) > 5 else key, "error": "Cannot revoke own key"},
                    success=False
                )
                raise HTTPException(status_code=400, detail="Cannot revoke your own key")
            
            # Log the activity attempt
            self.activity_logger.log_activity(
                "revoke_key",
                key_owner,
                {"key": key[:5] + "..." if len(key) > 5 else key}
            )
            
            if self.api_key_manager.revoke_key(key):
                return {"success": True, "message": "API key revoked"}
            else:
                # Log the failed activity
                self.activity_logger.log_activity(
                    "revoke_key",
                    key_owner,
                    {"key": key[:5] + "..." if len(key) > 5 else key, "error": "Key not found"},
                    success=False
                )
                raise HTTPException(status_code=404, detail="API key not found")

        @self.app.post("/api/keys/{key}/rotate")
        async def rotate_api_key(
            key: str,
            api_key: str = Depends(verify_api_key)
        ):
            """Rotate an API key by creating a new one and revoking the old one."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key or own key
            is_admin = self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin'
            is_own_key = key == api_key
            
            if not (is_admin or is_own_key):
                # Log the failed activity
                self.activity_logger.log_activity(
                    "rotate_key",
                    key_owner,
                    {"key": key[:5] + "..." if len(key) > 5 else key, "error": "Not admin and not own key"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Log the activity attempt
            self.activity_logger.log_activity(
                "rotate_key",
                key_owner,
                {"key": key[:5] + "..." if len(key) > 5 else key}
            )
            
            new_key = self.api_key_manager.rotate_key(key)
            if new_key:
                return new_key
            else:
                # Log the failed activity
                self.activity_logger.log_activity(
                    "rotate_key",
                    key_owner,
                    {"key": key[:5] + "..." if len(key) > 5 else key, "error": "Key not found"},
                    success=False
                )
                raise HTTPException(status_code=404, detail="API key not found")

        @self.app.get("/api/activity")
        async def get_activity(
            days: int = 1,
            activity_type: Optional[str] = None,
            user: Optional[str] = None,
            limit: int = 100,
            api_key: str = Depends(verify_api_key)
        ):
            """Get recent activity logs."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key
            if not self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin':
                # Log the failed activity
                self.activity_logger.log_activity(
                    "view_activity",
                    key_owner,
                    {"days": days, "activity_type": activity_type, "user": user, "limit": limit, "error": "Not admin"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Log this activity
            self.activity_logger.log_activity(
                "view_activity",
                key_owner,
                {"days": days, "activity_type": activity_type, "user": user, "limit": limit}
            )
            
            activities = self.activity_logger.get_activities(
                days=days,
                activity_type=activity_type,
                user=user,
                limit=limit
            )
            
            return {"activities": activities}

        @self.app.get("/api/activity/stats")
        async def get_activity_stats(
            days: int = 1,
            api_key: str = Depends(verify_api_key)
        ):
            """Get activity statistics."""
            # Get the API key owner
            key_owner = self.api_key_manager.keys.get(api_key, {}).get('owner', 'unknown')
            
            # Check if admin key
            if not self.api_key_manager.keys.get(api_key, {}).get('owner') == 'admin':
                # Log the failed activity
                self.activity_logger.log_activity(
                    "view_stats",
                    key_owner,
                    {"days": days, "error": "Not admin"},
                    success=False
                )
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Log this activity
            self.activity_logger.log_activity(
                "view_stats",
                key_owner,
                {"days": days}
            )
            
            stats = self.activity_logger.get_statistics(days=days)
            
            return {"stats": stats}
    
    def set_bot_loop(self, loop):
        """Set the reference to the bot's event loop."""
        self.bot_loop = loop
        logger.info("Bot event loop reference set in API server")
    
    def start(self, host: str, port: int):
        """Start the API server."""
        logger.info(f"Starting API server on {host}:{port}")
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
    
    def start_in_thread(self, host: str, port: int):
        """Start the API server in a separate thread."""
        import threading
        self.api_thread = threading.Thread(
            target=self.start,
            args=(host, port),
            daemon=True
        )
        self.api_thread.start()
        return self.api_thread