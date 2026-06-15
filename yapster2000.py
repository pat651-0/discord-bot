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
from typing import Any, Optional
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


# ---------------- DATA FILES ----------------
# On Railway, add a Volume if you want JSON data to survive redeploys.
# If Railway provides RAILWAY_VOLUME_MOUNT_PATH, this script will use it automatically.
DATA_DIR = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SERVER_SETTINGS_FILE = DATA_DIR / "server_settings.json"
WARNINGS_FILE = DATA_DIR / "knob_warnings.json"
TICKET_OWNERS_FILE = DATA_DIR / "ticket_owners.json"


# ---------------- DEFAULT IDS / FALLBACKS ----------------
# These keep your current servers working. New servers can be set up with commands.
DEFAULT_STAFF_ROLE_IDS = [
    1470379426297548957,
]

DEFAULT_TICKET_CATEGORY_IDS = [
    1472860643475329096,  # your server ticket category
    1507876447467995226,  # friend's server ticket category
]

DEFAULT_TICKET_OWNER_NAMES_BY_CATEGORY = {
    1472860643475329096: "Filiy V",  # your server
    1507876447467995226: "Mruss",    # friend's server
}

DEFAULT_TICKET_OWNER_NAME = "Filiy V"

DEFAULT_LEAVES_CHANNEL_ID = 1475079442291363901
DEFAULT_WALL_CHANNEL_ID = 1509103133479932085

# Your Discord ID. Your replies still trigger ticket-owner DMs.
# Configured staff roles can also trigger ticket-owner DMs.
OWNER_USER_IDS = [
    1137385938155221073,
]


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


# ---------------- WELCOME SETTINGS ----------------
DEFAULT_WELCOME_MESSAGE = "Hey {user} Please Read The Rules"

# Smart auto-replies. Per trigger/user/channel cooldown so XSI does not spam.
SMART_MESSAGE_COOLDOWN = 30


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

# Smart-message cooldown cache: guild:channel:user:trigger -> last_reply_time
smart_message_cooldowns: defaultdict[str, float] = defaultdict(float)


# ---------------- JSON HELPERS ----------------
def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default.copy() if isinstance(default, dict) else default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        log.warning("JSON file is corrupted, using default: %s", path)
        return default.copy() if isinstance(default, dict) else default
    except OSError as exc:
        log.warning("Could not read %s: %s", path, exc)
        return default.copy() if isinstance(default, dict) else default


def load_json_dict(path: Path) -> dict[str, Any]:
    data = load_json(path, {})

    if not isinstance(data, dict):
        log.warning("%s did not contain a JSON object, resetting to empty dict.", path)
        return {}

    return data


def save_json(path: Path, data: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        temp_path.replace(path)
    except OSError as exc:
        log.exception("Could not save %s: %s", path, exc)


server_settings: dict[str, Any] = load_json_dict(SERVER_SETTINGS_FILE)
warnings_store: dict[str, Any] = load_json_dict(WARNINGS_FILE)
ticket_owners: dict[str, Any] = load_json_dict(TICKET_OWNERS_FILE)


def save_server_settings() -> None:
    save_json(SERVER_SETTINGS_FILE, server_settings)


def save_warnings() -> None:
    save_json(WARNINGS_FILE, warnings_store)


def save_ticket_owners() -> None:
    save_json(TICKET_OWNERS_FILE, ticket_owners)


# ---------------- SERVER SETTINGS HELPERS ----------------
def get_guild_settings(guild_id: int) -> dict[str, Any]:
    key = str(guild_id)
    data = server_settings.get(key)

    if not isinstance(data, dict):
        data = {}
        server_settings[key] = data

    return data


def parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_staff_role_ids(guild_id: int) -> list[int]:
    settings = get_guild_settings(guild_id)
    saved_ids = settings.get("staff_role_ids")

    if isinstance(saved_ids, list):
        valid_ids = [role_id for role_id in (parse_int(item) for item in saved_ids) if role_id is not None]
        if valid_ids:
            return valid_ids

    return DEFAULT_STAFF_ROLE_IDS.copy()


def get_ticket_owner_name_for_guild(guild: discord.Guild, category: discord.CategoryChannel | None = None) -> str:
    settings = get_guild_settings(guild.id)
    saved_name = settings.get("ticket_owner_name")

    if isinstance(saved_name, str) and saved_name.strip():
        return saved_name.strip()

    if category is not None:
        return DEFAULT_TICKET_OWNER_NAMES_BY_CATEGORY.get(category.id, DEFAULT_TICKET_OWNER_NAME)

    return DEFAULT_TICKET_OWNER_NAME


def get_wall_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    saved_id = parse_int(settings.get("wall_channel_id"))

    if saved_id is not None:
        return saved_id

    if guild.get_channel(DEFAULT_WALL_CHANNEL_ID) is not None:
        return DEFAULT_WALL_CHANNEL_ID

    return None


def get_guilt_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)

    # Preferred key for the new setup system.
    saved_id = parse_int(settings.get("leaves_channel_id"))
    if saved_id is not None:
        return saved_id

    # Backwards/alternate naming support.
    saved_id = parse_int(settings.get("guilt_channel_id"))
    if saved_id is not None:
        return saved_id

    if guild.get_channel(DEFAULT_LEAVES_CHANNEL_ID) is not None:
        return DEFAULT_LEAVES_CHANNEL_ID

    return None


def get_welcome_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("welcome_channel_id"))


def get_welcome_message(guild: discord.Guild) -> str:
    settings = get_guild_settings(guild.id)
    saved_message = settings.get("welcome_message")

    if isinstance(saved_message, str) and saved_message.strip():
        return saved_message.strip()

    return DEFAULT_WELCOME_MESSAGE


def get_rules_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("rules_channel_id"))


def get_giveaways_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("giveaways_channel_id"))


def get_ticket_panel_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("ticket_panel_channel_id"))


def get_transcript_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("transcript_channel_id"))


def get_staff_logs_channel_id(guild: discord.Guild) -> int | None:
    settings = get_guild_settings(guild.id)
    return parse_int(settings.get("staff_logs_channel_id"))


def get_smart_messages(guild_id: int) -> dict[str, str]:
    settings = get_guild_settings(guild_id)
    messages = settings.get("smart_messages")

    if not isinstance(messages, dict):
        messages = {}
        settings["smart_messages"] = messages

    clean_messages: dict[str, str] = {}
    for trigger, reply in messages.items():
        if isinstance(trigger, str) and isinstance(reply, str) and trigger.strip() and reply.strip():
            clean_messages[trigger.strip().lower()] = reply.strip()

    if clean_messages != messages:
        settings["smart_messages"] = clean_messages

    return clean_messages


def format_welcome_message(template: str, member: discord.Member) -> str:
    return (
        template
        .replace("{user}", member.mention)
        .replace("@user", member.mention)
        .replace("{server}", member.guild.name)
        .replace("{username}", member.name)
        .replace("{display_name}", member.display_name)
    )


# ---------------- GENERAL HELPERS ----------------
def has_staff_role(member: discord.Member) -> bool:
    staff_role_ids = get_staff_role_ids(member.guild.id)
    return any(role.id in staff_role_ids for role in member.roles)


def is_staff_or_mod(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
        or has_staff_role(member)
    )


async def get_guild_sendable_channel(guild: discord.Guild, channel_id: int) -> discord.TextChannel | None:
    channel = guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except discord.HTTPException:
            return None

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


def mention_channel(guild: discord.Guild, channel_id: int | None) -> str:
    if channel_id is None:
        return "Not set"

    channel = guild.get_channel(channel_id)
    if channel is None:
        return f"Not found: `{channel_id}`"

    return channel.mention


def mention_category(guild: discord.Guild, category_id: int | None) -> str:
    if category_id is None:
        return "Not set"

    category = guild.get_channel(category_id)
    if isinstance(category, discord.CategoryChannel):
        return f"{category.name} (`{category.id}`)"

    return f"Not found: `{category_id}`"


# ---------------- PERMISSION CHECK HELPERS ----------------
REQUIRED_PERMISSION_ITEMS: list[tuple[str, str, str]] = [
    ("view_channel", "View Channels", "see setup/ticket/log channels"),
    ("send_messages", "Send Messages", "send replies, welcome messages, panels, and logs"),
    ("read_message_history", "Read Message History", "read ticket/giveaway messages"),
    ("manage_channels", "Manage Channels", "create setup categories and ticket channels"),
    ("manage_messages", "Manage Messages", "delete banned messages and clean commands"),
    ("embed_links", "Embed Links", "send ticket, setup, warning, and log embeds"),
    ("add_reactions", "Add Reactions", "add the giveaway reaction"),
    ("kick_members", "Kick Members", "kick users after max warnings"),
    ("ban_members", "Ban Members", "only needed if punishment mode is ban"),
]

OPTIONAL_PERMISSION_ITEMS: list[tuple[str, str, str]] = [
    ("manage_roles", "Manage Roles", "only needed later for auto-role/rules-button features"),
]


def build_recommended_permissions() -> discord.Permissions:
    permissions = discord.Permissions.none()

    for permission_name, _label, _reason in REQUIRED_PERMISSION_ITEMS:
        if hasattr(permissions, permission_name):
            setattr(permissions, permission_name, True)

    return permissions


def permission_lines(permissions: discord.Permissions, items: list[tuple[str, str, str]]) -> list[str]:
    lines: list[str] = []

    for permission_name, label, reason in items:
        has_permission = bool(getattr(permissions, permission_name, False))
        icon = "✅" if has_permission else "❌"
        lines.append(f"{icon} **{label}** — {reason}")

    return lines


def missing_permission_names(permissions: discord.Permissions) -> list[str]:
    missing: list[str] = []

    for permission_name, label, _reason in REQUIRED_PERMISSION_ITEMS:
        if not bool(getattr(permissions, permission_name, False)):
            missing.append(label)

    return missing


SETUP_COMPONENT_ALIASES: dict[str, str] = {
    "ticket": "tickets",
    "tickets": "tickets",
    "ticketcategory": "tickets",
    "ticketcategories": "tickets",
    "ticketpanel": "ticketpanel",
    "panel": "ticketpanel",
    "openaticket": "ticketpanel",
    "welcome": "welcome",
    "welcomes": "welcome",
    "rules": "rules",
    "rule": "rules",
    "giveaway": "giveaways",
    "giveaways": "giveaways",
    "gaw": "giveaways",
    "wall": "wall",
    "wallofknobs": "wall",
    "knobs": "wall",
    "guilt": "leaves",
    "gulit": "leaves",
    "board": "leaves",
    "boardofguilt": "leaves",
    "leave": "leaves",
    "leaves": "leaves",
    "transcript": "transcripts",
    "transcripts": "transcripts",
    "tickettranscript": "transcripts",
    "tickettranscripts": "transcripts",
    "stafflog": "stafflogs",
    "stafflogs": "stafflogs",
    "staff": "stafflogs",
    "logs": "logs",
    "info": "info",
}

SETUP_ALL_COMPONENTS = {
    "tickets",
    "ticketpanel",
    "welcome",
    "rules",
    "giveaways",
    "wall",
    "leaves",
    "transcripts",
    "stafflogs",
}


def normalize_setup_word(word: str) -> str | None:
    cleaned = re.sub(r"[^a-z0-9]", "", word.lower())
    if not cleaned:
        return None
    return SETUP_COMPONENT_ALIASES.get(cleaned)


def parse_setup_exclusions(raw: str | None) -> tuple[set[str], list[str]]:
    if not raw or not raw.strip():
        return set(), []

    words = re.findall(r"[a-zA-Z0-9_-]+", raw.lower().replace(",", " "))
    exclusions: set[str] = set()
    unknown: list[str] = []

    # Prefix style: !setup no giveaways no welcome
    if "no" in words:
        for index, word in enumerate(words):
            if word != "no":
                continue
            if index + 1 >= len(words):
                continue
            component = normalize_setup_word(words[index + 1])
            if component is None:
                unknown.append(words[index + 1])
            else:
                exclusions.add(component)
    else:
        # Slash style: /setup exclude: giveaways,welcome,transcripts
        for word in words:
            component = normalize_setup_word(word)
            if component is None:
                unknown.append(word)
            else:
                exclusions.add(component)

    if "logs" in exclusions:
        exclusions.update({"wall", "leaves", "transcripts", "stafflogs"})
        exclusions.discard("logs")

    if "info" in exclusions:
        exclusions.update({"welcome", "rules", "giveaways", "ticketpanel"})
        exclusions.discard("info")

    if "tickets" in exclusions:
        exclusions.add("ticketpanel")

    return exclusions, unknown


async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    for category in guild.categories:
        if category.name.lower() == name.lower():
            return category

    return await guild.create_category(name=name, reason="XSI automatic setup")


async def get_or_create_text_channel(
    guild: discord.Guild,
    name: str,
    *,
    category: discord.CategoryChannel | None = None,
    topic: str | None = None,
) -> discord.TextChannel:
    normalized_name = name.lower()

    for channel in guild.text_channels:
        if channel.name.lower() == normalized_name:
            if category is not None and channel.category_id != category.id:
                try:
                    await channel.edit(category=category, reason="XSI automatic setup")
                except discord.HTTPException:
                    pass
            return channel

    return await guild.create_text_channel(
        name=normalized_name,
        category=category,
        topic=topic,
        reason="XSI automatic setup",
    )


async def send_default_rules_embed(channel: discord.TextChannel) -> None:
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
    await channel.send(embed=embed)


def format_smart_reply(template: str, message: discord.Message) -> str:
    guild_name = message.guild.name if message.guild is not None else "this server"
    return (
        template
        .replace("{user}", message.author.mention)
        .replace("@user", message.author.mention)
        .replace("{server}", guild_name)
        .replace("{username}", message.author.name)
        .replace("{display_name}", getattr(message.author, "display_name", message.author.name))
    )


async def maybe_send_smart_message(message: discord.Message) -> None:
    if message.guild is None:
        return

    content = normalize_text(message.content or "")
    if not content:
        return

    prefixes = bot.command_prefix if isinstance(bot.command_prefix, (list, tuple)) else [bot.command_prefix]
    if any(content.startswith(str(prefix).lower()) for prefix in prefixes):
        return

    smart_messages = get_smart_messages(message.guild.id)
    if not smart_messages:
        return

    compact_message = compact_text(content)
    now = time.time()

    for trigger, reply in smart_messages.items():
        trigger_normal = normalize_text(trigger)
        trigger_compact = compact_text(trigger)

        if trigger_normal not in content and trigger_compact not in compact_message:
            continue

        cooldown_key = f"{message.guild.id}:{message.channel.id}:{message.author.id}:{trigger_normal}"
        if now - smart_message_cooldowns[cooldown_key] < SMART_MESSAGE_COOLDOWN:
            return

        smart_message_cooldowns[cooldown_key] = now
        await message.channel.send(
            format_smart_reply(reply, message),
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
        return


# ---------------- TICKET HELPERS ----------------
def get_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    settings = get_guild_settings(guild.id)
    saved_category_id = parse_int(settings.get("ticket_category_id"))

    if saved_category_id is not None:
        category = guild.get_channel(saved_category_id)
        if isinstance(category, discord.CategoryChannel):
            return category

    for category_id in DEFAULT_TICKET_CATEGORY_IDS:
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

    guild = getattr(channel, "guild", None)
    category = getattr(channel, "category", None)

    if isinstance(guild, discord.Guild):
        return get_ticket_owner_name_for_guild(guild, category if isinstance(category, discord.CategoryChannel) else None)

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

        saved_guild_id = parse_int(data.get("guild_id"))
        if saved_guild_id is not None and saved_guild_id != guild.id:
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
        await interaction.followup.send("❌ Ticket category not found. Admin can use `!setticketcategory` or `/setticketcategory`.")
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

    for role_id in get_staff_role_ids(guild.id):
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

    owner_display_name = get_ticket_owner_name_for_guild(guild, category)

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

    # Backwards compatibility with old flat JSON format: {"user_id": warning_count}.
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
    channel_id = get_wall_channel_id(member.guild)

    if channel_id is None:
        log.warning("Wall of Knobs channel not configured for guild: %s", member.guild.id)
        return

    channel = await get_guild_sendable_channel(member.guild, channel_id)

    if channel is None:
        log.warning("Wall of Knobs channel not found or not sendable: %s", channel_id)
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


# ---------------- READY / SYNC ----------------
async def sync_commands_for_guild(guild: discord.Guild) -> int:
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    return len(synced)


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
                count = await sync_commands_for_guild(guild)
                log.info("✅ Synced %s slash command(s) in %s", count, guild.name)
            except discord.HTTPException as exc:
                log.exception("❌ Slash sync failed in %s: %s", guild.name, exc)

        bot.synced = True


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        count = await sync_commands_for_guild(guild)
        log.info("✅ Synced %s slash command(s) after joining %s", count, guild.name)
    except discord.HTTPException as exc:
        log.exception("❌ Slash sync failed after joining %s: %s", guild.name, exc)


# ---------------- WELCOME / BOARD OF GUILT ----------------
@bot.event
async def on_member_join(member: discord.Member) -> None:
    channel_id = get_welcome_channel_id(member.guild)

    if channel_id is None:
        return

    channel = await get_guild_sendable_channel(member.guild, channel_id)

    if channel is None:
        log.warning("Welcome channel not found or not sendable: %s", channel_id)
        return

    message = format_welcome_message(get_welcome_message(member.guild), member)

    await channel.send(
        message,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    channel_id = get_guilt_channel_id(member.guild)

    if channel_id is None:
        log.warning("Board of Guilt channel not configured for guild: %s", member.guild.id)
        return

    channel = await get_guild_sendable_channel(member.guild, channel_id)

    if channel is None:
        log.warning("Board of Guilt channel not found or not sendable: %s", channel_id)
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

    if not isinstance(message.author, discord.Member):
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

    # Ticket updates can be triggered by your owner ID or by configured staff/mods.
    if message.author.id not in OWNER_USER_IDS and not is_staff_or_mod(message.author):
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
    await maybe_send_smart_message(message)

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


# ---------------- SETUP COMMAND HELPERS ----------------
async def set_guilt_channel_from_command(ctx: commands.Context, channel: Optional[discord.TextChannel]) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = channel
    if target is None:
        if isinstance(ctx.channel, discord.TextChannel):
            target = ctx.channel
        else:
            await ctx.send("❌ Please choose a text channel.")
            return

    settings = get_guild_settings(ctx.guild.id)
    settings["guilt_channel_id"] = target.id
    settings["leaves_channel_id"] = target.id
    save_server_settings()

    await ctx.send(f"✅ Leaves / Board of Guilt channel set to {target.mention}.")


# ---------------- AUTO SETUP COMMAND ----------------
@bot.hybrid_command(name="setup", description="Automatically create XSI categories/channels. Use 'no giveaways' etc. to skip parts.")
@commands.has_permissions(administrator=True)
@app_commands.describe(exclude="Optional skip list, for example: giveaways,welcome,transcripts")
async def setup(ctx: commands.Context, *, exclude: Optional[str] = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    exclusions, unknown = parse_setup_exclusions(exclude)

    if ctx.interaction is not None:
        await ctx.defer()

    settings = get_guild_settings(ctx.guild.id)
    created: list[str] = []
    used_existing: list[str] = []
    skipped: list[str] = []

    try:
        tickets_category: discord.CategoryChannel | None = None
        logs_category: discord.CategoryChannel | None = None
        info_category: discord.CategoryChannel | None = None

        needs_tickets_category = "tickets" not in exclusions
        needs_logs_category = any(part not in exclusions for part in ["wall", "leaves", "transcripts", "stafflogs"])
        needs_info_category = any(part not in exclusions for part in ["welcome", "rules", "giveaways", "ticketpanel"])

        if needs_tickets_category:
            before = len(ctx.guild.categories)
            tickets_category = await get_or_create_category(ctx.guild, "XSI Tickets")
            settings["ticket_category_id"] = tickets_category.id
            (created if len(ctx.guild.categories) > before else used_existing).append(f"Ticket Category: **{tickets_category.name}**")
        else:
            skipped.append("Ticket Category")

        if needs_logs_category:
            before = len(ctx.guild.categories)
            logs_category = await get_or_create_category(ctx.guild, "XSI Logs")
            (created if len(ctx.guild.categories) > before else used_existing).append(f"Logs Category: **{logs_category.name}**")

        if needs_info_category:
            before = len(ctx.guild.categories)
            info_category = await get_or_create_category(ctx.guild, "XSI Info")
            (created if len(ctx.guild.categories) > before else used_existing).append(f"Info Category: **{info_category.name}**")

        if "ticketpanel" not in exclusions and tickets_category is not None and info_category is not None:
            before = len(ctx.guild.text_channels)
            ticket_panel = await get_or_create_text_channel(
                ctx.guild,
                "open-a-ticket",
                category=info_category,
                topic="Open a ticket here.",
            )
            settings["ticket_panel_channel_id"] = ticket_panel.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Ticket Panel Channel: {ticket_panel.mention}")

            ticket_embed = discord.Embed(
                title="🎟️ Open a Ticket",
                description="Click the button below to open a ticket.\n\nAvailability Times: 9am to 10pm UK",
                color=discord.Color.green(),
            )
            await ticket_panel.send(embed=ticket_embed, view=TicketsButton())
        elif "ticketpanel" in exclusions:
            skipped.append("Ticket Panel Channel")

        if "welcome" not in exclusions and info_category is not None:
            before = len(ctx.guild.text_channels)
            welcome = await get_or_create_text_channel(
                ctx.guild,
                "welcome",
                category=info_category,
                topic="New member welcomes.",
            )
            settings["welcome_channel_id"] = welcome.id
            settings.setdefault("welcome_message", DEFAULT_WELCOME_MESSAGE)
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Welcome Channel: {welcome.mention}")
        else:
            skipped.append("Welcome Channel")

        if "rules" not in exclusions and info_category is not None:
            before = len(ctx.guild.text_channels)
            rules_channel = await get_or_create_text_channel(
                ctx.guild,
                "rules",
                category=info_category,
                topic="Server rules.",
            )
            settings["rules_channel_id"] = rules_channel.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Rules Channel: {rules_channel.mention}")
            await send_default_rules_embed(rules_channel)
        else:
            skipped.append("Rules Channel")

        if "giveaways" not in exclusions and info_category is not None:
            before = len(ctx.guild.text_channels)
            giveaways = await get_or_create_text_channel(
                ctx.guild,
                "giveaways",
                category=info_category,
                topic="Giveaways are posted here.",
            )
            settings["giveaways_channel_id"] = giveaways.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Giveaways Channel: {giveaways.mention}")
        else:
            skipped.append("Giveaways Channel")

        if "wall" not in exclusions and logs_category is not None:
            before = len(ctx.guild.text_channels)
            wall = await get_or_create_text_channel(
                ctx.guild,
                "wall-of-knobs",
                category=logs_category,
                topic="Moderation warning logs.",
            )
            settings["wall_channel_id"] = wall.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Wall Channel: {wall.mention}")
        else:
            skipped.append("Wall Channel")

        if "leaves" not in exclusions and logs_category is not None:
            before = len(ctx.guild.text_channels)
            leaves = await get_or_create_text_channel(
                ctx.guild,
                "leaves",
                category=logs_category,
                topic="Member leave logs / Board of Guilt.",
            )
            settings["leaves_channel_id"] = leaves.id
            settings["guilt_channel_id"] = leaves.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Leaves / Board of Guilt Channel: {leaves.mention}")
        else:
            skipped.append("Leaves / Board of Guilt Channel")

        if "transcripts" not in exclusions and logs_category is not None:
            before = len(ctx.guild.text_channels)
            transcripts = await get_or_create_text_channel(
                ctx.guild,
                "ticket-transcripts",
                category=logs_category,
                topic="Ticket transcripts can be posted here later.",
            )
            settings["transcript_channel_id"] = transcripts.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Transcript Channel: {transcripts.mention}")
        else:
            skipped.append("Transcript Channel")

        if "stafflogs" not in exclusions and logs_category is not None:
            before = len(ctx.guild.text_channels)
            staff_logs = await get_or_create_text_channel(
                ctx.guild,
                "staff-logs",
                category=logs_category,
                topic="Staff action logs can be posted here later.",
            )
            settings["staff_logs_channel_id"] = staff_logs.id
            (created if len(ctx.guild.text_channels) > before else used_existing).append(f"Staff Logs Channel: {staff_logs.mention}")
        else:
            skipped.append("Staff Logs Channel")

        save_server_settings()

    except discord.Forbidden:
        await ctx.send("❌ I need **Manage Channels** permission to run setup.")
        return
    except discord.HTTPException as exc:
        log.exception("Setup failed: %s", exc)
        await ctx.send("❌ Discord rejected part of the setup. Check my permissions and try again.")
        return

    embed = discord.Embed(
        title="✅ XSI Setup Complete",
        description="Server setup has been saved for this server.",
        color=discord.Color.green(),
    )

    if created:
        embed.add_field(name="Created", value="\n".join(created)[:1024], inline=False)

    if used_existing:
        embed.add_field(name="Already Existing / Reused", value="\n".join(used_existing)[:1024], inline=False)

    if skipped:
        embed.add_field(name="Skipped", value="\n".join(skipped)[:1024], inline=False)

    if unknown:
        embed.add_field(name="Unknown Skip Words Ignored", value=", ".join(unknown)[:1024], inline=False)

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

    await ctx.send(embed=embed)


# ---------------- SETUP HYBRID COMMANDS ----------------
@bot.hybrid_command(name="setticketcategory", aliases=["setcategory"], description="Set the category where tickets are created")
@commands.has_permissions(administrator=True)
@app_commands.describe(category="Ticket category. Leave empty to use this channel's current category.")
async def setticketcategory(ctx: commands.Context, category: Optional[discord.CategoryChannel] = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = category

    if target is None:
        if isinstance(ctx.channel, discord.TextChannel) and ctx.channel.category is not None:
            target = ctx.channel.category
        else:
            await ctx.send("❌ This channel is not inside a category. Use `!setticketcategory CATEGORY_ID` or `/setticketcategory`.")
            return

    settings = get_guild_settings(ctx.guild.id)
    settings["ticket_category_id"] = target.id
    save_server_settings()

    await ctx.send(f"✅ Ticket category set to **{target.name}**.")


@bot.hybrid_command(name="setgulitcategory", aliases=["setgulitchannel"], description="Set the Board of Guilt leave-log channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Board of Guilt text channel. Leave empty to use this channel.")
async def setgulitcategory(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_guilt_channel_from_command(ctx, channel)


@bot.hybrid_command(name="setguiltchannel", aliases=["setguiltcategory"], description="Set the Board of Guilt leave-log channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Board of Guilt text channel. Leave empty to use this channel.")
async def setguiltchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_guilt_channel_from_command(ctx, channel)


@bot.hybrid_command(name="setleaveschannel", description="Set the leaves / Board of Guilt channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Leaves text channel. Leave empty to use this channel.")
async def setleaveschannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_guilt_channel_from_command(ctx, channel)


@bot.hybrid_command(name="setwallchannel", description="Set the Wall of Knobs moderation-log channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Wall of Knobs text channel. Leave empty to use this channel.")
async def setwallchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = channel
    if target is None:
        if isinstance(ctx.channel, discord.TextChannel):
            target = ctx.channel
        else:
            await ctx.send("❌ Please choose a text channel.")
            return

    settings = get_guild_settings(ctx.guild.id)
    settings["wall_channel_id"] = target.id
    save_server_settings()

    await ctx.send(f"✅ Wall of Knobs channel set to {target.mention}.")


async def set_simple_channel_from_command(
    ctx: commands.Context,
    channel: Optional[discord.TextChannel],
    setting_key: str,
    label: str,
) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = channel
    if target is None:
        if isinstance(ctx.channel, discord.TextChannel):
            target = ctx.channel
        else:
            await ctx.send("❌ Please choose a text channel.")
            return

    settings = get_guild_settings(ctx.guild.id)
    settings[setting_key] = target.id
    save_server_settings()

    await ctx.send(f"✅ {label} set to {target.mention}.")


@bot.hybrid_command(name="setruleschannel", description="Set the rules channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Rules text channel. Leave empty to use this channel.")
async def setruleschannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_simple_channel_from_command(ctx, channel, "rules_channel_id", "Rules channel")


@bot.hybrid_command(name="setgiveawayschannel", description="Set the giveaways channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Giveaways text channel. Leave empty to use this channel.")
async def setgiveawayschannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_simple_channel_from_command(ctx, channel, "giveaways_channel_id", "Giveaways channel")


@bot.hybrid_command(name="settranscriptchannel", description="Set the ticket transcript channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Transcript text channel. Leave empty to use this channel.")
async def settranscriptchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_simple_channel_from_command(ctx, channel, "transcript_channel_id", "Ticket transcript channel")


@bot.hybrid_command(name="setstafflogchannel", description="Set the staff logs channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Staff logs text channel. Leave empty to use this channel.")
async def setstafflogchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_simple_channel_from_command(ctx, channel, "staff_logs_channel_id", "Staff logs channel")


@bot.hybrid_command(name="setticketpanelchannel", description="Set the channel where the ticket panel should be posted")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="Ticket panel text channel. Leave empty to use this channel.")
async def setticketpanelchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_simple_channel_from_command(ctx, channel, "ticket_panel_channel_id", "Ticket panel channel")


@bot.hybrid_command(name="setwelcome", description="Set the welcome channel and welcome message")
@commands.has_permissions(administrator=True)
@app_commands.describe(
    channel="Welcome text channel. Leave empty to use this channel.",
    message="Welcome message. Use {user}, @user, {server}, {username}, or {display_name}.",
)
async def setwelcome(
    ctx: commands.Context,
    channel: Optional[discord.TextChannel] = None,
    *,
    message: Optional[str] = None,
) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = channel
    if target is None:
        if isinstance(ctx.channel, discord.TextChannel):
            target = ctx.channel
        else:
            await ctx.send("❌ Please choose a text channel.")
            return

    welcome_message = message.strip() if isinstance(message, str) and message.strip() else DEFAULT_WELCOME_MESSAGE

    settings = get_guild_settings(ctx.guild.id)
    settings["welcome_channel_id"] = target.id
    settings["welcome_message"] = welcome_message
    save_server_settings()

    preview = format_welcome_message(welcome_message, ctx.author) if isinstance(ctx.author, discord.Member) else welcome_message

    await ctx.send(
        f"✅ Welcome channel set to {target.mention}.\n"
        f"Preview: {preview}",
        allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
    )


@bot.hybrid_command(name="testwelcome", description="Test the welcome message")
@commands.has_permissions(administrator=True)
async def testwelcome(ctx: commands.Context) -> None:
    if ctx.guild is None or not isinstance(ctx.author, discord.Member):
        await ctx.send("❌ This command only works inside a server.")
        return

    message = format_welcome_message(get_welcome_message(ctx.guild), ctx.author)
    await ctx.send(
        message,
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


@bot.hybrid_command(name="setstaffrole", description="Set the staff role that can see and close tickets")
@commands.has_permissions(administrator=True)
@app_commands.describe(role="Staff role")
async def setstaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    settings = get_guild_settings(ctx.guild.id)
    settings["staff_role_ids"] = [role.id]
    save_server_settings()

    await ctx.send(f"✅ Staff role set to {role.mention}.")


@bot.hybrid_command(name="addstaffrole", description="Add another staff role for tickets/mod bypass")
@commands.has_permissions(administrator=True)
@app_commands.describe(role="Staff role to add")
async def addstaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    settings = get_guild_settings(ctx.guild.id)
    role_ids = get_staff_role_ids(ctx.guild.id)

    if role.id not in role_ids:
        role_ids.append(role.id)

    settings["staff_role_ids"] = role_ids
    save_server_settings()

    await ctx.send(f"✅ Added staff role {role.mention}.")


@bot.hybrid_command(name="removestaffrole", description="Remove a staff role from bot settings")
@commands.has_permissions(administrator=True)
@app_commands.describe(role="Staff role to remove")
async def removestaffrole(ctx: commands.Context, role: discord.Role) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    settings = get_guild_settings(ctx.guild.id)
    role_ids = [role_id for role_id in get_staff_role_ids(ctx.guild.id) if role_id != role.id]
    settings["staff_role_ids"] = role_ids
    save_server_settings()

    await ctx.send(f"✅ Removed staff role {role.mention}.")


@bot.hybrid_command(name="setticketownername", description="Set the name used in ticket offline auto-replies")
@commands.has_permissions(administrator=True)
@app_commands.describe(name="Name to show in ticket offline messages")
async def setticketownername(ctx: commands.Context, *, name: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    clean_name = name.strip()
    if not clean_name:
        await ctx.send("❌ Please give me a name.")
        return

    settings = get_guild_settings(ctx.guild.id)
    settings["ticket_owner_name"] = clean_name
    save_server_settings()

    await ctx.send(f"✅ Ticket owner display name set to **{discord.utils.escape_markdown(clean_name)}**.")


@bot.hybrid_command(name="requiredpermissions", aliases=["permissions", "perms"], description="Show the permissions XSI needs")
@commands.has_permissions(administrator=True)
async def requiredpermissions(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    bot_member = ctx.guild.me or (ctx.guild.get_member(bot.user.id) if bot.user is not None else None)

    if bot_member is None:
        await ctx.send("❌ I could not check my permissions in this server.")
        return

    permissions = bot_member.guild_permissions
    missing = missing_permission_names(permissions)

    embed = discord.Embed(
        title="🔐 XSI Required Permissions",
        description=(
            "Use this to check whether XSI can run setup, tickets, welcomes, logs, giveaways, "
            "and moderation correctly."
        ),
        color=discord.Color.green() if not missing else discord.Color.orange(),
    )

    required_lines = permission_lines(permissions, REQUIRED_PERMISSION_ITEMS)
    optional_lines = permission_lines(permissions, OPTIONAL_PERMISSION_ITEMS)

    embed.add_field(
        name="Required Bot Permissions",
        value="\n".join(required_lines),
        inline=False,
    )

    embed.add_field(
        name="Optional / Future Permissions",
        value="\n".join(optional_lines),
        inline=False,
    )

    role_note = (
        f"My top role: {bot_member.top_role.mention}\n"
        "Move XSI's role above members it needs to kick/ban. "
        "Discord will block moderation if my role is lower than the target member's role."
    )
    embed.add_field(name="Role Position", value=role_note, inline=False)

    intent_note = (
        "Also enable these in the Discord Developer Portal:\n"
        "✅ Message Content Intent — for `!` commands and automod scanning\n"
        "✅ Server Members Intent — for welcome/leave messages"
    )
    embed.add_field(name="Developer Portal Intents", value=intent_note, inline=False)

    app_command_note = (
        "The invite link must include both scopes: `bot` and `applications.commands`.\n"
        "Server/channel permissions should allow staff to use application commands."
    )
    embed.add_field(name="Slash Commands", value=app_command_note, inline=False)

    if missing:
        embed.add_field(
            name="Missing Right Now",
            value="❌ " + "\n❌ ".join(missing),
            inline=False,
        )
    else:
        embed.add_field(
            name="Status",
            value="✅ XSI has the main permissions it needs.",
            inline=False,
        )

    if bot.user is not None:
        invite_url = discord.utils.oauth_url(
            bot.user.id,
            permissions=build_recommended_permissions(),
            scopes=("bot", "applications.commands"),
        )
        embed.add_field(
            name="Recommended Invite Link",
            value=f"[Re-invite XSI with recommended permissions]({invite_url})",
            inline=False,
        )

    await ctx.send(embed=embed)


@bot.hybrid_command(name="checksetup", description="Show this server's bot setup")
@commands.has_permissions(administrator=True)
async def checksetup(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    settings = get_guild_settings(ctx.guild.id)
    category_id = parse_int(settings.get("ticket_category_id"))
    category = get_ticket_category(ctx.guild)
    if category is not None:
        category_text = f"{category.name} (`{category.id}`)"
    else:
        category_text = mention_category(ctx.guild, category_id)

    staff_roles = []
    for role_id in get_staff_role_ids(ctx.guild.id):
        role = ctx.guild.get_role(role_id)
        staff_roles.append(role.mention if role is not None else f"Missing role `{role_id}`")

    embed = discord.Embed(
        title="⚙️ Bot Setup",
        color=discord.Color.blue(),
    )
    smart_count = len(get_smart_messages(ctx.guild.id))

    embed.add_field(name="Ticket Category", value=category_text, inline=False)
    embed.add_field(name="Ticket Panel Channel", value=mention_channel(ctx.guild, get_ticket_panel_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Welcome Channel", value=mention_channel(ctx.guild, get_welcome_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Welcome Message", value=get_welcome_message(ctx.guild), inline=False)
    embed.add_field(name="Rules Channel", value=mention_channel(ctx.guild, get_rules_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Giveaways Channel", value=mention_channel(ctx.guild, get_giveaways_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Leaves / Board of Guilt Channel", value=mention_channel(ctx.guild, get_guilt_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Wall of Knobs Channel", value=mention_channel(ctx.guild, get_wall_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Transcript Channel", value=mention_channel(ctx.guild, get_transcript_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Staff Logs Channel", value=mention_channel(ctx.guild, get_staff_logs_channel_id(ctx.guild)), inline=False)
    embed.add_field(name="Ticket Owner Name", value=get_ticket_owner_name_for_guild(ctx.guild), inline=False)
    embed.add_field(name="Staff Roles", value="\n".join(staff_roles) if staff_roles else "Not set", inline=False)
    embed.add_field(name="Smart Messages", value=str(smart_count), inline=False)

    await ctx.send(embed=embed)


@bot.hybrid_command(name="synccommands", description="Force slash commands to refresh in this server")
@commands.has_permissions(administrator=True)
async def synccommands(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    count = await sync_commands_for_guild(ctx.guild)
    await ctx.send(f"✅ Synced {count} slash command(s) in **{ctx.guild.name}**.")


# ---------------- TICKET COMMANDS ----------------
@bot.hybrid_command(name="tickets", aliases=["ticket"], description="Send the ticket panel with auto messages")
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


@bot.hybrid_command(name="tickets2", description="Send the basic ticket panel")
@commands.has_permissions(administrator=True)
async def tickets2(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title="🎫 Open a Ticket",
        description="Click the button below to create a ticket.",
        color=discord.Color.green(),
    )

    await ctx.send(embed=embed, view=Tickets2Button())


@bot.hybrid_command(name="checkcategory", description="Show the current ticket category")
@commands.has_permissions(administrator=True)
async def checkcategory(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    category = get_ticket_category(ctx.guild)

    if category is None:
        await ctx.send("❌ No ticket category found. Use `!setticketcategory` or `/setticketcategory`.")
    else:
        await ctx.send(f"✅ Current ticket category: **{category.name}**")


# ---------------- SALLY / UTILITY COMMANDS ----------------
@bot.hybrid_command(name="sallyspeak", description="Make the bot say a message")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(message="Message for the bot to send")
async def sallyspeak(ctx: commands.Context, *, message: str) -> None:
    if ctx.interaction is None:
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    await ctx.send(message)


@bot.hybrid_command(name="embed", description="Send a simple embed")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(title="Embed title", description="Embed description")
async def embed_command(ctx: commands.Context, title: str, *, description: str) -> None:
    if ctx.interaction is None:
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


@bot.hybrid_command(name="rules", description="Send the server rules embed")
async def rules(ctx: commands.Context) -> None:
    if ctx.interaction is None:
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


@bot.hybrid_command(name="slotinfo", description="Show slot info")
async def slotinfo(ctx: commands.Context) -> None:
    await ctx.send("❌ Sloty has been removed from this bot.")


# ---------------- SMART MESSAGE COMMANDS ----------------
@bot.hybrid_command(name="addsmartmessage", description="Add an automatic smart reply trigger")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(trigger="Word or phrase XSI should detect", reply="Reply to send. Supports {user}, {server}, {username}, {display_name}.")
async def addsmartmessage(ctx: commands.Context, trigger: str, *, reply: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    clean_trigger = normalize_text(trigger)
    clean_reply = reply.strip()

    if not clean_trigger or not clean_reply:
        await ctx.send("❌ Use: `!addsmartmessage price Please open a ticket for prices.`")
        return

    if len(clean_trigger) > 80:
        await ctx.send("❌ Trigger is too long. Keep it under 80 characters.")
        return

    if len(clean_reply) > 1500:
        await ctx.send("❌ Reply is too long. Keep it under 1500 characters.")
        return

    smart_messages = get_smart_messages(ctx.guild.id)
    smart_messages[clean_trigger] = clean_reply
    get_guild_settings(ctx.guild.id)["smart_messages"] = smart_messages
    save_server_settings()

    await ctx.send(f"✅ Smart message added. Trigger: `{discord.utils.escape_markdown(clean_trigger)}`")


@bot.hybrid_command(name="removesmartmessage", description="Remove a smart reply trigger")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(trigger="Trigger to remove")
async def removesmartmessage(ctx: commands.Context, trigger: str) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    clean_trigger = normalize_text(trigger)
    smart_messages = get_smart_messages(ctx.guild.id)

    if clean_trigger not in smart_messages:
        await ctx.send("❌ That smart message trigger was not found.")
        return

    smart_messages.pop(clean_trigger, None)
    get_guild_settings(ctx.guild.id)["smart_messages"] = smart_messages
    save_server_settings()

    await ctx.send(f"✅ Removed smart message trigger: `{discord.utils.escape_markdown(clean_trigger)}`")


@bot.hybrid_command(name="listsmartmessages", description="List this server's smart message triggers")
@commands.has_permissions(manage_messages=True)
async def listsmartmessages(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    smart_messages = get_smart_messages(ctx.guild.id)

    if not smart_messages:
        await ctx.send("No smart messages set. Add one with `!addsmartmessage price Please open a ticket.`")
        return

    lines = []
    for trigger, reply in smart_messages.items():
        safe_reply = discord.utils.escape_markdown(reply[:80])
        lines.append(f"• `{discord.utils.escape_markdown(trigger)}` → {safe_reply}")

    embed = discord.Embed(
        title="🧠 Smart Messages",
        description="\n".join(lines)[:4000],
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(name="clearsmartmessages", description="Remove all smart messages in this server")
@commands.has_permissions(administrator=True)
async def clearsmartmessages(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    get_guild_settings(ctx.guild.id)["smart_messages"] = {}
    save_server_settings()

    await ctx.send("✅ Cleared all smart messages for this server.")


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


async def finish_giveaway(channel_id: int, message_id: int, prize: str, seconds: int, test: bool = False) -> None:
    await asyncio.sleep(seconds)

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.HTTPException:
            log.warning("Giveaway channel could not be found: %s", channel_id)
            return

    if not isinstance(channel, discord.TextChannel):
        log.warning("Giveaway channel is not a text channel: %s", channel_id)
        return

    try:
        message = await channel.fetch_message(message_id)
    except discord.HTTPException:
        await channel.send("❌ Giveaway message was deleted or could not be found.")
        return

    entries: list[discord.User | discord.Member] = []

    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    entries.append(user)

    if len(entries) == 0:
        await channel.send(f"❌ No one entered the {prize} giveaway.")
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

    await channel.send(embed=end_embed)
    await channel.send(f"🎉 Congratulations {winner.mention}! You won {prize}!")


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

    # Giveaway completion works for both prefix and slash command starts.
    asyncio.create_task(finish_giveaway(message.channel.id, message.id, prize, seconds, test=test))


GIVEAWAY_PRIZE_CHOICES = [
    app_commands.Choice(name="Normal", value="normal"),
    app_commands.Choice(name="Hard Trade", value="hard trade"),
    app_commands.Choice(name="Very Hard Trade", value="very hard trade"),
]


@bot.hybrid_command(name="giveaway", description="Start a 24-hour giveaway")
@commands.has_permissions(administrator=True)
@app_commands.describe(amount="Amount of cars/trades", prize_type="Prize type")
@app_commands.choices(prize_type=GIVEAWAY_PRIZE_CHOICES)
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


@bot.hybrid_command(name="testgiveaway", description="Start a 30-second test giveaway")
@commands.has_permissions(administrator=True)
@app_commands.describe(amount="Amount of cars/trades", prize_type="Prize type")
@app_commands.choices(prize_type=GIVEAWAY_PRIZE_CHOICES)
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
@bot.hybrid_command(name="warn", description="Manually warn a member")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(member="The member to warn", reason="The reason for the warning")
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
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


@bot.hybrid_command(name="warnings", description="Check a member's warnings")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(member="Member to check. Leave empty to check yourself.")
async def warnings_command(ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    target = member

    if target is None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("❌ I could not identify that member.")
            return
        target = ctx.author

    count = get_warnings(ctx.guild.id, target.id)
    await ctx.send(f"⚠️ {target.mention} has {count}/{MAX_WARNINGS} warnings.")


@bot.hybrid_command(name="clearwarnings", description="Clear a member's warnings")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(member="Member whose warnings should be cleared")
async def clearwarnings(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    clear_warnings(ctx.guild.id, member.id)
    await ctx.send(f"✅ Cleared warnings for {member.mention}.")


@bot.hybrid_command(name="knobstatus", description="Show moderation status and banned phrases")
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


@bot.hybrid_command(name="manualwall", description="Manually add someone to the Wall of Knobs")
@commands.has_permissions(manage_messages=True)
@app_commands.describe(member="Member to add", offence="Offence/reason")
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


@bot.hybrid_command(name="testguilt", description="Test the Board of Guilt system")
@commands.has_permissions(administrator=True)
async def testguilt(ctx: commands.Context) -> None:
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")


# ---------------- ERROR HANDLERS ----------------
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You do not have permission to use that command."
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

    if isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ I could not find that channel.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Missing info. Examples:\n"
            "`!setup` or `!setup no giveaways`\n"
            "`!setticketcategory`\n"
            "`!setgulitcategory` / `!setleaveschannel`\n"
            "`!setwallchannel`\n"
            "`!setwelcome`\n"
            "`!addsmartmessage price Please open a ticket.`\n"
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
        await ctx.send("❌ Bad command format. Check the number/user/channel/role you typed.")
        return

    if isinstance(error, commands.HybridCommandError):
        original = error.original
        if isinstance(original, app_commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use that command.")
            return
        log.exception("Hybrid command failed: %s", original)
    elif isinstance(error, commands.CommandInvokeError):
        log.exception("Command failed: %s", error.original)
    else:
        log.exception("Command error: %s", error)

    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN BOT ----------------
def main() -> None:
    token = os.getenv(TOKEN_NAME)

    if not token:
        log.error("❌ %s not found in Railway variables.", TOKEN_NAME)
        return

    bot.run(token)


if __name__ == "__main__":
    main()

