import asyncio
import discord
from discord.ext import commands
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord_bot")

class DiscordBot:
    def __init__(self, token):
        """Initialize the Discord bot with the given token."""
        self.token = token
        # Create intents with message content intent enabled
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Create bot instance
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.is_ready = asyncio.Event()
        
        # Register event handlers
        @self.bot.event
        async def on_ready():
            logger.info(f"Discord Bot logged in as {self.bot.user}")
            self.is_ready.set()
        
        @self.bot.event
        async def on_message(message):
            # Don't respond to our own messages
            if message.author == self.bot.user:
                return
            
            # Process commands
            await self.bot.process_commands(message)
    
    async def start(self):
        """Start the Discord bot."""
        logger.info("Starting Discord bot...")
        await self.bot.start(self.token)
    
    def start_in_background(self):
        """Start the bot in a background task."""
        self.task = asyncio.create_task(self.start())
        return self.task
    
    async def wait_until_ready(self):
        """Wait until the bot is ready and connected to Discord."""
        await self.is_ready.wait()
    
    async def send_channel_message(self, channel_id, message_content):
        """Send a message to a specific channel."""
        try:
            await self.wait_until_ready()
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel with ID {channel_id} not found")
                return {"success": False, "error": "Channel not found"}
            
            message = await channel.send(content=message_content)
            logger.info(f"Message sent to channel {channel_id}")
            return {
                "success": True,
                "message_id": str(message.id),
                "timestamp": str(message.created_at)
            }
        except Exception as e:
            logger.error(f"Error sending message to channel: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_direct_message(self, user_id, message_content):
        """Send a direct message to a specific user."""
        try:
            await self.wait_until_ready()
            user = await self.bot.fetch_user(int(user_id))
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return {"success": False, "error": "User not found"}
            
            dm_channel = await user.create_dm()
            message = await dm_channel.send(content=message_content)
            logger.info(f"DM sent to user {user_id}")
            return {
                "success": True,
                "message_id": str(message.id),
                "timestamp": str(message.created_at)
            }
        except Exception as e:
            logger.error(f"Error sending DM: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_embed_message(self, channel_id, embed_data):
        """Send an embed message to a specific channel."""
        try:
            await self.wait_until_ready()
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Channel with ID {channel_id} not found")
                return {"success": False, "error": "Channel not found"}
            
            # Create the embed
            embed = discord.Embed(
                title=embed_data.get("title"),
                description=embed_data.get("description"),
                url=embed_data.get("url")
            )
            
            # Set color if provided
            if embed_data.get("color"):
                try:
                    color_hex = embed_data["color"].lstrip('#')
                    embed.color = int(color_hex, 16)
                except ValueError:
                    logger.warning(f"Invalid color format: {embed_data['color']}")
            
            # Add thumbnail if provided
            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=embed_data["thumbnail"])
            
            # Add image if provided
            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])
            
            # Add footer if provided
            if embed_data.get("footer"):
                icon_url = embed_data["footer"].get("icon_url")
                embed.set_footer(text=embed_data["footer"]["text"], icon_url=icon_url)
            
            # Add author if provided
            if embed_data.get("author"):
                name = embed_data["author"]["name"]
                url = embed_data["author"].get("url")
                icon_url = embed_data["author"].get("icon_url")
                embed.set_author(name=name, url=url, icon_url=icon_url)
            
            # Add fields if provided
            if embed_data.get("fields"):
                for field in embed_data["fields"]:
                    embed.add_field(
                        name=field["name"],
                        value=field["value"],
                        inline=field.get("inline", False)
                    )
            
            # Send the embed
            message = await channel.send(embed=embed)
            logger.info(f"Embed message sent to channel {channel_id}")
            return {
                "success": True,
                "message_id": str(message.id),
                "timestamp": str(message.created_at)
            }
        except Exception as e:
            logger.error(f"Error sending embed message to channel: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def close(self):
        """Close the Discord bot connection."""
        logger.info("Closing Discord bot...")
        await self.bot.close()