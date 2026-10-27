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

# Start time (IST)
START_HOUR = int(os.getenv("START_HOUR", "1"))
START_MINUTE = int(os.getenv("START_MINUTE", "30"))

# End time (IST)
END_HOUR = int(os.getenv("END_HOUR", "13"))
END_MINUTE = int(os.getenv("END_MINUTE", "40"))

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

def run_web():
    server = HTTPServer(("0.0.0.0", int(os.getenv("PORT", 10000))), DummyHandler)
    server.serve_forever()

Thread(target=run_web, daemon=True).start()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    daily_cycle.start()

@tasks.loop(minutes=1)
async def daily_cycle():
    global daily_message, participants
    now = datetime.now(IST)

    # Start entry
    if now.hour == START_HOUR and now.minute == START_MINUTE:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            participants = set()
            embed = discord.Embed(
                title="🏆 Daily Classic League Entry",
                description=f"React with {ENTRY_EMOJI} to enter today's draw!\nWinners will be picked at {END_HOUR:02d}:{END_MINUTE:02d} IST",
                color=0xFFAA00
            )
            daily_message = await channel.send(embed=embed)
            await daily_message.add_reaction(ENTRY_EMOJI)
            print(f"New daily entry started at {now}")

    # End entry / pick winners
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
