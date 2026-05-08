import discord
from discord.ext import commands
import os
import re
from datetime import datetime, timezone

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN4"

BOT_COLOR = 0x8E7CC3
ERROR_COLOR = 0xE74C3C
SUCCESS_COLOR = 0x57F287

SAFE_MENTIONS = discord.AllowedMentions(
    everyone=False,
    users=True,
    roles=False,
    replied_user=False
)

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    case_insensitive=True
)

bot.remove_command("help")


# ---------------- HELPERS ----------------
async def safe_delete(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass


def make_embed(title, description, color=BOT_COLOR):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_footer(text="Saly • clean server info")
    return embed


def parse_title_body(text, default_title="📌 Info"):
    if "|" in text:
        title, body = text.split("|", 1)
        title = title.strip()
        body = body.strip()

        if not title:
            title = default_title

        if not body:
            body = "No information provided."

        return title, body

    return default_title, text.strip()


def clean_sentence(text):
    text = text.strip()
    if not text:
        return ""

    return text[0].upper() + text[1:]


def smart_clean_text(raw_text):
    text = raw_text.strip()
    text = re.sub(r"[ \t]+", " ", text)

    lower = text.lower()

    # Vehicle / car info auto-cleaner
    if (
        "clean colour" in lower
        or "rim colour" in lower
        or "windows trim" in lower
        or "scratched" in lower
        or "tire smoke" in lower
        or "tyre smoke" in lower
    ):
        title = "🚗 Vehicle Condition Info"
        body = (
            "All vehicles are clean unless stated otherwise.\n\n"
            "**This includes:**\n"
            "• Body colour\n"
            "• Rim colour\n"
            "• Window tint\n"
            "• Trim\n"
            "• Accent colour\n\n"
            "If something is scratched, let me know and I’ll replace it with no problem.\n\n"
            "**Note:** tyre smoke and horns are not checked.\n\n"
            "🎟️ To trade, please create a ticket in the tickets channel."
        )
        return title, body

    # Heist payment info auto-cleaner
    if "heist" in lower or "heists" in lower:
        title = "💰 Heist Payment Availability"
        body = (
            "Please note that heist payments are only available during these times:\n\n"
            "• **Tuesday:** 12 PM – 4 PM UK time\n"
            "• **Thursday:** 12 PM – 4 PM UK time\n\n"
            "Outside these times, please use another payment method."
        )
        return title, body

    # Generic cleaner
    lines = [line.strip(" -•") for line in text.splitlines() if line.strip()]

    if len(lines) > 1:
        body = "\n".join(f"• {clean_sentence(line)}" for line in lines)
        return "📌 Server Info", body

    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [clean_sentence(part.strip()) for part in parts if part.strip()]

    if len(parts) > 1:
        body = "\n".join(f"• {part}" for part in parts)
    else:
        body = clean_sentence(text)

    return "📌 Server Info", body


# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"📝 Saly logged in as {bot.user}")
    print("----------------------------")


# ---------------- SALLY SPEAK ----------------
@bot.command(name="sallyspeak", aliases=["salyspeak", "speak", "say"])
@commands.has_permissions(administrator=True)
async def sallyspeak(ctx, *, message: str = None):
    if message is None:
        await ctx.send("❌ Usage: `!Sallyspeak your message here`")
        return

    await safe_delete(ctx)

    await ctx.send(
        message,
        allowed_mentions=SAFE_MENTIONS
    )


# ---------------- CLEAN YAP COMMAND ----------------
@bot.command(name="clean", aliases=["cleanyap", "format"])
@commands.has_permissions(administrator=True)
async def clean(ctx, *, message: str = None):
    if message is None:
        await ctx.send("❌ Usage: `!clean your messy message here`")
        return

    await safe_delete(ctx)

    title, body = smart_clean_text(message)

    embed = make_embed(title, body)
    await ctx.send(embed=embed)


# ---------------- CUSTOM EMBED ----------------
@bot.command(name="embed", aliases=["panel"])
@commands.has_permissions(administrator=True)
async def custom_embed(ctx, *, text: str = None):
    if text is None:
        await ctx.send(
            "❌ Usage:\n"
            "`!embed Title | Message here`"
        )
        return

    await safe_delete(ctx)

    title, body = parse_title_body(text, default_title="📌 Info")
    embed = make_embed(title, body)

    await ctx.send(embed=embed)


# ---------------- ANNOUNCE TO CHANNEL ----------------
@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel = None, *, message: str = None):
    if channel is None or message is None:
        await ctx.send(
            "❌ Usage:\n"
            "`!announce #channel message here`"
        )
        return

    await safe_delete(ctx)

    embed = make_embed("📢 Announcement", message)
    await channel.send(embed=embed, allowed_mentions=SAFE_MENTIONS)

    try:
        await ctx.send(f"✅ Announcement sent to {channel.mention}", delete_after=5)
    except Exception:
        pass


# ---------------- RULES PANEL ----------------
@bot.command(name="rules")
@commands.has_permissions(administrator=True)
async def rules(ctx):
    await safe_delete(ctx)

    description = (
        "Please read and follow the server rules.\n\n"
        "**1.** No BS.\n"
        "**2.** No NSFW content.\n"
        "**3.** Mods and the owner never go first in trades.\n"
        "**4.** English only.\n"
        "**5.** For DMO, payments must be made first.\n"
        "**6.** Selling money drops or modded accounts will result in a permanent ban.\n"
        "**7.** Do not promote your server outside the self-promo channel.\n"
        "**8.** If you get timed out twice, you may be banned.\n"
        "**9.** Do not waste staff time.\n\n"
        "Breaking the rules may result in timeouts, removal, or a ban."
    )

    embed = make_embed("📜 Rules", description)
    await ctx.send(embed=embed)


# ---------------- CAR INFO PANEL ----------------
@bot.command(name="carinfo", aliases=["cars", "vehicleinfo"])
@commands.has_permissions(administrator=True)
async def carinfo(ctx):
    await safe_delete(ctx)

    description = (
        "All vehicles are clean unless stated otherwise.\n\n"
        "**This includes:**\n"
        "• Body colour\n"
        "• Rim colour\n"
        "• Window tint\n"
        "• Trim\n"
        "• Accent colour\n\n"
        "If something is scratched, let me know and I’ll replace it with no problem.\n\n"
        "**Note:** tyre smoke and horns are not checked.\n\n"
        "🎟️ To trade, please create a ticket."
    )

    embed = make_embed("🚗 Vehicle Condition Info", description)
    await ctx.send(embed=embed)


# ---------------- HEIST INFO PANEL ----------------
@bot.command(name="heistinfo", aliases=["heists", "heist"])
@commands.has_permissions(administrator=True)
async def heistinfo(ctx):
    await safe_delete(ctx)

    description = (
        "Heist payments are only available during these times:\n\n"
        "• **Tuesday:** 12 PM – 4 PM UK time\n"
        "• **Thursday:** 12 PM – 4 PM UK time\n\n"
        "Outside these times, please use another payment method."
    )

    embed = make_embed("💰 Heist Payment Availability", description)
    await ctx.send(embed=embed)


# ---------------- SALY HELP ----------------
@bot.command(name="salyhelp", aliases=["sallyhelp", "salycommands"])
async def salyhelp(ctx):
    embed = make_embed(
        "📝 Saly Commands",
        (
            "**Speech Commands**\n"
            "`!Sallyspeak message` — Saly says your message.\n"
            "`!say message` — same as Sallyspeak.\n\n"
            "**Clean Info Commands**\n"
            "`!clean messy message` — turns messy text into a clean panel.\n"
            "`!embed Title | Message` — makes a custom info embed.\n"
            "`!announce #channel message` — posts an announcement to a channel.\n\n"
            "**Preset Panels**\n"
            "`!rules` — posts the rules panel.\n"
            "`!carinfo` — posts vehicle condition info.\n"
            "`!heistinfo` — posts heist payment times."
        )
    )

    await ctx.send(embed=embed)


# ---------------- ERRORS ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use Saly commands.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!salyhelp`.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing something. Try `!salyhelp`.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
