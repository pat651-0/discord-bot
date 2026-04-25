import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
if message.mention_everyone:
        await message.delete()
        await message.channel.send("No @everyone allowed 🚫")

    if message.content == "ping":
        await message.channel.send("pong")

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))



