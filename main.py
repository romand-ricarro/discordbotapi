# main.py
import asyncio
import signal
import sys
import logging
import os
from datetime import datetime

from discord_bot import DiscordBot
from api_server import APIServer
import config

# Set up logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
today = datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(log_dir, f"discord_bot_{today}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Global flag for shutdown
shutdown_flag = False

async def main():
    # Initialize the Discord bot
    bot = DiscordBot(config.DISCORD_BOT_TOKEN)
    
    # Get the current event loop
    bot_loop = asyncio.get_event_loop()
    
    # Initialize the API server
    api_server = APIServer(bot)
    
    # Pass the bot's event loop to the API server
    api_server.set_bot_loop(bot_loop)
    
    # Start the API server in a separate thread
    api_thread = api_server.start_in_thread(config.API_HOST, config.API_PORT)
    
    # Start the bot
    bot_task = bot.start_in_background()
    
    # Wait for the bot to connect
    try:
        await asyncio.wait_for(bot.wait_until_ready(), timeout=60)
        logger.info("Bot is ready and connected to Discord")
    except asyncio.TimeoutError:
        logger.error("Timed out waiting for bot to connect")
        return
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        global shutdown_flag
        if shutdown_flag:
            logger.info("Forced shutdown")
            sys.exit(1)
        
        logger.info("Shutdown signal received, closing connections...")
        shutdown_flag = True
        asyncio.create_task(bot.close())
        sys.exit(0)
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    
    # Keep the main task running
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Bot task cancelled")
    finally:
        logger.info("Bot is shutting down")
        await bot.close()

if __name__ == "__main__":
    try:
        # Run the main coroutine
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting...")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)