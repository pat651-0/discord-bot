
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

    try:
        message = await ctx.channel.fetch_message(message.id)
    except Exception:
        await ctx.send("❌ Giveaway message was deleted or could not be found.")
        return

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
async def giveaway(ctx, amount: int, *, prize_type):
    """
    Examples:
    ?giveaway 4 Normal
    ?giveaway 5 Hard Trade
    ?giveaway 2 Very Hard Trade
    """

    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize_type = prize_type.lower().strip()

    if prize_type == "normal":
        prize = f"🚘 {amount} Normal Car"
        if amount != 1:
            prize += "s"

    elif prize_type == "hard trade":
        prize = f"✨ {amount} Hard Trade"
        if amount != 1:
            prize += "s"

    elif prize_type == "very hard trade":
        prize = f"💎 {amount} Very Hard Trade"
        if amount != 1:
            prize += "s"

    else:
        await ctx.send(
            "❌ Use:\n"
            "`?giveaway 4 Normal`\n"
            "`?giveaway 5 Hard Trade`\n"
            "?giveaway 2 Very Hard Trade"
        )
        return

    try:
        await ctx.message.delete()
    except Exception:
        pass

    await start_giveaway(ctx, prize)


@bot.command(name="testgiveaway")
@commands.has_permissions(administrator=True)
async def testgiveaway(ctx, amount: int, *, prize_type):
    """
    30 second test giveaway.
    Examples:
    ?testgiveaway 1 Normal
    ?testgiveaway 2 Hard Trade
    """

    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize_type = prize_type.lower().strip()

    if prize_type == "normal":
        prize = f"🚘 {amount} Normal Car"
        if amount != 1:
            prize += "s"

    elif prize_type == "hard trade":
        prize = f"✨ {amount} Hard Trade"
        if amount != 1:
            prize += "s"

    elif prize_type == "very hard trade":
        prize = f"💎 {amount} Very Hard Trade"
        if amount != 1:
            prize += "s"

    else:
        await ctx.send(
            "❌ Use:\n"
            "`?testgiveaway 1 Normal`\n"
            "`?testgiveaway 2 Hard Trade`\n"
            "?testgiveaway 1 Very Hard Trade"
        )
        return

    embed = discord.Embed(
        title="🎉 TEST GIVEAWAY 🎉",
        description=(
            f"Prize: **{prize}**\n\n"
            "React with 🎉 to enter!\n\n"
            "⏰ Ends in *30 seconds*"
        ),
        color=discord.Color.gold()
    )

    try:
        await ctx.message.delete()
    except Exception:
        pass

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    await asyncio.sleep(30)

    try:
        message = await ctx.channel.fetch_message(message.id)
    except Exception:
        await ctx.send("❌ Test giveaway message was deleted or could not be found.")
        return

    entries = []

    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    entries.append(user)

    if len(entries) == 0:
        await ctx.send(f"❌ No one entered the *{prize}* test giveaway.")
        return

    winner = random.choice(entries)

    await ctx.send(f"🎉 TEST WINNER: {winner.mention} won *{prize}*!")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permission to start giveaways.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Missing info. Use:\n"
            "`?giveaway 4 Normal`\n"
            "`?giveaway 5 Hard Trade`\n"
            "?giveaway 2 Very Hard Trade"
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "❌ The first thing after ?giveaway must be a number.\n"
            "Example: ?giveaway 5 Hard Trade"
        )
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
