from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# XSI DISCORD BOT - FULL SINGLE FILE
# Start command stays the same:
# python xsi_bot_full_setup_requiredpermissions.py
# ============================================================

VERSION = "XSI full setup build 2026-06-16 / ticket-hidden-ui-dm-kick"
BUILD_TAG = "XSI-FORCE-45-TICKET-HIDDEN-UI-DM-KICK"

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("xsi_bot")


# ---------------- TOKEN ----------------
TOKEN_NAME = "TOKEN"


# ---------------- FILES ----------------
# If Railway Volume is enabled, Railway exposes RAILWAY_VOLUME_MOUNT_PATH.
# If not, files are stored next to this script.
DATA_DIR = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SERVER_SETTINGS_FILE = DATA_DIR / "xsi_server_settings.json"
WARNINGS_FILE = DATA_DIR / "xsi_warnings.json"
TICKET_OWNERS_FILE = DATA_DIR / "xsi_ticket_owners.json"
SMART_MESSAGES_FILE = DATA_DIR / "xsi_smart_messages.json"
GIVEAWAYS_FILE = DATA_DIR / "xsi_giveaways.json"


# ---------------- DEFAULTS ----------------
UK_TIMEZONE = ZoneInfo("Europe/London")
DEFAULT_TIMEZONE = "Europe/London"
DEFAULT_AVAILABLE_START = "9am"
DEFAULT_AVAILABLE_END = "10pm"
DEFAULT_WELCOME_MESSAGE = "Hey {user} Please Read The Rules"
DEFAULT_UNAVAILABLE_MESSAGE = "I am unavailable right now. I will reply when I am back."

MAX_WARNINGS = 3
SPAM_LIMIT = 5
SPAM_SECONDS = 10
PUNISHMENT_ON_MAX_WARNINGS = "kick"  # "kick" or "ban"
SMART_MESSAGE_COOLDOWN = 60
TICKET_DM_COOLDOWN = 60 * 60
AWAY_AUTO_REPLY_COOLDOWN = 60 * 60
AWAY_AUTO_REPLY_DELETE_AFTER = 5 * 60
GIVEAWAY_TIME = 24 * 60 * 60
TEST_GIVEAWAY_TIME = 30

# Optional: put your Discord user ID here if you want your ticket replies to DM ticket owners.
OWNER_USER_IDS = [1137385938155221073]

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

SETUP_COMPONENTS = {
    "tickets",
    "ticketpanel",
    "logs",
    "wall",
    "guilt",
    "leaves",
    "transcripts",
    "stafflogs",
    "info",
    "welcome",
    "rules",
    "giveaways",
}

SKIP_ALIASES = {
    "ticket": "tickets",
    "ticketcategory": "tickets",
    "panel": "ticketpanel",
    "ticket-panel": "ticketpanel",
    "open-a-ticket": "ticketpanel",
    "log": "logs",
    "wallofknobs": "wall",
    "wall-of-knobs": "wall",
    "boardofguilt": "guilt",
    "board-of-guilt": "guilt",
    "leave": "leaves",
    "left": "leaves",
    "transcript": "transcripts",
    "stafflog": "stafflogs",
    "staff-logs": "stafflogs",
    "staff_logs": "stafflogs",
    "giveaway": "giveaways",
}


# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True


# ---------------- JSON HELPERS ----------------
def _copy_default(default: Any) -> Any:
    if isinstance(default, dict):
        return default.copy()
    if isinstance(default, list):
        return default.copy()
    return default


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return _copy_default(default)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        log.warning("JSON file is corrupted, using default: %s", path)
        return _copy_default(default)
    except OSError as exc:
        log.warning("Could not read %s: %s", path, exc)
        return _copy_default(default)

    if isinstance(default, dict) and not isinstance(data, dict):
        log.warning("%s did not contain a JSON object, resetting to default.", path)
        return _copy_default(default)

    return data


def save_json(path: Path, data: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        temp_path.replace(path)
    except OSError as exc:
        log.exception("Could not save %s: %s", path, exc)


server_settings: dict[str, Any] = load_json(SERVER_SETTINGS_FILE, {})
warnings_store: dict[str, Any] = load_json(WARNINGS_FILE, {})
ticket_owners: dict[str, Any] = load_json(TICKET_OWNERS_FILE, {})
smart_messages: dict[str, Any] = load_json(SMART_MESSAGES_FILE, {})
active_giveaways: dict[str, Any] = load_json(GIVEAWAYS_FILE, {})

settings_lock = asyncio.Lock()
warnings_lock = asyncio.Lock()
tickets_lock = asyncio.Lock()
smart_lock = asyncio.Lock()
giveaway_lock = asyncio.Lock()


async def save_server_settings() -> None:
    save_json(SERVER_SETTINGS_FILE, server_settings)


async def save_warnings() -> None:
    save_json(WARNINGS_FILE, warnings_store)


async def save_ticket_owners() -> None:
    save_json(TICKET_OWNERS_FILE, ticket_owners)


async def save_smart_messages() -> None:
    save_json(SMART_MESSAGES_FILE, smart_messages)


async def save_giveaways() -> None:
    save_json(GIVEAWAYS_FILE, active_giveaways)


# ---------------- BOT CLASS ----------------
class XSIBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.add_view(TicketsButton())
        self.add_view(Tickets2Button())
        self.add_view(CloseButton())
        if not availability_refresher.is_running():
            availability_refresher.start()
        if not giveaway_checker.is_running():
            giveaway_checker.start()


bot = XSIBot(command_prefix=["!", "?"], intents=intents)

# Spam cache: guild:channel:user -> deque[(timestamp, normalized_content)]
recent_messages: defaultdict[str, deque[tuple[float, str]]] = defaultdict(deque)
smart_cooldowns: dict[str, float] = {}


# ============================================================
# CONFIG HELPERS
# ============================================================
def default_guild_config() -> dict[str, Any]:
    return {
        "staff_role_ids": [],
        "ticket_category_id": None,
        "ticket_panel_channel_id": None,
        "ticket_panel_message_id": None,
        "welcome_channel_id": None,
        "welcome_message": DEFAULT_WELCOME_MESSAGE,
        "wall_channel_id": None,
        "leaves_channel_id": None,
        "guilt_channel_id": None,
        "transcript_channel_id": None,
        "staff_log_channel_id": None,
        "rules_channel_id": None,
        "giveaways_channel_id": None,
        "availability": {
            "timezone": DEFAULT_TIMEZONE,
            "start": DEFAULT_AVAILABLE_START,
            "end": DEFAULT_AVAILABLE_END,
            "enabled": True,
        },
        "temporary_unavailable": None,
        "last_availability_status": None,
        "created_category_ids": [],
        "created_channel_ids": [],
    }


def ensure_guild_config(guild_id: int) -> dict[str, Any]:
    gid = str(guild_id)
    data = server_settings.get(gid)
    defaults = default_guild_config()

    if not isinstance(data, dict):
        server_settings[gid] = defaults
        return defaults

    changed = False
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
            changed = True

    if not isinstance(data.get("staff_role_ids"), list):
        data["staff_role_ids"] = []
        changed = True

    if not isinstance(data.get("created_category_ids"), list):
        data["created_category_ids"] = []
        changed = True

    if not isinstance(data.get("created_channel_ids"), list):
        data["created_channel_ids"] = []
        changed = True

    if not isinstance(data.get("availability"), dict):
        data["availability"] = defaults["availability"]
        changed = True

    if changed:
        server_settings[gid] = data

    return data


def guild_config(guild: discord.Guild | int) -> dict[str, Any]:
    guild_id = guild.id if isinstance(guild, discord.Guild) else guild
    return ensure_guild_config(guild_id)


def add_created_category(config: dict[str, Any], category_id: int) -> None:
    ids = config.setdefault("created_category_ids", [])
    if category_id not in ids:
        ids.append(category_id)


def add_created_channel(config: dict[str, Any], channel_id: int) -> None:
    ids = config.setdefault("created_channel_ids", [])
    if channel_id not in ids:
        ids.append(channel_id)


# ============================================================
# GENERAL HELPERS
# ============================================================
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


def clean_channel_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")[:40] or "user"


def has_staff_role(member: discord.Member) -> bool:
    config = guild_config(member.guild.id)
    staff_ids = {int(role_id) for role_id in config.get("staff_role_ids", [])}
    return any(role.id in staff_ids for role in member.roles)


def is_staff_or_mod(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
        or has_staff_role(member)
    )


async def get_text_channel(guild: discord.Guild, channel_id: int | None) -> discord.TextChannel | None:
    if not channel_id:
        return None

    channel = guild.get_channel(int(channel_id))
    if channel is None:
        try:
            fetched = await guild.fetch_channel(int(channel_id))
        except discord.HTTPException:
            return None
        channel = fetched

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


def format_mentions_safe(text: str, member: discord.Member | discord.User, guild: discord.Guild | None) -> str:
    display_name = getattr(member, "display_name", member.name)
    server_name = guild.name if guild is not None else "this server"
    return (
        text.replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{display_name}", display_name)
        .replace("{server}", server_name)
    )


async def send_staff_log(guild: discord.Guild, text: str) -> None:
    config = guild_config(guild.id)
    channel = await get_text_channel(guild, config.get("staff_log_channel_id"))
    if channel is None:
        return
    try:
        await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        pass


# ============================================================
# TIME / AVAILABILITY HELPERS
# ============================================================
def parse_time_to_minutes(value: str) -> int:
    raw = value.strip().lower().replace(".", "")
    raw = re.sub(r"\s+", "", raw)

    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", raw)
    if not match:
        raise ValueError("Use times like 9am, 10pm, 15:30, or 3:30pm.")

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3)

    if minute < 0 or minute > 59:
        raise ValueError("Minute must be between 00 and 59.")

    if suffix:
        if hour < 1 or hour > 12:
            raise ValueError("12-hour time must be between 1 and 12.")
        if suffix == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
    else:
        if hour < 0 or hour > 23:
            raise ValueError("24-hour time must be between 0 and 23.")

    return hour * 60 + minute


def format_minutes(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    hour = minutes // 60
    minute = minutes % 60
    suffix = "am" if hour < 12 else "pm"
    h12 = hour % 12 or 12
    if minute == 0:
        return f"{h12}{suffix}"
    return f"{h12}:{minute:02d}{suffix}"


def format_dt(dt: datetime) -> str:
    return dt.strftime("%-I:%M%p").lower().replace(":00", "")


def minutes_between(now_minutes: int, start_minutes: int, end_minutes: int) -> bool:
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= now_minutes < end_minutes
    return now_minutes >= start_minutes or now_minutes < end_minutes


def get_timezone(config: dict[str, Any]) -> ZoneInfo:
    availability = config.get("availability", {})
    tz_name = availability.get("timezone", DEFAULT_TIMEZONE) if isinstance(availability, dict) else DEFAULT_TIMEZONE
    try:
        return ZoneInfo(str(tz_name))
    except Exception:
        return UK_TIMEZONE


def make_unavailable_window(config: dict[str, Any], start_time: str, end_time: str) -> tuple[datetime, datetime]:
    tz = get_timezone(config)
    now = datetime.now(tz)
    start_minutes = parse_time_to_minutes(start_time)
    end_minutes = parse_time_to_minutes(end_time)

    start_dt = now.replace(hour=start_minutes // 60, minute=start_minutes % 60, second=0, microsecond=0)
    end_dt = now.replace(hour=end_minutes // 60, minute=end_minutes % 60, second=0, microsecond=0)

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    # If the full window is already over today, schedule it for tomorrow.
    if now > end_dt:
        start_dt += timedelta(days=1)
        end_dt += timedelta(days=1)

    return start_dt, end_dt


def get_availability_state(guild_id: int) -> dict[str, Any]:
    config = guild_config(guild_id)
    tz = get_timezone(config)
    now = datetime.now(tz)

    temp = config.get("temporary_unavailable")
    if isinstance(temp, dict):
        try:
            start_dt = datetime.fromisoformat(str(temp.get("start_iso")))
            end_dt = datetime.fromisoformat(str(temp.get("end_iso")))
        except Exception:
            start_dt = None
            end_dt = None

        if start_dt is not None and end_dt is not None:
            if start_dt <= now < end_dt:
                return {
                    "status": "temporary_unavailable",
                    "available": False,
                    "title": "Currently Unavailable",
                    "panel_line": f"Unavailable until {format_dt(end_dt)} UK",
                    "message": str(temp.get("message") or DEFAULT_UNAVAILABLE_MESSAGE),
                    "until": end_dt,
                }
            if now >= end_dt:
                # Mark expired; caller may save during refresher/commands.
                pass

    availability = config.get("availability", {})
    if not isinstance(availability, dict):
        availability = default_guild_config()["availability"]

    start_text = str(availability.get("start") or DEFAULT_AVAILABLE_START)
    end_text = str(availability.get("end") or DEFAULT_AVAILABLE_END)
    enabled = bool(availability.get("enabled", True))

    try:
        start_minutes = parse_time_to_minutes(start_text)
        end_minutes = parse_time_to_minutes(end_text)
    except ValueError:
        start_text = DEFAULT_AVAILABLE_START
        end_text = DEFAULT_AVAILABLE_END
        start_minutes = parse_time_to_minutes(start_text)
        end_minutes = parse_time_to_minutes(end_text)

    now_minutes = now.hour * 60 + now.minute
    currently_available = enabled and minutes_between(now_minutes, start_minutes, end_minutes)
    normal_line = f"Availability Times: {format_minutes(start_minutes)} to {format_minutes(end_minutes)} UK"

    if currently_available:
        return {
            "status": "available",
            "available": True,
            "title": "Available",
            "panel_line": normal_line,
            "message": "Staff are available right now.",
            "until": None,
        }

    return {
        "status": "outside_hours",
        "available": False,
        "title": "Currently Offline",
        "panel_line": normal_line,
        "message": f"I am currently offline. Available hours are {format_minutes(start_minutes)} to {format_minutes(end_minutes)} UK.",
        "until": None,
    }


async def cleanup_expired_unavailable(guild_id: int) -> bool:
    config = guild_config(guild_id)
    temp = config.get("temporary_unavailable")
    if not isinstance(temp, dict):
        return False

    tz = get_timezone(config)
    now = datetime.now(tz)
    try:
        end_dt = datetime.fromisoformat(str(temp.get("end_iso")))
    except Exception:
        config["temporary_unavailable"] = None
        return True

    if now >= end_dt:
        config["temporary_unavailable"] = None
        return True

    return False


# ============================================================
# WARNING / MODERATION HELPERS
# ============================================================
def _warning_bucket(guild_id: int) -> dict[str, int]:
    gid = str(guild_id)
    bucket = warnings_store.get(gid)
    if not isinstance(bucket, dict):
        bucket = {}
        warnings_store[gid] = bucket
    return bucket


def get_warnings(guild_id: int, user_id: int) -> int:
    bucket = _warning_bucket(guild_id)
    return int(bucket.get(str(user_id), 0))


async def add_warning(guild_id: int, user_id: int) -> int:
    async with warnings_lock:
        bucket = _warning_bucket(guild_id)
        uid = str(user_id)
        bucket[uid] = int(bucket.get(uid, 0)) + 1
        await save_warnings()
        return bucket[uid]


async def clear_warnings_for(guild_id: int, user_id: int) -> None:
    async with warnings_lock:
        bucket = _warning_bucket(guild_id)
        bucket.pop(str(user_id), None)
        await save_warnings()


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
    if not clean_content:
        return False

    key = f"{guild_id}:{channel_id}:{user_id}"
    entries = recent_messages[key]
    entries.append((now, clean_content))

    while entries and now - entries[0][0] > SPAM_SECONDS:
        entries.popleft()

    same_messages = sum(1 for _, old_content in entries if old_content == clean_content)
    return same_messages >= SPAM_LIMIT


async def send_wall_log(
    member: discord.Member,
    offence: str,
    punishment: str,
    message_content: str,
    warning_count: int,
    moderator: discord.Member | discord.User | None = None,
) -> None:
    config = guild_config(member.guild.id)
    channel = await get_text_channel(member.guild, config.get("wall_channel_id"))
    if channel is None:
        channel = await get_text_channel(member.guild, config.get("guilt_channel_id"))
    if channel is None:
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
        await clear_warnings_for(guild.id, member.id)
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
    await clear_warnings_for(guild.id, member.id)
    return True


async def kick_member_with_checks(
    guild: discord.Guild,
    actor: discord.Member | discord.User,
    member: discord.Member,
    reason: str,
) -> tuple[bool, str]:
    clean_reason = str(reason or "").strip() or "No reason provided"

    if member.id == actor.id:
        return False, "❌ You cannot kick yourself."

    if member == guild.owner:
        return False, "❌ I cannot kick the server owner."

    if member.guild_permissions.administrator:
        return False, "❌ I cannot kick an administrator."

    if bot.user is not None and member.id == bot.user.id:
        return False, "❌ I cannot kick myself."

    if isinstance(actor, discord.Member) and actor != guild.owner:
        if actor.top_role <= member.top_role:
            return False, "❌ You cannot kick someone with an equal or higher role than you."

    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    if bot_member is None:
        return False, "❌ I could not check my role hierarchy."

    if not bot_member.guild_permissions.kick_members:
        return False, "❌ I need the Kick Members permission."

    if bot_member.top_role <= member.top_role:
        return False, "❌ My role is not high enough to kick that member. Move my role above theirs."

    try:
        await member.send(
            f"🔨 You were kicked from {guild.name}.\n"
            f"Reason: {clean_reason}"
        )
    except discord.HTTPException:
        pass

    audit_reason = f"Kicked by {actor} ({actor.id}). Reason: {clean_reason}"[:512]

    try:
        await member.kick(reason=audit_reason)
    except discord.Forbidden:
        return False, "❌ I do not have permission to kick that member."
    except discord.HTTPException:
        return False, "❌ Discord rejected the kick action."

    await send_staff_log(
        guild,
        f"🔨 {actor.mention} kicked {member.mention} (`{member.id}`). Reason: {clean_reason[:500]}",
    )
    return True, f"✅ Kicked {member.mention}. Reason: {clean_reason}"


# ============================================================
# TICKET HELPERS
# ============================================================
def get_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    config = guild_config(guild.id)
    category_id = config.get("ticket_category_id")
    if category_id:
        category = guild.get_channel(int(category_id))
        if isinstance(category, discord.CategoryChannel):
            return category

    category = discord.utils.get(guild.categories, name="XSI Tickets")
    return category


def find_existing_ticket(guild: discord.Guild, user_id: int) -> discord.TextChannel | None:
    stale_channel_ids: list[str] = []
    for channel_id, data in ticket_owners.items():
        if not isinstance(data, dict):
            continue
        if int(data.get("owner_id", 0)) != user_id:
            continue
        if int(data.get("guild_id", 0)) != guild.id:
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
        save_json(TICKET_OWNERS_FILE, ticket_owners)
    return None


def staff_role_objects(guild: discord.Guild) -> list[discord.Role]:
    config = guild_config(guild.id)
    role_ids = config.get("staff_role_ids", [])
    roles: list[discord.Role] = []
    for role_id in role_ids:
        role = guild.get_role(int(role_id))
        if role is not None:
            roles.append(role)
    return roles


def ticket_panel_embed(guild_id: int, normal: bool = True) -> discord.Embed:
    state = get_availability_state(guild_id)
    color = discord.Color.green() if state["available"] else discord.Color.orange()

    if normal:
        title = "🎟️ Open a Ticket"
        description = "Click the button below to open a ticket.\n\n" + state["panel_line"]
    else:
        title = "🎫 Open a Ticket"
        description = "Click the button below to create a ticket."

    if not state["available"] and normal:
        description += f"\n\n⚠️ {state['title']}: {state['message']}"

    return discord.Embed(title=title, description=description, color=color)


async def send_or_update_ticket_panel(
    guild: discord.Guild,
    channel: discord.TextChannel | None = None,
    *,
    force_new: bool = False,
) -> discord.Message | None:
    config = guild_config(guild.id)

    if channel is None:
        channel = await get_text_channel(guild, config.get("ticket_panel_channel_id"))

    if channel is None:
        return None

    embed = ticket_panel_embed(guild.id, normal=True)
    message_id = config.get("ticket_panel_message_id")

    if message_id and not force_new:
        try:
            message = await channel.fetch_message(int(message_id))
            await message.edit(embed=embed, view=TicketsButton())
            return message
        except discord.HTTPException:
            pass

    message = await channel.send(embed=embed, view=TicketsButton())
    config["ticket_panel_channel_id"] = channel.id
    config["ticket_panel_message_id"] = message.id
    await save_server_settings()
    return message


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
        await interaction.followup.send("❌ Ticket category not found. Run `/setup` or `/setticketcategory` first.")
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

    for role in staff_role_objects(guild):
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
        await interaction.followup.send("❌ Discord rejected the ticket channel creation. Check permissions/category limits.")
        return

    async with tickets_lock:
        ticket_owners[str(channel.id)] = {
            "guild_id": guild.id,
            "owner_id": user.id,
            "last_dm_time": 0,
            "last_away_reply_time": 0,
            "auto_messages": auto_messages,
            "created_at": int(time.time()),
            "claimed_by": None,
        }
        await save_ticket_owners()

    state = get_availability_state(guild.id)
    if auto_messages:
        description = "Please explain what you need help with.\n\n" + state["panel_line"]
        if not state["available"]:
            description += f"\n\n⚠️ {state['title']}: {state['message']}"
        ticket_embed = discord.Embed(title="🎟️ Ticket Opened", description=description, color=discord.Color.green())
    else:
        ticket_embed = discord.Embed(
            title="🎫 Ticket Opened",
            description="Please explain what you need help with.",
            color=discord.Color.green(),
        )

    ticket_embed.add_field(name="Opened By", value=user.mention, inline=True)
    ticket_embed.add_field(name="Status", value="Open", inline=True)
    ticket_embed.add_field(name="Claimed By", value="Not claimed", inline=True)

    await channel.send(content=user.mention, embed=ticket_embed, view=CloseButton())

    try:
        await user.send(f"🎫 Your ticket has been created in {guild.name}.\nTicket: {channel.mention}")
    except discord.HTTPException:
        pass

    await interaction.followup.send(f"✅ Created {channel.mention}")


async def delete_message_later(message: discord.Message, seconds: int) -> None:
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def maybe_dm_ticket_owner(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel) or message.guild is None:
        return

    data = ticket_owners.get(str(message.channel.id))
    if not isinstance(data, dict):
        return
    if not bool(data.get("auto_messages", False)):
        return

    owner_id = int(data.get("owner_id", 0))
    if owner_id == message.author.id:
        return
    if message.author.id not in OWNER_USER_IDS:
        return

    now = time.time()
    last_dm_time = float(data.get("last_dm_time", 0))
    if now - last_dm_time < TICKET_DM_COOLDOWN:
        return

    try:
        owner = message.guild.get_member(owner_id) or await message.guild.fetch_member(owner_id)
    except discord.HTTPException:
        return

    try:
        await owner.send(
            "📩 Ticket Update\n\n"
            f"{message.author.display_name} has replied to your ticket in {message.guild.name}.\n\n"
            f"Ticket: {message.channel.mention}\n\n"
            "Please check it when you can."
        )
        data["last_dm_time"] = now
        ticket_owners[str(message.channel.id)] = data
        await save_ticket_owners()
    except discord.HTTPException:
        pass


async def maybe_send_unavailable_ticket_reply(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel) or message.guild is None:
        return

    channel_id = str(message.channel.id)
    data = ticket_owners.get(channel_id)
    if not isinstance(data, dict):
        return
    if not bool(data.get("auto_messages", False)):
        return

    owner_id = int(data.get("owner_id", 0))
    if message.author.id != owner_id:
        return

    state = get_availability_state(message.guild.id)
    if state["available"]:
        return

    now = time.time()
    last_away_reply_time = float(data.get("last_away_reply_time", 0))
    if now - last_away_reply_time < AWAY_AUTO_REPLY_COOLDOWN:
        return

    away_msg = await message.channel.send(
        f"{message.author.mention}\n"
        f"⏰ XSI staff are currently unavailable.\n\n"
        f"{state['message']}\n"
        f"{state['panel_line']}",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )

    data["last_away_reply_time"] = now
    ticket_owners[channel_id] = data
    await save_ticket_owners()
    asyncio.create_task(delete_message_later(away_msg, AWAY_AUTO_REPLY_DELETE_AFTER))



# ============================================================
# HIDDEN STAFF UI HELPERS
# ============================================================
def extract_user_id(value: str) -> int | None:
    """Accepts a raw Discord ID or a mention like <@123> / <@!123>."""
    match = re.search(r"\d{15,25}", value or "")
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


async def resolve_member_from_text(guild: discord.Guild, value: str) -> discord.Member | None:
    user_id = extract_user_id(value)
    if user_id is None:
        return None

    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except discord.HTTPException:
        return None


async def resolve_user_from_text(guild: discord.Guild, value: str) -> discord.User | discord.Member | None:
    user_id = extract_user_id(value)
    if user_id is None:
        return None

    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except discord.HTTPException:
        pass

    try:
        return await bot.fetch_user(user_id)
    except discord.HTTPException:
        return None


def is_tracked_ticket_channel(channel: discord.abc.GuildChannel | None) -> bool:
    return isinstance(channel, discord.TextChannel) and isinstance(ticket_owners.get(str(channel.id)), dict)


def get_ticket_data(channel: discord.abc.GuildChannel | None) -> dict[str, Any] | None:
    if not isinstance(channel, discord.TextChannel):
        return None
    data = ticket_owners.get(str(channel.id))
    return data if isinstance(data, dict) else None


def can_use_hidden_ui(user: discord.abc.User, guild: discord.Guild | None) -> bool:
    if guild is None or not isinstance(user, discord.Member):
        return False
    return is_staff_or_mod(user)


async def add_member_to_ticket_channel(
    channel: discord.TextChannel,
    member: discord.Member,
    actor: discord.Member | discord.User,
) -> str:
    data = get_ticket_data(channel)
    if not isinstance(data, dict):
        return "❌ This channel is not a tracked ticket."

    try:
        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            reason=f"XSI UI: added to ticket by {actor} ({actor.id})",
        )
    except discord.Forbidden:
        return "❌ I need Manage Channels permission to add users to tickets."
    except discord.HTTPException:
        return "❌ Discord rejected the permission update."

    added_ids = data.setdefault("added_user_ids", [])
    if member.id not in added_ids:
        added_ids.append(member.id)
    ticket_owners[str(channel.id)] = data
    await save_ticket_owners()

    await channel.send(
        f"➕ {member.mention} was added to this ticket by {actor.mention}.",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )
    return f"✅ Added {member.mention} to {channel.mention}."


async def remove_member_from_ticket_channel(
    channel: discord.TextChannel,
    member: discord.Member,
    actor: discord.Member | discord.User,
) -> str:
    data = get_ticket_data(channel)
    if not isinstance(data, dict):
        return "❌ This channel is not a tracked ticket."

    owner_id = int(data.get("owner_id", 0))
    if member.id == owner_id:
        return "❌ You cannot remove the ticket owner from their own ticket. Close the ticket instead."

    try:
        await channel.set_permissions(
            member,
            overwrite=None,
            reason=f"XSI UI: removed from ticket by {actor} ({actor.id})",
        )
    except discord.Forbidden:
        return "❌ I need Manage Channels permission to remove users from tickets."
    except discord.HTTPException:
        return "❌ Discord rejected the permission update."

    added_ids = data.setdefault("added_user_ids", [])
    if member.id in added_ids:
        added_ids.remove(member.id)
    ticket_owners[str(channel.id)] = data
    await save_ticket_owners()

    await channel.send(
        f"➖ {member.mention} was removed from this ticket by {actor.mention}.",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )
    return f"✅ Removed {member.mention} from {channel.mention}."


async def send_staff_dm(
    guild: discord.Guild,
    target: discord.User | discord.Member,
    sender: discord.Member | discord.User,
    message: str,
) -> tuple[bool, str]:
    body = (
        f"📩 **Message from {guild.name} staff**\n"
        f"Sent by: {getattr(sender, 'display_name', sender.name)}\n\n"
        f"{message}"
    )

    try:
        await target.send(body)
    except discord.Forbidden:
        return False, "❌ I could not DM that user. Their DMs may be closed."
    except discord.HTTPException:
        return False, "❌ Discord rejected the DM."

    await send_staff_log(
        guild,
        f"📩 {sender.mention} sent a DM through XSI to {target.mention}: {message[:500]}",
    )
    return True, f"✅ DM sent to {target.mention}."


def build_hidden_ui_embed(interaction: discord.Interaction) -> discord.Embed:
    guild = interaction.guild
    channel = interaction.channel
    embed = discord.Embed(
        title="🧰 XSI Hidden Staff UI",
        description=(
            "Private ticket control panel opened only for you.\n"
            "This UI only shows ticket-related tools: claim, users, DMs, owner ping, rename, ticket info, and ticket-panel refresh."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Opened By", value=interaction.user.mention, inline=True)
    embed.add_field(name="Server", value=guild.name if guild else "Unknown", inline=True)
    embed.add_field(
        name="Current Channel",
        value=channel.mention if isinstance(channel, discord.TextChannel) else "Not a text channel",
        inline=True,
    )

    data = get_ticket_data(channel)
    if isinstance(data, dict):
        owner_id = int(data.get("owner_id", 0))
        claimed_by = data.get("claimed_by")
        created_at = int(data.get("created_at", 0))
        ticket_lines = [
            f"Owner: <@{owner_id}>" if owner_id else "Owner: Unknown",
            f"Claimed: <@{int(claimed_by)}>" if claimed_by else "Claimed: Not claimed",
        ]
        if created_at:
            ticket_lines.append(f"Created: <t:{created_at}:R>")
        embed.add_field(name="Ticket Context", value="\n".join(ticket_lines), inline=False)
    else:
        embed.add_field(name="Ticket Context", value="This is not a tracked ticket channel.", inline=False)

    embed.set_footer(text="Use Hide UI when finished. This panel is ephemeral/private and only ticket related.")
    return embed


def build_ticket_info_embed(guild: discord.Guild, channel: discord.TextChannel) -> discord.Embed:
    data = get_ticket_data(channel)
    embed = discord.Embed(title="🎟️ Ticket Info", color=discord.Color.blue())
    if not isinstance(data, dict):
        embed.description = "This channel is not a tracked ticket."
        return embed

    owner_id = int(data.get("owner_id", 0))
    claimed_by = data.get("claimed_by")
    created_at = int(data.get("created_at", 0))
    added_ids = data.get("added_user_ids", []) if isinstance(data.get("added_user_ids", []), list) else []

    embed.add_field(name="Channel", value=channel.mention, inline=True)
    embed.add_field(name="Owner", value=f"<@{owner_id}>" if owner_id else "Unknown", inline=True)
    embed.add_field(name="Claimed By", value=f"<@{int(claimed_by)}>" if claimed_by else "Not claimed", inline=True)
    embed.add_field(name="Auto Messages", value="Enabled" if data.get("auto_messages") else "Disabled", inline=True)
    embed.add_field(name="Created", value=f"<t:{created_at}:f>\n<t:{created_at}:R>" if created_at else "Unknown", inline=True)
    embed.add_field(
        name="Added Users",
        value=", ".join(f"<@{int(user_id)}>" for user_id in added_ids[:20]) if added_ids else "None tracked",
        inline=False,
    )

    state = get_availability_state(guild.id)
    embed.add_field(name="Availability", value=f"{state['title']} — {state['panel_line']}", inline=False)
    return embed


def build_active_giveaways_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(title="🎉 Active Giveaways", color=discord.Color.gold())
    lines: list[str] = []
    for giveaway_id, data in active_giveaways.items():
        if not isinstance(data, dict):
            continue
        if int(data.get("guild_id", 0)) != guild.id:
            continue
        channel_id = int(data.get("channel_id", 0))
        message_id = int(data.get("message_id", 0))
        ends_at = int(data.get("ends_at", 0))
        prize = str(data.get("prize", "Unknown prize"))
        channel = guild.get_channel(channel_id)
        channel_text = channel.mention if isinstance(channel, discord.TextChannel) else f"Channel `{channel_id}`"
        jump = f"https://discord.com/channels/{guild.id}/{channel_id}/{message_id}" if channel_id and message_id else ""
        lines.append(f"• **{prize}** in {channel_text} — ends <t:{ends_at}:R>\n{jump}")

    embed.description = "\n".join(lines[:10]) if lines else "No active giveaways in this server."
    return embed


class AddUserToTicketModal(discord.ui.Modal, title="Add User To Ticket"):
    target = discord.ui.TextInput(
        label="User mention or ID",
        placeholder="Example: @user or 123456789012345678",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a server ticket channel.", ephemeral=True)
            return
        if not can_use_hidden_ui(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You do not have permission to use this UI.", ephemeral=True)
            return

        member = await resolve_member_from_text(interaction.guild, str(self.target.value))
        if member is None:
            await interaction.response.send_message("❌ I could not find that server member.", ephemeral=True)
            return

        result = await add_member_to_ticket_channel(interaction.channel, member, interaction.user)
        await interaction.response.send_message(result, ephemeral=True)


class RemoveUserFromTicketModal(discord.ui.Modal, title="Remove User From Ticket"):
    target = discord.ui.TextInput(
        label="User mention or ID",
        placeholder="Example: @user or 123456789012345678",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a server ticket channel.", ephemeral=True)
            return
        if not can_use_hidden_ui(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You do not have permission to use this UI.", ephemeral=True)
            return

        member = await resolve_member_from_text(interaction.guild, str(self.target.value))
        if member is None:
            await interaction.response.send_message("❌ I could not find that server member.", ephemeral=True)
            return

        result = await remove_member_from_ticket_channel(interaction.channel, member, interaction.user)
        await interaction.response.send_message(result, ephemeral=True)


class DMUserModal(discord.ui.Modal, title="DM User Through XSI"):
    target = discord.ui.TextInput(
        label="User mention or ID",
        placeholder="Example: @user or 123456789012345678",
        required=True,
        max_length=100,
    )
    dm_message = discord.ui.TextInput(
        label="Message",
        placeholder="Type the message to send to their DMs",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1800,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
            return
        if not can_use_hidden_ui(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You do not have permission to use this UI.", ephemeral=True)
            return

        target = await resolve_user_from_text(interaction.guild, str(self.target.value))
        if target is None:
            await interaction.response.send_message("❌ I could not find that user. Use a mention or raw Discord user ID.", ephemeral=True)
            return

        ok, result = await send_staff_dm(interaction.guild, target, interaction.user, str(self.dm_message.value))
        await interaction.response.send_message(result, ephemeral=True)




class RenameTicketModal(discord.ui.Modal, title="Rename Ticket"):
    new_name = discord.ui.TextInput(
        label="New ticket name",
        placeholder="Example: trade-help-babloouvi",
        required=True,
        max_length=40,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a server ticket channel.", ephemeral=True)
            return
        if not can_use_hidden_ui(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You do not have permission to use this UI.", ephemeral=True)
            return
        if not is_tracked_ticket_channel(interaction.channel):
            await interaction.response.send_message("❌ This is not a tracked ticket channel.", ephemeral=True)
            return

        cleaned = clean_channel_name(str(self.new_name.value))
        if not cleaned.startswith("ticket-"):
            cleaned = f"ticket-{cleaned}"

        try:
            old_name = interaction.channel.name
            await interaction.channel.edit(
                name=cleaned[:90],
                reason=f"XSI UI: ticket renamed by {interaction.user} ({interaction.user.id})",
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ I need Manage Channels permission to rename tickets.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("❌ Discord rejected the ticket rename.", ephemeral=True)
            return

        await interaction.channel.send(f"✏️ Ticket renamed from `#{old_name}` to `#{interaction.channel.name}` by {interaction.user.mention}.")
        await interaction.response.send_message(f"✅ Ticket renamed to #{interaction.channel.name}.", ephemeral=True)

class XSIHiddenUIView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=10 * 60)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if can_use_hidden_ui(interaction.user, interaction.guild):
            return True
        await interaction.response.send_message("❌ You do not have permission to use this UI.", ephemeral=True)
        return False

    @discord.ui.button(label="Claim", emoji="✅", style=discord.ButtonStyle.green, row=0)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
            return
        data = get_ticket_data(interaction.channel)
        if not isinstance(data, dict):
            await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
            return
        data["claimed_by"] = interaction.user.id
        ticket_owners[str(interaction.channel.id)] = data
        await save_ticket_owners()
        await interaction.channel.send(f"✅ Ticket claimed by {interaction.user.mention}.")
        await interaction.response.send_message("✅ Ticket claimed.", ephemeral=True)

    @discord.ui.button(label="Unclaim", emoji="↩️", style=discord.ButtonStyle.secondary, row=0)
    async def unclaim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
            return
        data = get_ticket_data(interaction.channel)
        if not isinstance(data, dict):
            await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
            return
        data["claimed_by"] = None
        ticket_owners[str(interaction.channel.id)] = data
        await save_ticket_owners()
        await interaction.channel.send(f"↩️ Ticket unclaimed by {interaction.user.mention}.")
        await interaction.response.send_message("✅ Ticket unclaimed.", ephemeral=True)

    @discord.ui.button(label="Ticket Info", emoji="📌", style=discord.ButtonStyle.secondary, row=0)
    async def ticket_info_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
            return
        await interaction.response.send_message(embed=build_ticket_info_embed(interaction.guild, interaction.channel), ephemeral=True)

    @discord.ui.button(label="Add User", emoji="➕", style=discord.ButtonStyle.primary, row=1)
    async def add_user_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(AddUserToTicketModal())

    @discord.ui.button(label="Remove User", emoji="➖", style=discord.ButtonStyle.secondary, row=1)
    async def remove_user_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RemoveUserFromTicketModal())

    @discord.ui.button(label="DM User", emoji="📩", style=discord.ButtonStyle.primary, row=1)
    async def dm_user_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(DMUserModal())

    @discord.ui.button(label="DM Owner", emoji="🔔", style=discord.ButtonStyle.secondary, row=2)
    async def dm_owner_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
            return
        data = get_ticket_data(interaction.channel)
        if not isinstance(data, dict):
            await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
            return
        owner_id = int(data.get("owner_id", 0))
        if not owner_id:
            await interaction.response.send_message("❌ This ticket has no tracked owner.", ephemeral=True)
            return
        try:
            owner = interaction.guild.get_member(owner_id) or await interaction.guild.fetch_member(owner_id)
        except discord.HTTPException:
            await interaction.response.send_message("❌ I could not find the ticket owner.", ephemeral=True)
            return
        ok, result = await send_staff_dm(
            interaction.guild,
            owner,
            interaction.user,
            f"Your ticket has been updated. Please check {interaction.channel.mention} when you can.",
        )
        await interaction.response.send_message(result, ephemeral=True)

    @discord.ui.button(label="Rename Ticket", emoji="✏️", style=discord.ButtonStyle.secondary, row=2)
    async def rename_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RenameTicketModal())

    @discord.ui.button(label="Availability", emoji="⏰", style=discord.ButtonStyle.secondary, row=2)
    async def availability_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
            return
        state = get_availability_state(interaction.guild.id)
        await interaction.response.send_message(
            f"⏰ **{state['title']}** — {state['panel_line']}\n{state['message']}",
            ephemeral=True,
        )

    @discord.ui.button(label="Refresh Panel", emoji="🔄", style=discord.ButtonStyle.secondary, row=3)
    async def refresh_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        message = await send_or_update_ticket_panel(interaction.guild)
        await interaction.followup.send(
            "✅ Ticket panel refreshed." if message else "❌ Ticket panel channel is not set. Run `/setup` or `/tickets`.",
            ephemeral=True,
        )

    @discord.ui.button(label="Hide UI", emoji="🙈", style=discord.ButtonStyle.danger, row=3)
    async def hide_ui_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="🙈 XSI hidden UI closed.", embed=None, view=None)


# ============================================================
# BUTTON VIEWS
# ============================================================
class CloseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="xsi_close_ticket")
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
        await save_ticket_owners()
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await asyncio.sleep(2)

        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user} ({interaction.user.id})")
        except discord.HTTPException as exc:
            log.warning("Failed to delete ticket channel %s: %s", interaction.channel.id, exc)


class TicketsButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Open Ticket", style=discord.ButtonStyle.green, custom_id="xsi_create_ticket_auto")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await create_ticket_channel(interaction, auto_messages=True)


class Tickets2Button(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green, custom_id="xsi_create_ticket_basic")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await create_ticket_channel(interaction, auto_messages=False)


# ============================================================
# SETUP HELPERS
# ============================================================
def parse_setup_exclusions(text: str | None) -> set[str]:
    if not text:
        return set()

    raw = text.lower().replace(",", " ")
    words = [word.strip() for word in raw.split() if word.strip()]
    skips: set[str] = set()
    next_is_skip = False

    for word in words:
        word = word.strip("!?.;:,_-")
        if word in {"no", "skip", "without", "exclude"}:
            next_is_skip = True
            continue
        normalized = SKIP_ALIASES.get(word, word)
        if normalized in SETUP_COMPONENTS:
            if next_is_skip or "no" in words or "skip" in words or "exclude" in words or "without" in words:
                skips.add(normalized)
        next_is_skip = False

    # If a whole category is skipped, skip its children.
    if "tickets" in skips:
        skips.add("ticketpanel")
    if "logs" in skips:
        skips.update({"wall", "guilt", "leaves", "transcripts", "stafflogs"})
    if "info" in skips:
        skips.update({"welcome", "rules", "giveaways"})
    return skips


async def get_or_create_category(guild: discord.Guild, name: str, config: dict[str, Any]) -> discord.CategoryChannel:
    existing = discord.utils.get(guild.categories, name=name)
    if existing is not None:
        return existing
    category = await guild.create_category(name=name, reason="XSI setup")
    add_created_category(config, category.id)
    return category


async def get_or_create_text_channel(
    guild: discord.Guild,
    name: str,
    category: discord.CategoryChannel | None,
    config: dict[str, Any],
    *,
    topic: str | None = None,
) -> discord.TextChannel:
    existing = discord.utils.get(guild.text_channels, name=name)
    if existing is not None:
        if category is not None and existing.category_id != category.id:
            try:
                await existing.edit(category=category, reason="XSI setup organize channel")
            except discord.HTTPException:
                pass
        return existing

    channel = await guild.create_text_channel(name=name, category=category, topic=topic, reason="XSI setup")
    add_created_channel(config, channel.id)
    return channel


async def run_setup(guild: discord.Guild, channel: discord.abc.Messageable, exclusions: set[str]) -> discord.Embed:
    config = guild_config(guild.id)
    created_lines: list[str] = []
    skipped_lines: list[str] = []

    # Tickets category + ticket panel under tickets category.
    tickets_category: discord.CategoryChannel | None = None
    if "tickets" not in exclusions:
        tickets_category = await get_or_create_category(guild, "XSI Tickets", config)
        config["ticket_category_id"] = tickets_category.id
        created_lines.append(f"📁 Ticket Category: {tickets_category.name}")

        if "ticketpanel" not in exclusions:
            panel_channel = await get_or_create_text_channel(
                guild,
                "open-a-ticket",
                tickets_category,
                config,
                topic="Open support/trade tickets here.",
            )
            config["ticket_panel_channel_id"] = panel_channel.id
            created_lines.append(f"🎟️ Ticket Panel: {panel_channel.mention}")
            await send_or_update_ticket_panel(guild, panel_channel)
    else:
        skipped_lines.append("Tickets")

    # Logs category/channels.
    log_children = {"wall", "guilt", "leaves", "transcripts", "stafflogs"}
    if "logs" not in exclusions and not log_children.issubset(exclusions):
        logs_category = await get_or_create_category(guild, "XSI Logs", config)
        created_lines.append(f"📁 Logs Category: {logs_category.name}")

        if "wall" not in exclusions:
            wall = await get_or_create_text_channel(guild, "wall-of-knobs", logs_category, config)
            config["wall_channel_id"] = wall.id
            created_lines.append(f"🧱 Wall: {wall.mention}")
        else:
            skipped_lines.append("Wall")

        if "leaves" not in exclusions:
            leaves = await get_or_create_text_channel(guild, "leaves", logs_category, config)
            config["leaves_channel_id"] = leaves.id
            config["guilt_channel_id"] = leaves.id
            created_lines.append(f"👋 Leaves: {leaves.mention}")
        else:
            skipped_lines.append("Leaves")

        if "transcripts" not in exclusions:
            transcripts = await get_or_create_text_channel(guild, "ticket-transcripts", logs_category, config)
            config["transcript_channel_id"] = transcripts.id
            created_lines.append(f"📜 Transcripts: {transcripts.mention}")
        else:
            skipped_lines.append("Transcripts")

        if "stafflogs" not in exclusions:
            staff_logs = await get_or_create_text_channel(guild, "staff-logs", logs_category, config)
            config["staff_log_channel_id"] = staff_logs.id
            created_lines.append(f"🛡️ Staff Logs: {staff_logs.mention}")
        else:
            skipped_lines.append("Staff Logs")
    else:
        skipped_lines.append("Logs")

    # Info category/channels.
    info_children = {"welcome", "rules", "giveaways"}
    if "info" not in exclusions and not info_children.issubset(exclusions):
        info_category = await get_or_create_category(guild, "XSI Info", config)
        created_lines.append(f"📁 Info Category: {info_category.name}")

        if "welcome" not in exclusions:
            welcome = await get_or_create_text_channel(guild, "welcome", info_category, config)
            config["welcome_channel_id"] = welcome.id
            created_lines.append(f"👋 Welcome: {welcome.mention}")
        else:
            skipped_lines.append("Welcome")

        if "rules" not in exclusions:
            rules = await get_or_create_text_channel(guild, "rules", info_category, config)
            config["rules_channel_id"] = rules.id
            created_lines.append(f"📜 Rules: {rules.mention}")
        else:
            skipped_lines.append("Rules")

        if "giveaways" not in exclusions:
            giveaways = await get_or_create_text_channel(guild, "giveaways", info_category, config)
            config["giveaways_channel_id"] = giveaways.id
            created_lines.append(f"🎉 Giveaways: {giveaways.mention}")
        else:
            skipped_lines.append("Giveaways")
    else:
        skipped_lines.append("Info")

    config.setdefault("availability", default_guild_config()["availability"])
    await save_server_settings()

    embed = discord.Embed(
        title="✅ XSI setup complete",
        description="Server setup was created and saved for this server.",
        color=discord.Color.green(),
    )
    embed.add_field(name="Created / Saved", value="\n".join(created_lines)[:1024] or "Nothing new created.", inline=False)
    embed.add_field(name="Skipped", value="\n".join(sorted(set(skipped_lines)))[:1024] or "Nothing skipped.", inline=False)
    embed.add_field(
        name="Examples",
        value=(
            "`!setup` = create everything\n"
            "`!setup no giveaways` = skip giveaways\n"
            "`!setup no welcome no transcripts` = skip welcome and transcripts\n"
            "Slash: `/setup exclude: giveaways,welcome`"
        ),
        inline=False,
    )
    return embed


async def delete_channel_safely(channel: discord.abc.GuildChannel, reason: str) -> bool:
    try:
        await channel.delete(reason=reason)
        return True
    except discord.HTTPException:
        return False


async def clear_setup_impl(guild: discord.Guild, mode: str, confirm: str) -> tuple[discord.Embed, bool]:
    mode = mode.lower().strip().replace(" ", "_")
    confirm_clean = confirm.strip().upper()
    destructive = mode in {"delete", "delete_created", "wipe", "factory", "factory_wipe", "full", "full_wipe"}

    if mode in {"", "safe", "keep", "reset"}:
        async with settings_lock:
            server_settings.pop(str(guild.id), None)
            await save_server_settings()
        embed = discord.Embed(
            title="✅ Setup cleared",
            description="XSI settings were cleared, but channels were kept.",
            color=discord.Color.green(),
        )
        return embed, True

    if destructive and confirm_clean not in {"YES", "CONFIRM", "CONFIRM WIPE", "DELETE"}:
        embed = discord.Embed(
            title="⚠️ Confirmation needed",
            description=(
                "This will delete channels/categories that XSI created.\n\n"
                "Run one of these:\n"
                "`/clearsetup mode: delete_created confirm: YES`\n"
                "`/clearsetup mode: factory_wipe confirm: YES`\n\n"
                "Prefix:\n"
                "`!clearsetup delete_created YES`\n"
                "`!clearsetup factory_wipe YES`"
            ),
            color=discord.Color.orange(),
        )
        return embed, False

    config = guild_config(guild.id)
    deleted: list[str] = []
    failed: list[str] = []

    if mode in {"delete", "delete_created"}:
        channel_ids = [int(x) for x in config.get("created_channel_ids", []) if str(x).isdigit()]
        category_ids = [int(x) for x in config.get("created_category_ids", []) if str(x).isdigit()]

        # Delete known created channels first.
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if channel is None:
                continue
            ok = await delete_channel_safely(channel, "XSI clearsetup delete_created")
            (deleted if ok else failed).append(f"#{channel.name}")

        # Delete child channels under created categories, then categories.
        for category_id in category_ids:
            category = guild.get_channel(category_id)
            if isinstance(category, discord.CategoryChannel):
                for child in list(category.channels):
                    ok = await delete_channel_safely(child, "XSI clearsetup delete_created child")
                    (deleted if ok else failed).append(f"#{child.name}")
                ok = await delete_channel_safely(category, "XSI clearsetup delete_created category")
                (deleted if ok else failed).append(f"📁 {category.name}")

    elif mode in {"wipe", "factory", "factory_wipe", "full", "full_wipe"}:
        # Delete exactly named XSI categories and their children.
        for name in ["XSI Tickets", "XSI Logs", "XSI Info"]:
            category = discord.utils.get(guild.categories, name=name)
            if category is None:
                continue
            for child in list(category.channels):
                ok = await delete_channel_safely(child, "XSI factory wipe child")
                (deleted if ok else failed).append(f"#{child.name}")
            ok = await delete_channel_safely(category, "XSI factory wipe category")
            (deleted if ok else failed).append(f"📁 {category.name}")

    async with settings_lock:
        server_settings.pop(str(guild.id), None)
        await save_server_settings()

    embed = discord.Embed(
        title="🧹 XSI setup cleared",
        description="Settings were cleared and requested setup channels/categories were processed.",
        color=discord.Color.green() if not failed else discord.Color.orange(),
    )
    embed.add_field(name="Deleted", value="\n".join(deleted)[:1024] or "Nothing deleted.", inline=False)
    if failed:
        embed.add_field(name="Failed", value="\n".join(failed)[:1024], inline=False)
    embed.add_field(name="Mode", value=mode, inline=True)
    return embed, True


# ============================================================
# SMART MESSAGES
# ============================================================
def get_guild_smart_messages(guild_id: int) -> dict[str, Any]:
    gid = str(guild_id)
    data = smart_messages.get(gid)
    if not isinstance(data, dict):
        data = {}
        smart_messages[gid] = data
    return data


async def maybe_handle_smart_message(message: discord.Message) -> bool:
    if message.guild is None or message.author.bot:
        return False
    if message.content.startswith(("!", "?", "/")):
        return False

    rules = get_guild_smart_messages(message.guild.id)
    if not rules:
        return False

    content = normalize_text(message.content)
    now = time.time()

    for trigger, data in rules.items():
        if not isinstance(data, dict):
            continue
        trigger_normal = normalize_text(trigger)
        if not trigger_normal or trigger_normal not in content:
            continue

        cooldown_key = f"{message.guild.id}:{message.channel.id}:{trigger_normal}"
        last = smart_cooldowns.get(cooldown_key, 0)
        if now - last < int(data.get("cooldown", SMART_MESSAGE_COOLDOWN)):
            return False

        response = str(data.get("response") or "")
        if not response:
            return False

        response = format_mentions_safe(response, message.author, message.guild)
        smart_cooldowns[cooldown_key] = now
        await message.channel.send(
            response,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        return True

    return False


# ============================================================
# GIVEAWAYS
# ============================================================
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


async def finish_giveaway_by_data(data: dict[str, Any]) -> None:
    guild = bot.get_guild(int(data["guild_id"]))
    if guild is None:
        return
    channel = await get_text_channel(guild, int(data["channel_id"]))
    if channel is None:
        return

    prize = str(data["prize"])
    try:
        message = await channel.fetch_message(int(data["message_id"]))
    except discord.HTTPException:
        await channel.send(f"❌ Giveaway message for {prize} was deleted or could not be found.")
        return

    entries: list[discord.User | discord.Member] = []
    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    entries.append(user)

    if not entries:
        await channel.send(f"❌ No one entered the {prize} giveaway.")
        return

    winner = random.choice(entries)
    end_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=f"Prize: {prize}\n\nWinner: {winner.mention}",
        color=discord.Color.green(),
    )
    await channel.send(embed=end_embed)
    await channel.send(f"🎉 Congratulations {winner.mention}! You won {prize}!")


async def start_giveaway_in_channel(channel: discord.TextChannel, amount: int, prize_type: str, seconds: int, test: bool = False) -> str:
    if amount <= 0:
        return "❌ Amount must be at least 1."
    prize = make_prize(amount, prize_type)
    if prize is None:
        return "❌ Use Normal, Hard Trade, or Very Hard Trade."

    title = "🎉 TEST GIVEAWAY 🎉" if test else "🎉 GIVEAWAY 🎉"
    time_text = "30 seconds" if test else "24 hours"
    embed = discord.Embed(
        title=title,
        description=f"Prize: {prize}\n\nReact with 🎉 to enter!\n\n⏰ Ends in {time_text}",
        color=discord.Color.gold(),
    )
    message = await channel.send(embed=embed)
    await message.add_reaction("🎉")

    giveaway_id = str(message.id)
    active_giveaways[giveaway_id] = {
        "guild_id": channel.guild.id,
        "channel_id": channel.id,
        "message_id": message.id,
        "prize": prize,
        "ends_at": int(time.time() + seconds),
    }
    await save_giveaways()
    return f"✅ Started giveaway for {prize}."


# ============================================================
# BACKGROUND TASKS
# ============================================================
@tasks.loop(seconds=60)
async def availability_refresher() -> None:
    await bot.wait_until_ready()
    changed_any = False

    for guild in list(bot.guilds):
        config = guild_config(guild.id)
        old_status = config.get("last_availability_status")
        cleaned = await cleanup_expired_unavailable(guild.id)
        state = get_availability_state(guild.id)
        new_status = state.get("status")

        if cleaned:
            changed_any = True

        if old_status != new_status:
            config["last_availability_status"] = new_status
            changed_any = True
            try:
                await send_or_update_ticket_panel(guild)
            except discord.HTTPException:
                pass

    if changed_any:
        await save_server_settings()


@tasks.loop(seconds=30)
async def giveaway_checker() -> None:
    await bot.wait_until_ready()
    now = int(time.time())
    finished: list[str] = []

    for giveaway_id, data in list(active_giveaways.items()):
        if not isinstance(data, dict):
            finished.append(giveaway_id)
            continue
        if now >= int(data.get("ends_at", 0)):
            await finish_giveaway_by_data(data)
            finished.append(giveaway_id)

    if finished:
        async with giveaway_lock:
            for giveaway_id in finished:
                active_giveaways.pop(giveaway_id, None)
            await save_giveaways()


# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready() -> None:
    log.info("----------------------------")
    log.info("✅ XSI logged in as %s", bot.user)
    log.info("✅ %s", VERSION)
    log.info("----------------------------")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    config = guild_config(member.guild.id)
    channel = await get_text_channel(member.guild, config.get("welcome_channel_id"))
    if channel is None:
        return

    welcome_text = str(config.get("welcome_message") or DEFAULT_WELCOME_MESSAGE)
    message = format_mentions_safe(welcome_text, member, member.guild)
    try:
        await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
    except discord.HTTPException:
        pass


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    config = guild_config(member.guild.id)
    channel = await get_text_channel(member.guild, config.get("leaves_channel_id") or config.get("guilt_channel_id"))
    if channel is None:
        return

    embed = discord.Embed(
        title="⚖️ Board of Guilt",
        description=f"💀 {member.name} left the server...\n\nTheir name shall stay here forever.",
        color=discord.Color.red(),
    )
    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    try:
        await channel.send(content=f"bye I guess... <@{member.id}>", embed=embed)
    except discord.HTTPException:
        pass


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if message.guild is None or not isinstance(message.author, discord.Member):
        return

    await maybe_dm_ticket_owner(message)
    await maybe_send_unavailable_ticket_reply(message)
    await maybe_handle_smart_message(message)

    member = message.author

    if is_staff_or_mod(member):
        await bot.process_commands(message)
        return

    content = message.content or ""
    offence = detect_offence(content)
    if offence is None and is_spam(message.guild.id, message.channel.id, member.id, content):
        offence = "Spam / repeated messages"

    if offence is not None:
        warning_count = await add_warning(message.guild.id, member.id)
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send("❌ I need Manage Messages permission.")
        except discord.HTTPException:
            pass

        if warning_count >= MAX_WARNINGS:
            punishment = "Banned" if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban" else "Kicked"
            await send_wall_log(member, offence, punishment, content, warning_count)
            try:
                await punish_if_needed(message.guild, message.channel, member, offence, warning_count)
            except discord.Forbidden:
                await message.channel.send(f"❌ I do not have permission to punish {member.mention}.")
            except discord.HTTPException as exc:
                log.exception("Punishment failed: %s", exc)
                await message.channel.send("❌ Something went wrong while punishing.")
            return

        await send_wall_log(member, offence, "Warning", content, warning_count)
        await message.channel.send(
            f"⚠️ {member.mention}, warning {warning_count}/{MAX_WARNINGS} — {offence}.\nYour message was deleted."
        )
        return

    await bot.process_commands(message)


# ============================================================
# PREFIX COMMANDS - SETUP / STATUS
# ============================================================
@bot.command(name="version")
async def version_cmd(ctx: commands.Context) -> None:
    await ctx.send(f"✅ {VERSION}\nBuild tag: `{BUILD_TAG}`")


@bot.command(name="buildcheck", aliases=["commandcount", "slashcount"])
async def buildcheck_cmd(ctx: commands.Context) -> None:
    names = sorted(command.name for command in bot.tree.get_commands())
    critical = ["clearsetup", "setunavailable", "refreshticketpanel", "setavailability", "availability", "clearunavailable", "ui", "dm", "kick"]
    missing = [name for name in critical if name not in names]
    missing_text = ", ".join(missing) if missing else "None"
    await ctx.send(
        f"✅ {VERSION}\n"
        f"Build tag: `{BUILD_TAG}`\n"
        f"Slash commands loaded in memory: `{len(names)}`\n"
        f"Critical commands missing: `{missing_text}`"
    )


@bot.command(name="synccommands", aliases=["sync"])
@commands.has_permissions(administrator=True)
async def synccommands(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ Run this inside a server.")
        return
    bot.tree.clear_commands(guild=ctx.guild)
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Synced {len(synced)} slash command(s) in **{ctx.guild.name}**.")


@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_prefix(ctx: commands.Context, *, options: str = "") -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    embed = await run_setup(ctx.guild, ctx.channel, parse_setup_exclusions(options))
    await ctx.send(embed=embed)


@bot.command(name="clearsetup")
@commands.has_permissions(administrator=True)
async def clearsetup_prefix(ctx: commands.Context, mode: str = "keep", confirm: str = "") -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    embed, _ = await clear_setup_impl(ctx.guild, mode, confirm)
    await ctx.send(embed=embed)


@bot.command(name="checksetup")
@commands.has_permissions(administrator=True)
async def checksetup(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)

    def ch_line(label: str, key: str) -> str:
        channel_id = config.get(key)
        channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None
        return f"{label}: {channel.mention if isinstance(channel, discord.TextChannel) else 'Not set'}"

    category = get_ticket_category(ctx.guild)
    roles = staff_role_objects(ctx.guild)
    state = get_availability_state(ctx.guild.id)

    embed = discord.Embed(title="🔧 XSI Setup Check", color=discord.Color.blue())
    embed.add_field(name="Ticket Category", value=category.name if category else "Not set", inline=False)
    embed.add_field(
        name="Channels",
        value="\n".join(
            [
                ch_line("Ticket Panel", "ticket_panel_channel_id"),
                ch_line("Welcome", "welcome_channel_id"),
                ch_line("Wall", "wall_channel_id"),
                ch_line("Leaves", "leaves_channel_id"),
                ch_line("Transcripts", "transcript_channel_id"),
                ch_line("Staff Logs", "staff_log_channel_id"),
                ch_line("Rules", "rules_channel_id"),
                ch_line("Giveaways", "giveaways_channel_id"),
            ]
        )[:1024],
        inline=False,
    )
    embed.add_field(name="Staff Roles", value=", ".join(role.mention for role in roles) or "None", inline=False)
    embed.add_field(name="Availability", value=f"{state['title']} — {state['panel_line']}", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="requiredpermissions", aliases=["permissions", "perms"])
async def requiredpermissions_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    await ctx.send(embed=build_required_permissions_embed(ctx.guild))


# ============================================================
# PREFIX COMMANDS - CONFIG SETTERS
# ============================================================
@bot.command(name="setticketcategory", aliases=["setcategory"])
@commands.has_permissions(administrator=True)
async def setticketcategory(ctx: commands.Context, category_id: int | None = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    if category_id is None:
        if not isinstance(ctx.channel, discord.TextChannel) or ctx.channel.category is None:
            await ctx.send("❌ This channel is not inside a category. Use `!setticketcategory CATEGORY_ID`.")
            return
        category = ctx.channel.category
    else:
        category = ctx.guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ That ID is not a valid category in this server.")
        return
    config = guild_config(ctx.guild.id)
    config["ticket_category_id"] = category.id
    await save_server_settings()
    await ctx.send(f"✅ Ticket category set to **{category.name}**.")


@bot.command(name="checkcategory")
@commands.has_permissions(administrator=True)
async def checkcategory(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    category = get_ticket_category(ctx.guild)
    await ctx.send(f"✅ Current ticket category: **{category.name}**" if category else "❌ No ticket category found.")


@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx: commands.Context, *, message: str = DEFAULT_WELCOME_MESSAGE) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a server text channel.")
        return
    config = guild_config(ctx.guild.id)
    config["welcome_channel_id"] = ctx.channel.id
    config["welcome_message"] = message
    await save_server_settings()
    await ctx.send(f"✅ Welcome channel set to {ctx.channel.mention}. Message: `{message}`")


@bot.command(name="setwallchannel")
@commands.has_permissions(administrator=True)
async def setwallchannel(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a server text channel.")
        return
    config = guild_config(ctx.guild.id)
    config["wall_channel_id"] = ctx.channel.id
    await save_server_settings()
    await ctx.send(f"✅ Wall channel set to {ctx.channel.mention}.")


@bot.command(name="setleaveschannel", aliases=["setgulitcategory", "setguiltchannel", "setguiltcategory"])
@commands.has_permissions(administrator=True)
async def setleaveschannel(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a server text channel.")
        return
    config = guild_config(ctx.guild.id)
    config["leaves_channel_id"] = ctx.channel.id
    config["guilt_channel_id"] = ctx.channel.id
    await save_server_settings()
    await ctx.send(f"✅ Leaves / Board of Guilt channel set to {ctx.channel.mention}.")


@bot.command(name="setstaffrole")
@commands.has_permissions(administrator=True)
async def setstaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    config["staff_role_ids"] = [role.id]
    await save_server_settings()
    await ctx.send(f"✅ Staff role set to {role.mention}.")


@bot.command(name="addstaffrole")
@commands.has_permissions(administrator=True)
async def addstaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    ids = config.setdefault("staff_role_ids", [])
    if role.id not in ids:
        ids.append(role.id)
    await save_server_settings()
    await ctx.send(f"✅ Added staff role {role.mention}.")


@bot.command(name="removestaffrole")
@commands.has_permissions(administrator=True)
async def removestaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    ids = config.setdefault("staff_role_ids", [])
    if role.id in ids:
        ids.remove(role.id)
    await save_server_settings()
    await ctx.send(f"✅ Removed staff role {role.mention}.")


# ============================================================
# PREFIX COMMANDS - AVAILABILITY
# ============================================================
@bot.command(name="setavailability")
@commands.has_permissions(administrator=True)
async def setavailability_prefix(ctx: commands.Context, start_time: str, end_time: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    try:
        start_minutes = parse_time_to_minutes(start_time)
        end_minutes = parse_time_to_minutes(end_time)
    except ValueError as exc:
        await ctx.send(f"❌ {exc}")
        return
    config = guild_config(ctx.guild.id)
    config["availability"] = {
        "timezone": DEFAULT_TIMEZONE,
        "start": format_minutes(start_minutes),
        "end": format_minutes(end_minutes),
        "enabled": True,
    }
    await save_server_settings()
    await send_or_update_ticket_panel(ctx.guild)
    await ctx.send(f"✅ Availability set to {format_minutes(start_minutes)} to {format_minutes(end_minutes)} UK.")


@bot.command(name="clearavailability")
@commands.has_permissions(administrator=True)
async def clearavailability_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    config["availability"] = default_guild_config()["availability"]
    await save_server_settings()
    await send_or_update_ticket_panel(ctx.guild)
    await ctx.send("✅ Availability reset to 9am to 10pm UK.")


@bot.command(name="setunavailable")
@commands.has_permissions(administrator=True)
async def setunavailable_prefix(ctx: commands.Context, start_time: str, end_time: str, *, message: str = DEFAULT_UNAVAILABLE_MESSAGE) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    try:
        start_dt, end_dt = make_unavailable_window(config, start_time, end_time)
    except ValueError as exc:
        await ctx.send(f"❌ {exc}")
        return
    config["temporary_unavailable"] = {
        "start_iso": start_dt.isoformat(),
        "end_iso": end_dt.isoformat(),
        "message": message,
    }
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(ctx.guild)
    await ctx.send(f"✅ Temporary unavailable set from {format_dt(start_dt)} to {format_dt(end_dt)} UK.")


@bot.command(name="clearunavailable")
@commands.has_permissions(administrator=True)
async def clearunavailable_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    config = guild_config(ctx.guild.id)
    config["temporary_unavailable"] = None
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(ctx.guild)
    await ctx.send("✅ Temporary unavailable cleared. Ticket panel is back to normal availability.")


@bot.command(name="availability")
async def availability_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    state = get_availability_state(ctx.guild.id)
    await ctx.send(f"⏰ **{state['title']}** — {state['panel_line']}\n{state['message']}")


@bot.command(name="refreshticketpanel")
@commands.has_permissions(administrator=True)
async def refreshticketpanel_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    message = await send_or_update_ticket_panel(ctx.guild)
    await ctx.send("✅ Ticket panel refreshed." if message else "❌ Ticket panel channel is not set. Run `/setup` or `/tickets`.")


# ============================================================
# PREFIX COMMANDS - TICKETS
# ============================================================
@bot.command(name="tickets", aliases=["ticket"])
@commands.has_permissions(administrator=True)
async def tickets(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a server text channel.")
        return
    config = guild_config(ctx.guild.id)
    config["ticket_panel_channel_id"] = ctx.channel.id
    await save_server_settings()
    await send_or_update_ticket_panel(ctx.guild, ctx.channel, force_new=True)


@bot.command(name="tickets2")
@commands.has_permissions(administrator=True)
async def tickets2(ctx: commands.Context) -> None:
    embed = ticket_panel_embed(ctx.guild.id if ctx.guild else 0, normal=False)
    await ctx.send(embed=embed, view=Tickets2Button())


@bot.command(name="claim")
@commands.has_permissions(manage_messages=True)
async def claim_ticket(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a ticket channel.")
        return
    data = ticket_owners.get(str(ctx.channel.id))
    if not isinstance(data, dict):
        await ctx.send("❌ This is not a tracked ticket.")
        return
    data["claimed_by"] = ctx.author.id
    await save_ticket_owners()
    await ctx.send(f"✅ Ticket claimed by {ctx.author.mention}.")


@bot.command(name="unclaim")
@commands.has_permissions(manage_messages=True)
async def unclaim_ticket(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a ticket channel.")
        return
    data = ticket_owners.get(str(ctx.channel.id))
    if not isinstance(data, dict):
        await ctx.send("❌ This is not a tracked ticket.")
        return
    data["claimed_by"] = None
    await save_ticket_owners()
    await ctx.send("✅ Ticket unclaimed.")


# ============================================================
# PREFIX COMMANDS - MODERATION
# ============================================================

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def prefix_kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    ok, result = await kick_member_with_checks(ctx.guild, ctx.author, member, reason)
    await ctx.send(
        result,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def prefix_warn(ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    warning_count = await add_warning(ctx.guild.id, member.id)
    await send_wall_log(member, reason, "Manual warning", "Manual staff warning", warning_count, ctx.author)
    await ctx.send(
        f"⚠️ {member.mention} has been warned by {ctx.author.mention}.\nReason: {reason}\nWarnings: {warning_count}/{MAX_WARNINGS}"
    )
    if warning_count >= MAX_WARNINGS:
        await punish_if_needed(ctx.guild, ctx.channel, member, reason, warning_count)


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings_cmd(ctx: commands.Context, member: discord.Member | None = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    member = member or ctx.author
    if not isinstance(member, discord.Member):
        await ctx.send("❌ I could not identify that member.")
        return
    count = get_warnings(ctx.guild.id, member.id)
    await ctx.send(f"⚠️ {member.mention} has {count}/{MAX_WARNINGS} warnings.")


@bot.command(name="clearwarnings")
@commands.has_permissions(manage_messages=True)
async def clearwarnings_cmd(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    await clear_warnings_for(ctx.guild.id, member.id)
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
            "Bad messages are automatically deleted.\n\n"
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
    warning_count = await add_warning(ctx.guild.id, member.id)
    await send_wall_log(member, offence, "Manual warning", "Manual staff report", warning_count, ctx.author)
    await ctx.send(f"🧱 Added {member.mention} to the Wall of Knobs.")


@bot.command(name="testguilt")
@commands.has_permissions(administrator=True)
async def testguilt(ctx: commands.Context) -> None:
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")


# ============================================================
# PREFIX COMMANDS - SMART MESSAGES
# ============================================================
@bot.command(name="addsmartmessage")
@commands.has_permissions(manage_messages=True)
async def addsmartmessage(ctx: commands.Context, trigger: str, *, response: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    async with smart_lock:
        rules = get_guild_smart_messages(ctx.guild.id)
        rules[trigger.lower()] = {"response": response, "cooldown": SMART_MESSAGE_COOLDOWN}
        await save_smart_messages()
    await ctx.send(f"✅ Smart message added for `{trigger}`.")


@bot.command(name="removesmartmessage")
@commands.has_permissions(manage_messages=True)
async def removesmartmessage(ctx: commands.Context, trigger: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    async with smart_lock:
        rules = get_guild_smart_messages(ctx.guild.id)
        rules.pop(trigger.lower(), None)
        await save_smart_messages()
    await ctx.send(f"✅ Smart message removed for `{trigger}`.")


@bot.command(name="listsmartmessages")
@commands.has_permissions(manage_messages=True)
async def listsmartmessages(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    rules = get_guild_smart_messages(ctx.guild.id)
    if not rules:
        await ctx.send("No smart messages set.")
        return
    lines = [f"`{trigger}` → {str(data.get('response', ''))[:80]}" for trigger, data in rules.items() if isinstance(data, dict)]
    await ctx.send("🧠 Smart messages:\n" + "\n".join(lines)[:1800])


@bot.command(name="clearsmartmessages")
@commands.has_permissions(manage_messages=True)
async def clearsmartmessages(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    async with smart_lock:
        smart_messages[str(ctx.guild.id)] = {}
        await save_smart_messages()
    await ctx.send("✅ Removed all smart messages in this server.")


# ============================================================
# PREFIX COMMANDS - UTILITY / GIVEAWAYS
# ============================================================
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
    embed = discord.Embed(title=title, description=description, color=discord.Color.purple())
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
            "8. No money services or boosts."
        ),
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed)


@bot.command(name="slotinfo")
async def slotinfo(ctx: commands.Context) -> None:
    await ctx.send("❌ Sloty has been removed from this bot.")


@bot.command(name="giveaway")
@commands.has_permissions(administrator=True)
async def giveaway(ctx: commands.Context, amount: int, *, prize_type: str) -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return
    result = await start_giveaway_in_channel(ctx.channel, amount, prize_type, GIVEAWAY_TIME)
    await ctx.send(result)


@bot.command(name="testgiveaway")
@commands.has_permissions(administrator=True)
async def testgiveaway(ctx: commands.Context, amount: int, *, prize_type: str) -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return
    result = await start_giveaway_in_channel(ctx.channel, amount, prize_type, TEST_GIVEAWAY_TIME, test=True)
    await ctx.send(result)


# ============================================================
# SLASH COMMANDS
# ============================================================
@bot.tree.command(name="version", description="Show the running XSI build version")
async def slash_version(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"✅ {VERSION}\nBuild tag: `{BUILD_TAG}`", ephemeral=True)


@bot.tree.command(name="buildcheck", description="Show XSI build and slash-command diagnostics")
async def slash_buildcheck(interaction: discord.Interaction) -> None:
    names = sorted(command.name for command in bot.tree.get_commands())
    critical = ["clearsetup", "setunavailable", "refreshticketpanel", "setavailability", "availability", "clearunavailable", "ui", "dm", "kick"]
    missing = [name for name in critical if name not in names]
    missing_text = ", ".join(missing) if missing else "None"
    await interaction.response.send_message(
        f"✅ {VERSION}\n"
        f"Build tag: `{BUILD_TAG}`\n"
        f"Slash commands loaded in memory: `{len(names)}`\n"
        f"Critical commands missing: `{missing_text}`",
        ephemeral=True,
    )


@bot.tree.command(name="ui", description="Open the hidden XSI ticket staff UI")
async def slash_ui(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    if not can_use_hidden_ui(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You do not have permission to use the hidden staff UI.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=build_hidden_ui_embed(interaction),
        view=XSIHiddenUIView(),
        ephemeral=True,
    )


@bot.tree.command(name="dm", description="Send a private DM to a user through XSI")
@app_commands.describe(member="The server member to DM", message="The message to send to their DMs")
async def slash_dm(interaction: discord.Interaction, member: discord.Member, message: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    if not can_use_hidden_ui(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You do not have permission to send DMs through XSI.", ephemeral=True)
        return
    ok, result = await send_staff_dm(interaction.guild, member, interaction.user, message)
    await interaction.response.send_message(result, ephemeral=True)


@bot.tree.command(name="synccommands", description="Sync XSI slash commands in this server")
@app_commands.checks.has_permissions(administrator=True)
async def slash_synccommands(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ Run this inside a server.", ephemeral=True)
        return
    bot.tree.clear_commands(guild=interaction.guild)
    bot.tree.copy_global_to(guild=interaction.guild)
    synced = await bot.tree.sync(guild=interaction.guild)
    await interaction.response.send_message(f"✅ Synced {len(synced)} slash command(s) in **{interaction.guild.name}**.")


@bot.tree.command(name="setup", description="Create XSI categories/channels and save setup")
@app_commands.describe(exclude="Optional: giveaways,welcome,transcripts etc")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup(interaction: discord.Interaction, exclude: str = "") -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    embed = await run_setup(interaction.guild, interaction.channel, parse_setup_exclusions(exclude))
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="clearsetup", description="Clear XSI setup; optionally delete XSI-created channels")
@app_commands.describe(
    mode="keep, delete_created, or factory_wipe",
    confirm="Required for delete modes. Type YES.",
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_clearsetup(interaction: discord.Interaction, mode: str = "keep", confirm: str = "") -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await interaction.response.defer(thinking=True, ephemeral=True)
    embed, _ = await clear_setup_impl(interaction.guild, mode, confirm)
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="checksetup", description="Show current XSI setup for this server")
@app_commands.checks.has_permissions(administrator=True)
async def slash_checksetup(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)

    def ch_line(label: str, key: str) -> str:
        channel_id = config.get(key)
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        return f"{label}: {channel.mention if isinstance(channel, discord.TextChannel) else 'Not set'}"

    category = get_ticket_category(interaction.guild)
    roles = staff_role_objects(interaction.guild)
    state = get_availability_state(interaction.guild.id)
    embed = discord.Embed(title="🔧 XSI Setup Check", color=discord.Color.blue())
    embed.add_field(name="Ticket Category", value=category.name if category else "Not set", inline=False)
    embed.add_field(
        name="Channels",
        value="\n".join(
            [
                ch_line("Ticket Panel", "ticket_panel_channel_id"),
                ch_line("Welcome", "welcome_channel_id"),
                ch_line("Wall", "wall_channel_id"),
                ch_line("Leaves", "leaves_channel_id"),
                ch_line("Transcripts", "transcript_channel_id"),
                ch_line("Staff Logs", "staff_log_channel_id"),
                ch_line("Rules", "rules_channel_id"),
                ch_line("Giveaways", "giveaways_channel_id"),
            ]
        )[:1024],
        inline=False,
    )
    embed.add_field(name="Staff Roles", value=", ".join(role.mention for role in roles) or "None", inline=False)
    embed.add_field(name="Availability", value=f"{state['title']} — {state['panel_line']}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="requiredpermissions", description="Show the permissions XSI needs")
async def slash_requiredpermissions(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_required_permissions_embed(interaction.guild), ephemeral=True)


@bot.tree.command(name="setticketcategory", description="Set this channel's category as ticket category")
@app_commands.describe(category_id="Optional category ID. Leave blank to use this channel's category.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setticketcategory(interaction: discord.Interaction, category_id: str = "") -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    if category_id:
        category = interaction.guild.get_channel(int(category_id)) if category_id.isdigit() else None
    else:
        category = interaction.channel.category if isinstance(interaction.channel, discord.TextChannel) else None
    if not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message("❌ Could not find a valid category.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["ticket_category_id"] = category.id
    await save_server_settings()
    await interaction.response.send_message(f"✅ Ticket category set to **{category.name}**.", ephemeral=True)


@bot.tree.command(name="checkcategory", description="Show the current ticket category")
@app_commands.checks.has_permissions(administrator=True)
async def slash_checkcategory(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    category = get_ticket_category(interaction.guild)
    await interaction.response.send_message(
        f"✅ Current ticket category: **{category.name}**" if category else "❌ No ticket category found.",
        ephemeral=True,
    )


@bot.tree.command(name="setwelcome", description="Set this channel as welcome channel")
@app_commands.describe(message="Welcome message. Use {user}, {server}, {username}, {display_name}.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setwelcome(interaction: discord.Interaction, message: str = DEFAULT_WELCOME_MESSAGE) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["welcome_channel_id"] = interaction.channel.id
    config["welcome_message"] = message
    await save_server_settings()
    await interaction.response.send_message(f"✅ Welcome channel set to {interaction.channel.mention}.", ephemeral=True)


@bot.tree.command(name="setwallchannel", description="Set this channel as Wall of Knobs log channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setwallchannel(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["wall_channel_id"] = interaction.channel.id
    await save_server_settings()
    await interaction.response.send_message(f"✅ Wall channel set to {interaction.channel.mention}.", ephemeral=True)


@bot.tree.command(name="setleaveschannel", description="Set this channel as leaves / Board of Guilt channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setleaveschannel(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["leaves_channel_id"] = interaction.channel.id
    config["guilt_channel_id"] = interaction.channel.id
    await save_server_settings()
    await interaction.response.send_message(f"✅ Leaves / Board of Guilt channel set to {interaction.channel.mention}.", ephemeral=True)


@bot.tree.command(name="setgulitcategory", description="Set this channel as Board of Guilt/leaves channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setgulitcategory(interaction: discord.Interaction) -> None:
    await slash_setleaveschannel(interaction)


@bot.tree.command(name="setstaffrole", description="Set the only staff role for XSI")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setstaffrole(interaction: discord.Interaction, role: discord.Role) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["staff_role_ids"] = [role.id]
    await save_server_settings()
    await interaction.response.send_message(f"✅ Staff role set to {role.mention}.", ephemeral=True)


@bot.tree.command(name="addstaffrole", description="Add another staff role for tickets/mod bypass")
@app_commands.checks.has_permissions(administrator=True)
async def slash_addstaffrole(interaction: discord.Interaction, role: discord.Role) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    ids = config.setdefault("staff_role_ids", [])
    if role.id not in ids:
        ids.append(role.id)
    await save_server_settings()
    await interaction.response.send_message(f"✅ Added staff role {role.mention}.", ephemeral=True)


@bot.tree.command(name="removestaffrole", description="Remove a staff role from XSI")
@app_commands.checks.has_permissions(administrator=True)
async def slash_removestaffrole(interaction: discord.Interaction, role: discord.Role) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    ids = config.setdefault("staff_role_ids", [])
    if role.id in ids:
        ids.remove(role.id)
    await save_server_settings()
    await interaction.response.send_message(f"✅ Removed staff role {role.mention}.", ephemeral=True)


@bot.tree.command(name="setavailability", description="Set normal availability times for the ticket panel")
@app_commands.describe(start_time="Example: 9am", end_time="Example: 10pm")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setavailability(interaction: discord.Interaction, start_time: str, end_time: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    try:
        start_minutes = parse_time_to_minutes(start_time)
        end_minutes = parse_time_to_minutes(end_time)
    except ValueError as exc:
        await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["availability"] = {
        "timezone": DEFAULT_TIMEZONE,
        "start": format_minutes(start_minutes),
        "end": format_minutes(end_minutes),
        "enabled": True,
    }
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(interaction.guild)
    await interaction.response.send_message(
        f"✅ Availability set to {format_minutes(start_minutes)} to {format_minutes(end_minutes)} UK.",
        ephemeral=True,
    )


@bot.tree.command(name="clearavailability", description="Reset normal availability to 9am-10pm UK")
@app_commands.checks.has_permissions(administrator=True)
async def slash_clearavailability(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["availability"] = default_guild_config()["availability"]
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(interaction.guild)
    await interaction.response.send_message("✅ Availability reset to 9am to 10pm UK.", ephemeral=True)


@bot.tree.command(name="setunavailable", description="Set temporary unavailable time and update ticket panel")
@app_commands.describe(
    start_time="Example: 3pm",
    end_time="Example: 6pm",
    message="Message sent in tickets during unavailable time",
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_setunavailable(
    interaction: discord.Interaction,
    start_time: str,
    end_time: str,
    message: str = DEFAULT_UNAVAILABLE_MESSAGE,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    try:
        start_dt, end_dt = make_unavailable_window(config, start_time, end_time)
    except ValueError as exc:
        await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        return
    config["temporary_unavailable"] = {
        "start_iso": start_dt.isoformat(),
        "end_iso": end_dt.isoformat(),
        "message": message,
    }
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(interaction.guild)
    await interaction.response.send_message(
        f"✅ Temporary unavailable set from {format_dt(start_dt)} to {format_dt(end_dt)} UK. Ticket panel updated.",
        ephemeral=True,
    )


@bot.tree.command(name="clearunavailable", description="Clear temporary unavailable and refresh ticket panel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_clearunavailable(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["temporary_unavailable"] = None
    config["last_availability_status"] = None
    await save_server_settings()
    await send_or_update_ticket_panel(interaction.guild)
    await interaction.response.send_message("✅ Temporary unavailable cleared. Ticket panel refreshed.", ephemeral=True)


@bot.tree.command(name="availability", description="Show current XSI ticket availability")
async def slash_availability(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    state = get_availability_state(interaction.guild.id)
    await interaction.response.send_message(
        f"⏰ **{state['title']}** — {state['panel_line']}\n{state['message']}",
        ephemeral=True,
    )


@bot.tree.command(name="refreshticketpanel", description="Refresh the existing ticket panel message")
@app_commands.checks.has_permissions(administrator=True)
async def slash_refreshticketpanel(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    message = await send_or_update_ticket_panel(interaction.guild)
    await interaction.followup.send(
        "✅ Ticket panel refreshed." if message else "❌ Ticket panel channel is not set. Run `/setup` or `/tickets`.",
        ephemeral=True,
    )


@bot.tree.command(name="tickets", description="Post the ticket panel in this channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_tickets(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["ticket_panel_channel_id"] = interaction.channel.id
    await save_server_settings()
    await send_or_update_ticket_panel(interaction.guild, interaction.channel, force_new=True)
    await interaction.response.send_message("✅ Ticket panel posted.", ephemeral=True)


@bot.tree.command(name="tickets2", description="Post a basic ticket panel in this channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_tickets2(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    await interaction.channel.send(embed=ticket_panel_embed(interaction.guild.id, normal=False), view=Tickets2Button())
    await interaction.response.send_message("✅ Basic ticket panel posted.", ephemeral=True)


@bot.tree.command(name="claim", description="Claim the current ticket")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_claim(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
        return
    data = ticket_owners.get(str(interaction.channel.id))
    if not isinstance(data, dict):
        await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
        return
    data["claimed_by"] = interaction.user.id
    await save_ticket_owners()
    await interaction.response.send_message(f"✅ Ticket claimed by {interaction.user.mention}.")


@bot.tree.command(name="unclaim", description="Unclaim the current ticket")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_unclaim(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
        return
    data = ticket_owners.get(str(interaction.channel.id))
    if not isinstance(data, dict):
        await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
        return
    data["claimed_by"] = None
    await save_ticket_owners()
    await interaction.response.send_message("✅ Ticket unclaimed.")



@bot.tree.command(name="kick", description="Kick a member from this server")
@app_commands.describe(member="The member to kick", reason="The reason for the kick")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    ok, result = await kick_member_with_checks(interaction.guild, interaction.user, member, reason)
    await interaction.followup.send(
        result,
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


@bot.tree.command(name="warn", description="Manually warn a member")
@app_commands.describe(member="The member to warn", reason="The reason for the warning")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    warning_count = await add_warning(interaction.guild.id, member.id)
    await send_wall_log(member, reason, "Manual warning", "Manual slash warning", warning_count, interaction.user)
    await interaction.response.send_message(
        f"⚠️ {member.mention} has been warned by {interaction.user.mention}.\nReason: {reason}\nWarnings: {warning_count}/{MAX_WARNINGS}"
    )
    if warning_count >= MAX_WARNINGS:
        await punish_if_needed(interaction.guild, interaction.channel, member, reason, warning_count)


@bot.tree.command(name="warnings", description="Show a member's warnings")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_warnings(interaction: discord.Interaction, member: discord.Member | None = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    member = member or interaction.user
    count = get_warnings(interaction.guild.id, member.id)
    await interaction.response.send_message(f"⚠️ {member.mention} has {count}/{MAX_WARNINGS} warnings.")


@bot.tree.command(name="clearwarnings", description="Clear a member's warnings")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_clearwarnings(interaction: discord.Interaction, member: discord.Member) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await clear_warnings_for(interaction.guild.id, member.id)
    await interaction.response.send_message(f"✅ Cleared warnings for {member.mention}.")


@bot.tree.command(name="knobstatus", description="Show moderation status")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_knobstatus(interaction: discord.Interaction) -> None:
    banned_list = "\n".join(f"- {phrase}" for phrase in BANNED_PHRASES)
    embed = discord.Embed(
        title="🔨 Knob Bot Status",
        description=(
            "Knob moderation is active.\n\n"
            f"Punishment: {PUNISHMENT_ON_MAX_WARNINGS.title()} after {MAX_WARNINGS} warnings\n"
            "Bad messages are automatically deleted.\n\n"
            "Banned phrases:\n"
            f"{banned_list[:3500]}"
        ),
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="manualwall", description="Manually add someone to Wall of Knobs")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_manualwall(interaction: discord.Interaction, member: discord.Member, offence: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    warning_count = await add_warning(interaction.guild.id, member.id)
    await send_wall_log(member, offence, "Manual warning", "Manual staff report", warning_count, interaction.user)
    await interaction.response.send_message(f"🧱 Added {member.mention} to the Wall of Knobs.")


@bot.tree.command(name="testguilt", description="Test the Board of Guilt")
@app_commands.checks.has_permissions(administrator=True)
async def slash_testguilt(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("⚖️ Board of Guilt is alive. Nobody is safe.")


@bot.tree.command(name="addsmartmessage", description="Add a smart auto reply")
@app_commands.describe(trigger="Word/phrase to detect", response="Reply. Use {user}, {server}, {username}, {display_name}.")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_addsmartmessage(interaction: discord.Interaction, trigger: str, response: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    async with smart_lock:
        rules = get_guild_smart_messages(interaction.guild.id)
        rules[trigger.lower()] = {"response": response, "cooldown": SMART_MESSAGE_COOLDOWN}
        await save_smart_messages()
    await interaction.response.send_message(f"✅ Smart message added for `{trigger}`.", ephemeral=True)


@bot.tree.command(name="removesmartmessage", description="Remove a smart auto reply")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_removesmartmessage(interaction: discord.Interaction, trigger: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    async with smart_lock:
        rules = get_guild_smart_messages(interaction.guild.id)
        rules.pop(trigger.lower(), None)
        await save_smart_messages()
    await interaction.response.send_message(f"✅ Smart message removed for `{trigger}`.", ephemeral=True)


@bot.tree.command(name="listsmartmessages", description="List smart auto replies")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_listsmartmessages(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    rules = get_guild_smart_messages(interaction.guild.id)
    if not rules:
        await interaction.response.send_message("No smart messages set.", ephemeral=True)
        return
    lines = [f"`{trigger}` → {str(data.get('response', ''))[:80]}" for trigger, data in rules.items() if isinstance(data, dict)]
    await interaction.response.send_message("🧠 Smart messages:\n" + "\n".join(lines)[:1800], ephemeral=True)


@bot.tree.command(name="clearsmartmessages", description="Remove all smart messages in this server")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_clearsmartmessages(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    async with smart_lock:
        smart_messages[str(interaction.guild.id)] = {}
        await save_smart_messages()
    await interaction.response.send_message("✅ Removed all smart messages in this server.", ephemeral=True)


@bot.tree.command(name="sallyspeak", description="Make XSI say a message")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_sallyspeak(interaction: discord.Interaction, message: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    await interaction.channel.send(message)
    await interaction.response.send_message("✅ Sent.", ephemeral=True)


@bot.tree.command(name="embed", description="Send a simple embed")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_embed(interaction: discord.Interaction, title: str, description: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    embed = discord.Embed(title=title, description=description, color=discord.Color.purple())
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Embed sent.", ephemeral=True)


@bot.tree.command(name="rules", description="Post server rules embed")
async def slash_rules(interaction: discord.Interaction) -> None:
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
            "8. No money services or boosts."
        ),
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="slotinfo", description="Show Sloty removal notice")
async def slash_slotinfo(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("❌ Sloty has been removed from this bot.")


@bot.tree.command(name="giveaway", description="Start a 24 hour giveaway")
@app_commands.describe(prize_type="Normal, Hard Trade, or Very Hard Trade")
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveaway(interaction: discord.Interaction, amount: int, prize_type: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    result = await start_giveaway_in_channel(interaction.channel, amount, prize_type, GIVEAWAY_TIME)
    await interaction.response.send_message(result, ephemeral=True)


@bot.tree.command(name="testgiveaway", description="Start a 30 second test giveaway")
@app_commands.describe(prize_type="Normal, Hard Trade, or Very Hard Trade")
@app_commands.checks.has_permissions(administrator=True)
async def slash_testgiveaway(interaction: discord.Interaction, amount: int, prize_type: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    result = await start_giveaway_in_channel(interaction.channel, amount, prize_type, TEST_GIVEAWAY_TIME, test=True)
    await interaction.response.send_message(result, ephemeral=True)


# ============================================================
# REQUIRED PERMISSIONS EMBED
# ============================================================
def build_required_permissions_embed(guild: discord.Guild) -> discord.Embed:
    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    perms = bot_member.guild_permissions if bot_member else discord.Permissions.none()

    checks = [
        ("View Channels", perms.view_channel, "see setup/ticket/log channels"),
        ("Send Messages", perms.send_messages, "send replies, welcomes, panels, and logs"),
        ("Read Message History", perms.read_message_history, "read ticket/giveaway messages"),
        ("Manage Channels", perms.manage_channels, "create setup categories and ticket channels"),
        ("Manage Messages", perms.manage_messages, "delete banned messages and clean commands"),
        ("Embed Links", perms.embed_links, "send ticket, setup, warning, and log embeds"),
        ("Add Reactions", perms.add_reactions, "add the giveaway reaction"),
        ("Kick Members", perms.kick_members, "kick users after max warnings and use manual /kick"),
        ("Ban Members", perms.ban_members, "only needed if punishment mode is ban"),
    ]
    optional = [
        ("Manage Roles", perms.manage_roles, "only needed later for autoroles/reaction roles"),
    ]

    def line(name: str, ok: bool, desc: str) -> str:
        return f"{'✅' if ok else '❌'} **{name}** — {desc}"

    embed = discord.Embed(
        title="🔐 XSI Required Permissions",
        description="Use this to check whether XSI can run setup, tickets, welcomes, logs, giveaways, and moderation correctly.",
        color=discord.Color.green() if all(ok for _, ok, _ in checks) else discord.Color.orange(),
    )
    embed.add_field(name="Required Bot Permissions", value="\n".join(line(*item) for item in checks)[:1024], inline=False)
    embed.add_field(name="Optional / Future Permissions", value="\n".join(line(*item) for item in optional)[:1024], inline=False)

    if bot_member:
        hierarchy = "✅ Bot role is available."
        if guild.owner_id and bot_member.top_role <= guild.default_role:
            hierarchy = "⚠️ Bot role looks low. Move XSI's role higher for moderation."
        embed.add_field(name="Role Hierarchy", value=hierarchy, inline=False)

    app_id = bot.user.id if bot.user else 0
    perms_value = discord.Permissions(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        manage_channels=True,
        manage_messages=True,
        embed_links=True,
        add_reactions=True,
        kick_members=True,
        ban_members=True,
    ).value
    invite = f"https://discord.com/oauth2/authorize?client_id={app_id}&permissions={perms_value}&scope=bot%20applications.commands"
    embed.add_field(name="Invite / Reinvite", value=f"Use an invite with `bot` and `applications.commands` scopes.\n{invite}", inline=False)
    embed.set_footer(text="Also enable Message Content Intent and Server Members Intent in the Discord Developer Portal.")
    return embed


# ============================================================
# ERROR HANDLERS
# ============================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You do not have permission to use that command."
    else:
        log.exception("Slash command error: %s", error)
        message = "❌ Something went wrong. Check Railway logs."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


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
    if isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ I could not find that role.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Missing info. Examples:\n"
            "`!setup`\n"
            "`!setup no giveaways`\n"
            "`!clearsetup keep`\n"
            "`!clearsetup delete_created YES`\n"
            "`!setunavailable 3pm 6pm I am unavailable right now.`\n"
            "`!refreshticketpanel`\n"
            "`!warn @user reason`\n"
            "`!kick @user reason`"
        )
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad command format. Check the number/user/role/time you typed.")
        return
    if isinstance(error, commands.CommandInvokeError):
        log.exception("Command failed: %s", error.original)
    else:
        log.exception("Command error: %s", error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ============================================================
# RUN BOT
# ============================================================
def main() -> None:
    token = os.getenv(TOKEN_NAME)
    if not token:
        log.error("❌ %s not found in Railway variables.", TOKEN_NAME)
        return
    bot.run(token)


if __name__ == "__main__":
    main()
