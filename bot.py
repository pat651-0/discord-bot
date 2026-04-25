import discord
from discord.ext import commands
import os

# intents
intents = discord.Intents.default()
intents.message_content = True

# bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# ready event
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# message handler
@bot.event
async def on_message(message):
    # ignore self
    if message.author == bot.user:
        return

    # Tickety handling
    if message.author.bot and message.author.name == "Tickety":

        if message.embeds:
            embed = message.embeds[0]
            title = embed.title or ""

            # 🎟️ Ticket Created
            if "Ticket Created" in title:
                await message.delete()
                await message.channel.send(f"<@1137385938155221073> 🎟️ New ticket created!")
                return

            # ❌ Ticket Closed
            if "Ticket Closed" in title:
                await message.delete()
                return

    # block @everyone
    if message.mention_everyone:
        await message.delete()
        await message.channel.send("No @everyone allowed ❌")
        return

    # allow commands
    await bot.process_commands(message)

# run bot
bot.run(os.getenv("TOKEN"))
