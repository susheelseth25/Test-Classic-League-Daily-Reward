import discord
from discord.ext import commands, tasks
import random
from datetime import datetime, timezone, timedelta
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
WINNERS_COUNT = int(os.getenv("WINNERS_COUNT", "3"))
ENTRY_EMOJI = "✅"

# Times in HH:MM format (IST)
START_TIME = os.getenv("START_TIME", "01:30")
END_TIME = os.getenv("END_TIME", "13:40")

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

daily_message = None
participants = set()

# Dummy web server so Render free plan doesn't kill it
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return  # Silence logs

def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting dummy server on port {port}")
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

Thread(target=run_web, daemon=True).start()

def parse_time(time_str):
    hour, minute = map(int, time_str.split(":"))
    return hour, minute

START_HOUR, START_MINUTE = parse_time(START_TIME)
END_HOUR, END_MINUTE = parse_time(END_TIME)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Entry starts at {START_TIME} IST, ends at {END_TIME} IST")
    daily_cycle.start()

@tasks.loop(minutes=1)
async def daily_cycle():
    global daily_message, participants
    now = datetime.now(IST)

    if now.hour == START_HOUR and now.minute == START_MINUTE:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            participants = set()
            embed = discord.Embed(
                title="🏆 Daily Classic League Entry",
                description=f"React with {ENTRY_EMOJI} to enter today's draw!\nWinners will be picked at {END_TIME} IST",
                color=0xFFAA00
            )
            daily_message = await channel.send(embed=embed)
            await daily_message.add_reaction(ENTRY_EMOJI)
            print(f"New daily entry started at {now}")

    if now.hour == END_HOUR and now.minute == END_MINUTE and daily_message:
        channel = bot.get_channel(CHANNEL_ID)
        if channel and participants:
            winners = random.sample(list(participants), min(WINNERS_COUNT, len(participants)))
            mentions = " ".join(w.mention for w in winners)
            await channel.send(
                f"🎉 **Today's Winners** 🎉\n{mentions}\n\nCongrats! Tagging you as requested."
            )
            print(f"Winners: {[w.name for w in winners]}")
        else:
            await channel.send("No entries today.")
        daily_message = None
        participants = set()

@bot.event
async def on_raw_reaction_add(payload):
    global participants
    if daily_message and payload.message_id == daily_message.id and str(payload.emoji) == ENTRY_EMOJI:
        if payload.user_id != bot.user.id:
            user = bot.get_user(payload.user_id)
            if user:
                participants.add(user)

@bot.event
async def on_raw_reaction_remove(payload):
    global participants
    if daily_message and payload.message_id == daily_message.id and str(payload.emoji) == ENTRY_EMOJI:
        user = bot.get_user(payload.user_id)
        if user in participants:
            participants.remove(user)

if __name__ == "__main__":
    bot.run(TOKEN)
