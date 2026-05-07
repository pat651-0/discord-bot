import discord
from discord.ext import commands
import os

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN3"
LEAVES_CHANNEL_ID = 1475079442291363901

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"⚖️ Board of Guilt logged in as {bot.user}")
    print("----------------------------")

# ---------------- WHEN SOMEONE LEAVES ----------------
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        print(f"❌ Channel not found: {LEAVES_CHANNEL_ID}")
        return

    embed = discord.Embed(
        title="⚖️ Board of Guilt",
        description=(
            f"💀 **{member.name}** left the server...\n\n"
            "Their name shall stay here forever."
        ),
        color=discord.Color.red()
    )

    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)

    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(
        content=f"bye I guess... <@{member.id}>",
        embed=embed
    )

# ---------------- TEST COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def testguilt(ctx):
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")

# ---------------- ERRORS ----------------
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
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
