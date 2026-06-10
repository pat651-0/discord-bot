import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import re
import time
import random
import asyncio
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo


# ---------------- TOKEN ----------------
TOKEN_NAME = "TOKEN"


# ---------------- IDS ----------------

STAFF_ROLE_IDS = [
    1470379426297548957
]

TICKET_CATEGORY_IDS = [
    1472860643475329096,  # your server ticket category
    1507876447467995226   # friend's server ticket category
]

TICKET_OWNER_NAMES_BY_CATEGORY = {
    1472860643475329096: "Filiy V",  # your server
    1507876447467995226: "Mruss"     # friend's server
}

DEFAULT_TICKET_OWNER_NAME = "Filiy V"

LEAVES_CHANNEL_ID = 1475079442291363901
WALL_CHANNEL_ID = 1509103133479932085

# Your Discord ID. Your replies trigger the ticket-owner DM for !tickets only.
OWNER_USER_IDS = [
    1137385938155221073
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

# use "kick" or "ban"
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

recent_messages = defaultdict(list)
bot.synced = False


# ---------------- JSON HELPERS ----------------
def load_json(file_name, default):
    if not os.path.exists(file_name):
        return default

    try:
        with open(file_name, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(file_name, data):
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


yapper_settings = load_json(YAPPER_SETTINGS_FILE, {})
warnings_store = load_json(WARNINGS_FILE, {})
ticket_owners = load_json(TICKET_OWNERS_FILE, {})


def save_yapper_settings():
    save_json(YAPPER_SETTINGS_FILE, yapper_settings)


def save_warnings():
    save_json(WARNINGS_FILE, warnings_store)


def save_ticket_owners():
    save_json(TICKET_OWNERS_FILE, ticket_owners)


# ---------------- TICKET HELPERS ----------------
def get_ticket_category(guild):
    guild_id = str(guild.id)

    saved_data = yapper_settings.get(guild_id)

    if saved_data:
        try:
            if isinstance(saved_data, dict):
                saved_category_id = int(saved_data.get("ticket_category_id"))
            else:
                saved_category_id = int(saved_data)

            category = guild.get_channel(saved_category_id)

            if isinstance(category, discord.CategoryChannel):
                return category
        except Exception:
            pass

    for category_id in TICKET_CATEGORY_IDS:
        category = guild.get_channel(category_id)

        if isinstance(category, discord.CategoryChannel):
            return category

    return None


def clean_channel_name(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")[:40]


def is_fily_offline_hours():
    now_uk = datetime.now(UK_TIMEZONE)
    hour = now_uk.hour

    return hour < AVAILABLE_START_HOUR or hour >= AVAILABLE_END_HOUR


def get_ticket_owner_display_name(channel):
    channel_id = str(channel.id)
    data = ticket_owners.get(channel_id)

    if data:
        saved_name = data.get("owner_display_name")
        if saved_name:
            return saved_name

    if channel.category is not None:
        return TICKET_OWNER_NAMES_BY_CATEGORY.get(
            channel.category.id,
            DEFAULT_TICKET_OWNER_NAME
        )

    return DEFAULT_TICKET_OWNER_NAME


def ticket_auto_messages_enabled(channel):
    data = ticket_owners.get(str(channel.id))

    if not data:
        return False

    return bool(data.get("auto_messages", False))


async def create_ticket_channel(interaction, auto_messages):
    guild = interaction.guild
    user = interaction.user

    if guild is None:
        await interaction.response.send_message("❌ This only works inside a server.", ephemeral=True)
        return

    category = get_ticket_category(guild)

    if category is None:
        await interaction.response.send_message(
            "❌ Ticket category not found. Admin can use !setcategory CATEGORY_ID.",
            ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    for role_id in STAFF_ROLE_IDS:
        role = guild.get_role(role_id)

        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

    channel_name = f"ticket-{clean_channel_name(user.name)}"
    existing = discord.utils.get(category.text_channels, name=channel_name)

    if existing:
        await interaction.response.send_message(
            f"❌ You already have a ticket: {existing.mention}",
            ephemeral=True
        )
        return

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I do not have permission to create ticket channels.",
            ephemeral=True
        )
        return

    owner_display_name = TICKET_OWNER_NAMES_BY_CATEGORY.get(
        category.id,
        DEFAULT_TICKET_OWNER_NAME
    )

    ticket_owners[str(channel.id)] = {
        "owner_id": user.id,
        "last_dm_time": 0,
        "last_away_reply_time": 0,
        "auto_messages": auto_messages,
        "owner_display_name": owner_display_name
    }
    save_ticket_owners()

    if auto_messages:
        ticket_embed = discord.Embed(
            title="🎟️ Ticket Opened",
            description=(
                "Please explain what you need help with.\n\n"
                "*Availability Times:* 9am to 10pm UK"
            ),
            color=discord.Color.green()
        )
    else:
        ticket_embed = discord.Embed(
            title="🎫 Ticket Opened",
            description="Please explain what you need help with.",
            color=discord.Color.green()
        )

    await channel.send(
        content=f"{user.mention}",
        embed=ticket_embed,
        view=CloseButton()
    )

    try:
        await user.send(
            f"🎫 Your ticket has been created in *{guild.name}*.\n"
            f"Ticket: {channel.mention}"
        )
    except Exception:
        pass

    await interaction.response.send_message(f"✅ Created {channel.mention}", ephemeral=True)


# ---------------- WARNING HELPERS ----------------
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


# ---------------- SMART DETECTION ----------------
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
        embed.add_field(name="Message", value=safe_message, inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(embed=embed)


async def punish_if_needed(guild, channel, member, offence, warning_count):
    if warning_count < MAX_WARNINGS:
        return False

    if member.guild_permissions.administrator:
        await channel.send(f"❌ {member.mention} reached max warnings, but I cannot punish an admin.")
        return True

    bot_member = guild.me or guild.get_member(bot.user.id)

    if bot_member.top_role <= member.top_role:
        await channel.send(
            f"❌ {member.mention} reached max warnings, but my role is not high enough."
        )
        return True

    if PUNISHMENT_ON_MAX_WARNINGS.lower() == "ban":
        try:
            await member.send(
                f"🔨 You were banned from {guild.name}.\n"
                f"Reason: {offence}\n"
                f"You reached {MAX_WARNINGS} warnings."
            )
        except Exception:
            pass

        await member.ban(
            reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}"
        )

        clear_warnings(member.id)
        return True

    try:
        await member.send(
            f"🔨 You were kicked from {guild.name}.\n"
            f"Reason: {offence}\n"
            f"You reached {MAX_WARNINGS} warnings."
        )
    except Exception:
        pass

    await member.kick(
        reason=f"Reached {MAX_WARNINGS} warnings. Last offence: {offence}"
    )

    clear_warnings(member.id)
    return True


# ---------------- TICKET BUTTONS ----------------
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="merged_close_ticket"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_id = str(interaction.channel.id)

        if channel_id in ticket_owners:
            del ticket_owners[channel_id]
            save_ticket_owners()

        await interaction.response.send_message("Closing ticket...", ephemeral=True)

        await asyncio.sleep(2)

        try:
            await interaction.channel.delete()
        except Exception:
            pass


class TicketsButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎟️ Open Ticket",
        style=discord.ButtonStyle.green,
        custom_id="tickets_system_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, auto_messages=True)


class Tickets2Button(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="tickets2_normal_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, auto_messages=False)


# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(TicketsButton())
    bot.add_view(Tickets2Button())
    bot.add_view(CloseButton())

    print("----------------------------")
    print(f"✅ Merged Bot logged in as {bot.user}")
    print("----------------------------")

    if not bot.synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"✅ Slash commands synced in {guild.name}")
            except Exception as e:
                print(f"❌ Slash sync failed in {guild.name}: {e}")

        bot.synced = True


# ---------------- BOARD OF GUILT ----------------
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        print(f"❌ Leaves channel not found: {LEAVES_CHANNEL_ID}")
        return

    embed = discord.Embed(
        title="⚖️ Board of Guilt",
        description=(
            f"💀 {member.name} left the server...\n\n"
            "Their name shall stay here forever."
        ),
        color=discord.Color.red()
    )

    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(content=f"bye I guess... <@{member.id}>", embed=embed)


# ---------------- TICKET AUTO MESSAGES ----------------
async def delete_message_later(message, seconds):
    await asyncio.sleep(seconds)

    try:
        await message.delete()
    except Exception:
        pass


async def maybe_dm_ticket_owner(message):
    channel_id = str(message.channel.id)

    if channel_id not in ticket_owners:
        return

    if not ticket_auto_messages_enabled(message.channel):
        return

    data = ticket_owners[channel_id]
    owner_id = int(data.get("owner_id", 0))

    # Do not DM the owner if they are the one replying
    if owner_id == message.author.id:
        return

    # Only your replies trigger the DM
    if message.author.id not in OWNER_USER_IDS:
        return

    now = time.time()
    last_dm_time = float(data.get("last_dm_time", 0))

    # Only DM once per hour per ticket
    if now - last_dm_time < TICKET_DM_COOLDOWN:
        return

    owner = message.guild.get_member(owner_id)

    if owner is None:
        try:
            owner = await message.guild.fetch_member(owner_id)
        except Exception:
            return

    try:
        await owner.send(
            f"📩 **Ticket Update**\n\n"
            f"{message.author.display_name} has replied to your ticket in *{message.guild.name}*.\n\n"
            f"Ticket: {message.channel.mention}\n\n"
            "Please check it when you can."
        )

        data["last_dm_time"] = now
        ticket_owners[channel_id] = data
        save_ticket_owners()

    except Exception:
        pass


async def maybe_send_away_auto_reply(message):
    channel_id = str(message.channel.id)

    if channel_id not in ticket_owners:
        return

    if not ticket_auto_messages_enabled(message.channel):
        return

    data = ticket_owners[channel_id]
    owner_id = int(data.get("owner_id", 0))

    # Only auto-reply when the ticket owner sends a message
    if message.author.id != owner_id:
        return

    # Only outside 9am to 10pm UK
    if not is_fily_offline_hours():
        return

    now = time.time()
    last_away_reply_time = float(data.get("last_away_reply_time", 0))

    # Cooldown, not an automatic timer
    if now - last_away_reply_time < AWAY_AUTO_REPLY_COOLDOWN:
        return

    owner_display_name = get_ticket_owner_display_name(message.channel)

    away_msg = await message.channel.send(
        f"{message.author.mention}\n"
        f"⏰ **{owner_display_name} is currently offline.**\n\n"
        "Available hours are *9:00 AM - 10:00 PM UK time*.\n"
        f"{owner_display_name} will reply when they’re back online.",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
    )

    data["last_away_reply_time"] = now
    ticket_owners[channel_id] = data
    save_ticket_owners()

    asyncio.create_task(delete_message_later(away_msg, AWAY_AUTO_REPLY_DELETE_AFTER))


# ---------------- AUTO MODERATION ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    await maybe_dm_ticket_owner(message)
    await maybe_send_away_auto_reply(message)

    member = message.author

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
            await message.channel.send("❌ I need Manage Messages permission.")
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
                await message.channel.send(f"❌ I do not have permission to punish {member.mention}.")
            except Exception as e:
                print(e)
                await message.channel.send("❌ Something went wrong while punishing.")

            return

        await send_wall_log(
            member=member,
            offence=offence,
            punishment="Warning",
            message_content=content,
            warning_count=warning_count
        )

        await message.channel.send(
            f"⚠️ {member.mention}, warning {warning_count}/{MAX_WARNINGS} — {offence}.\n"
            "Your message was deleted."
        )

        return

    await bot.process_commands(message)


# ---------------- YAPPER COMMANDS ----------------
@bot.command(name="tickets", aliases=["ticket"])
@commands.has_permissions(administrator=True)
async def tickets(ctx):
    embed = discord.Embed(
        title="🎟️ Open a Ticket to Trade",
        description=(
            "Click the button below to open a ticket.\n\n"
            "*Availability Times:* 9am to 10pm UK"
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketsButton())


@bot.command(name="tickets2")
@commands.has_permissions(administrator=True)
async def tickets2(ctx):
    embed = discord.Embed(
        title="🎫 Open a Ticket",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=Tickets2Button())


@bot.command()
@commands.has_permissions(administrator=True)
async def setcategory(ctx, category_id: int = None):
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    if category_id is None:
        if ctx.channel.category is None:
            await ctx.send("❌ This channel is not inside a category. Use !setcategory CATEGORY_ID.")
            return

        category = ctx.channel.category

    else:
        category = ctx.guild.get_channel(category_id)

    if not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ That ID is not a valid category in this server.")
        return

    yapper_settings[str(ctx.guild.id)] = category.id
    save_yapper_settings()

    await ctx.send(f"✅ Ticket category set to {category.name}.")


@bot.command()
@commands.has_permissions(administrator=True)
async def checkcategory(ctx):
    category = get_ticket_category(ctx.guild)

    if category is None:
        await ctx.send("❌ No ticket category found.")
    else:
        await ctx.send(f"✅ Current ticket category: {category.name}")


# ---------------- SALLY COMMANDS ----------------
@bot.command()
async def sallyspeak(ctx, *, message):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    await ctx.send(message)


@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_command(ctx, title, *, description):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed)


@bot.command()
async def rules(ctx):
    try:
        await ctx.message.delete()
    except Exception:
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
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)


@bot.command()
async def slotinfo(ctx):
    await ctx.send("❌ Sloty has been removed from this bot.")


# ---------------- GIVEAWAY COMMANDS ----------------
def make_prize(amount, prize_type):
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


async def start_giveaway(ctx, prize, seconds, test=False):
    title = "🎉 TEST GIVEAWAY 🎉" if test else "🎉 GIVEAWAY 🎉"
    time_text = "30 seconds" if test else "24 hours"

    embed = discord.Embed(
        title=title,
        description=(
            f"Prize: {prize}\n\n"
            "React with 🎉 to enter!\n\n"
            f"⏰ Ends in {time_text}"
        ),
        color=discord.Color.gold()
    )

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    await asyncio.sleep(seconds)

    try:
        message = await ctx.channel.fetch_message(message.id)
    except Exception:
        await ctx.send("❌ Giveaway message was deleted or could not be found.")
        return

    entries = []

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
        color=discord.Color.green()
    )

    await ctx.send(embed=end_embed)
    await ctx.send(f"🎉 Congratulations {winner.mention}! You won {prize}!")


@bot.command(name="giveaway")
@commands.has_permissions(administrator=True)
async def giveaway(ctx, amount: int, *, prize_type):
    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize = make_prize(amount, prize_type)

    if prize is None:
        await ctx.send(
            "❌ Use:\n"
            "!giveaway 4 Normal\n"
            "!giveaway 5 Hard Trade\n"
            "!giveaway 2 Very Hard Trade"
        )
        return

    await start_giveaway(ctx, prize, GIVEAWAY_TIME)


@bot.command(name="testgiveaway")
@commands.has_permissions(administrator=True)
async def testgiveaway(ctx, amount: int, *, prize_type):
    if amount <= 0:
        await ctx.send("❌ Amount must be at least 1.")
        return

    prize = make_prize(amount, prize_type)

    if prize is None:
        await ctx.send("❌ Use: !testgiveaway 1 Normal")
        return

    await start_giveaway(ctx, prize, TEST_GIVEAWAY_TIME, test=True)


# ---------------- KNOB COMMANDS ----------------
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
            moderator=ctx.author
        )

        await punish_if_needed(ctx.guild, ctx.channel, member, reason, warning_count)


@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    count = get_warnings(member.id)
    await ctx.send(f"⚠️ {member.mention} has {count}/{MAX_WARNINGS} warnings.")


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
            "Knob moderation is active.\n\n"
            f"Punishment: {PUNISHMENT_ON_MAX_WARNINGS.title()} after {MAX_WARNINGS} warnings\n"
            "Bad messages are automatically deleted.\n"
            "Sales, car trading, and Discord links are allowed.\n\n"
            "Banned phrases:\n"
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


@bot.command(name="testguilt")
@commands.has_permissions(administrator=True)
async def testguilt(ctx):
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")


# ---------------- SLASH WARN ----------------
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
            moderator=interaction.user
        )

        await punish_if_needed(interaction.guild, interaction.channel, member, reason, warning_count)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need Manage Messages permission to use this command.",
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
            "❌ Missing info. Examples:\n"
            "!tickets\n"
            "!tickets2\n"
            "!giveaway 4 Normal\n"
            "!sallyspeak message\n"
            "!warn @user reason\n"
            "!warnings @user\n"
            "!clearwarnings @user"
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad command format. Check the number/user you typed.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN BOT ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
