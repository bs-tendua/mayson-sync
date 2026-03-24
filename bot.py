# RENDER CALLS MAIN.PY NOT THIS

import discord
from discord.ext import tasks
import feedparser
import os
import json
import re
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# ==========================================
# CONFIGURATIONS
# ==========================================
RSS_FEED_URL = "https://rsshub.app/twitter/user/AskMayson"

# Card/Embed Elements
USERNAME = "Mayson.dev (@AskMayson)"
AUTHOR_ICON = "https://pbs.twimg.com/profile_images/2024024478930673664/H9OF_jv5_400x400.jpg"
EMBED_COLOR = 0x733DF2 # Discord.py uses 0x prefix for Hex colors
HOSTNAME = "x.com"

HISTORY_FILE = "posted_tweets.json"

# Set up Discord Client
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history), f)

def extract_image(html_content):
    match = re.search(r'<img[^>]+src="([^">]+)"', html_content)
    if match:
        return match.group(1)
    return None

# ==========================================
# BACKGROUND TASK (Runs every 5 minutes)
# ==========================================
@tasks.loop(minutes=5)
async def check_rss():
    # Fetch Channel ID from Environment Variables
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = client.get_channel(channel_id)
    
    if not channel:
        print("Error: Could not find channel. Check your CHANNEL_ID.")
        return

    posted_history = load_history()
    
    # If starting fresh, mark existing tweets as read without posting to prevent spam
    first_run = len(posted_history) == 0

    try:
        feed = feedparser.parse(RSS_FEED_URL)
        
        for entry in reversed(feed.entries):
            post_id = entry.get("id", entry.link)
            
            if post_id not in posted_history:
                if not first_run:
                    # 1. Title & Link
                    title_text = entry.title if len(entry.title) < 256 else entry.title[:253] + "..."
                    embed = discord.Embed(title=title_text, url=entry.link, color=EMBED_COLOR)
                    
                    # 2. Author
                    embed.set_author(name=USERNAME, icon_url=AUTHOR_ICON)
                    
                    # 3. Hostname (Footer)
                    embed.set_footer(text=HOSTNAME)
                    
                    # 4. Image Extraction
                    image_url = None
                    if 'media_content' in entry and len(entry.media_content) > 0:
                        image_url = entry.media_content[0]['url']
                    elif hasattr(entry, 'summary'):
                        image_url = extract_image(entry.summary)
                    
                    if image_url:
                        embed.set_image(url=image_url)
                        
                    # 5. Timestamp
                    try:
                        # Convert to timezone-aware datetime for discord.py
                        parsed_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        embed.timestamp = parsed_date
                    except Exception:
                        pass
                    
                    # Send Message
                    await channel.send(embed=embed)
                    await asyncio.sleep(2) # Prevent API rate limits
                
                posted_history.add(post_id)
        
        save_history(posted_history)
        
    except Exception as e:
        print(f"Error checking RSS: {e}")

@check_rss.before_loop
async def before_check_rss():
    await client.wait_until_ready()

# ==========================================
# BOT EVENTS
# ==========================================
@client.event
async def on_ready():
    print(f'Logged in securely as {client.user}')
    if not check_rss.is_running():
        check_rss.start()

# Start the bot
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing!")
    else:
        client.run(TOKEN)