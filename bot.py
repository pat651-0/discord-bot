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
    if message.author == bot.user:
        return

    # Tickety handling
    if message.author.bot and message.author.name == "Tickety":

        if message.embeds:
            embed = message.embeds[0]
            title = embed.title or ""

            # 🎟️ Ticket Created
            if "Ticket Created" in title:
                await asyncio.sleep(1)  # 👈 delay fixes error
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(f"<@1137385938155221073> 🎟️ New ticket created!")
                return

            # ❌ Ticket Closed
            if "Ticket Closed" in title:
                await asyncio.sleep(1)  # 👈 delay fixes error
                try:
                    await message.delete()
                except:
                    pass
                return

    # block @everyone
    if message.mention_everyone:
        try:
            await message.delete()
        except:
            pass
        await message.channel.send("No @everyone allowed ❌")
        return

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
