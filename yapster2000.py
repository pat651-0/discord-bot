import discord
from discord.ext import commands
import os
import json
import time
import random
import re
from datetime import datetime, timezone

# ==================================================
# YAPSTER2000
# Sally + Sloty + Yapper + Board of Guilt in one bot
# ==================================================

# Railway variable can be either TOKENS or TOKEN5
TOKEN = (os.getenv("TOKENS") or os.getenv("TOKEN5") or "").strip()

# Removes accidental quotes if pasted like "token"
TOKEN = TOKEN.strip('"').strip("'")

# ---------------- IDS ----------------
STAFF_ROLE_ID = 1470379426297548957
TICKET_CATEGORY_ID = 1472860643475329096
GAME_CORNER_CATEGORY_ID = 1500809187595259984
LEAVES_CHANNEL_ID = 1475079442291363901

# ---------------- FILES ----------------
COINS_FILE = "coins.json"
TICKETS_FILE = "tickets.json"

# Coins expire after 1 hour
COIN_LIFE_SECONDS = 60 * 60

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    case_insensitive=True
)

bot.remove_command("help")

VIEWS_ADDED = False


# ==================================================
# JSON HELPERS
# ==================================================
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


coins_store = load_json(COINS_FILE, {})
tickets_store = load_json(TICKETS_FILE, {})


def save_coins():
    save_json(COINS_FILE, coins_store)


def save_tickets():
    save_json(TICKETS_FILE, tickets_store)


# ==================================================
# GENERAL HELPERS
# ==================================================
def make_embed(title, description, color=0x8E7CC3):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Yapster2000")
    return embed


async def delete_command(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass


def clean_channel_name(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name[:40].strip("-")

    if not name:
        name = "user"

    return name


async def find_member(ctx, raw_target):
    if ctx.guild is None:
        return None

    if raw_target is None:
        return None

    raw_target = str(raw_target).strip()

    mention_match = re.fullmatch(r"<@!?(\d+)>", raw_target)

    if mention_match:
        user_id = int(mention_match.group(1))
    elif raw_target.isdigit():
        user_id = int(raw_target)
    else:
        lowered = raw_target.lower()

        for member in ctx.guild.members:
            if member.name.lower() == lowered or member.display_name.lower() == lowered:
                return member

        return None

    member = ctx.guild.get_member(user_id)

    if member is not None:
        return member

    try:
        return await ctx.guild.fetch_member(user_id)
    except Exception:
        return None


# ==================================================
# COIN SYSTEM
# ==================================================
def ensure_coin_list(user_id):
    uid = str(user_id)
    changed = False

    if uid not in coins_store:
        coins_store[uid] = []
        changed = True

    value = coins_store[uid]

    # Old format support: {"123": 5}
    if isinstance(value, int):
        amount = max(value, 0)
        expiry = time.time() + COIN_LIFE_SECONDS
        coins_store[uid] = [expiry for _ in range(amount)]
        changed = True

    elif isinstance(value, list):
        fixed = []

        for expiry in value:
            try:
                expiry = float(expiry)
                if expiry > time.time():
                    fixed.append(expiry)
            except Exception:
                pass

        coins_store[uid] = fixed
        changed = True

    else:
        coins_store[uid] = []
        changed = True

    if changed:
        save_coins()

    return coins_store[uid]


def get_coin_count(user_id):
    return len(ensure_coin_list(user_id))


def add_coins_to_user(user_id, amount):
    uid = str(user_id)
    ensure_coin_list(uid)

    expiry = time.time() + COIN_LIFE_SECONDS

    for _ in range(amount):
        coins_store[uid].append(expiry)

    save_coins()


def remove_coins_from_user(user_id, amount):
    uid = str(user_id)
    ensure_coin_list(uid)

    if len(coins_store[uid]) < amount:
        return False

    coins_store[uid].sort()
    coins_store[uid] = coins_store[uid][amount:]
    save_coins()
    return True


def get_next_expiry_text(user_id):
    coin_list = ensure_coin_list(user_id)

    if not coin_list:
        return "No valid coins"

    seconds_left = int(min(coin_list) - time.time())

    if seconds_left <= 0:
        return "Expiring now"

    minutes = seconds_left // 60
    seconds = seconds_left % 60

    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    return f"{minutes}m {seconds}s"


# ==================================================
# YAPPER TICKET SYSTEM
# ==================================================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="yapster_close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)

        try:
            await interaction.channel.delete()
        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to delete this ticket.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not close ticket: {e}", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎟️ Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="yapster_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message("❌ This only works in a server.", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)
        bot_member = guild.me or guild.get_member(bot.user.id)

        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category not found or not a category.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        if bot_member is not None:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{clean_channel_name(user.name)}",
                category=category,
                overwrites=overwrites,
                reason="Yapster2000 ticket created"
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ I need Manage Channels permission.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not create ticket: {e}", ephemeral=True)
            return

        tickets_store[str(channel.id)] = {
            "type": "yapper_ticket",
            "user_id": str(user.id)
        }
        save_tickets()

        embed = make_embed(
            "🎟️ Ticket Created",
            (
                f"{user.mention}, welcome to your ticket.\n\n"
                "Staff will help you soon."
            ),
            discord.Color.green()
        )

        await channel.send(
            content=user.mention,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# ==================================================
# SLOTY SYSTEM
# ==================================================
class CloseWinTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Win Ticket",
        style=discord.ButtonStyle.red,
        custom_id="yapster_close_win_ticket"
    )
    async def close_win_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing win ticket...", ephemeral=True)

        try:
            await interaction.channel.delete()
        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to delete this ticket.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not close ticket: {e}", ephemeral=True)


async def create_win_ticket(interaction, result_name, result_emoji):
    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return None, "This only works inside a server."

    category = guild.get_channel(GAME_CORNER_CATEGORY_ID)
    staff_role = guild.get_role(STAFF_ROLE_ID)
    bot_member = guild.me or guild.get_member(bot.user.id)

    if category is None or not isinstance(category, discord.CategoryChannel):
        return None, "Game Corner category not found or not a category."

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
    }

    if bot_member is not None:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )

    if staff_role is not None:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

    try:
        channel = await guild.create_text_channel(
            name=f"slot-win-{clean_channel_name(user.name)}",
            category=category,
            overwrites=overwrites,
            reason="Yapster2000 slot win ticket created"
        )
    except discord.Forbidden:
        return None, "Missing Manage Channels permission."
    except Exception as e:
        return None, str(e)

    embed = make_embed(
        f"{result_emoji} Slot Win Ticket",
        (
            f"{user.mention} won **{result_name}**!\n\n"
            "Send a pic of what car you want 🚗📸\n"
            "Staff will sort your prize here."
        ),
        discord.Color.green()
    )

    embed.add_field(name="Winner", value=user.mention, inline=False)
    embed.add_field(name="Prize", value=f"{result_emoji} {result_name}", inline=False)

    await channel.send(
        content=user.mention,
        embed=embed,
        view=CloseWinTicketView()
    )

    return channel, None


class SlotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎰 Spin Slot Machine",
        style=discord.ButtonStyle.green,
        custom_id="yapster_spin_slot"
    )
    async def spin_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if get_coin_count(user.id) < 1:
            await interaction.response.send_message(
                "❌ You have no valid coins!\nCoins expire after **1 hour**.",
                ephemeral=True
            )
            return

        removed = remove_coins_from_user(user.id, 1)

        if not removed:
            await interaction.response.send_message(
                "❌ You have no valid coins!\nCoins expire after **1 hour**.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        roll = random.randint(1, 100)
        ticket_channel = None
        ticket_error = None

        if roll <= 70:
            result = "Nothing"
            emoji = "🚫"
            message = "Maybe next time 😭"
            color = discord.Color.red()

        elif roll <= 94:
            result = "Normal Cars"
            emoji = "🚘"
            message = "Not bad 🚘"
            color = discord.Color.blue()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        elif roll <= 99:
            result = "Hard Trade"
            emoji = "✨"
            message = "Nice pull ✨"
            color = discord.Color.gold()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        else:
            result = "Very Hard Trade"
            emoji = "💎"
            message = "🎰🎰💎🔥"
            color = discord.Color.purple()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        balance = get_coin_count(user.id)

        embed = make_embed("🎰 Slot Machine Result", message, color)
        embed.add_field(name="Result", value=f"{emoji} {result}", inline=False)
        embed.add_field(name="Coin Cost", value="1 coin", inline=True)
        embed.add_field(name="Balance", value=f"{balance} valid coin(s)", inline=True)

        if balance > 0:
            embed.add_field(name="Next Coin Expires", value=get_next_expiry_text(user.id), inline=False)

        if result != "Nothing":
            if ticket_channel is not None:
                embed.add_field(name="Win Ticket", value=ticket_channel.mention, inline=False)
            else:
                embed.add_field(name="Win Ticket", value=f"❌ Could not create ticket: {ticket_error}", inline=False)

        await interaction.followup.send(embed=embed)


# ==================================================
# READY EVENT
# ==================================================
@bot.event
async def on_ready():
    global VIEWS_ADDED

    if not VIEWS_ADDED:
        bot.add_view(TicketView())
        bot.add_view(CloseTicketView())
        bot.add_view(SlotView())
        bot.add_view(CloseWinTicketView())
        VIEWS_ADDED = True

    print("----------------------------")
    print(f"🤖 Yapster2000 logged in as {bot.user}")
    print("----------------------------")


# ==================================================
# BOARD OF GUILT
# ==================================================
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        print(f"❌ Leaves channel not found: {LEAVES_CHANNEL_ID}")
        return

    embed = make_embed(
        "⚖️ Board of Guilt",
        (
            f"💀 **{member.name}** left the server...\n\n"
            "Their name shall stay here forever."
        ),
        discord.Color.red()
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


# ==================================================
# TICKET CLOSE EVENT
# Gives exactly 1 coin when a Yapper ticket closes
# ==================================================
@bot.event
async def on_guild_channel_delete(channel):
    channel_id = str(channel.id)

    if channel_id not in tickets_store:
        return

    ticket_data = tickets_store[channel_id]
    user_id = None

    if isinstance(ticket_data, dict):
        user_id = ticket_data.get("user_id")
    elif isinstance(ticket_data, str):
        user_id = ticket_data

    if user_id:
        add_coins_to_user(user_id, 1)
        print(f"Ticket closed. Added exactly 1 coin to user ID {user_id}.")

    del tickets_store[channel_id]
    save_tickets()


# ==================================================
# YAPPER COMMANDS
# ==================================================
@bot.command(name="ticket")
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    embed = make_embed(
        "🎟️ Ticket Machine",
        "Click the button below to create a ticket.",
        discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketView())
    await delete_command(ctx)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("🏓 Yapster2000 is alive!")


# ==================================================
# SLOTY COMMANDS
# ==================================================
@bot.command(name="slotpanel")
@commands.has_permissions(administrator=True)
async def slot_panel(ctx):
    embed = make_embed(
        "🎰 Slot Machine",
        (
            "Click the button below to spin.\n\n"
            "**Chances:**\n"
            "🚫 Nothing — **70%**\n"
            "🚘 Normal Cars — **24%**\n"
            "✨ Hard Trade — **5%**\n"
            "💎 Very Hard Trade — **1%**\n\n"
            "Each spin costs **1 coin**.\n"
            "Coins expire after **1 hour**.\n\n"
            "Winning anything except **Nothing** opens a win ticket."
        ),
        discord.Color.green()
    )

    await ctx.send(embed=embed, view=SlotView())
    await delete_command(ctx)


@bot.command(name="coins", aliases=["balance", "bal"])
async def coins_command(ctx, target: str = None):
    if target is None:
        member = ctx.author
    else:
        member = await find_member(ctx, target)

        if member is None:
            await ctx.send("❌ I could not find that user. Try mentioning them or using their user ID.")
            return

    balance = get_coin_count(member.id)
    expiry_text = get_next_expiry_text(member.id)

    await ctx.send(
        f"🪙 {member.mention} has **{balance}** valid coin(s).\n"
        f"⏰ Next coin expires: **{expiry_text}**"
    )


@bot.command(name="addcoins", aliases=["givecoins"])
@commands.has_permissions(administrator=True)
async def addcoins_command(ctx, *args):
    if len(args) == 1:
        try:
            amount = int(args[0])
            member = ctx.author
        except Exception:
            await ctx.send("❌ Usage: `!addcoins 5` or `!addcoins @user 5`")
            return

    elif len(args) >= 2:
        # Supports both:
        # !addcoins @user 5
        # !addcoins 5 @user
        if args[0].isdigit():
            amount = int(args[0])
            target = args[1]
        else:
            target = args[0]
            try:
                amount = int(args[1])
            except Exception:
                await ctx.send("❌ Usage: `!addcoins 5 @user` or `!addcoins @user 5`")
                return

        member = await find_member(ctx, target)

        if member is None:
            await ctx.send("❌ I could not find that user. Try mentioning them or using their user ID.")
            return

    else:
        await ctx.send("❌ Usage: `!addcoins 5` or `!addcoins @user 5`")
        return

    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    add_coins_to_user(member.id, amount)

    await ctx.send(
        f"✅ Added **{amount}** coin(s) to {member.mention}.\n"
        f"⏰ These coins expire in **1 hour**."
    )

    await delete_command(ctx)


@bot.command(name="removecoins", aliases=["takecoins"])
@commands.has_permissions(administrator=True)
async def removecoins_command(ctx, *args):
    if len(args) == 1:
        try:
            amount = int(args[0])
            member = ctx.author
        except Exception:
            await ctx.send("❌ Usage: `!removecoins 5` or `!removecoins @user 5`")
            return

    elif len(args) >= 2:
        if args[0].isdigit():
            amount = int(args[0])
            target = args[1]
        else:
            target = args[0]
            try:
                amount = int(args[1])
            except Exception:
                await ctx.send("❌ Usage: `!removecoins 5 @user` or `!removecoins @user 5`")
                return

        member = await find_member(ctx, target)

        if member is None:
            await ctx.send("❌ I could not find that user. Try mentioning them or using their user ID.")
            return

    else:
        await ctx.send("❌ Usage: `!removecoins 5` or `!removecoins @user 5`")
        return

    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    success = remove_coins_from_user(member.id, amount)

    if success:
        await ctx.send(f"✅ Removed **{amount}** coin(s) from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have enough valid coins.")

    await delete_command(ctx)


# ==================================================
# SALLY COMMANDS
# ==================================================
@bot.command(name="sallyspeak", aliases=["salyspeak", "say", "speak", "yap"])
@commands.has_permissions(administrator=True)
async def sallyspeak(ctx, *, message: str = None):
    if message is None:
        await ctx.send("❌ Usage: `!sallyspeak your message here`")
        return

    await ctx.send(message)
    await delete_command(ctx)


@bot.command(name="embed", aliases=["panel"])
@commands.has_permissions(administrator=True)
async def embed_command(ctx, *, text: str = None):
    if text is None:
        await ctx.send("❌ Usage: `!embed Title | Message here`")
        return

    if "|" in text:
        title, body = text.split("|", 1)
    else:
        title = "📌 Info"
        body = text

    await ctx.send(embed=make_embed(title.strip(), body.strip()))
    await delete_command(ctx)


@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel = None, *, message: str = None):
    if channel is None or message is None:
        await ctx.send("❌ Usage: `!announce #channel message here`")
        return

    await channel.send(embed=make_embed("📢 Announcement", message))
    await delete_command(ctx)

    try:
        await ctx.send(f"✅ Announcement sent to {channel.mention}", delete_after=5)
    except Exception:
        pass


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
        "If you win anything except **Nothing**, a win ticket opens under **Game Corner**.\n\n"
        "In the ticket, send a pic of what car you want so staff can sort your prize. 🚗📸\n\n"
        "You’ll earn a coin when the trade is finished. 🎟️➡️🪙"
    )

    await ctx.send(embed=make_embed("🎰 Slot Machine Info 🎰", description))
    await delete_command(ctx)


@bot.command(name="rules")
@commands.has_permissions(administrator=True)
async def rules(ctx):
    description = (
        "**1.** No BS.\n"
        "**2.** No NSFW content.\n"
        "**3.** Mods and the owner never go first in trades.\n"
        "**4.** English only.\n"
        "**5.** For DMO, payments must be made first.\n"
        "**6.** Selling money drops or modded accounts will result in a permanent ban.\n"
        "**7.** Do not promote your server outside the self-promo channel.\n"
        "**8.** If you get timed out twice, you may be banned.\n"
        "**9.** Do not waste staff time."
    )

    await ctx.send(embed=make_embed("📜 Rules", description, discord.Color.red()))
    await delete_command(ctx)


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

    await ctx.send(embed=make_embed("🚗 Vehicle Condition Info", description))
    await delete_command(ctx)


@bot.command(name="heistinfo", aliases=["heists", "heist"])
@commands.has_permissions(administrator=True)
async def heistinfo(ctx):
    description = (
        "Heist payments are only available during these times:\n\n"
        "• **Tuesday:** 12 PM – 4 PM UK time\n"
        "• **Thursday:** 12 PM – 4 PM UK time\n\n"
        "Outside these times, please use another payment method."
    )

    await ctx.send(embed=make_embed("💰 Heist Payment Availability", description))
    await delete_command(ctx)


# ==================================================
# HELP / TEST COMMANDS
# ==================================================
@bot.command(name="testguilt")
async def testguilt(ctx):
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")


@bot.command(name="yapsterhelp", aliases=["help"])
async def yapsterhelp(ctx):
    help_text = (
        "**🤖 Yapster2000 Commands**\n\n"
        "**Yapper**\n"
        "`!ticket` — send ticket panel\n\n"
        "**Sloty**\n"
        "`!slotpanel` — send slot machine panel\n"
        "`!coins` — check your coins\n"
        "`!coins @user` — check another user\n"
        "`!addcoins 5` — add coins to yourself\n"
        "`!addcoins @user 5` — add coins to user\n"
        "`!removecoins @user 5` — remove coins\n\n"
        "**Sally**\n"
        "`!sallyspeak message` — bot says your message\n"
        "`!embed Title | Message` — clean embed\n"
        "`!announce #channel message` — announce in channel\n"
        "`!slotinfo` — slot info panel\n"
        "`!rules` — rules panel\n"
        "`!carinfo` — car info panel\n"
        "`!heistinfo` — heist info panel\n\n"
        "**Board of Guilt**\n"
        "`!testguilt` — test command\n"
        "Leaving users are logged automatically."
    )

    await ctx.send(help_text)


# ==================================================
# ERROR HANDLING
# ==================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing something. Try `!yapsterhelp`.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!yapsterhelp`.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ==================================================
# RUN BOT
# ==================================================
if not TOKEN:
    print("❌ Token not found.")
    print("Add a Railway variable named TOKENS or TOKEN5 with your bot token.")
else:
    bot.run(TOKEN)
