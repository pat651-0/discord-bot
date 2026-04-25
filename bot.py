import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    # ignore bot itself
    if message.author == bot.user:
        return

    # 🎟️ Tickety handling
    if message.author.bot and message.author.name == "Tickety":

        # wait so message exists properly
        await asyncio.sleep(1)

        try:
            # delete ping messages
            if message.mentions:
                await message.delete()
                return

            # ticket created
            if "Ticket Created" in message.content or "Ticket Created" in str(message.embeds):
                await message.delete()
                await message.channel.send(f"<@1137385938155221073> 🎟️ New ticket created!")
                return

            # ticket closed
            if "Ticket Closed" in message.content or "Ticket Closed" in str(message.embeds):
                await message.delete()
                return

        except:
            pass  # prevents Unknown Message error

    # 🚫 block @everyone
    if message.mention_everyone:
        try:
            await message.delete()
            await message.channel.send("No @everyone allowed ❌")
        except:
            pass
        return

    # allow commands to still work
    await bot.process_commands(message)


bot.run(os.getenv("TOKEN"))
