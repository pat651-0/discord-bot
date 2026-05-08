import discord
from discord.ext import commands
import os
import random
import json
import time
import re

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN2"

GAME_CORNER_CATEGORY_ID = 1500809187595259984
STAFF_ROLE_ID = 1470379426297548957

COINS_FILE = "coins.json"
YAPPER_TICKETS_FILE = "tickets.json"

COIN_LIFETIME_SECONDS = 60 * 60  # 1 hour

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

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


coins_store = load_json(COINS_FILE, {})
yapper_tickets = load_json(YAPPER_TICKETS_FILE, {})


def save_coins():
    save_json(COINS_FILE, coins_store)


def save_yapper_tickets():
    save_json(YAPPER_TICKETS_FILE, yapper_tickets)


# ---------------- COIN TIMER SYSTEM ----------------
def ensure_coin_list(user_id):
    uid = str(user_id)
    changed = False

    if uid not in coins_store:
        coins_store[uid] = []
        changed = True

    value = coins_store[uid]

    # Old format: user had a number like 5
    if isinstance(value, int):
        old_amount = max(value, 0)
        expiry = time.time() + COIN_LIFETIME_SECONDS
        coins_store[uid] = [expiry for _ in range(old_amount)]
        changed = True

    # Correct format: list of expiry timestamps
    elif isinstance(value, list):
        fixed_list = []

        for expiry in value:
            try:
                fixed_list.append(float(expiry))
            except Exception:
                pass

        if fixed_list != value:
            coins_store[uid] = fixed_list
            changed = True

    # Broken format
    else:
        coins_store[uid] = []
        changed = True

    if changed:
        save_coins()

    return coins_store[uid]


def clean_expired_coins(user_id):
    uid = str(user_id)
    coin_list = ensure_coin_list(uid)

    now = time.time()
    valid_coins = [expiry for expiry in coin_list if expiry > now]

    if len(valid_coins) != len(coin_list):
        coins_store[uid] = valid_coins
        save_coins()

    return valid_coins


def get_coin_count(user_id):
    return len(clean_expired_coins(user_id))


def add_coins_to_user(user_id, amount):
    uid = str(user_id)
    coin_list = clean_expired_coins(uid)

    expiry = time.time() + COIN_LIFETIME_SECONDS

    for _ in range(amount):
        coin_list.append(expiry)

    coins_store[uid] = coin_list
    save_coins()


def remove_coins_from_user(user_id, amount):
    uid = str(user_id)
    coin_list = clean_expired_coins(uid)

    if len(coin_list) < amount:
        return False

    coin_list.sort()
    coins_store[uid] = coin_list[amount:]
    save_coins()
    return True


def get_next_expiry_text(user_id):
    coin_list = clean_expired_coins(user_id)

    if not coin_list:
        return "No valid coins"

    next_expiry = min(coin_list)
    seconds_left = int(next_expiry - time.time())

    if seconds_left <= 0:
        return "Expiring now"

    minutes = seconds_left // 60
    seconds = seconds_left % 60

    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    return f"{minutes}m {seconds}s"


# ---------------- USER FINDER ----------------
async def find_member(ctx, raw_target):
    if ctx.guild is None:
        return None

    if raw_target is None:
        return None

    raw_target = str(raw_target).strip()

    match = re.fullmatch(r"<@!?(\d+)>", raw_target)

    if match:
        user_id = int(match.group(1))
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


def clean_channel_name(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name[:40].strip("-")


# ---------------- CLOSE WIN TICKET BUTTON ----------------
class CloseWinTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Win Ticket",
        style=discord.ButtonStyle.red,
        custom_id="sloty_close_win_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing win ticket...", ephemeral=True)
        await interaction.channel.delete()


# ---------------- CREATE WIN TICKET ----------------
async def create_win_ticket(interaction, result_name, result_emoji):
    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return None, "This only works inside a server."

    category = guild.get_channel(GAME_CORNER_CATEGORY_ID)

    if category is None:
        return None, "Game Corner category not found."

    if not isinstance(category, discord.CategoryChannel):
        return None, "GAME_CORNER_CATEGORY_ID is not a category."

    bot_member = guild.me or guild.get_member(bot.user.id)

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

    staff_role = guild.get_role(STAFF_ROLE_ID)

    if staff_role is not None:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

    safe_name = clean_channel_name(user.name)
    channel_name = f"slot-win-{safe_name}"

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason="Sloty win ticket created"
        )
    except discord.Forbidden:
        return None, "Sloty is missing Manage Channels permission."
    except Exception as e:
        return None, str(e)

    embed = discord.Embed(
        title=f"{result_emoji} Sloty Win Ticket",
        description=(
            f"{user.mention} won **{result_name}**!\n\n"
            "Send a pic of what car you want 🚘📸\n"
            "Staff will sort your prize here."
        ),
        color=discord.Color.green()
    )

    embed.add_field(name="Winner", value=user.mention, inline=False)
    embed.add_field(name="Prize", value=f"{result_emoji} {result_name}", inline=False)

    await channel.send(
        content=user.mention,
        embed=embed,
        view=CloseWinTicketView()
    )

    return channel, None


# ---------------- SLOT MACHINE BUTTON ----------------
class SlotMachineView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎰 Spin Slot Machine",
        style=discord.ButtonStyle.green,
        custom_id="spin_slot"
    )
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            description = "maybe next time 😭"
            color = discord.Color.red()

        elif roll <= 94:
            result = "Normal Cars"
            emoji = "🚘"
            description = "not bad"
            color = discord.Color.blue()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        elif roll <= 99:
            result = "Hard Trade"
            emoji = "✨"
            description = "nice"
            color = discord.Color.gold()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        else:
            result = "Very Hard Trade"
            emoji = "💎"
            description = "🎰🎰💎🔥"
            color = discord.Color.purple()
            ticket_channel, ticket_error = await create_win_ticket(interaction, result, emoji)

        balance = get_coin_count(user.id)

        embed = discord.Embed(
            title="🎰 Slot Machine Result",
            description=description,
            color=color
        )

        embed.add_field(name="Result", value=f"{emoji} {result}", inline=False)
        embed.add_field(name="Coin Cost", value="1 coin", inline=True)
        embed.add_field(name="Balance", value=f"{balance} valid coin(s)", inline=True)

        if balance > 0:
            embed.add_field(
                name="Next Coin Expires In",
                value=get_next_expiry_text(user.id),
                inline=False
            )

        if result != "Nothing":
            if ticket_channel is not None:
                embed.add_field(
                    name="Win Ticket",
                    value=f"Created: {ticket_channel.mention}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Win Ticket",
                    value=f"❌ Could not create ticket: {ticket_error}",
                    inline=False
                )

        await interaction.followup.send(embed=embed)


# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(SlotMachineView())
    bot.add_view(CloseWinTicketView())

    print("----------------------------")
    print(f"🎰 Sloty logged in as {bot.user}")
    print("----------------------------")


# ---------------- WATCH YAPPER TICKETS ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        if "welcome to your ticket" in message.content.lower():
            if len(message.mentions) > 0:
                user = message.mentions[0]

                yapper_tickets[str(message.channel.id)] = {
                    "type": "yapper_ticket",
                    "user_id": str(user.id)
                }

                save_yapper_tickets()

                print(f"Saved Yapper ticket owner: #{message.channel} -> {user}")

        return

    await bot.process_commands(message)


@bot.event
async def on_guild_channel_delete(channel):
    channel_id = str(channel.id)

    if channel_id not in yapper_tickets:
        return

    ticket_data = yapper_tickets[channel_id]
    user_id = None

    if isinstance(ticket_data, dict):
        if ticket_data.get("type") == "yapper_ticket":
            user_id = ticket_data.get("user_id")

    elif isinstance(ticket_data, str):
        user_id = ticket_data

    if user_id is not None:
        add_coins_to_user(user_id, 1)
        print(f"Yapper ticket closed. Added 1 coin to user ID {user_id}. Expires in 1 hour.")

    del yapper_tickets[channel_id]
    save_yapper_tickets()


# ---------------- PANEL COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def slotpanel(ctx):
    embed = discord.Embed(
        title="🎰 Slot Machine",
        description=(
            "Click the button below to spin.\n\n"
            "**Chances:**\n"
            "🚫 Nothing — **70%**\n"
            "maybe next time 😭\n\n"
            "🚘 Normal Cars — **24%**\n"
            "not bad\n\n"
            "✨ Hard Trade — **5%**\n"
            "nice\n\n"
            "💎 Very Hard Trade — **1%**\n"
            "🎰🎰💎🔥\n\n"
            "Each spin costs **1 coin**.\n"
            "Coins expire after **1 hour**.\n\n"
            "Winning anything except **Nothing** opens a win ticket."
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=SlotMachineView())


# ---------------- COIN COMMANDS ----------------
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
async def addcoins_command(ctx, target: str = None, amount: int = None):
    if target is None:
        await ctx.send("❌ Usage: `!addcoins @user 5` or `!addcoins 5`")
        return

    # Allows: !addcoins 5
    if amount is None:
        try:
            amount = int(target)
            member = ctx.author
        except Exception:
            await ctx.send("❌ Usage: `!addcoins @user 5` or `!addcoins 5`")
            return

    # Allows: !addcoins @user 5 OR !addcoins USER_ID 5
    else:
        member = await find_member(ctx, target)

        if member is None:
            await ctx.send("❌ I could not find that user. Try mentioning them or using their user ID.")
            return

    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    add_coins_to_user(member.id, amount)

    await ctx.send(
        f"✅ Added **{amount}** coin(s) to {member.mention}.\n"
        f"⏰ These coins expire in **1 hour**."
    )


@bot.command(name="removecoins", aliases=["takecoins"])
@commands.has_permissions(administrator=True)
async def removecoins_command(ctx, target: str = None, amount: int = None):
    if target is None:
        await ctx.send("❌ Usage: `!removecoins @user 5` or `!removecoins 5`")
        return

    # Allows: !removecoins 5
    if amount is None:
        try:
            amount = int(target)
            member = ctx.author
        except Exception:
            await ctx.send("❌ Usage: `!removecoins @user 5` or `!removecoins 5`")
            return

    # Allows: !removecoins @user 5 OR !removecoins USER_ID 5
    else:
        member = await find_member(ctx, target)

        if member is None:
            await ctx.send("❌ I could not find that user. Try mentioning them or using their user ID.")
            return

    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    success = remove_coins_from_user(member.id, amount)

    if success:
        await ctx.send(f"✅ Removed **{amount}** coin(s) from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have enough valid coins.")


# ---------------- HELP ----------------
@bot.command()
async def slothelp(ctx):
    embed = discord.Embed(
        title="🎰 Sloty Commands",
        description="Here are Sloty's commands:",
        color=discord.Color.gold()
    )

    embed.add_field(name="!slotpanel", value="Admin only: sends the slot machine panel.", inline=False)
    embed.add_field(name="!coins / !balance / !bal", value="Check your own coins.", inline=False)
    embed.add_field(name="!coins @user", value="Check someone else's coins.", inline=False)
    embed.add_field(name="!addcoins 5", value="Admin only: add coins to yourself.", inline=False)
    embed.add_field(name="!addcoins @user 5", value="Admin only: add coins to someone.", inline=False)
    embed.add_field(name="!removecoins @user 5", value="Admin only: remove coins.", inline=False)
    embed.add_field(name="Coin Timer", value="All coins expire after **1 hour**.", inline=False)

    await ctx.send(embed=embed)


# ---------------- ERROR HANDLING ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing something. Try `!slothelp`.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!slothelp`.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN ----------------
token = os.getenv("TOKEN2")

if token is None:
    print("❌ TOKEN2 not found in Railway variables.")
else:
    bot.run(token)
