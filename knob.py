import discord
from discord.ext import commands
from discord import app_commands
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

# Kick or ban when they reach max warnings
PUNISHMENT_ON_MAX_WARNINGS = "kick"  # change to "ban" if you want bans

# Sales are allowed.
# Discord server links are allowed.
# Car trading words are allowed.
# This list only targets modded accounts / account sales / money boosts.
BANNED_PHRASES = [
    # Mass pings
    "@everyone",
    "@here",

    # Modded account wording
    "modded account",
    "modded accounts",
    "modded acc",
    "modded accs",
    "modded gta account",
    "modded gta accounts",
    "gta modded account",
    "gta modded accounts",
    "pre modded account",
    "pre-modded account",
    "fresh modded account",
    "fresh modded accounts",
    "stacked account",
    "stacked accounts",
    "boosted account",
    "boosted accounts",
    "maxed account",
    "maxed accounts",
    "ranked account",
    "ranked accounts",
    "high level account",
    "high level accounts",
    "recovery account",
    "recovery accounts",

    # Account selling only
    "account for sale",
    "accounts for sale",
    "account's for sale",
    "acc for sale",
    "accs for sale",
    "account sale",
    "accounts sale",
    "selling account",
    "selling accounts",
    "selling acc",
    "selling accs",
    "sell account",
    "sell accounts",
    "sell acc",
    "sell accs",
    "buy account",
    "buy accounts",
    "buy acc",
    "buy accs",
    "account selling",
    "account seller",
    "acc seller",
    "account shop",
    "acc shop",
    "account store",
    "acc store",
    "cheap account",
    "cheap accounts",
    "cheap acc",
    "cheap accs",

    # Money service wording
    "money service",
    "money services",
    "money serv",
    "money boost",
    "money boosts",
    "money boosting",
    "cash service",
    "cash services",
    "cash boost",
    "cash boosts",
    "cash boosting",
    "money drop",
    "money drops",
    "cash drop",
    "cash drops",
    "gta money service",
    "gta money services",
    "gta cash service",
    "gta cash services",
    "bank boost",
    "bank boosts",

    # Account/rank/XP boost services
    "account boost",
    "account boosting",
    "rank boost",
    "rank boosts",
    "rp boost",
    "rp boosts",
    "level boost",
    "level boosts",
    "xp boost",
    "xp boosts",

    # Unlocks / recoveries
    "unlock all",
    "unlock-all",
    "unlock service",
    "unlock services",
    "unlocks service",
    "unlocks services",
    "recovery service",
    "recovery services",
    "account recovery",
    "account recoveries",
    "gta recovery",
    "gta recoveries",
    "boosting service",
    "boosting services",
    "mod menu service",
    "mod menu services",
]

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

recent_messages = defaultdict(list)
bot.synced = False

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

        if phrase_normal in normal:
            return f"Banned phrase: {phrase}"

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
async def send_wall_log(member, offence, punishment, message_content, warning_count, moderator=None):
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

    if moderator is not None:
        embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if message_content:
        safe_message = message_content[:900]
        embed.add_field(name="Message", value=f"```{safe_message}```", inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(embed=embed)


# ---------------- PUNISHMENT ----------------
async def punish_if_needed(guild, channel, member, offence, warning_count):
    if warning_count < MAX_WARNINGS:
        return False

    if member.guild_permissions.administrator:
        await channel.send(f"❌ {member.mention} reached max warnings, but I cannot punish an admin.")
        return True

    bot_member = guild.me or guild.get_member(bot.user.id)

    if bot_member.top_role <= member.top_role:
        await channel.send(
            f"❌ {member.mention} reached max warnings, but my role is not high enough to punish them."
        )
        return True

    if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban":
        try:
            await member.send(
                f"🔨 You were banned from *{guild.name}*.\n"
                f"Reason: **{offence}**\n"
                f"You reached *{MAX_WARNINGS} warnings*."
            )
        except Exception:
            pass

        await member.ban(
            reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}",
            delete_message_days=0
        )

        clear_warnings(member.id)
        return True

    try:
        await member.send(
            f"🔨 You were kicked from *{guild.name}*.\n"
            f"Reason: **{offence}**\n"
            f"You reached *{MAX_WARNINGS} warnings*."
        )
    except Exception:
        pass

    await member.kick(
        reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}"
    )

    clear_warnings(member.id)
    return True


# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"🔨 Knob Bot logged in as {bot.user}")
    print("----------------------------")

    # Sync slash commands quickly to every server the bot is in
    if not bot.synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"✅ Slash commands synced in {guild.name}")
            except Exception as e:
                print(f"❌ Slash sync failed in {guild.name}: {e}")

        bot.synced = True


# ---------------- AUTO MODERATION ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    member = message.author

    # Staff/admins are immune from auto moderation
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

        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send(
                "❌ I need *Manage Messages* permission to delete rule-breaking messages."
            )
        except Exception:
            pass

        if warning_count >= MAX_WARNINGS:
            punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

            await send_wall_log(
                member=member,
                offence=offence,
                punishment=punishment,
                message_content=content,
                warning_count=warning_count
            )

            try:
                await punish_if_needed(message.guild, message.channel, member, offence, warning_count)
            except discord.Forbidden:
                await message.channel.send(
                    f"❌ I tried to punish {member.mention}, but I do not have permission."
                )
            except Exception as e:
                print(e)
                await message.channel.send(
                    f"❌ I tried to punish {member.mention}, but something went wrong."
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


# ---------------- PREFIX COMMANDS ----------------
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def prefix_warn(ctx, member: discord.Member, *, reason):
    warning_count = add_warning(member.id)

    await send_wall_log(
        member=member,
        offence=reason,
        punishment="Manual warning",
        message_content="Manual staff warning",
        warning_count=warning_count,
        moderator=ctx.author
    )

    await ctx.send(
        f"⚠️ {member.mention} has been warned by {ctx.author.mention}.\n"
        f"Reason: **{reason}**\n"
        f"Warnings: *{warning_count}/{MAX_WARNINGS}*"
    )

    if warning_count >= MAX_WARNINGS:
        punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

        await send_wall_log(
            member=member,
            offence=reason,
            punishment=punishment,
            message_content="Reached max warnings from manual warning",
            warning_count=warning_count,
            moderator=ctx.author
        )

        try:
            await punish_if_needed(ctx.guild, ctx.channel, member, reason, warning_count)
        except Exception as e:
            print(e)
            await ctx.send("❌ I tried to punish them, but something went wrong.")


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
            f"Punishment: **{PUNISHMENT_ON_MAX_WARNINGS.title()} after {MAX_WARNINGS} warnings**\n"
            "Bad messages are automatically deleted.\n"
            "Sales, car trading, and Discord links are allowed.\n\n"
            "**Banned phrases:**\n"
            f"{banned_list[:3500]}"
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
        warning_count=warning_count,
        moderator=ctx.author
    )

    await ctx.send(f"🧱 Added {member.mention} to the Wall of Knobs.")


# ---------------- SLASH COMMANDS ----------------
@bot.tree.command(name="warn", description="Manually warn a member")
@app_commands.describe(
    member="The member to warn",
    reason="The reason for the warning"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return

    warning_count = add_warning(member.id)

    await send_wall_log(
        member=member,
        offence=reason,
        punishment="Manual warning",
        message_content="Manual slash warning",
        warning_count=warning_count,
        moderator=interaction.user
    )

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned by {interaction.user.mention}.\n"
        f"Reason: **{reason}**\n"
        f"Warnings: *{warning_count}/{MAX_WARNINGS}*"
    )

    if warning_count >= MAX_WARNINGS:
        punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

        await send_wall_log(
            member=member,
            offence=reason,
            punishment=punishment,
            message_content="Reached max warnings from slash warning",
            warning_count=warning_count,
            moderator=interaction.user
        )

        try:
            await punish_if_needed(interaction.guild, interaction.channel, member, reason, warning_count)
        except Exception as e:
            print(e)
            await interaction.followup.send("❌ I tried to punish them, but something went wrong.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need *Manage Messages* permission to use this command.",
            ephemeral=True
        )
        return

    print(error)

    if interaction.response.is_done():
        await interaction.followup.send("❌ Something went wrong. Check Railway logs.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Something went wrong. Check Railway logs.", ephemeral=True)


# ---------------- PREFIX ERROR HANDLER ----------------
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
            "`?warn @user reason`\n"
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
