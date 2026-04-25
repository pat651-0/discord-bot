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

    # Tickety handling
    if message.author.bot and message.author.name == "Tickety":

        if message.mentions:
            await message.delete()
            return

        if "Ticket Created" in message.content or "Ticket Created" in str(message.embeds):
            await message.delete()
            await message.channel.send(f"<@1137385938155221073> 🎟️ New ticket created!")
            return

        if "Ticket Closed" in message.content or "Ticket Closed" in str(message.embeds):
            await message.delete()
            return

    if message.mention_everyone:
        await message.delete()
        await message.channel.send("No @everyone allowed ❌")
        return

    await bot.process_commands(message)

    await bot.process_commands(message)   
bot.run(os.getenv("TOKEN"))



