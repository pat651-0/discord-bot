from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands


# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("merged_discord_bot")


# ---------------- TOKEN ----------------
# Railway variable name. Do NOT paste the token directly into this file.
TOKEN_NAME = "TOKEN"


# ---------------- IDS ----------------
STAFF_ROLE_IDS = [
    1470379426297548957,
]

TICKET_CATEGORY_IDS = [
    1472860643475329096,  # your server ticket category
    1507876447467995226,  # friend's server ticket category
]

TICKET_OWNER_NAMES_BY_CATEGORY = {
    1472860643475329096: "Filiy V",  # your server
    1507876447467995226: "Mruss",    # friend's server
}

DEFAULT_TICKET_OWNER_NAME = "Filiy V"

LEAVES_CHANNEL_ID = 1475079442291363901
WALL_CHANNEL_ID = 1509103133479932085

# Your Discord ID. Your replies trigger the ticket-owner DM for !tickets only.
OWNER_USER_IDS = [
    1137385938155221073,
]


# ---------------- FILES ----------------
YAPPER_SETTINGS_FILE = "yapper_settings.json"
WARNINGS_FILE = "knob_warnings.json"
TICKET_OWNERS_FILE = "ticket_owners.json"


# ---------------- GIVEAWAY SETTINGS ----------------
GIVEAWAY_TIME = 24 * 60 * 60
TEST_GIVEAWAY_TIME = 30


# ---------------- TICKET AUTO MESSAGE SETTINGS ----------------
UK_TIMEZONE = ZoneInfo("Europe/London")
AVAILABLE_START_HOUR = 9
AVAILABLE_END_HOUR = 22

TICKET_DM_COOLDOWN = 60 * 60
AWAY_AUTO_REPLY_COOLDOWN = 60 * 60
AWAY_AUTO_REPLY_DELETE_AFTER = 5 * 60


# ---------------- MODERATION SETTINGS ----------------
MAX_WARNINGS = 3
SPAM_LIMIT = 5
SPAM_SECONDS = 10

# Use "kick" or "ban".
PUNISHMENT_ON_MAX_WARNINGS = "kick"

BANNED_PHRASES = [
    "@everyone",
    "@here",

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
intents.reactions = True

bot = commands.Bot(command_prefix=["!", "?"], intents=intents)
bot.synced = False
bot.views_added = False

# Spam cache: guild:channel:user -> deque[(timestamp, normalized_content)]
recent_messages: defaultdict[str, deque[tuple[float, str]]] = defaultdict(deque)


# ---------------- JSON HELPERS ----------------
def load_json(file_name: str, default: Any) -> Any:
    path = Path(file_name)
    if not path.exists():
        return default.copy() if isinstance(default, dict) else default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        log.warning("JSON file is corrupted, using default: %s", file_name)
        return default.copy() if isinstance(default, dict) else default
    except OSError as exc:
        log.warning("Could not read %s: %s", file_name, exc)
        return default.copy() if isinstance(default, dict) else default


def save_json(file_name: str, data: Any) -> None:
    path = Path(file_name)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        temp_path.replace(path)
    except OSError as exc:
        log.exception("Could not save %s: %s", file_name, exc)


yapper_settings: dict[str, Any] = load_json(YAPPER_SETTINGS_FILE, {})
warnings_store: dict[str, Any] = load_json(WARNINGS_FILE, {})
ticket_owners: dict[str, Any] = load_json(TICKET_OWNERS_FILE, {})


def save_yapper_settings() -> None:
    save_json(YAPPER_SETTINGS_FILE, yapper_settings)


def save_warnings() -> None:
    save_json(WARNINGS_FILE, warnings_store)


def save_ticket_owners() -> None:
    save_json(TICKET_OWNERS_FILE, ticket_owners)


# ---------------- GENERAL HELPERS ----------------
def has_staff_role(member: discord.Member) -> bool:
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)


def is_staff_or_mod(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
        or has_staff_role(member)
    )


async def get_sendable_channel(channel_id: int) -> discord.abc.Messageable | None:
    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.HTTPException:
            return None

    if hasattr(channel, "send"):
        return channel  # type: ignore[return-value]

    return None


# ---------------- TICKET HELPERS ----------------
def get_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    guild_id = str(guild.id)
    saved_data = yapper_settings.get(guild_id)

    if saved_data:
        try:
            if isinstance(saved_data, dict):
                saved_category_id = int(saved_data.get("ticket_category_id"))
            else:
                # Backwards compatibility with your old JSON format.
                saved_category_id = int(saved_data)

            category = guild.get_channel(saved_category_id)
            if isinstance(category, discord.CategoryChannel):
                return category
        except (TypeError, ValueError):
            pass

    for category_id in TICKET_CATEGORY_IDS:
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            return category

    return None


def clean_channel_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")[:40] or "user"


def is_fily_offline_hours() -> bool:
    now_uk = datetime.now(UK_TIMEZONE)
    return now_uk.hour < AVAILABLE_START_HOUR or now_uk.hour >= AVAILABLE_END_HOUR


def get_ticket_owner_display_name(channel: discord.abc.GuildChannel) -> str:
    channel_id = str(channel.id)
    data = ticket_owners.get(channel_id)

    if isinstance(data, dict):
        saved_name = data.get("owner_display_name")
        if saved_name:
            return str(saved_name)

    if getattr(channel, "category", None) is not None:
        return TICKET_OWNER_NAMES_BY_CATEGORY.get(
            channel.category.id,  # type: ignore[union-attr]
            DEFAULT_TICKET_OWNER_NAME,
        )

    return DEFAULT_TICKET_OWNER_NAME


def ticket_auto_messages_enabled(channel: discord.abc.GuildChannel) -> bool:
    data = ticket_owners.get(str(channel.id))
    if not isinstance(data, dict):
        return False
    return bool(data.get("auto_messages", False))


def find_existing_ticket(guild: discord.Guild, user_id: int) -> discord.TextChannel | None:
    stale_channel_ids: list[str] = []

    for channel_id, data in ticket_owners.items():
        if not isinstance(data, dict):
            continue

        if int(data.get("owner_id", 0)) != user_id:
            continue

        try:
            channel = guild.get_channel(int(channel_id))
        except ValueError:
            continue

        if isinstance(channel, discord.TextChannel):
            return channel

        stale_channel_ids.append(channel_id)

    for channel_id in stale_channel_ids:
        ticket_owners.pop(channel_id, None)

    if stale_channel_ids:
        save_ticket_owners()

    return None


async def create_ticket_channel(interaction: discord.Interaction, auto_messages: bool) -> None:
    guild = interaction.guild
    user = interaction.user

    if guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    existing_ticket = find_existing_ticket(guild, user.id)
    if existing_ticket is not None:
        await interaction.followup.send(f"❌ You already have a ticket: {existing_ticket.mention}")
        return

    category = get_ticket_category(guild)
    if category is None:
        await interaction.followup.send("❌ Ticket category not found. Admin can use `!setcategory CATEGORY_ID`.")
        return

    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)

    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }

    if isinstance(user, discord.Member):
        overwrites[user] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        )

    if bot_member is not None:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
        )

    for role_id in STAFF_ROLE_IDS:
        role = guild.get_role(role_id)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            )

    channel_name = f"ticket-{clean_channel_name(user.name)}-{str(user.id)[-4:]}"

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {user} ({user.id})",
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ I do not have permission to create ticket channels.")
        return
    except discord.HTTPException as exc:
        log.exception("Failed to create ticket channel: %s", exc)
        await interaction.followup.send("❌ Discord rejected the ticket channel creation. Check my permissions and category limits.")
        return

    owner_display_name = TICKET_OWNER_NAMES_BY_CATEGORY.get(category.id, DEFAULT_TICKET_OWNER_NAME)

    ticket_owners[str(channel.id)] = {
        "guild_id": guild.id,
        "owner_id": user.id,
        "last_dm_time": 0,
        "last_away_reply_time": 0,
        "auto_messages": auto_messages,
        "owner_display_name": owner_display_name,
        "created_at": int(time.time()),
    }
    save_ticket_owners()

    if auto_messages:
        ticket_embed = discord.Embed(
            title="🎟️ Ticket Opened",
            description=(
                "Please explain what you need help with.\n\n"
                "Availability Times: 9am to 10pm UK"
            ),
            color=discord.Color.green(),
        )
    else:
        ticket_embed = discord.Embed(
            title="🎫 Ticket Opened",
            description="Please explain what you need help with.",
            color=discord.Color.green(),
        )

    await channel.send(content=user.mention, embed=ticket_embed, view=CloseButton())

    try:
        await user.send(
            f"🎫 Your ticket has been created in {guild.name}.\n"
            f"Ticket: {channel.mention}"
        )
    except discord.HTTPException:
        pass

    await interaction.followup.send(f"✅ Created {channel.mention}")


# ---------------- WARNING HELPERS ----------------
def _warning_bucket(guild_id: int) -> dict[str, int]:
    gid = str(guild_id)
    bucket = warnings_store.get(gid)

    if not isinstance(bucket, dict):
        bucket = {}
        warnings_store[gid] = bucket

    return bucket


def get_warnings(guild_id: int, user_id: int) -> int:
    uid = str(user_id)
    bucket = _warning_bucket(guild_id)

    if uid in bucket:
        return int(bucket.get(uid, 0))

    # Backwards compatibility with your old flat JSON format: {"user_id": warning_count}.
    legacy_count = warnings_store.get(uid)
    if isinstance(legacy_count, int):
        return legacy_count

    return 0


def add_warning(guild_id: int, user_id: int) -> int:
    bucket = _warning_bucket(guild_id)
    uid = str(user_id)

    # Migrate old flat warning data into this guild the first time that user is warned again.
    if uid not in bucket and isinstance(warnings_store.get(uid), int):
        bucket[uid] = int(warnings_store.pop(uid))

    bucket[uid] = int(bucket.get(uid, 0)) + 1
    save_warnings()
    return bucket[uid]


def clear_warnings(guild_id: int, user_id: int) -> None:
    bucket = _warning_bucket(guild_id)
    uid = str(user_id)
    changed = False

    if uid in bucket:
        del bucket[uid]
        changed = True

    if uid in warnings_store:
        warnings_store.pop(uid, None)
        changed = True

    if changed:
        save_warnings()


# ---------------- SMART DETECTION ----------------
def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("@\u200b", "@")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_text(text: str) -> str:
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
        "@": "a",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"[^a-z0-9]", "", text)


def detect_offence(message_content: str) -> str | None:
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


def is_spam(guild_id: int, channel_id: int, user_id: int, content: str) -> bool:
    now = time.time()
    clean_content = normalize_text(content)

    # Ignore blank/attachment-only messages.
    if not clean_content:
        return False

    key = f"{guild_id}:{channel_id}:{user_id}"
    entries = recent_messages[key]
    entries.append((now, clean_content))

    while entries and now - entries[0][0] > SPAM_SECONDS:
        entries.popleft()

    same_messages = sum(1 for _, old_content in entries if old_content == clean_content)
    return same_messages >= SPAM_LIMIT


# ---------------- WALL LOG ----------------
async def send_wall_log(
    member: discord.Member,
    offence: str,
    punishment: str,
    message_content: str,
    warning_count: int,
    moderator: discord.Member | discord.User | None = None,
) -> None:
    channel = await get_sendable_channel(WALL_CHANNEL_ID)

    if channel is None:
        log.warning("Wall of Knobs channel not found or not sendable: %s", WALL_CHANNEL_ID)
        return

    embed = discord.Embed(
        title="🧱 Wall of Knobs 🧱",
        description="Another rule breaker has been added to the wall.",
        color=discord.Color.red(),
    )

    embed.add_field(name="Their @", value=member.mention, inline=False)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.add_field(name="Offence", value=offence[:1024], inline=False)
    embed.add_field(name="Warnings", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
    embed.add_field(name="Punishment", value=punishment, inline=True)

    if moderator is not None:
        embed.add_field(name="Moderator", value=moderator.mention, inline=False)

    if message_content:
        safe_message = discord.utils.escape_markdown(message_content[:900])
        embed.add_field(name="Message", value=safe_message or "*No text content*", inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)


async def punish_if_needed(
    guild: discord.Guild,
    channel: discord.abc.Messageable,
    member: discord.Member,
    offence: str,
    warning_count: int,
) -> bool:
    if warning_count < MAX_WARNINGS:
        return False

    if member == guild.owner:
        await channel.send(f"❌ {member.mention} reached max warnings, but I cannot punish the server owner.")
        return True

    if member.guild_permissions.administrator:
        await channel.send(f"❌ {member.mention} reached max warnings, but I cannot punish an admin.")
        return True

    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)

    if bot_member is None:
        await channel.send("❌ I could not check my role hierarchy.")
        return True

    if bot_member.top_role <= member.top_role:
        await channel.send(f"❌ {member.mention} reached max warnings, but my role is not high enough.")
        return True

    punishment = PUNISHMENT_ON_MAX_WARNINGS.lower().strip()

    if punishment == "ban":
        if not bot_member.guild_permissions.ban_members:
            await channel.send("❌ I need the Ban Members permission.")
            return True

        try:
            await member.send(
                f"🔨 You were banned from {guild.name}.\n"
                f"Reason: {offence}\n"
                f"You reached {MAX_WARNINGS} warnings."
            )
        except discord.HTTPException:
            pass

        await member.ban(reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}")
        clear_warnings(guild.id, member.id)
        return True

    if not bot_member.guild_permissions.kick_members:
        await channel.send("❌ I need the Kick Members permission.")
        return True

    try:
        await member.send(
            f"🔨 You were kicked from {guild.name}.\n"
            f"Reason: {offence}\n"
            f"You reached {MAX_WARNINGS} warnings."
        )
    except discord.HTTPException:
        pass

    await member.kick(reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}")
    clear_warnings(guild.id, member.id)
    return True


# ---------------- TICKET BUTTONS ----------------
class CloseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="merged_close_ticket",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This button only works inside ticket channels.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
            return

        channel_id = str(interaction.channel.id)
        data = ticket_owners.get(channel_id)

        if not isinstance(data, dict):
            await interaction.response.send_message("❌ This does not look like a tracked ticket channel.", ephemeral=True)
            return

        owner_id = int(data.get("owner_id", 0))
        allowed = (
            interaction.user.id == owner_id
            or interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.administrator
            or has_staff_role(interaction.user)
        )

        if not allowed:
            await interaction.response.send_message("❌ Only the ticket owner or staff can close this ticket.", ephemeral=True)
            return

        ticket_owners.pop(channel_id, None)
        save_ticket_owners()

        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await asyncio.sleep(2)

        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user} ({interaction.user.id})")
        except discord.HTTPException as exc:
            log.warning("Failed to delete ticket channel %s: %s", interaction.channel.id, exc)


class TicketsButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎟️ Open Ticket",
        style=discord.ButtonStyle.green,
        custom_id="tickets_system_create_ticket",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await create_ticket_channel(interaction, auto_messages=True)


class Tickets2Button(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="tickets2_normal_create_ticket",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await create_ticket_channel(interaction, auto_messages=False)


# ---------------- READY ----------------
@bot.event
async def on_ready() -> None:
    if not bot.views_added:
        bot.add_view(TicketsButton())
        bot.add_view(Tickets2Button())
        bot.add_view(CloseButton())
        bot.views_added = True

    log.info("----------------------------")
    log.info("✅ Merged Bot logged in as %s", bot.user)
    log.info("----------------------------")

    if not bot.synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                log.info("✅ Slash commands synced in %s", guild.name)
            except discord.HTTPException as exc:
                log.exception("❌ Slash sync failed in %s: %s", guild.name, exc)

        bot.synced = True


# ---------------- BOARD OF GUILT ----------------
@bot.event
async def on_member_remove(member: discord.Member) -> None:
    channel = await get_sendable_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        log.warning("Leaves channel not found or not sendable: %s", LEAVES_CHANNEL_ID)
        return

    embed = discord.Embed(
        title="⚖️ Board of Guilt",
        description=(
            f"💀 {member.name} left the server...\n\n"
            "Their name shall stay here forever."
        ),
        color=discord.Color.red(),
    )

    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(content=f"bye I guess... <@{member.id}>", embed=embed)


# ---------------- TICKET AUTO MESSAGES ----------------
async def delete_message_later(message: discord.Message, seconds: int) -> None:
    await asyncio.sleep(seconds)

    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def maybe_dm_ticket_owner(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel):
        return

    channel_id = str(message.channel.id)
    data = ticket_owners.get(channel_id)

    if not isinstance(data, dict):
        return

    if not ticket_auto_messages_enabled(message.channel):
        return

    owner_id = int(data.get("owner_id", 0))

    # Do not DM the owner if they are the one replying.
    if owner_id == message.author.id:
        return

    # Only your replies trigger the DM.
    if message.author.id not in OWNER_USER_IDS:
        return

    now = time.time()
    last_dm_time = float(data.get("last_dm_time", 0))

    # Only DM once per hour per ticket.
    if now - last_dm_time < TICKET_DM_COOLDOWN:
        return

    owner = message.guild.get_member(owner_id) if message.guild else None

    if owner is None and message.guild is not None:
        try:
            owner = await message.guild.fetch_member(owner_id)
        except discord.HTTPException:
            return

    if owner is None:
        return

    try:
        await owner.send(
            "📩 Ticket Update\n\n"
            f"{message.author.display_name} has replied to your ticket in {message.guild.name}.\n\n"
            f"Ticket: {message.channel.mention}\n\n"
            "Please check it when you can."
        )

        data["last_dm_time"] = now
        ticket_owners[channel_id] = data
        save_ticket_owners()
    except discord.HTTPException:
        pass


async def maybe_send_away_auto_reply(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel):
        return

    channel_id = str(message.channel.id)
    data = ticket_owners.get(channel_id)

    if not isinstance(data, dict):
        return

    if not ticket_auto_messages_enabled(message.channel):
        return

    owner_id = int(data.get("owner_id", 0))

    # Only auto-reply when the ticket owner sends a message.
    if message.author.id != owner_id:
        return

    # Only outside 9am to 10pm UK.
    if not is_fily_offline_hours():
        return

    now = time.time()
    last_away_reply_time = float(data.get("last_away_reply_time", 0))

    # Cooldown, not an automatic timer.
    if now - last_away_reply_time < AWAY_AUTO_REPLY_COOLDOWN:
        return

    owner_display_name = get_ticket_owner_display_name(message.channel)

    away_msg = await message.channel.send(
        f"{message.author.mention}\n"
        f"⏰ {owner_display_name} is currently offline.\n\n"
        "Available hours are 9:00 AM - 10:00 PM UK time.\n"
        f"{owner_display_name} will reply when they’re back online.",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )

    data["last_away_reply_time"] = now
    ticket_owners[channel_id] = data
    save_ticket_owners()

    asyncio.create_task(delete_message_later(away_msg, AWAY_AUTO_REPLY_DELETE_AFTER))


# ---------------- AUTO MODERATION ----------------
@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    if message.guild is None or not isinstance(message.author, discord.Member):
        return

    await maybe_dm_ticket_owner(message)
    await maybe_send_away_auto_reply(message)

    member = message.author

    if is_staff_or_mod(member):
        await bot.process_commands(message)
        return

    content = message.content or ""
    offence = detect_offence(content)

    if offence is None and is_spam(message.guild.id, message.channel.id, member.id, content):
        offence = "Spam / repeated messages"

    if offence is not None:
        warning_count = add_warning(message.guild.id, member.id)

        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send("❌ I need Manage Messages permission.")
        except discord.HTTPException:
            pass

        if warning_count >= MAX_WARNINGS:
            punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

            await send_wall_log(
                member=member,
                offence=offence,
                punishment=punishment,
                message_content=content,
                warning_count=warning_count,
            )

            try:
                await punish_if_needed(message.guild, message.channel, member, offence, warning_count)
            except discord.Forbidden:
                await message.channel.send(f"❌ I do not have permission to punish {member.mention}.")
            except discord.HTTPException as exc:
                log.exception("Punishment failed: %s", exc)
                await message.channel.send("❌ Something went wrong while punishing.")

            return

        await send_wall_log(
            member=member,
            offence=offence,
            punishment="Warning",
            message_content=content,
            warning_count=warning_count,
        )

        await message.channel.send(
            f"⚠️ {member.mention}, warning {warning_count}/{MAX_WARNINGS} — {offence}.\n"
            "Your message was deleted."
        )
        return

    await bot.process_commands(message)


# ---------------- TICKET COMMANDS ----------------
@bot.command(name="tickets", aliases=["ticket"])
@commands.has_permissions(administrator=True)
async def tickets(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title="🎟️ Open a Ticket to Trade",
        description=(
            "Click the button below to open a ticket.\n\n"
            "Availability Times: 9am to 10pm UK"
        ),
        color=discord.Color.green(),
    )

    await ctx.send(embed=embed, view=TicketsButton())


@bot.command(name="tickets2")
@commands.has_permissions(administrator=True)
async def tickets2(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title="🎫 Open a Ticket",
        description="Click the button below to create a ticket.",
        color=discord.Color.green(),
    )

    await ctx.send(embed=embed, view=Tickets2Button())


@bot.command(name="setcategory")
@commands.has_permissions(administrator=True)
async def setcategory(ctx: commands.Context, category_id: int | None = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    if category_id is None:
        if ctx.channel.category is None:  # type: ignore[attr-defined]
            await ctx.send("❌ This channel is not inside a category. Use `!setcategory CATEGORY_ID`.")
            return

        category = ctx.channel.category  # type: ignore[attr-defined]
    else:
        category = ctx.guild.get_channel(category_id)

    if not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ That ID is not a valid category in this server.")
        return

    yapper_settings[str(ctx.guild.id)] = {"ticket_category_id": category.id}
    save_yapper_settings()

    await ctx.send(f"✅ Ticket category set to {category.name}.")


@bot.command(name="checkcategory")
@commands.has_permissions(administrator=True)
async def checkcategory(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    category = get_ticket_category(ctx.guild)

    if category is None:
        await ctx.send("❌ No ticket category found.")
    else:
        await ctx.send(f"✅ Current ticket category: {category.name}")


# ---------------- SALLY COMMANDS ----------------
@bot.command(name="sallyspeak")
@commands.has_permissions(manage_messages=True)
async def sallyspeak(ctx: commands.Context, *, message: str) -> None:
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(message)


@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_command(ctx: commands.Context, title: str, *, description: str) -> None:
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.purple(),
    )

    await ctx.send(embed=embed)


@bot.command(name="rules")
async def rules(ctx: commands.Context) -> None:
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    embed = discord.Embed(
        title="📜 Server Rules 📜",
        description=(
            "1. No BS.\n"
            "2. No NSFW.\n"
            "3. English only.\n"
            "4. No scams.\n"
            "5. Respect staff.\n"
            "6. Use tickets for trades.\n"
            "7. No modded accounts.\n"
            "8. No money services or boosts.\n"
        ),
        color=discord.Color.red(),
    )

    await ctx.send(embed=embed)


@bot.command(name="slotinfo")
async def slotinfo(ctx: commands.Context) -> None:
    await ctx.send("❌ Sloty has been removed from this bot.")


# ---------------- GIVEAWAY COMMANDS ----------------
def make_prize(amount: int, prize_type: str) -> str | None:
    prize_type = prize_type.lower().strip()

    if prize_type == "normal":
        prize = f"🚘 {amount} Normal Car"
        if amount != 1:
            prize += "s"
        return prize

    if prize_type == "hard trade":
        prize = f"✨ {amount} Hard Trade"
        if amount != 1:
            prize += "s"
        return prize

    if prize_type == "very hard trade":
        prize = f"💎 {amount} Very Hard Trade"
        if amount != 1:
            prize += "s"
        return prize

    return None


async def finish_giveaway(ctx: commands.Context, message_id: int, prize: str, seconds: int, test: bool = False) -> None:
    await asyncio.sleep(seconds)

    try:
        message = await ctx.channel.fetch_message(message_id)  # type: ignore[attr-defined]
    except discord.HTTPException:
        await ctx.send("❌ Giveaway message was deleted or could not be found.")
        return

    entries: list[discord.User | discord.Member] = []

    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    entries.append(user)

    if len(entries) == 0:
        await ctx.send(f"❌ No one entered the {prize} giveaway.")
        return

    winner = random.choice(entries)

    end_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=(
            f"Prize: {prize}\n\n"
            f"Winner: {winner.mention}"
        ),
        color=discord.Color.green(),
    )

    await ctx.send(embed=end_embed)
    await ctx.send(f"🎉 Congratulations {winner.mention}! You won {prize}!")


async def start_giveaway(ctx: commands.Context, prize: str, seconds: int, test: bool = False) -> None:
    title = "🎉 TEST GIVEAWAY 🎉" if test else "🎉 GIVEAWAY 🎉"
    time_text = "30 seconds" if test else "24 hours"

    embed = discord.Embed(
        title=title,
        description=(
            f"Prize: {prize}\n\n"
            "React with 🎉 to enter!\n\n"
            f"⏰ Ends in {time_text}"
        ),
        color=discord.Color.gold(),
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    # This keeps the command responsive. Note: giveaways still do not survive a bot restart.
    asyncio.create_task(finish_giveaway(ctx, message.id, prize, seconds, test=test))


@bot.command(name="giveaway")
@commands.has_permissions(administrator=True)
async def giveaway(ctx: commands.Context, amount: int, *, prize_type: str) -> None:
    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize = make_prize(amount, prize_type)

    if prize is None:
        await ctx.send(
            "❌ Use:\n"
            "`!giveaway 4 Normal`\n"
            "`!giveaway 5 Hard Trade`\n"
            "`!giveaway 2 Very Hard Trade`"
        )
        return

    await start_giveaway(ctx, prize, GIVEAWAY_TIME)


@bot.command(name="testgiveaway")
@commands.has_permissions(administrator=True)
async def testgiveaway(ctx: commands.Context, amount: int, *, prize_type: str) -> None:
    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize = make_prize(amount, prize_type)

    if prize is None:
        await ctx.send("❌ Use: `!testgiveaway 1 Normal`")
        return

    await start_giveaway(ctx, prize, TEST_GIVEAWAY_TIME, test=True)


# ---------------- KNOB COMMANDS ----------------
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def prefix_warn(ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    warning_count = add_warning(ctx.guild.id, member.id)

    await send_wall_log(
        member=member,
        offence=reason,
        punishment="Manual warning",
        message_content="Manual staff warning",
        warning_count=warning_count,
        moderator=ctx.author,
    )

    await ctx.send(
        f"⚠️ {member.mention} has been warned by {ctx.author.mention}.\n"
        f"Reason: {reason}\n"
        f"Warnings: {warning_count}/{MAX_WARNINGS}"
    )

    if warning_count >= MAX_WARNINGS:
        punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

        await send_wall_log(
            member=member,
            offence=reason,
            punishment=punishment,
            message_content="Reached max warnings from manual warning",
            warning_count=warning_count,
            moderator=ctx.author,
        )

        await punish_if_needed(ctx.guild, ctx.channel, member, reason, warning_count)


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx: commands.Context, member: discord.Member | None = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    if member is None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("❌ I could not identify that member.")
            return
        member = ctx.author

    count = get_warnings(ctx.guild.id, member.id)
    await ctx.send(f"⚠️ {member.mention} has {count}/{MAX_WARNINGS} warnings.")


@bot.command(name="clearwarnings")
@commands.has_permissions(manage_messages=True)
async def clearwarnings(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    clear_warnings(ctx.guild.id, member.id)
    await ctx.send(f"✅ Cleared warnings for {member.mention}.")


@bot.command(name="knobstatus")
@commands.has_permissions(manage_messages=True)
async def knobstatus(ctx: commands.Context) -> None:
    banned_list = "\n".join(f"- {phrase}" for phrase in BANNED_PHRASES)

    embed = discord.Embed(
        title="🔨 Knob Bot Status",
        description=(
            "Knob moderation is active.\n\n"
            f"Punishment: {PUNISHMENT_ON_MAX_WARNINGS.title()} after {MAX_WARNINGS} warnings\n"
            "Bad messages are automatically deleted.\n"
            "Sales, car trading, and Discord links are allowed.\n\n"
            "Banned phrases:\n"
            f"{banned_list[:3500]}"
        ),
        color=discord.Color.red(),
    )

    await ctx.send(embed=embed)


@bot.command(name="manualwall")
@commands.has_permissions(manage_messages=True)
async def manualwall(ctx: commands.Context, member: discord.Member, *, offence: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    warning_count = add_warning(ctx.guild.id, member.id)

    await send_wall_log(
        member=member,
        offence=offence,
        punishment="Manual warning",
        message_content="Manual staff report",
        warning_count=warning_count,
        moderator=ctx.author,
    )

    await ctx.send(f"🧱 Added {member.mention} to the Wall of Knobs.")


@bot.command(name="testguilt")
@commands.has_permissions(administrator=True)
async def testguilt(ctx: commands.Context) -> None:
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")


# ---------------- SLASH WARN ----------------
@bot.tree.command(name="warn", description="Manually warn a member")
@app_commands.describe(
    member="The member to warn",
    reason="The reason for the warning",
)
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return

    warning_count = add_warning(interaction.guild.id, member.id)

    await send_wall_log(
        member=member,
        offence=reason,
        punishment="Manual warning",
        message_content="Manual slash warning",
        warning_count=warning_count,
        moderator=interaction.user,
    )

    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned by {interaction.user.mention}.\n"
        f"Reason: {reason}\n"
        f"Warnings: {warning_count}/{MAX_WARNINGS}"
    )

    if warning_count >= MAX_WARNINGS:
        punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"

        await send_wall_log(
            member=member,
            offence=reason,
            punishment=punishment,
            message_content="Reached max warnings from slash warning",
            warning_count=warning_count,
            moderator=interaction.user,
        )

        await punish_if_needed(interaction.guild, interaction.channel, member, reason, warning_count)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You need Manage Messages permission to use this command."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return

    log.exception("Slash command error: %s", error)

    if interaction.response.is_done():
        await interaction.followup.send("❌ Something went wrong. Check Railway logs.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Something went wrong. Check Railway logs.", ephemeral=True)


# ---------------- PREFIX ERROR HANDLER ----------------
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
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
            "❌ Missing info. Examples:\n"
            "`!tickets`\n"
            "`!tickets2`\n"
            "`!giveaway 4 Normal`\n"
            "`!sallyspeak message`\n"
            "`!warn @user reason`\n"
            "`!warnings @user`\n"
            "`!clearwarnings @user`"
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad command format. Check the number/user you typed.")
        return

    if isinstance(error, commands.CommandInvokeError):
        log.exception("Command failed: %s", error.original)
    else:
        log.exception("Command error: %s", error)

    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN BOT ----------------
def main() -> None:
    token = os.getenv(TOKEN_NAME)

    if token is None:
        log.error("❌ %s not found in Railway variables.", TOKEN_NAME)
        return

    bot.run(token)


if __name__ == "__main__":
    main()
