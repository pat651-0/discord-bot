from __future__ import annotations

import asyncio
import io
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

VERSION = "XSI full setup build 2026-06-21 / giveaway-duration-controls-ticketusers"
BUILD_TAG = "XSI-FORCE-48-GIVEAWAY-DURATION-CONTROLS-TICKETUSERS"

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
TICKET_RECORDS_FILE = DATA_DIR / "xsi_ticket_records.json"
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
MAX_GIVEAWAY_WINNERS = 25
MIN_GIVEAWAY_SECONDS = 10
MAX_GIVEAWAY_SECONDS = 30 * 24 * 60 * 60
RECORD_CHANNEL_DELETE_AFTER = 60 * 60
MAX_RECORD_SELECT_OPTIONS = 25
MAX_RECORD_PREVIEW_CHUNKS = 20

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
ticket_records: dict[str, Any] = load_json(TICKET_RECORDS_FILE, {})
smart_messages: dict[str, Any] = load_json(SMART_MESSAGES_FILE, {})
active_giveaways: dict[str, Any] = load_json(GIVEAWAYS_FILE, {})

settings_lock = asyncio.Lock()
warnings_lock = asyncio.Lock()
tickets_lock = asyncio.Lock()
record_lock = asyncio.Lock()
smart_lock = asyncio.Lock()
giveaway_lock = asyncio.Lock()


async def save_server_settings() -> None:
    save_json(SERVER_SETTINGS_FILE, server_settings)


async def save_warnings() -> None:
    save_json(WARNINGS_FILE, warnings_store)


async def save_ticket_owners() -> None:
    save_json(TICKET_OWNERS_FILE, ticket_owners)


async def save_ticket_records() -> None:
    save_json(TICKET_RECORDS_FILE, ticket_records)


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
        self.add_view(RecordCloseButton())
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
        "record_category_id": None,
        "record_channel_id": None,
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



def parse_xsikick_reason(raw_reason: str | None) -> tuple[bool, str]:
    """Return (test_mode, reason) for prefix commands.

    Supported prefix examples:
    !xsikick @user being rude
    !xsikick @user --test being rude
    !xsikick @user test being rude
    !xsikick @user being rude --test
    """
    reason = (raw_reason or "").strip()
    if not reason:
        return False, "No reason provided."

    test_markers = {"--test", "test", "testmode", "test-mode", "dryrun", "dry-run", "simulate", "simulation"}
    words = reason.split()
    test_mode = False

    while words and words[0].lower() in test_markers:
        test_mode = True
        words.pop(0)

    while words and words[-1].lower() in test_markers:
        test_mode = True
        words.pop()

    clean_reason = " ".join(words).strip() or "No reason provided."
    return test_mode, clean_reason


async def send_xsikick_log(
    guild: discord.Guild,
    member: discord.Member,
    moderator: discord.Member | discord.User,
    reason: str,
    test_mode: bool,
    result: str,
) -> None:
    config = guild_config(guild.id)
    channel = await get_text_channel(guild, config.get("staff_log_channel_id"))
    if channel is None:
        return

    embed = discord.Embed(
        title="🧪 XSI Kick Test" if test_mode else "👢 XSI Kick",
        description="No one was kicked. This was a test run." if test_mode else "A member was kicked with XSI.",
        color=discord.Color.orange() if test_mode else discord.Color.red(),
        timestamp=datetime.now(UK_TIMEZONE),
    )
    embed.add_field(name="Target", value=f"{member.mention}\n`{member}`\nID: `{member.id}`", inline=False)
    embed.add_field(name="Moderator", value=f"{moderator.mention}\n`{moderator}`\nID: `{moderator.id}`", inline=False)
    embed.add_field(name="Reason", value=discord.utils.escape_markdown(reason[:1000]), inline=False)
    embed.add_field(name="Result", value=result[:1000], inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        pass


async def run_xsikick(
    guild: discord.Guild,
    member: discord.Member,
    moderator: discord.Member | discord.User,
    reason: str,
    *,
    test_mode: bool = False,
) -> tuple[bool, str]:
    reason = (reason or "").strip() or "No reason provided."
    if len(reason) > 900:
        reason = reason[:897] + "..."

    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    if bot_member is None:
        return False, "❌ I could not check my role hierarchy."

    if member.id == guild.owner_id:
        return False, "❌ I cannot kick the server owner."

    if member.id == moderator.id:
        return False, "❌ You cannot kick yourself with this command."

    if member.id == bot_member.id:
        return False, "❌ I cannot kick myself."

    if member.guild_permissions.administrator:
        return False, f"❌ I will not kick {member.mention} because they are an administrator."

    if not bot_member.guild_permissions.kick_members:
        return False, "❌ I need the Kick Members permission."

    if bot_member.top_role <= member.top_role:
        return False, f"❌ I cannot kick {member.mention} because my role is not high enough."

    if isinstance(moderator, discord.Member) and moderator.id != guild.owner_id:
        if moderator.top_role <= member.top_role:
            return False, f"❌ You cannot kick {member.mention} because their role is equal to or higher than yours."

    action_name = "would be kicked" if test_mode else "was kicked"
    audit_reason = f"XSI kick by {moderator} ({moderator.id}): {reason}"[:512]

    if test_mode:
        result = f"🧪 TEST MODE: {member.mention} {action_name}. No action was taken."
        await send_xsikick_log(guild, member, moderator, reason, True, result)
        return True, f"{result}\nReason: {reason}"

    dm_status = "DM sent."
    try:
        await member.send(f"🔨 You were kicked from {guild.name}.\nReason: {reason}")
    except discord.HTTPException:
        dm_status = "Could not DM the member."

    try:
        await member.kick(reason=audit_reason)
    except discord.Forbidden:
        return False, f"❌ I do not have permission to kick {member.mention}. Check my role and Kick Members permission."
    except discord.HTTPException as exc:
        log.exception("XSI kick failed: %s", exc)
        return False, "❌ Discord rejected the kick. Check Railway logs."

    result = f"✅ {member.mention} {action_name} by {moderator.mention}. {dm_status}"
    await send_xsikick_log(guild, member, moderator, reason, False, result)
    return True, f"{result}\nReason: {reason}"


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


# ============================================================
# TICKET RECORD HELPERS
# ============================================================
def _record_bucket(guild_id: int) -> dict[str, Any]:
    gid = str(guild_id)
    bucket = ticket_records.get(gid)
    if not isinstance(bucket, dict):
        bucket = {}
        ticket_records[gid] = bucket

    if not isinstance(bucket.get("records"), dict):
        bucket["records"] = {}
    if not isinstance(bucket.get("by_channel"), dict):
        bucket["by_channel"] = {}
    try:
        next_id = int(bucket.get("next_id", 1))
    except (TypeError, ValueError):
        next_id = 1
    if next_id < 1:
        next_id = 1
    bucket["next_id"] = next_id
    return bucket


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _record_datetime_text(timestamp: Any) -> str:
    value = _safe_int(timestamp, 0)
    if value <= 0:
        return "Unknown"
    return datetime.fromtimestamp(value, UK_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")


def _record_short_time(timestamp: Any) -> str:
    value = _safe_int(timestamp, 0)
    if value <= 0:
        return "Unknown time"
    return datetime.fromtimestamp(value, UK_TIMEZONE).strftime("%d %b %H:%M")


def _record_user_text(user_id: Any, fallback: str = "Unknown") -> str:
    uid = _safe_int(user_id, 0)
    if uid <= 0:
        return fallback
    return f"{fallback} ({uid})" if fallback and fallback != str(uid) else str(uid)


def _record_copy(guild_id: int, record_id: str) -> dict[str, Any] | None:
    bucket = _record_bucket(guild_id)
    record = bucket["records"].get(str(record_id))
    if not isinstance(record, dict):
        return None
    # JSON round trip gives us a cheap isolated copy for rendering outside the lock.
    return json.loads(json.dumps(record))


def _new_record_id(bucket: dict[str, Any]) -> str:
    records = bucket.setdefault("records", {})
    next_id = _safe_int(bucket.get("next_id"), 1)
    while str(next_id) in records:
        next_id += 1
    bucket["next_id"] = next_id + 1
    return str(next_id)


def _append_record_event_unlocked(
    record: dict[str, Any],
    event_type: str,
    text: str,
    *,
    actor: discord.Member | discord.User | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    events = record.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        record["events"] = events

    event = {
        "time": int(time.time()),
        "type": event_type,
        "text": text,
    }
    if actor is not None:
        event["actor_id"] = actor.id
        event["actor_name"] = str(actor)
    if extra:
        event.update(extra)
    events.append(event)


async def create_ticket_record(channel: discord.TextChannel, owner: discord.Member | discord.User, auto_messages: bool) -> str:
    async with record_lock:
        bucket = _record_bucket(channel.guild.id)
        record_id = _new_record_id(bucket)
        record = {
            "record_id": record_id,
            "guild_id": channel.guild.id,
            "channel_id": channel.id,
            "channel_name": channel.name,
            "owner_id": owner.id,
            "owner_name": str(owner),
            "created_at": int(time.time()),
            "closed_at": None,
            "closed_by_id": None,
            "closed_by_name": None,
            "close_reason": None,
            "status": "open",
            "auto_messages": bool(auto_messages),
            "claimed_by": None,
            "messages": [],
            "events": [],
        }
        _append_record_event_unlocked(
            record,
            "ticket_opened",
            f"Ticket opened by {owner}.",
            actor=owner,
            extra={"channel_id": channel.id, "channel_name": channel.name},
        )
        bucket["records"][record_id] = record
        bucket["by_channel"][str(channel.id)] = record_id
        await save_ticket_records()
        return record_id


async def get_or_create_ticket_record_for_channel(channel: discord.TextChannel, data: dict[str, Any]) -> str:
    guild_id = channel.guild.id
    record_id = str(data.get("record_id") or "")

    async with record_lock:
        bucket = _record_bucket(guild_id)
        if record_id and isinstance(bucket["records"].get(record_id), dict):
            bucket["by_channel"][str(channel.id)] = record_id
            await save_ticket_records()
            return record_id

        mapped_id = str(bucket["by_channel"].get(str(channel.id)) or "")
        if mapped_id and isinstance(bucket["records"].get(mapped_id), dict):
            data["record_id"] = mapped_id
            ticket_owners[str(channel.id)] = data
            await save_ticket_records()
            await save_ticket_owners()
            return mapped_id

        owner_id = _safe_int(data.get("owner_id"), 0)
        owner = channel.guild.get_member(owner_id)
        owner_name = str(owner) if owner is not None else str(owner_id or "Unknown")
        created_at = _safe_int(data.get("created_at"), int(time.time()))
        new_id = _new_record_id(bucket)
        record = {
            "record_id": new_id,
            "guild_id": guild_id,
            "channel_id": channel.id,
            "channel_name": channel.name,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "created_at": created_at,
            "closed_at": None,
            "closed_by_id": None,
            "closed_by_name": None,
            "close_reason": None,
            "status": "open",
            "auto_messages": bool(data.get("auto_messages", False)),
            "claimed_by": data.get("claimed_by"),
            "messages": [],
            "events": [],
        }
        _append_record_event_unlocked(
            record,
            "record_started",
            "Record tracking started for this existing active ticket.",
            extra={"channel_id": channel.id, "channel_name": channel.name},
        )
        bucket["records"][new_id] = record
        bucket["by_channel"][str(channel.id)] = new_id
        data["record_id"] = new_id
        ticket_owners[str(channel.id)] = data
        await save_ticket_records()
        await save_ticket_owners()
        return new_id


async def append_ticket_record_event(
    guild_id: int,
    record_id: str,
    event_type: str,
    text: str,
    *,
    actor: discord.Member | discord.User | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    async with record_lock:
        bucket = _record_bucket(guild_id)
        record = bucket["records"].get(str(record_id))
        if not isinstance(record, dict):
            return
        _append_record_event_unlocked(record, event_type, text, actor=actor, extra=extra)
        await save_ticket_records()


async def append_ticket_record_event_for_channel(
    channel: discord.TextChannel,
    data: dict[str, Any],
    event_type: str,
    text: str,
    *,
    actor: discord.Member | discord.User | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    record_id = await get_or_create_ticket_record_for_channel(channel, data)
    await append_ticket_record_event(channel.guild.id, record_id, event_type, text, actor=actor, extra=extra)


async def append_ticket_record_message(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel) or message.guild is None:
        return

    data = ticket_owners.get(str(message.channel.id))
    if not isinstance(data, dict):
        return

    record_id = await get_or_create_ticket_record_for_channel(message.channel, data)
    attachments = [
        {
            "filename": attachment.filename,
            "url": attachment.url,
            "size": attachment.size,
        }
        for attachment in message.attachments
    ]

    async with record_lock:
        bucket = _record_bucket(message.guild.id)
        record = bucket["records"].get(record_id)
        if not isinstance(record, dict):
            return
        messages = record.setdefault("messages", [])
        if not isinstance(messages, list):
            messages = []
            record["messages"] = messages
        messages.append(
            {
                "time": int(message.created_at.timestamp()) if message.created_at else int(time.time()),
                "message_id": message.id,
                "author_id": message.author.id,
                "author_name": str(message.author),
                "content": message.content or "",
                "attachments": attachments,
                "jump_url": message.jump_url,
            }
        )
        await save_ticket_records()


async def mark_ticket_record_closed(
    channel: discord.TextChannel,
    data: dict[str, Any],
    closer: discord.Member | discord.User,
    reason: str = "Closed with ticket button.",
) -> None:
    record_id = await get_or_create_ticket_record_for_channel(channel, data)
    async with record_lock:
        bucket = _record_bucket(channel.guild.id)
        record = bucket["records"].get(record_id)
        if not isinstance(record, dict):
            return
        now = int(time.time())
        record["status"] = "closed"
        record["closed_at"] = now
        record["closed_by_id"] = closer.id
        record["closed_by_name"] = str(closer)
        record["close_reason"] = reason
        record["claimed_by"] = data.get("claimed_by")
        _append_record_event_unlocked(
            record,
            "ticket_closed",
            f"Ticket closed by {closer}. Reason: {reason}",
            actor=closer,
            extra={"channel_id": channel.id, "channel_name": channel.name},
        )
        await save_ticket_records()


async def ensure_active_records_for_member(guild: discord.Guild, member: discord.Member | discord.User) -> None:
    for channel_id, data in list(ticket_owners.items()):
        if not isinstance(data, dict):
            continue
        if _safe_int(data.get("guild_id"), 0) != guild.id:
            continue
        if _safe_int(data.get("owner_id"), 0) != member.id:
            continue
        channel = guild.get_channel(_safe_int(channel_id, 0))
        if isinstance(channel, discord.TextChannel):
            await get_or_create_ticket_record_for_channel(channel, data)


def find_ticket_records_for_member(guild_id: int, user_id: int) -> list[dict[str, Any]]:
    bucket = _record_bucket(guild_id)
    records = []
    for record in bucket["records"].values():
        if not isinstance(record, dict):
            continue
        if _safe_int(record.get("owner_id"), 0) == user_id:
            records.append(record)
    records.sort(key=lambda item: _safe_int(item.get("created_at"), 0), reverse=True)
    return records


def build_ticket_record_transcript(record: dict[str, Any]) -> str:
    lines: list[str] = []
    owner_text = _record_user_text(record.get("owner_id"), str(record.get("owner_name") or "Unknown"))
    lines.append(f"XSI Ticket Record #{record.get('record_id', 'Unknown')}")
    lines.append("=" * 60)
    lines.append(f"Owner: {owner_text}")
    lines.append(f"Status: {str(record.get('status') or 'unknown').title()}")
    lines.append(f"Original Channel: #{record.get('channel_name', 'unknown')} ({record.get('channel_id', 'unknown')})")
    lines.append(f"Created: {_record_datetime_text(record.get('created_at'))}")
    if record.get("closed_at"):
        closer_text = _record_user_text(record.get("closed_by_id"), str(record.get("closed_by_name") or "Unknown"))
        lines.append(f"Closed: {_record_datetime_text(record.get('closed_at'))}")
        lines.append(f"Closed By: {closer_text}")
        lines.append(f"Close Reason: {record.get('close_reason') or 'No reason stored'}")
    if record.get("claimed_by"):
        lines.append(f"Claimed By ID: {record.get('claimed_by')}")
    lines.append("")
    lines.append("Timeline")
    lines.append("-" * 60)

    timeline: list[tuple[int, int, str]] = []
    for index, event in enumerate(record.get("events") or []):
        if not isinstance(event, dict):
            continue
        ts = _safe_int(event.get("time"), 0)
        text = str(event.get("text") or event.get("type") or "Event")
        actor = event.get("actor_name")
        actor_id = event.get("actor_id")
        if actor:
            text += f" [actor: {actor} ({actor_id})]"
        timeline.append((ts, index, f"[{_record_datetime_text(ts)}] EVENT: {text}"))

    offset = len(timeline) + 1
    for index, message in enumerate(record.get("messages") or []):
        if not isinstance(message, dict):
            continue
        ts = _safe_int(message.get("time"), 0)
        author = str(message.get("author_name") or "Unknown")
        author_id = message.get("author_id")
        content = str(message.get("content") or "").replace("\r", "")
        if not content:
            content = "[No text content]"
        entry_lines = [f"[{_record_datetime_text(ts)}] MESSAGE: {author} ({author_id})", content]
        attachments = message.get("attachments") or []
        if attachments:
            entry_lines.append("Attachments:")
            for attachment in attachments:
                if isinstance(attachment, dict):
                    entry_lines.append(f"- {attachment.get('filename', 'attachment')}: {attachment.get('url', '')}")
        if message.get("jump_url"):
            entry_lines.append(f"Jump URL: {message.get('jump_url')}")
        timeline.append((ts, offset + index, "\n".join(entry_lines)))

    if not timeline:
        lines.append("No events or messages were recorded.")
    else:
        for _, _, line in sorted(timeline, key=lambda item: (item[0], item[1])):
            lines.append(line)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def split_record_text(text: str, limit: int = 1800) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        addition = len(line) + 1
        if current and current_len + addition > limit:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        if addition > limit:
            while line:
                chunks.append(line[:limit])
                line = line[limit:]
            continue
        current.append(line)
        current_len += addition
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def safe_code_block(text: str) -> str:
    return text.replace("```", "`\u200b``")


def get_record_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    config = guild_config(guild.id)
    category_id = config.get("record_category_id")
    if not category_id:
        return None
    category = guild.get_channel(_safe_int(category_id, 0))
    return category if isinstance(category, discord.CategoryChannel) else None


def get_record_channel(guild: discord.Guild) -> discord.TextChannel | None:
    config = guild_config(guild.id)
    channel_id = config.get("record_channel_id")
    if not channel_id:
        return None
    channel = guild.get_channel(_safe_int(channel_id, 0))
    return channel if isinstance(channel, discord.TextChannel) else None


async def delete_record_channel_later(guild_id: int, channel_id: int, seconds: int = RECORD_CHANNEL_DELETE_AFTER) -> None:
    await asyncio.sleep(seconds)
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    channel = guild.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel) and channel.name.startswith("record-"):
        try:
            await channel.delete(reason="XSI record channel expired")
        except discord.HTTPException:
            pass


async def create_record_review_channel(
    guild: discord.Guild,
    requester: discord.Member | discord.User,
    record: dict[str, Any],
) -> discord.TextChannel | None:
    bot_member = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }
    if isinstance(requester, discord.Member):
        overwrites[requester] = discord.PermissionOverwrite(
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
            attach_files=True,
        )
    for role in staff_role_objects(guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        )

    owner_name = str(record.get("owner_name") or record.get("owner_id") or "user")
    record_id = str(record.get("record_id") or "unknown")
    channel_name = f"record-{clean_channel_name(owner_name)}-{record_id}"[:90]
    category = get_record_category(guild)

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"XSI ticket record opened by {requester} ({requester.id})",
        )
    except discord.HTTPException:
        return None

    record_log_channel = get_record_channel(guild)
    if record_log_channel is not None and record_log_channel.id != channel.id:
        owner_for_log = f"<@{record.get('owner_id')}>" if _safe_int(record.get("owner_id"), 0) else str(record.get("owner_name") or "Unknown")
        try:
            await record_log_channel.send(
                f"📁 Ticket record opened by {requester.mention} for {owner_for_log}: {channel.mention}",
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except discord.HTTPException:
            pass

    owner_text = f"<@{record.get('owner_id')}>" if _safe_int(record.get("owner_id"), 0) else str(record.get("owner_name") or "Unknown")
    transcript = build_ticket_record_transcript(record)
    transcript_file = discord.File(
        fp=io.BytesIO(transcript.encode("utf-8")),
        filename=f"xsi-ticket-record-{record_id}.txt",
    )
    embed = discord.Embed(
        title=f"📁 Ticket Record #{record_id}",
        description=(
            f"Owner: {owner_text}\n"
            f"Status: **{str(record.get('status') or 'unknown').title()}**\n"
            f"Created: `{_record_datetime_text(record.get('created_at'))}`\n"
            f"Original Channel: `#{record.get('channel_name', 'unknown')}`\n\n"
            "Use the button below when finished. This temporary record channel also auto-deletes after 1 hour."
        ),
        color=discord.Color.blurple(),
    )
    if record.get("closed_at"):
        embed.add_field(name="Closed", value=_record_datetime_text(record.get("closed_at")), inline=True)
        embed.add_field(name="Closed By", value=str(record.get("closed_by_name") or record.get("closed_by_id") or "Unknown"), inline=True)
        embed.add_field(name="Reason", value=str(record.get("close_reason") or "No reason stored")[:1024], inline=False)
    await channel.send(embed=embed, view=RecordCloseButton(), allowed_mentions=discord.AllowedMentions.none())
    await channel.send("📄 Full record transcript:", file=transcript_file)

    chunks = split_record_text(transcript)
    for index, chunk in enumerate(chunks[:MAX_RECORD_PREVIEW_CHUNKS], start=1):
        await channel.send(f"```txt\n{safe_code_block(chunk)}\n```")
    if len(chunks) > MAX_RECORD_PREVIEW_CHUNKS:
        await channel.send("⚠️ Preview stopped because the record is long. The attached `.txt` file contains the full record.")

    asyncio.create_task(delete_record_channel_later(guild.id, channel.id))
    return channel


async def send_record_picker_response(
    interaction: discord.Interaction,
    member: discord.Member,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    await ensure_active_records_for_member(interaction.guild, member)
    records = find_ticket_records_for_member(interaction.guild.id, member.id)
    if not records:
        await interaction.response.send_message(
            f"❌ No ticket records found for {member.mention}. Records are saved for tickets created or active after this update.",
            ephemeral=True,
        )
        return
    view = RecordPickerView(interaction.user.id, records[:MAX_RECORD_SELECT_OPTIONS])
    extra = "" if len(records) <= MAX_RECORD_SELECT_OPTIONS else f"\nShowing newest {MAX_RECORD_SELECT_OPTIONS} records only."
    await interaction.response.send_message(
        f"📁 Pick which ticket record you want to open for {member.mention}.{extra}",
        view=view,
        ephemeral=True,
    )


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

    record_id = await create_ticket_record(channel, user, auto_messages)

    async with tickets_lock:
        ticket_owners[str(channel.id)] = {
            "guild_id": guild.id,
            "owner_id": user.id,
            "last_dm_time": 0,
            "last_away_reply_time": 0,
            "auto_messages": auto_messages,
            "created_at": int(time.time()),
            "claimed_by": None,
            "record_id": record_id,
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
        await append_ticket_record_event_for_channel(
            message.channel,
            data,
            "owner_dm_sent",
            f"Ticket owner was DMed because {message.author} replied.",
            actor=message.author,
        )
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
    await append_ticket_record_event_for_channel(
        message.channel,
        data,
        "away_reply_sent",
        "Unavailable auto-reply was sent in the ticket.",
        actor=bot.user,
    )
    asyncio.create_task(delete_message_later(away_msg, AWAY_AUTO_REPLY_DELETE_AFTER))


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

        await mark_ticket_record_closed(interaction.channel, data, interaction.user)
        ticket_owners.pop(channel_id, None)
        await save_ticket_owners()
        await interaction.response.send_message("Closing ticket and saving record...", ephemeral=True)
        await asyncio.sleep(2)

        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user} ({interaction.user.id})")
        except discord.HTTPException as exc:
            log.warning("Failed to delete ticket channel %s: %s", interaction.channel.id, exc)


class RecordCloseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Record", style=discord.ButtonStyle.red, custom_id="xsi_close_record_channel")
    async def close_record(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ This button only works inside a record channel.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
            return
        if not interaction.channel.name.startswith("record-"):
            await interaction.response.send_message("❌ This does not look like an XSI record channel.", ephemeral=True)
            return
        if not is_staff_or_mod(interaction.user):
            await interaction.response.send_message("❌ Only staff can close record channels.", ephemeral=True)
            return
        await interaction.response.send_message("🧹 Deleting this record channel...", ephemeral=True)
        record_log_channel = get_record_channel(interaction.guild)
        if record_log_channel is not None and record_log_channel.id != interaction.channel.id:
            try:
                await record_log_channel.send(
                    f"🧹 Ticket record channel closed by {interaction.user.mention}: `#{interaction.channel.name}`",
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                )
            except discord.HTTPException:
                pass
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete(reason=f"XSI record channel closed by {interaction.user} ({interaction.user.id})")
        except discord.HTTPException:
            pass


class RecordTicketSelect(discord.ui.Select):
    def __init__(self, records: list[dict[str, Any]]) -> None:
        options: list[discord.SelectOption] = []
        for record in records[:MAX_RECORD_SELECT_OPTIONS]:
            record_id = str(record.get("record_id") or "unknown")
            channel_name = str(record.get("channel_name") or "ticket")
            status = str(record.get("status") or "unknown").title()
            msg_count = len(record.get("messages") or [])
            label = f"#{record_id} {channel_name}"[:100]
            description = f"{status} • {_record_short_time(record.get('created_at'))} • {msg_count} messages"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=record_id))
        if not options:
            options.append(discord.SelectOption(label="No records found", value="none", description="No ticket records are available"))
        super().__init__(placeholder="Pick a ticket record to open...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        parent = self.view
        if not isinstance(parent, RecordPickerView):
            await interaction.response.send_message("❌ This menu expired. Run `/record` again.", ephemeral=True)
            return
        if interaction.user.id != parent.requester_id:
            await interaction.response.send_message("❌ This record menu was not opened for you.", ephemeral=True)
            return
        record_id = self.values[0]
        if record_id == "none" or interaction.guild is None:
            await interaction.response.send_message("❌ No record selected.", ephemeral=True)
            return
        record = _record_copy(interaction.guild.id, record_id)
        if record is None:
            await interaction.response.send_message("❌ That record could not be found anymore.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = await create_record_review_channel(interaction.guild, interaction.user, record)
        if channel is None:
            await interaction.followup.send("❌ I could not create the record channel. Check Manage Channels permissions.", ephemeral=True)
            return
        await interaction.followup.send(f"✅ Record opened: {channel.mention}", ephemeral=True)


class RecordPickerView(discord.ui.View):
    def __init__(self, requester_id: int, records: list[dict[str, Any]]) -> None:
        super().__init__(timeout=180)
        self.requester_id = requester_id
        self.add_item(RecordTicketSelect(records))


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
DURATION_PATTERN = re.compile(
    r"^(?P<amount>\d+)\s*(?P<unit>s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$",
    flags=re.IGNORECASE,
)


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


def parse_duration_to_seconds(raw_duration: str | None, default_seconds: int = GIVEAWAY_TIME) -> int:
    if raw_duration is None:
        return default_seconds

    text = str(raw_duration).strip().lower()
    if not text:
        return default_seconds

    text = text.replace("duration:", "").replace("time:", "").strip()
    text = re.sub(r"\s+", " ", text)
    match = DURATION_PATTERN.fullmatch(text)
    if not match:
        raise ValueError("Use a duration like 30s, 10m, 2h, or 1d.")

    amount = int(match.group("amount"))
    unit = match.group("unit").lower()
    if unit.startswith("s"):
        seconds = amount
    elif unit.startswith("m"):
        seconds = amount * 60
    elif unit.startswith("h"):
        seconds = amount * 60 * 60
    else:
        seconds = amount * 24 * 60 * 60

    if seconds < MIN_GIVEAWAY_SECONDS:
        raise ValueError(f"Giveaway duration must be at least {MIN_GIVEAWAY_SECONDS} seconds.")
    if seconds > MAX_GIVEAWAY_SECONDS:
        raise ValueError("Giveaway duration cannot be more than 30 days.")
    return seconds


def format_duration(seconds: int) -> str:
    if seconds % (24 * 60 * 60) == 0:
        amount = seconds // (24 * 60 * 60)
        return f"{amount} day" + ("" if amount == 1 else "s")
    if seconds % (60 * 60) == 0:
        amount = seconds // (60 * 60)
        return f"{amount} hour" + ("" if amount == 1 else "s")
    if seconds % 60 == 0:
        amount = seconds // 60
        return f"{amount} minute" + ("" if amount == 1 else "s")
    return f"{seconds} second" + ("" if seconds == 1 else "s")


def _try_parse_duration_token(parts: list[str]) -> tuple[int | None, list[str]]:
    """Pull a duration token out of prefix giveaway text.

    Supported examples:
    - 2h
    - duration:2h
    - 2 hours
    """
    if not parts:
        return None, parts

    clean_parts = parts[:]

    # duration:2h or time:30m can appear anywhere.
    for index, token in enumerate(clean_parts):
        lowered = token.lower().strip()
        if lowered.startswith("duration:") or lowered.startswith("time:"):
            seconds = parse_duration_to_seconds(lowered)
            return seconds, clean_parts[:index] + clean_parts[index + 1 :]

    # End token: 2h / 30m / 1d.
    if DURATION_PATTERN.fullmatch(clean_parts[-1].lower()):
        seconds = parse_duration_to_seconds(clean_parts[-1])
        return seconds, clean_parts[:-1]

    # End pair: 2 hours / 30 minutes.
    if len(clean_parts) >= 2 and clean_parts[-2].isdigit():
        pair = f"{clean_parts[-2]} {clean_parts[-1]}"
        if DURATION_PATTERN.fullmatch(pair.lower()):
            seconds = parse_duration_to_seconds(pair)
            return seconds, clean_parts[:-2]

    return None, clean_parts


def parse_giveaway_options(raw_prize_text: str, default_seconds: int = GIVEAWAY_TIME) -> tuple[int, str, int, str]:
    """Allow old and new prefix formats.

    Old format still works:
    !giveaway 1 normal

    Winner amount examples:
    !giveaway 1 3 normal
    !giveaway 1 normal 3

    Duration examples:
    !giveaway 1 normal 2h
    !giveaway 1 normal 3 2h
    !giveaway 1 3 normal duration:2h
    """
    text = raw_prize_text.strip()
    parts = text.split()
    parsed_seconds, parts = _try_parse_duration_token(parts)
    duration_seconds = parsed_seconds if parsed_seconds is not None else default_seconds

    winner_amount = 1
    if len(parts) >= 2 and parts[0].isdigit():
        winner_amount = int(parts[0])
        parts = parts[1:]
    elif len(parts) >= 2 and parts[-1].isdigit():
        winner_amount = int(parts[-1])
        parts = parts[:-1]

    prize_type = " ".join(parts).strip()
    return winner_amount, prize_type, duration_seconds, format_duration(duration_seconds)


# Kept for compatibility with older code/imports that might call this directly.
def parse_giveaway_prize_and_winners(raw_prize_text: str) -> tuple[int, str]:
    winner_amount, clean_prize_type, _, _ = parse_giveaway_options(raw_prize_text, GIVEAWAY_TIME)
    return winner_amount, clean_prize_type


def validate_giveaway_numbers(amount: int, winner_amount: int) -> str | None:
    if amount <= 0:
        return "❌ Amount must be at least 1."
    if winner_amount <= 0:
        return "❌ Winner amount must be at least 1."
    if winner_amount > MAX_GIVEAWAY_WINNERS:
        return f"❌ Winner amount cannot be more than {MAX_GIVEAWAY_WINNERS}."
    return None


def giveaway_winner_word(winner_amount: int) -> str:
    return "winner" if winner_amount == 1 else "winners"


def format_giveaway_winners(winners: list[discord.User | discord.Member]) -> str:
    if len(winners) == 1:
        return f"Winner: {winners[0].mention}"
    return "Winners:\n" + "\n".join(f"{index}. {winner.mention}" for index, winner in enumerate(winners, start=1))


def format_stored_winner_ids(winner_ids: list[Any]) -> str:
    clean_ids = [_safe_int(user_id, 0) for user_id in winner_ids]
    clean_ids = [user_id for user_id in clean_ids if user_id > 0]
    if not clean_ids:
        return "No winners stored."
    if len(clean_ids) == 1:
        return f"Winner: <@{clean_ids[0]}>"
    return "Winners:\n" + "\n".join(f"{index}. <@{user_id}>" for index, user_id in enumerate(clean_ids, start=1))


def prize_from_giveaway_message(message: discord.Message) -> str:
    for embed in message.embeds:
        description = embed.description or ""
        match = re.search(r"^Prize:\s*(.+)$", description, flags=re.MULTILINE)
        if match:
            return match.group(1).strip().strip("*")
        for field in embed.fields:
            if field.name.lower().strip("*: ") == "prize":
                return str(field.value).strip()
    return "this giveaway"


def giveaway_status_emoji(status: str) -> str:
    status = status.lower().strip()
    if status == "active":
        return "🎉"
    if status == "ended":
        return "✅"
    if status == "cancelled":
        return "🚫"
    return "📌"


def build_active_giveaway_embed(
    *,
    prize: str,
    winner_amount: int,
    ends_at: int,
    duration_text: str,
    host: discord.Member | discord.User | None,
    message_id: int | None,
    test: bool = False,
) -> discord.Embed:
    title = "🎉 TEST GIVEAWAY 🎉" if test else "🎉 GIVEAWAY 🎉"
    host_text = host.mention if host is not None else "Unknown"
    message_text = f"`{message_id}`" if message_id else "`posting...`"
    embed = discord.Embed(
        title=title,
        description=(
            f"Prize: {prize}\n"
            f"Winners: {winner_amount}\n"
            f"Duration: {duration_text}\n"
            f"Ends: <t:{ends_at}:R> • <t:{ends_at}:f>\n"
            f"Hosted by: {host_text}\n"
            f"Message ID: {message_text}\n\n"
            "React with 🎉 to enter!"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(UK_TIMEZONE),
    )
    embed.set_footer(text="Use the Message ID for reroll, end, or cancel commands.")
    return embed


def build_giveaway_result_embed(
    data: dict[str, Any],
    *,
    title: str,
    color: discord.Color,
    entry_count: int | None = None,
    winners: list[discord.User | discord.Member] | None = None,
    note: str | None = None,
) -> discord.Embed:
    prize = str(data.get("prize") or "this giveaway")
    winner_amount = _safe_int(data.get("winner_amount"), 1)
    message_id = _safe_int(data.get("message_id"), 0)
    host_id = _safe_int(data.get("host_id"), 0)
    ended_at = _safe_int(data.get("ended_at"), int(time.time()))
    cancelled_at = _safe_int(data.get("cancelled_at"), 0)
    status_time = cancelled_at or ended_at or int(time.time())

    lines = [
        f"Prize: {prize}",
        f"Requested winners: {winner_amount}",
    ]
    if entry_count is not None:
        lines.append(f"Entries: {entry_count}")
    if host_id:
        lines.append(f"Hosted by: <@{host_id}>")
    if status_time:
        lines.append(f"Time: <t:{status_time}:R> • <t:{status_time}:f>")
    if message_id:
        lines.append(f"Message ID: `{message_id}`")

    lines.append("")
    if winners is not None:
        lines.append(format_giveaway_winners(winners) if winners else "No winners were drawn.")
    else:
        lines.append(format_stored_winner_ids(data.get("winner_ids", [])))

    if note:
        lines.append(f"\n{note}")

    embed = discord.Embed(
        title=title,
        description="\n".join(lines),
        color=color,
        timestamp=datetime.now(UK_TIMEZONE),
    )
    return embed


async def edit_original_giveaway_message(message: discord.Message, data: dict[str, Any], embed: discord.Embed) -> None:
    try:
        await message.edit(embed=embed)
    except discord.HTTPException:
        pass


async def get_giveaway_entries(message: discord.Message) -> list[discord.User | discord.Member]:
    entries_by_id: dict[int, discord.User | discord.Member] = {}
    for reaction in message.reactions:
        if str(reaction.emoji) != "🎉":
            continue
        async for user in reaction.users():
            if not user.bot:
                entries_by_id[user.id] = user
    return list(entries_by_id.values())


async def pick_giveaway_winners(
    message: discord.Message,
    winner_amount: int,
    *,
    excluded_user_ids: set[int] | None = None,
) -> tuple[list[discord.User | discord.Member], int]:
    entries = await get_giveaway_entries(message)
    if not entries:
        return [], 0

    requested = min(winner_amount, len(entries))
    eligible = entries
    if excluded_user_ids:
        fresh_entries = [entry for entry in entries if entry.id not in excluded_user_ids]
        # Prefer new winners on reroll, but fall back to all entries if there are not enough fresh entries.
        if len(fresh_entries) >= requested:
            eligible = fresh_entries

    winner_total = min(winner_amount, len(eligible))
    return random.sample(eligible, winner_total), len(entries)


def mark_giveaway_finished(
    data: dict[str, Any],
    winners: list[discord.User | discord.Member],
    *,
    note: str | None = None,
    ended_by: discord.Member | discord.User | None = None,
) -> None:
    data["status"] = "ended"
    data["ended_at"] = int(time.time())
    data["winner_ids"] = [winner.id for winner in winners]
    if ended_by is not None:
        data["ended_by_id"] = ended_by.id
        data["ended_by_name"] = str(ended_by)
    if note:
        data["end_note"] = note


def mark_giveaway_cancelled(data: dict[str, Any], actor: discord.Member | discord.User | None = None) -> None:
    data["status"] = "cancelled"
    data["cancelled_at"] = int(time.time())
    if actor is not None:
        data["cancelled_by_id"] = actor.id
        data["cancelled_by_name"] = str(actor)


async def finish_giveaway_by_data(data: dict[str, Any], *, ended_by: discord.Member | discord.User | None = None) -> str:
    guild = bot.get_guild(int(data["guild_id"]))
    if guild is None:
        mark_giveaway_finished(data, [], note="Guild could not be found.", ended_by=ended_by)
        return "❌ I could not find the server for that giveaway."
    channel = await get_text_channel(guild, int(data["channel_id"]))
    if channel is None:
        mark_giveaway_finished(data, [], note="Giveaway channel could not be found.", ended_by=ended_by)
        return "❌ I could not find the channel for that giveaway."

    prize = str(data["prize"])
    winner_amount = _safe_int(data.get("winner_amount"), 1)
    if winner_amount <= 0:
        winner_amount = 1

    try:
        message = await channel.fetch_message(int(data["message_id"]))
    except discord.HTTPException:
        mark_giveaway_finished(data, [], note="Giveaway message was deleted or could not be found.", ended_by=ended_by)
        await channel.send(f"❌ Giveaway message for {prize} was deleted or could not be found.")
        return f"❌ Giveaway message for {prize} was deleted or could not be found."

    winners, entry_count = await pick_giveaway_winners(message, winner_amount)

    if not winners:
        mark_giveaway_finished(data, [], note="No valid entries.", ended_by=ended_by)
        no_winner_embed = build_giveaway_result_embed(
            data,
            title="🎉 GIVEAWAY ENDED 🎉",
            color=discord.Color.orange(),
            entry_count=entry_count,
            winners=[],
            note="No valid entries were found.",
        )
        await edit_original_giveaway_message(message, data, no_winner_embed)
        await channel.send(f"❌ No one entered the {prize} giveaway.")
        return f"❌ No one entered the {prize} giveaway."

    mark_giveaway_finished(data, winners, ended_by=ended_by)
    short_note = ""
    if len(winners) < winner_amount:
        short_note = f"Only {len(winners)} valid entrant(s) were available for {winner_amount} requested {giveaway_winner_word(winner_amount)}."

    end_embed = build_giveaway_result_embed(
        data,
        title="🎉 GIVEAWAY ENDED 🎉",
        color=discord.Color.green(),
        entry_count=entry_count,
        winners=winners,
        note=short_note or None,
    )
    await edit_original_giveaway_message(message, data, end_embed)
    await channel.send(embed=end_embed, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
    await channel.send(
        f"🎉 Congratulations {', '.join(winner.mention for winner in winners)}! You won {prize}!",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )
    return f"✅ Ended {prize} with {len(winners)} winner(s) in {channel.mention}."


async def start_giveaway_in_channel(
    channel: discord.TextChannel,
    amount: int,
    prize_type: str,
    seconds: int,
    test: bool = False,
    winner_amount: int = 1,
    host: discord.Member | discord.User | None = None,
) -> str:
    number_error = validate_giveaway_numbers(amount, winner_amount)
    if number_error:
        return number_error

    try:
        seconds = parse_duration_to_seconds(format_duration(seconds), GIVEAWAY_TIME)
    except ValueError as exc:
        return f"❌ {exc}"

    prize = make_prize(amount, prize_type)
    if prize is None:
        return "❌ Use Normal, Hard Trade, or Very Hard Trade."

    started_at = int(time.time())
    ends_at = started_at + seconds
    duration_text = format_duration(seconds)
    embed = build_active_giveaway_embed(
        prize=prize,
        winner_amount=winner_amount,
        ends_at=ends_at,
        duration_text=duration_text,
        host=host,
        message_id=None,
        test=test,
    )
    message = await channel.send(embed=embed)
    await message.add_reaction("🎉")

    final_embed = build_active_giveaway_embed(
        prize=prize,
        winner_amount=winner_amount,
        ends_at=ends_at,
        duration_text=duration_text,
        host=host,
        message_id=message.id,
        test=test,
    )
    await edit_original_giveaway_message(message, {}, final_embed)

    giveaway_id = str(message.id)
    async with giveaway_lock:
        active_giveaways[giveaway_id] = {
            "guild_id": channel.guild.id,
            "channel_id": channel.id,
            "message_id": message.id,
            "prize": prize,
            "prize_amount": amount,
            "prize_type": prize_type.lower().strip(),
            "winner_amount": winner_amount,
            "status": "active",
            "started_at": started_at,
            "ends_at": ends_at,
            "duration_seconds": seconds,
            "test": bool(test),
            "host_id": host.id if host is not None else None,
            "host_name": str(host) if host is not None else None,
            "winner_ids": [],
            "rerolls": [],
        }
        await save_giveaways()
    return f"✅ Started giveaway for {prize} with {winner_amount} {giveaway_winner_word(winner_amount)}. Ends <t:{ends_at}:R>. Message ID: `{message.id}`"


async def reroll_giveaway_in_channel(channel: discord.TextChannel, message_id: int, winner_amount: int = 1) -> str:
    if winner_amount <= 0:
        return "❌ Winner amount must be at least 1."
    if winner_amount > MAX_GIVEAWAY_WINNERS:
        return f"❌ Winner amount cannot be more than {MAX_GIVEAWAY_WINNERS}."

    giveaway_id = str(message_id)
    stored_data = active_giveaways.get(giveaway_id)
    giveaway_channel = channel
    prize = "this giveaway"
    previous_winner_ids: set[int] = set()

    if isinstance(stored_data, dict):
        ends_at = _safe_int(stored_data.get("ends_at"), 0)
        status = str(stored_data.get("status") or "active")
        if status == "cancelled":
            return "❌ That giveaway was cancelled, so it cannot be rerolled."
        if status != "ended" and ends_at > int(time.time()):
            return "❌ That giveaway is still running. Use `!giveawayend` first or wait until it ends before rerolling."

        guild = bot.get_guild(_safe_int(stored_data.get("guild_id"), 0)) or channel.guild
        if guild is not None:
            stored_channel = await get_text_channel(guild, _safe_int(stored_data.get("channel_id"), 0))
            if stored_channel is not None:
                giveaway_channel = stored_channel
        prize = str(stored_data.get("prize") or prize)
        previous_winner_ids = {
            _safe_int(user_id, 0)
            for user_id in stored_data.get("winner_ids", [])
            if _safe_int(user_id, 0) > 0
        }

    try:
        message = await giveaway_channel.fetch_message(message_id)
    except discord.HTTPException:
        return "❌ I could not find that giveaway message. Use the original giveaway message ID in the same channel, or reroll one started after this update."

    if not isinstance(stored_data, dict):
        prize = prize_from_giveaway_message(message)

    winners, entry_count = await pick_giveaway_winners(message, winner_amount, excluded_user_ids=previous_winner_ids)
    if not winners:
        return f"❌ No valid entries found for {prize}."

    if isinstance(stored_data, dict):
        stored_data["status"] = "ended"
        stored_data["winner_amount"] = winner_amount
        stored_data["winner_ids"] = [winner.id for winner in winners]
        stored_data["last_rerolled_at"] = int(time.time())

    reroll_embed = build_giveaway_result_embed(
        stored_data if isinstance(stored_data, dict) else {"prize": prize, "winner_amount": winner_amount, "message_id": message_id},
        title="🔁 GIVEAWAY REROLLED 🔁",
        color=discord.Color.blurple(),
        entry_count=entry_count,
        winners=winners,
    )
    await giveaway_channel.send(embed=reroll_embed, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
    await giveaway_channel.send(
        f"🎉 New giveaway winner(s): {', '.join(winner.mention for winner in winners)}",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )

    if isinstance(stored_data, dict):
        async with giveaway_lock:
            rerolls = stored_data.get("rerolls")
            if not isinstance(rerolls, list):
                rerolls = []
                stored_data["rerolls"] = rerolls
            rerolls.append(
                {
                    "time": int(time.time()),
                    "winner_amount": winner_amount,
                    "winner_ids": [winner.id for winner in winners],
                }
            )
            await save_giveaways()

    return f"✅ Rerolled {prize} with {len(winners)} winner(s) in {giveaway_channel.mention}."


async def end_giveaway_in_channel(channel: discord.TextChannel, message_id: int, actor: discord.Member | discord.User | None = None) -> str:
    giveaway_id = str(message_id)
    stored_data = active_giveaways.get(giveaway_id)
    if not isinstance(stored_data, dict):
        return "❌ I can only end giveaways started after this update. Use the original giveaway Message ID."

    status = str(stored_data.get("status") or "active")
    if status == "ended":
        return "❌ That giveaway has already ended. Use reroll if you need new winners."
    if status == "cancelled":
        return "❌ That giveaway was cancelled."

    result = await finish_giveaway_by_data(stored_data, ended_by=actor)
    async with giveaway_lock:
        active_giveaways[giveaway_id] = stored_data
        await save_giveaways()
    return result


async def cancel_giveaway_in_channel(channel: discord.TextChannel, message_id: int, actor: discord.Member | discord.User | None = None) -> str:
    giveaway_id = str(message_id)
    stored_data = active_giveaways.get(giveaway_id)
    if not isinstance(stored_data, dict):
        return "❌ I can only cancel giveaways started after this update. Use the original giveaway Message ID."

    status = str(stored_data.get("status") or "active")
    if status == "ended":
        return "❌ That giveaway has already ended, so it cannot be cancelled."
    if status == "cancelled":
        return "❌ That giveaway is already cancelled."

    guild = bot.get_guild(_safe_int(stored_data.get("guild_id"), 0)) or channel.guild
    giveaway_channel = channel
    if guild is not None:
        stored_channel = await get_text_channel(guild, _safe_int(stored_data.get("channel_id"), 0))
        if stored_channel is not None:
            giveaway_channel = stored_channel

    mark_giveaway_cancelled(stored_data, actor)

    cancel_embed = build_giveaway_result_embed(
        stored_data,
        title="🚫 GIVEAWAY CANCELLED 🚫",
        color=discord.Color.red(),
        note=f"Cancelled by {actor.mention}." if actor is not None else "Cancelled.",
    )

    try:
        message = await giveaway_channel.fetch_message(message_id)
        await edit_original_giveaway_message(message, stored_data, cancel_embed)
    except discord.HTTPException:
        pass

    await giveaway_channel.send(embed=cancel_embed, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))

    async with giveaway_lock:
        active_giveaways[giveaway_id] = stored_data
        await save_giveaways()
    return f"✅ Cancelled giveaway `{message_id}` in {giveaway_channel.mention}."


def build_giveaway_list_embed(guild: discord.Guild) -> discord.Embed:
    records: list[dict[str, Any]] = []
    for data in active_giveaways.values():
        if not isinstance(data, dict):
            continue
        if _safe_int(data.get("guild_id"), 0) != guild.id:
            continue
        records.append(data)

    active_records = [record for record in records if str(record.get("status") or "active") == "active"]
    inactive_records = [record for record in records if str(record.get("status") or "active") != "active"]
    active_records.sort(key=lambda record: _safe_int(record.get("ends_at"), 0))
    inactive_records.sort(
        key=lambda record: max(
            _safe_int(record.get("ended_at"), 0),
            _safe_int(record.get("cancelled_at"), 0),
            _safe_int(record.get("started_at"), 0),
        ),
        reverse=True,
    )
    ordered = (active_records + inactive_records)[:20]

    embed = discord.Embed(
        title="🎉 XSI Giveaways",
        description=f"Active: **{len(active_records)}** • Saved: **{len(records)}**",
        color=discord.Color.gold() if active_records else discord.Color.blurple(),
        timestamp=datetime.now(UK_TIMEZONE),
    )

    if not ordered:
        embed.description = "No giveaways are saved yet."
        return embed

    for record in ordered:
        status = str(record.get("status") or "active").title()
        status_key = status.lower()
        prize = str(record.get("prize") or "Unknown prize")
        message_id = _safe_int(record.get("message_id"), 0)
        channel_id = _safe_int(record.get("channel_id"), 0)
        winner_amount = _safe_int(record.get("winner_amount"), 1)
        ends_at = _safe_int(record.get("ends_at"), 0)
        ended_at = _safe_int(record.get("ended_at"), 0)
        cancelled_at = _safe_int(record.get("cancelled_at"), 0)

        timing = ""
        if status_key == "active" and ends_at:
            timing = f"Ends: <t:{ends_at}:R>"
        elif status_key == "ended" and ended_at:
            timing = f"Ended: <t:{ended_at}:R>"
        elif status_key == "cancelled" and cancelled_at:
            timing = f"Cancelled: <t:{cancelled_at}:R>"

        value_lines = [
            f"Status: **{status}**",
            f"Channel: <#{channel_id}>" if channel_id else "Channel: Unknown",
            f"Winners: {winner_amount}",
        ]
        if timing:
            value_lines.append(timing)
        if message_id:
            value_lines.append(f"Message ID: `{message_id}`")

        embed.add_field(
            name=f"{giveaway_status_emoji(status_key)} {prize}"[:256],
            value="\n".join(value_lines)[:1024],
            inline=False,
        )

    if len(records) > len(ordered):
        embed.set_footer(text=f"Showing newest/active {len(ordered)} giveaways only.")
    return embed


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
    invalid_ids: list[str] = []
    changed = False

    for giveaway_id, data in list(active_giveaways.items()):
        if not isinstance(data, dict):
            invalid_ids.append(giveaway_id)
            continue
        if str(data.get("status") or "active") == "ended":
            continue
        if now >= _safe_int(data.get("ends_at"), 0):
            await finish_giveaway_by_data(data)
            changed = True

    if invalid_ids or changed:
        async with giveaway_lock:
            for giveaway_id in invalid_ids:
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

    await append_ticket_record_message(message)
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
    critical = ["clearsetup", "setunavailable", "refreshticketpanel", "setavailability", "availability", "clearunavailable", "record", "setrecordcategory", "setrecordchannel"]
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
                ch_line("Record Channel", "record_channel_id"),
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
    await append_ticket_record_event_for_channel(ctx.channel, data, "ticket_claimed", f"Ticket claimed by {ctx.author}.", actor=ctx.author)
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
    await append_ticket_record_event_for_channel(ctx.channel, data, "ticket_unclaimed", f"Ticket unclaimed by {ctx.author}.", actor=ctx.author)
    await ctx.send("✅ Ticket unclaimed.")


async def update_ticket_member_access(
    channel: discord.TextChannel,
    data: dict[str, Any],
    member: discord.Member,
    *,
    allow: bool,
    actor: discord.Member | discord.User,
) -> str:
    owner_id = _safe_int(data.get("owner_id"), 0)
    if not allow and member.id == owner_id:
        return "❌ You cannot remove the ticket owner from their own ticket. Close the ticket instead."

    if allow:
        overwrite = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        )
        action_text = "added to"
        event_type = "ticket_user_added"
        event_text = f"{member} was added to the ticket by {actor}."
    else:
        overwrite = None
        action_text = "removed from"
        event_type = "ticket_user_removed"
        event_text = f"{member} was removed from the ticket by {actor}."

    try:
        await channel.set_permissions(
            member,
            overwrite=overwrite,
            reason=f"XSI ticket user {'add' if allow else 'remove'} by {actor} ({actor.id})",
        )
    except discord.Forbidden:
        return "❌ I do not have permission to edit this ticket's channel permissions."
    except discord.HTTPException:
        return "❌ Discord rejected the permission update. Try again or check channel permissions."

    extra_users = data.get("extra_user_ids")
    if not isinstance(extra_users, list):
        extra_users = []
        data["extra_user_ids"] = extra_users

    if allow:
        if member.id not in extra_users:
            extra_users.append(member.id)
    else:
        data["extra_user_ids"] = [user_id for user_id in extra_users if _safe_int(user_id, 0) != member.id]

    ticket_owners[str(channel.id)] = data
    await save_ticket_owners()
    await append_ticket_record_event_for_channel(
        channel,
        data,
        event_type,
        event_text,
        actor=actor,
        extra={"target_user_id": member.id, "target_user_name": str(member)},
    )

    note = ""
    if not allow and (member.guild_permissions.administrator or has_staff_role(member)):
        note = " They may still see the ticket through admin/staff permissions."
    return f"✅ {member.mention} {action_text} this ticket.{note}"


@bot.command(name="ticketadd", aliases=["addticketuser", "ticketuseradd"])
@commands.has_permissions(manage_messages=True)
async def ticketadd_prefix(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a ticket channel.")
        return
    data = ticket_owners.get(str(ctx.channel.id))
    if not isinstance(data, dict):
        await ctx.send("❌ This is not a tracked ticket.")
        return
    result = await update_ticket_member_access(ctx.channel, data, member, allow=True, actor=ctx.author)
    await ctx.send(result, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))


@bot.command(name="ticketremove", aliases=["removeticketuser", "ticketuserremove"])
@commands.has_permissions(manage_messages=True)
async def ticketremove_prefix(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a ticket channel.")
        return
    data = ticket_owners.get(str(ctx.channel.id))
    if not isinstance(data, dict):
        await ctx.send("❌ This is not a tracked ticket.")
        return
    result = await update_ticket_member_access(ctx.channel, data, member, allow=False, actor=ctx.author)
    await ctx.send(result, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))


@bot.command(name="setrecordcategory")
@commands.has_permissions(manage_channels=True)
async def setrecordcategory_prefix(ctx: commands.Context, category_id: int | None = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    if category_id is None:
        if not isinstance(ctx.channel, discord.TextChannel) or ctx.channel.category is None:
            await ctx.send("❌ Use this inside a category channel, or run `!setrecordcategory CATEGORY_ID`.")
            return
        category = ctx.channel.category
    else:
        category = ctx.guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ That ID is not a valid category in this server.")
        return
    config = guild_config(ctx.guild.id)
    config["record_category_id"] = category.id
    await save_server_settings()
    await ctx.send(f"✅ Record category set to **{category.name}**. Record channels will be created there.")


@bot.command(name="setrecordchannel", aliases=["recordchannel", "setrecordlogchannel"])
@commands.has_permissions(manage_channels=True)
async def setrecordchannel_prefix(ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
    if ctx.guild is None or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works inside a server text channel.")
        return
    target = channel or ctx.channel
    config = guild_config(ctx.guild.id)
    config["record_channel_id"] = target.id
    await save_server_settings()
    await ctx.send(f"✅ Record channel set to {target.mention}. Record open/close notices will be posted there.")


@bot.command(name="record", aliases=["ticketrecord", "records"])
@commands.has_permissions(manage_messages=True)
async def record_prefix(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    await ensure_active_records_for_member(ctx.guild, member)
    records = find_ticket_records_for_member(ctx.guild.id, member.id)
    if not records:
        await ctx.send(f"❌ No ticket records found for {member.mention}. Records are saved for tickets created or active after this update.")
        return
    view = RecordPickerView(ctx.author.id, records[:MAX_RECORD_SELECT_OPTIONS])
    extra = "" if len(records) <= MAX_RECORD_SELECT_OPTIONS else f"\nShowing newest {MAX_RECORD_SELECT_OPTIONS} records only."
    await ctx.send(f"📁 Pick which ticket record you want to open for {member.mention}.{extra}", view=view)


# ============================================================
# PREFIX COMMANDS - MODERATION
# ============================================================
@bot.command(name="kick", aliases=["xsikick", "xkick", "xsi-kick", "xsi_kick"])
@commands.has_permissions(kick_members=True)
async def xsikick_prefix(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    test_mode, clean_reason = parse_xsikick_reason(reason)
    _, message = await run_xsikick(ctx.guild, member, ctx.author, clean_reason, test_mode=test_mode)
    await ctx.send(message, allowed_mentions=discord.AllowedMentions.none())


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
    try:
        winner_amount, clean_prize_type, duration_seconds, _ = parse_giveaway_options(prize_type, GIVEAWAY_TIME)
    except ValueError as exc:
        await ctx.send(f"❌ {exc}")
        return
    result = await start_giveaway_in_channel(
        ctx.channel,
        amount,
        clean_prize_type,
        duration_seconds,
        winner_amount=winner_amount,
        host=ctx.author,
    )
    await ctx.send(result)


@bot.command(name="testgiveaway")
@commands.has_permissions(administrator=True)
async def testgiveaway(ctx: commands.Context, amount: int, *, prize_type: str) -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return
    try:
        winner_amount, clean_prize_type, duration_seconds, _ = parse_giveaway_options(prize_type, TEST_GIVEAWAY_TIME)
    except ValueError as exc:
        await ctx.send(f"❌ {exc}")
        return
    result = await start_giveaway_in_channel(
        ctx.channel,
        amount,
        clean_prize_type,
        duration_seconds,
        test=True,
        winner_amount=winner_amount,
        host=ctx.author,
    )
    await ctx.send(result)


@bot.command(name="giveawayreroll", aliases=["rerollgiveaway", "reroll"])
@commands.has_permissions(administrator=True)
async def giveawayreroll(ctx: commands.Context, *, args: str = "") -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return

    parts = args.split()
    reference_message_id = ctx.message.reference.message_id if ctx.message.reference else None
    message_id: int | None = None
    winner_amount = 1

    if reference_message_id is not None:
        message_id = int(reference_message_id)

    if parts:
        if not all(part.isdigit() for part in parts[:2]):
            await ctx.send("❌ Use `!giveawayreroll <message_id> [winner_amount]` or reply to the giveaway with `!giveawayreroll [winner_amount]`.")
            return
        first_number = int(parts[0])
        if message_id is not None and len(parts) == 1 and first_number < 10_000_000_000:
            winner_amount = first_number
        else:
            message_id = first_number
            if len(parts) >= 2:
                winner_amount = int(parts[1])

    if message_id is None:
        await ctx.send("❌ Reply to the giveaway message with `!giveawayreroll` or use `!giveawayreroll <message_id> [winner_amount]`.")
        return

    result = await reroll_giveaway_in_channel(ctx.channel, message_id, winner_amount)
    await ctx.send(result)


@bot.command(name="giveawayend", aliases=["endgiveaway"])
@commands.has_permissions(administrator=True)
async def giveawayend_prefix(ctx: commands.Context, message_id: int = 0) -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return
    reference_message_id = ctx.message.reference.message_id if ctx.message.reference else None
    final_message_id = message_id or reference_message_id
    if final_message_id is None:
        await ctx.send("❌ Use `!giveawayend <message_id>` or reply to the giveaway with `!giveawayend`.")
        return
    result = await end_giveaway_in_channel(ctx.channel, int(final_message_id), ctx.author)
    await ctx.send(result)


@bot.command(name="giveawaycancel", aliases=["cancelgiveaway"])
@commands.has_permissions(administrator=True)
async def giveawaycancel_prefix(ctx: commands.Context, message_id: int = 0) -> None:
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("❌ This command only works in a text channel.")
        return
    reference_message_id = ctx.message.reference.message_id if ctx.message.reference else None
    final_message_id = message_id or reference_message_id
    if final_message_id is None:
        await ctx.send("❌ Use `!giveawaycancel <message_id>` or reply to the giveaway with `!giveawaycancel`.")
        return
    result = await cancel_giveaway_in_channel(ctx.channel, int(final_message_id), ctx.author)
    await ctx.send(result)


@bot.command(name="giveawaylist", aliases=["giveaways", "listgiveaways"])
@commands.has_permissions(administrator=True)
async def giveawaylist_prefix(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return
    embed = build_giveaway_list_embed(ctx.guild)
    await ctx.send(embed=embed)


# ============================================================
# SLASH COMMANDS
# ============================================================
@bot.tree.command(name="version", description="Show the running XSI build version")
async def slash_version(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"✅ {VERSION}\nBuild tag: `{BUILD_TAG}`", ephemeral=True)


@bot.tree.command(name="buildcheck", description="Show XSI build and slash-command diagnostics")
async def slash_buildcheck(interaction: discord.Interaction) -> None:
    names = sorted(command.name for command in bot.tree.get_commands())
    critical = ["clearsetup", "setunavailable", "refreshticketpanel", "setavailability", "availability", "clearunavailable", "record", "setrecordcategory", "setrecordchannel"]
    missing = [name for name in critical if name not in names]
    missing_text = ", ".join(missing) if missing else "None"
    await interaction.response.send_message(
        f"✅ {VERSION}\n"
        f"Build tag: `{BUILD_TAG}`\n"
        f"Slash commands loaded in memory: `{len(names)}`\n"
        f"Critical commands missing: `{missing_text}`",
        ephemeral=True,
    )


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
                ch_line("Record Channel", "record_channel_id"),
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


async def set_leaves_guilt_channel_from_interaction(interaction: discord.Interaction) -> None:
    """Shared slash-command helper for leaves / Board of Guilt channel setup.

    Do not call another decorated slash command directly from a slash command.
    app_commands wraps decorated callbacks, so reusing the decorated function can
    raise an internal error and make Discord show "Something went wrong".
    """
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a server text channel.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["leaves_channel_id"] = interaction.channel.id
    config["guilt_channel_id"] = interaction.channel.id
    await save_server_settings()
    await interaction.response.send_message(f"✅ Leaves / Board of Guilt channel set to {interaction.channel.mention}.", ephemeral=True)


@bot.tree.command(name="setleaveschannel", description="Set this channel as leaves / Board of Guilt channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setleaveschannel(interaction: discord.Interaction) -> None:
    await set_leaves_guilt_channel_from_interaction(interaction)


@bot.tree.command(name="setgulitcategory", description="Set this channel as Board of Guilt/leaves channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setgulitcategory(interaction: discord.Interaction) -> None:
    # Kept for compatibility with the old misspelled slash command.
    await set_leaves_guilt_channel_from_interaction(interaction)


@bot.tree.command(name="setguiltcategory", description="Set this channel as Board of Guilt/leaves channel")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setguiltcategory(interaction: discord.Interaction) -> None:
    await set_leaves_guilt_channel_from_interaction(interaction)


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
    await append_ticket_record_event_for_channel(interaction.channel, data, "ticket_claimed", f"Ticket claimed by {interaction.user}.", actor=interaction.user)
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
    await append_ticket_record_event_for_channel(interaction.channel, data, "ticket_unclaimed", f"Ticket unclaimed by {interaction.user}.", actor=interaction.user)
    await interaction.response.send_message("✅ Ticket unclaimed.")


@bot.tree.command(name="ticketadd", description="Add a member to the current ticket")
@app_commands.describe(member="Member to add to this ticket")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_ticketadd(interaction: discord.Interaction, member: discord.Member) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
        return
    data = ticket_owners.get(str(interaction.channel.id))
    if not isinstance(data, dict):
        await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
        return
    result = await update_ticket_member_access(interaction.channel, data, member, allow=True, actor=interaction.user)
    await interaction.response.send_message(result, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))


@bot.tree.command(name="ticketremove", description="Remove a member from the current ticket")
@app_commands.describe(member="Member to remove from this ticket")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_ticketremove(interaction: discord.Interaction, member: discord.Member) -> None:
    if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works inside a ticket channel.", ephemeral=True)
        return
    data = ticket_owners.get(str(interaction.channel.id))
    if not isinstance(data, dict):
        await interaction.response.send_message("❌ This is not a tracked ticket.", ephemeral=True)
        return
    result = await update_ticket_member_access(interaction.channel, data, member, allow=False, actor=interaction.user)
    await interaction.response.send_message(result, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))


@bot.tree.command(name="setrecordcategory", description="Set the optional category for temporary /record channels")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_setrecordcategory(interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["record_category_id"] = category.id
    await save_server_settings()
    await interaction.response.send_message(
        f"✅ Record category set to **{category.name}**. `/record` channels will be created there.",
        ephemeral=True,
    )


@bot.tree.command(name="setrecordchannel", description="Set the channel for XSI ticket-record notices")
@app_commands.describe(channel="Channel where XSI should post record-open notices")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_setrecordchannel(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    config = guild_config(interaction.guild.id)
    config["record_channel_id"] = channel.id
    await save_server_settings()
    await interaction.response.send_message(
        f"✅ Record channel set to {channel.mention}. Record open/close notices will be posted there.",
        ephemeral=True,
    )


@bot.tree.command(name="record", description="Open a temporary record channel for a member's previous ticket")
@app_commands.describe(member="Member whose ticket records you want to view")
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_record(interaction: discord.Interaction, member: discord.Member) -> None:
    await send_record_picker_response(interaction, member)


@bot.tree.command(name="kick", description="Kick a member through XSI, or test without kicking")
@app_commands.describe(
    member="The member to kick",
    reason="Reason for the kick",
    test_mode="Turn this on to test without kicking the member",
)
@app_commands.checks.has_permissions(kick_members=True)
async def slash_xsikick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided.",
    test_mode: bool = False,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    _, message = await run_xsikick(interaction.guild, member, interaction.user, reason, test_mode=test_mode)
    await interaction.response.send_message(message, allowed_mentions=discord.AllowedMentions.none())


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


@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(
    amount="Prize amount, for example 1 Normal Car or 3 Hard Trades",
    prize_type="Normal, Hard Trade, or Very Hard Trade",
    winner_amount="How many winners to draw. Default is 1.",
    duration="How long the giveaway runs: 30s, 10m, 2h, or 1d. Default is 24h.",
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveaway(
    interaction: discord.Interaction,
    amount: int,
    prize_type: str,
    winner_amount: int = 1,
    duration: str = "24h",
) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    try:
        duration_seconds = parse_duration_to_seconds(duration, GIVEAWAY_TIME)
    except ValueError as exc:
        await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        return
    result = await start_giveaway_in_channel(
        interaction.channel,
        amount,
        prize_type,
        duration_seconds,
        winner_amount=winner_amount,
        host=interaction.user,
    )
    await interaction.response.send_message(result, ephemeral=True)


@bot.tree.command(name="testgiveaway", description="Start a quick test giveaway")
@app_commands.describe(
    amount="Prize amount, for example 1 Normal Car or 3 Hard Trades",
    prize_type="Normal, Hard Trade, or Very Hard Trade",
    winner_amount="How many winners to draw. Default is 1.",
    duration="Optional test duration: 10s, 30s, 1m, etc. Default is 30s.",
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_testgiveaway(
    interaction: discord.Interaction,
    amount: int,
    prize_type: str,
    winner_amount: int = 1,
    duration: str = "30s",
) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    try:
        duration_seconds = parse_duration_to_seconds(duration, TEST_GIVEAWAY_TIME)
    except ValueError as exc:
        await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        return
    result = await start_giveaway_in_channel(
        interaction.channel,
        amount,
        prize_type,
        duration_seconds,
        test=True,
        winner_amount=winner_amount,
        host=interaction.user,
    )
    await interaction.response.send_message(result, ephemeral=True)


@bot.tree.command(name="giveawayreroll", description="Reroll an ended giveaway")
@app_commands.describe(
    message_id="Original giveaway message ID",
    winner_amount="How many winners to draw. Default is 1.",
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveawayreroll(interaction: discord.Interaction, message_id: str, winner_amount: int = 1) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    if not message_id.isdigit():
        await interaction.response.send_message("❌ Message ID must be numbers only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    result = await reroll_giveaway_in_channel(interaction.channel, int(message_id), winner_amount)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="giveawayend", description="End an active giveaway now")
@app_commands.describe(message_id="Original giveaway message ID")
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveawayend(interaction: discord.Interaction, message_id: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    if not message_id.isdigit():
        await interaction.response.send_message("❌ Message ID must be numbers only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    result = await end_giveaway_in_channel(interaction.channel, int(message_id), interaction.user)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="giveawaycancel", description="Cancel an active giveaway")
@app_commands.describe(message_id="Original giveaway message ID")
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveawaycancel(interaction: discord.Interaction, message_id: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This only works in a text channel.", ephemeral=True)
        return
    if not message_id.isdigit():
        await interaction.response.send_message("❌ Message ID must be numbers only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    result = await cancel_giveaway_in_channel(interaction.channel, int(message_id), interaction.user)
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="giveawaylist", description="List saved giveaways")
@app_commands.checks.has_permissions(administrator=True)
async def slash_giveawaylist(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return
    embed = build_giveaway_list_embed(interaction.guild)
    await interaction.response.send_message(embed=embed, ephemeral=True)


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
        ("Manage Channels", perms.manage_channels, "create setup categories, ticket channels, and ticket access"),
        ("Manage Messages", perms.manage_messages, "delete banned messages and clean commands"),
        ("Embed Links", perms.embed_links, "send ticket, setup, warning, and log embeds"),
        ("Add Reactions", perms.add_reactions, "add the giveaway reaction"),
        ("Kick Members", perms.kick_members, "kick users after max warnings"),
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
            "`!kick @user reason`\n"
            "`!kick @user --test reason`\n"
            "`!warn @user reason`\n"
            "`!ticketadd @user` / `!ticketremove @user`\n"
            "`!giveaway 1 normal 3 2h` = 1 Normal Car, 3 winners, 2 hours\n"
            "`!giveawayend <message_id>` / `!giveawaycancel <message_id>`\n"
            "`!giveawaylist`\n"
            "`!giveawayreroll <message_id> [winner_amount]`"
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


