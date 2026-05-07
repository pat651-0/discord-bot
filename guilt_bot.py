import discord
from discord.ext import commands
import os
from datetime import datetime

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN3"
LEAVES_CHANNEL_ID = 1475079442291363901

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"⚖️ Board of Guilt logged in as {bot.user}")
    print("----------------------------")

# ---------------- MEMBER LEAVE EVENT ----------------
@bot.event
async def on_member_remove(member: discord.Member):
    channel = bot.get_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        print(f"❌ Leaves channel not found: {LEAVES_CHANNEL_ID}")
        return

    joined_at = "Unknown"
    if member.joined_at is not None:
        joined_at = member.joined_at.strftime("%d/%m/%Y %H:%M")

    created_at = member.created_at.strftime("%d/%m/%Y %H:%M")

    embed = discord.Embed(
        title="⚖️ Board of Guilt",
        description="Oh you leaving?",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )

    embed.add_field(
        name="Guilty Member",
        value=f"**Name:** {member.name}\n**Display:** {member.display_name}\n**ID:** `{member.id}`",
        inline=False
    )

    embed.add_field(
        name="Account Created",
        value=created_at,
        inline=True
    )

    embed.add_field(
        name="Joined Server",
        value=joined_at,
        inline=True
    )

    embed.add_field(
        name="Server Members Left",
        value=str(member.guild.member_count),
        inline=True
    )

    embed.set_footer(text="Their name stays on the board forever.")
    
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(
        content=f"bye I guess... **{member.name}** (`{member.id}`)",
        embed=embed
    )

# ---------------- TEST COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def testguilt(ctx):
    embed = discord.Embed(
        title="⚖️ Board of Guilt Test",
        description="If you can see this, the Board of Guilt is working.",
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)

# ---------------- ERROR HANDLING ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that command.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")

# ---------------- RUN ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found. Add {TOKEN_NAME} in Railway Variables.")
else:
    bot.run(token)