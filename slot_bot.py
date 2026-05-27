import discord
from discord.ext import commands
import os
import json
import re
import time
from collections import defaultdict

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN2"  # replacing Sloty

WALL_CHANNEL_ID = 1509103133479932085  # Wall of Knobs channel

WARNINGS_FILE = "knob_warnings.json"

MAX_WARNINGS = 3
SPAM_LIMIT = 5
SPAM_SECONDS = 10

# These are banned anywhere in the message.
# Discord invite links are NOT banned.
BANNED_PHRASES = [
    "@everyone",
    "@here",

    "modded account",
    "modded accounts",
    "modded acc",
    "modded accs",
    "modded",

    "money boost",
    "money boosts",
    "money boosting",
    "cash boost",
    "cash boosts",

    "account boost",
    "account boosting",
    "boosting service",

    "selling accounts",
    "sell accounts",
    "buy accounts",
]

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

recent_messages = defaultdict(list)

# ---------------- JSON HELPERS ----------------
def load_json(file_name, default):
    if not os.path.exists(file_name):
        return default

    try:
        with open(file_name, "r") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(file_name, data):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4)


warnings_store = load_json(WARNINGS_FILE, {})


def save_warnings():
    save_json(WARNINGS_FILE, warnings_store)


def get_warnings(user_id):
    return warnings_store.get(str(user_id), 0)


def add_warning(user_id):
    uid = str(user_id)
    warnings_store[uid] = warnings_store.get(uid, 0) + 1
    save_warnings()
    return warnings_store[uid]


def clear_warnings(user_id):
    uid = str(user_id)

    if uid in warnings_store:
        del warnings_store[uid]
        save_warnings()


# ---------------- SMART TEXT DETECTION ----------------
def normalize_text(text):
    text = text.lower()
    text = text.replace("@\u200b", "@")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_text(text):
    text = text.lower()

    replacements = {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "$": "s",
        "!": "i",
        "@": "a"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def detect_offence(message_content):
    normal = normalize_text(message_content)
    compact = compact_text(message_content)

    for phrase in BANNED_PHRASES:
        phrase_normal = normalize_text(phrase)
        phrase_compact = compact_text(phrase)

        # Detect phrase normally anywhere in the message
        if phrase_normal in normal:
            return f"Banned phrase: {phrase}"

        # Detect sneaky versions like m0dded acc / money_boost
        if phrase_compact and phrase_compact in compact:
            return f"Banned phrase: {phrase}"

    return None


def is_spam(user_id, content):
    now = time.time()
    uid = str(user_id)
    clean_content = normalize_text(content)

    recent_messages[uid].append((now, clean_content))

    recent_messages[uid] = [
        item for item in recent_messages[uid]
        if now - item[0] <= SPAM_SECONDS
    ]

    same_messages = [
        item for item in recent_messages[uid]
        if item[1] == clean_content
    ]

    return len(same_messages) >= SPAM_LIMIT


# ---------------- WALL LOG ----------------
async def send_wall_log(member, offence, punishment, message_content, warning_count):
    channel = bot.get_channel(WALL_CHANNEL_ID)

    if channel is None:
        print(f"❌ Wall of Knobs channel not found: {WALL_CHANNEL_ID}")
        return

    embed = discord.Embed(
        title="🧱 Wall of Knobs 🧱",
        description="Another rule breaker has been added to the wall.",
        color=discord.Color.red()
    )

    embed.add_field(name="Their @", value=member.mention, inline=False)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.add_field(name="Offence", value=offence, inline=False)
    embed.add_field(name="Warnings", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
    embed.add_field(name="Punishment", value=punishment, inline=True)

    if message_content:
        safe_message = message_content[:900]
        embed.add_field(name="Deleted Message", value=f"```{safe_message}```", inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(embed=embed)


# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"🔨 Knob Bot logged in as {bot.user}")
    print("----------------------------")


# ---------------- AUTO MODERATION ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    member = message.author

    # Staff/admins are immune
    if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
        await bot.process_commands(message)
        return

    content = message.content
    offence = detect_offence(content)

    if offence is None:
        if is_spam(member.id, content):
            offence = "Spam / repeated messages"

    if offence is not None:
        warning_count = add_warning(member.id)

        # Delete the rule-breaking message
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send(
                "❌ I need *Manage Messages* permission to delete rule-breaking messages."
            )
        except Exception:
            pass

        if warning_count >= MAX_WARNINGS:
            punishment = "Kicked"

            await send_wall_log(
                member=member,
                offence=offence,
                punishment=punishment,
                message_content=content,
                warning_count=warning_count
            )

            try:
                await member.send(
                    f"🔨 You were kicked from *{message.guild.name}*.\n"
                    f"Reason: **{offence}**\n"
                    f"You reached *{MAX_WARNINGS} warnings*."
                )
            except Exception:
                pass

            try:
                await member.kick(
                    reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}"
                )
                clear_warnings(member.id)
            except discord.Forbidden:
                await message.channel.send(
                    f"❌ I tried to kick {member.mention}, but my role is not high enough."
                )
            except Exception as e:
                print(e)
                await message.channel.send(
                    f"❌ I tried to kick {member.mention}, but something went wrong."
                )

            return

        await send_wall_log(
            member=member,
            offence=offence,
            punishment="Warning",
            message_content=content,
            warning_count=warning_count
        )

        await message.channel.send(
            f"⚠️ {member.mention}, warning *{warning_count}/{MAX_WARNINGS}* — {offence}.\n"
            "Your message was deleted."
        )

        return

    await bot.process_commands(message)


# ---------------- COMMANDS ----------------
@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    count = get_warnings(member.id)
    await ctx.send(f"⚠️ {member.mention} has *{count}/{MAX_WARNINGS}* warnings.")


@bot.command(name="clearwarnings")
@commands.has_permissions(manage_messages=True)
async def clearwarnings(ctx, member: discord.Member):
    clear_warnings(member.id)
    await ctx.send(f"✅ Cleared warnings for {member.mention}.")


@bot.command(name="knobstatus")
@commands.has_permissions(manage_messages=True)
async def knobstatus(ctx):
    banned_list = "\n".join(f"- {phrase}" for phrase in BANNED_PHRASES)

    embed = discord.Embed(
        title="🔨 Knob Bot Status",
        description=(
            "Knob Bot is active.\n\n"
            f"Punishment: **Kick after {MAX_WARNINGS} warnings**\n"
            "Bad messages are automatically deleted.\n\n"
            "**Banned phrases:**\n"
            f"{banned_list}"
        ),
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)


@bot.command(name="manualwall")
@commands.has_permissions(manage_messages=True)
async def manualwall(ctx, member: discord.Member, *, offence):
    warning_count = add_warning(member.id)

    await send_wall_log(
        member=member,
        offence=offence,
        punishment="Manual warning",
        message_content="Manual staff report",
        warning_count=warning_count
    )

    await ctx.send(f"🧱 Added {member.mention} to the Wall of Knobs.")


# ---------------- ERROR HANDLER ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that command.")
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ I could not find that member.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Missing info. Try:\n"
            "`?warnings @user`\n"
            "`?clearwarnings @user`\n"
            "?manualwall @user offence"
        )
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN BOT ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
