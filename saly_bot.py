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
async def delete_command(ctx):
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
        title = title.strip() or default_title
        body = body.strip() or "No information provided."
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
            "🎟️ To trade, please create a ticket."
        )
        return title, body

    if "heist" in lower or "heists" in lower:
        title = "💰 Heist Payment Availability"
        body = (
            "Please note that heist payments are only available during these times:\n\n"
            "• **Tuesday:** 12 PM – 4 PM UK time\n"
            "• **Thursday:** 12 PM – 4 PM UK time\n\n"
            "Outside these times, please use another payment method."
        )
        return title, body

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
        await ctx.send("❌ Usage: `!sallyspeak your message here`")
        return

    await ctx.send(message)
    await delete_command(ctx)


# ---------------- CLEAN YAP COMMAND ----------------
@bot.command(name="clean", aliases=["cleanyap", "format"])
@commands.has_permissions(administrator=True)
async def clean(ctx, *, message: str = None):
    if message is None:
        await ctx.send("❌ Usage: `!clean your messy message here`")
        return

    title, body = smart_clean_text(message)
    embed = make_embed(title, body)

    await ctx.send(embed=embed)
    await delete_command(ctx)


# ---------------- CUSTOM EMBED ----------------
@bot.command(name="embed", aliases=["panel"])
@commands.has_permissions(administrator=True)
async def custom_embed(ctx, *, text: str = None):
    if text is None:
        await ctx.send("❌ Usage: `!embed Title | Message here`")
        return

    title, body = parse_title_body(text, default_title="📌 Info")
    embed = make_embed(title, body)

    await ctx.send(embed=embed)
    await delete_command(ctx)


# ---------------- ANNOUNCE TO CHANNEL ----------------
@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel = None, *, message: str = None):
    if channel is None or message is None:
        await ctx.send("❌ Usage: `!announce #channel message here`")
        return

    embed = make_embed("📢 Announcement", message)

    await channel.send(embed=embed)
    await delete_command(ctx)

    try:
        await ctx.send(f"✅ Announcement sent to {channel.mention}", delete_after=5)
    except Exception:
        pass


# ---------------- RULES PANEL ----------------
@bot.command(name="rules")
@commands.has_permissions(administrator=True)
async def rules(ctx):
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
    await delete_command(ctx)


# ---------------- CAR INFO PANEL ----------------
@bot.command(name="carinfo", aliases=["cars", "vehicleinfo"])
@commands.has_permissions(administrator=True)
async def carinfo(ctx):
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
    await delete_command(ctx)


# ---------------- HEIST INFO PANEL ----------------
@bot.command(name="heistinfo", aliases=["heists", "heist"])
@commands.has_permissions(administrator=True)
async def heistinfo(ctx):
    description = (
        "Heist payments are only available during these times:\n\n"
        "• **Tuesday:** 12 PM – 4 PM UK time\n"
        "• **Thursday:** 12 PM – 4 PM UK time\n\n"
        "Outside these times, please use another payment method."
    )

    embed = make_embed("💰 Heist Payment Availability", description)
    await ctx.send(embed=embed)
    await delete_command(ctx)


# ---------------- SLOT INFO PANEL ----------------
@bot.command(name="slotinfo")
@commands.has_permissions(administrator=True)
async def slotinfo(ctx):
    description = (
        "Use your coins to spin the Sloty machine and try your luck 🍀\n\n"
        "Each spin costs **1 coin**.\n\n"
        "**Chances:**\n\n"
        "🚫 **Nothing — 70%**\n"
        "Maybe next time 🚫\n\n"
        "🚘 **Normal Cars — 24%**\n"
        "Not bad 🚘\n\n"
        "✨ **Hard Trade — 5%**\n"
        "Nice pull ✨\n\n"
        "💎 **Very Hard Trade — 1%**\n"
        "🎰🎰💎🔥\n\n"
        "If you win anything except **Nothing**, Sloty will automatically open a win ticket under **Game Corner**.\n\n"
        "In the ticket, send a pic of what car you want so I can sort your prize. 🚗📸\n\n"
        "You’ll earn a coin when we finish the trade. 🎟️➡️🪙"
    )

    embed = make_embed("🎰 Slot Machine Info 🎰", description)
    await ctx.send(embed=embed)
    await delete_command(ctx)


# ---------------- SALY HELP ----------------
@bot.command(name="salyhelp", aliases=["sallyhelp", "salycommands"])
async def salyhelp(ctx):
    embed = make_embed(
        "📝 Saly Commands",
        (
            "**Speech Commands**\n"
            "`!sallyspeak message` — Saly says your message.\n"
            "`!say message` — same as sallyspeak.\n\n"
            "**Clean Info Commands**\n"
            "`!clean messy message` — turns messy text into a clean panel.\n"
            "`!embed Title | Message` — makes a custom info embed.\n"
            "`!announce #channel message` — posts an announcement to a channel.\n\n"
            "**Preset Panels**\n"
            "`!rules` — posts the rules panel.\n"
            "`!carinfo` — posts vehicle condition info.\n"
            "`!heistinfo` — posts heist payment times.\n"
            "`!slotinfo` — posts Sloty info."
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

