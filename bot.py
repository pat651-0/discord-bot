import discord
from discord.ext import commands
import os
import asyncio

# intents
intents = discord.Intents.default()
intents.message_content = True

# bot
bot = commands.Bot(command_prefix="!", intents=intents)

# ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# main handler
@bot.event
async def on_message(message):
    # ignore itself
    if message.author == bot.user:
        return

    # 🎟️ Tickety handling
    if message.author.bot and message.author.name.lower() == "tickety":

        # wait so message fully loads (fixes unknown message error)
        await asyncio.sleep(1)

        try:
            # handle embeds (Tickety uses embeds)
            if message.embeds:
                embed = message.embeds[0]
                title = embed.title or ""

                # ticket created
                if "Ticket Created" in title:
                    await message.delete()
                    await message.channel.send(f"<@1137385938155221073> 🎟️ New ticket created!")
                    return

                # ticket closed
                if "Ticket Closed" in title:
                    await message.delete()
                    return

            # fallback (mentions)
            if message.mentions:
                await message.delete()
                return

        except:
            pass  # stops crashes

    # 🚫 block @everyone
    if message.mention_everyone:
        try:
            await message.delete()
            await message.channel.send("No @everyone allowed ❌")
        except:
            pass
        return

    # allow commands
    await bot.process_commands(message)


# run bot
bot.run(os.getenv("TOKEN"))
