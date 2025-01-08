import requests
import xml.etree.ElementTree as ET
import re
import discord
from discord.ext import tasks

intents = discord.Intents.default()
intents.messages = True
bot = discord.Client(intents=intents)

with open ("token.txt", "r") as file:
    TOKEN = file.read().strip()

CHANNEL_ID = 123456789  # Replace with your channel ID

last_message_id = None
last_date = None
last_alert_type = None

def fetch_alert_feed():
    url = "https://www.fcps.edu/alert_msg_feed"

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        item = root.find(".//item")
        if item is not None:
            title = item.find("title").text if item.find("title") is not None else ""
            date = ""
            closed = False
            delay = False

            if "Closed" in title:
                closed = True
                match = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b", title)
                if match:
                    date = match.group(0)
            elif "two hours late" in title.lower():
                delay = True
                match = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b", title)
                if match:
                    date = match.group(0)

            return date, closed, delay
        else:
            return None, None, None

    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None, None, None

@tasks.loop(minutes=1)
async def check_alerts():
    global last_date, last_message_id, last_alert_type
    current_date, is_closed, is_delay = fetch_alert_feed()

    channel = bot.get_channel(CHANNEL_ID)

    if channel is not None:
        if current_date != last_date or (is_closed and last_alert_type != "closed") or (is_delay and last_alert_type != "delay"):
            if last_message_id:
                try:
                    last_message = await channel.fetch_message(last_message_id)
                    await last_message.delete()
                except discord.NotFound:
                    pass

            if is_closed:
                message = await channel.send(f"**Alert:** FCPS Schools and Offices Closed on {current_date}")
                last_alert_type = "closed"
            elif is_delay:
                message = await channel.send(f"**Alert:** FCPS Schools Two Hours Late on {current_date}")
                last_alert_type = "delay"
            else:
                message = await channel.send("**No active alerts:** Schools are operating normally.")
                last_alert_type = "normal"

            last_message_id = message.id
            last_date = current_date

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    check_alerts.start()

bot.run(TOKEN)
