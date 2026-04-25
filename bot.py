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
    # Ignore yourself
    if message.author == bot.user:
        return

    # Handle Tickety messages safely (NO deleting)
    if message.author.bot and message.author.name.lower() == "tickety":
        if message.embeds:
            embed = message.embeds[0]
            title = embed.title or ""

            if "Ticket Created" in title:
                await message.channel.send(
                    "<@1137385938155221073> 🎟️ New ticket created!"
                )
                return

            if "Ticket Closed" in title:
                return

    # Block @everyone
    if message.mention_everyone:
        await message.delete()
        await message.channel.send("No @everyone allowed ❌")
        return

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
