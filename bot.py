import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):

    @bot.event
async def on_message(message):
    if message.author.bot:
        return

    # detect ticket close
    if "ticket closed" in message.content.lower():
        await message.channel.send("Closing ticket in 5 seconds...")
        await message.channel.delete(delay=5)

    # delete transcripts/logs
    if "transcript" in message.content.lower():
        try:
            await message.delete(delay=5)
        except:
            pass

    await bot.process_commands(message)

import os
bot.run(os.getnev("TOKEN"))




