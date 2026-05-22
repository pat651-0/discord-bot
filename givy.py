import discord
from discord.ext import commands
import os
import random
import asyncio

TOKEN_NAME = "TOKEN5"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

GIVEAWAY_TIME = 24 * 60 * 60  # 24 hours


@bot.event
async def on_ready():
    print("----------------------------")
    print(f"🎉 Giveaway Bot logged in as {bot.user}")
    print("----------------------------")


async def start_giveaway(ctx, prize):
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"Prize: **{prize}**\n\n"
            "React with 🎉 to enter!\n\n"
            "⏰ Ends in *24 hours*"
        ),
        color=discord.Color.gold()
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    await asyncio.sleep(GIVEAWAY_TIME)

    message = await ctx.channel.fetch_message(message.id)

    entries = []

    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    entries.append(user)

    if len(entries) == 0:
        await ctx.send(f"❌ No one entered the *{prize}* giveaway.")
        return

    winner = random.choice(entries)

    end_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=(
            f"Prize: **{prize}**\n\n"
            f"Winner: {winner.mention}"
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=end_embed)
    await ctx.send(f"🎉 Congratulations {winner.mention}! You won *{prize}*!")


@bot.command(name="giveaway")
@commands.has_permissions(administrator=True)
async def giveaway(ctx, *, prize_type):
    prize_type = prize_type.lower()

    if prize_type == "normal":
        await start_giveaway(ctx, "🚘 Normal")
    elif prize_type == "hard trade":
        await start_giveaway(ctx, "✨ Hard Trade")
    elif prize_type == "very hard trade":
        await start_giveaway(ctx, "💎 Very Hard Trade")
    else:
        await ctx.send(
            "❌ Use:\n"
            "`?giveaway Normal`\n"
            "`?giveaway Hard Trade`\n"
            "?giveaway Very Hard Trade"
        )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permission to start giveaways.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
