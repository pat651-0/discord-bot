import discord
from discord.ext import commands
import os, json, time, random, re
from datetime import datetime, timezone

TOKEN_NAME = "TOKEN5"

STAFF_ROLE_ID = 1470379426297548957
TICKET_CATEGORY_ID = 1472860643475329096
GAME_CORNER_CATEGORY_ID = 1500809187595259984
LEAVES_CHANNEL_ID = 1475079442291363901

COINS_FILE = "coins.json"
TICKETS_FILE = "tickets.json"
COIN_LIFE = 60 * 60

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)
bot.remove_command("help")

def load_json(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

coins_store = load_json(COINS_FILE, {})
tickets_store = load_json(TICKETS_FILE, {})

def save_coins():
    save_json(COINS_FILE, coins_store)

def save_tickets():
    save_json(TICKETS_FILE, tickets_store)

def clean_name(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name[:40].strip("-")

def make_embed(title, desc, color=0x8E7CC3):
    e = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    e.set_footer(text="Yapster2000")
    return e

async def delete_cmd(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

def ensure_coins(user_id):
    uid = str(user_id)

    if uid not in coins_store:
        coins_store[uid] = []

    if isinstance(coins_store[uid], int):
        amount = max(coins_store[uid], 0)
        expiry = time.time() + COIN_LIFE
        coins_store[uid] = [expiry for _ in range(amount)]

    fixed = []
    for c in coins_store[uid]:
        try:
            c = float(c)
            if c > time.time():
                fixed.append(c)
        except:
            pass

    coins_store[uid] = fixed
    save_coins()
    return coins_store[uid]

def coin_count(user_id):
    return len(ensure_coins(user_id))

def add_coins(user_id, amount=1):
    uid = str(user_id)
    ensure_coins(uid)
    expiry = time.time() + COIN_LIFE

    for _ in range(amount):
        coins_store[uid].append(expiry)

    save_coins()

def remove_coins(user_id, amount=1):
    uid = str(user_id)
    ensure_coins(uid)

    if len(coins_store[uid]) < amount:
        return False

    coins_store[uid].sort()
    coins_store[uid] = coins_store[uid][amount:]
    save_coins()
    return True

def next_expiry(user_id):
    coins = ensure_coins(user_id)
    if not coins:
        return "No valid coins"

    left = int(min(coins) - time.time())
    if left <= 0:
        return "Expiring now"

    return f"{left // 60}m {left % 60}s"

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="yapster_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Create Ticket", style=discord.ButtonStyle.green, custom_id="yapster_create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff = guild.get_role(STAFF_ROLE_ID)

        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category not found or not a category.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }

        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{clean_name(user.name)}",
            category=category,
            overwrites=overwrites
        )

        tickets_store[str(channel.id)] = {
            "type": "yapper_ticket",
            "user_id": str(user.id)
        }
        save_tickets()

        await channel.send(
            content=f"{user.mention} welcome to your ticket!",
            embed=make_embed("🎟️ Ticket Created", "Staff will help you soon.", discord.Color.green()),
            view=CloseTicketView()
        )

        await interaction.response.send_message(f"✅ Created {channel.mention}", ephemeral=True)

class CloseWinTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Win Ticket", style=discord.ButtonStyle.red, custom_id="yapster_close_win_ticket")
    async def close_win_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing win ticket...", ephemeral=True)
        await interaction.channel.delete()

async def create_win_ticket(interaction, result, emoji):
    guild = interaction.guild
    user = interaction.user

    category = guild.get_channel(GAME_CORNER_CATEGORY_ID)
    staff = guild.get_role(STAFF_ROLE_ID)

    if category is None or not isinstance(category, discord.CategoryChannel):
        return None, "Game Corner category not found."

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
    }

    if staff:
        overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    channel = await guild.create_text_channel(
        name=f"slot-win-{clean_name(user.name)}",
        category=category,
        overwrites=overwrites
    )

    await channel.send(
        content=user.mention,
        embed=make_embed(
            f"{emoji} Slot Win Ticket",
            f"{user.mention} won **{result}**!\n\nSend a pic of what car you want 🚗📸\nStaff will sort your prize here.",
            discord.Color.green()
        ),
        view=CloseWinTicketView()
    )

    return channel, None

class SlotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎰 Spin Slot Machine", style=discord.ButtonStyle.green, custom_id="yapster_spin_slot")
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if coin_count(user.id) < 1:
            await interaction.response.send_message(
                "❌ You have no valid coins!\nCoins expire after **1 hour**.",
                ephemeral=True
            )
            return

        remove_coins(user.id, 1)
        await interaction.response.defer()

        roll = random.randint(1, 100)
        ticket = None
        ticket_error = None

        if roll <= 70:
            result, emoji, msg, color = "Nothing", "🚫", "maybe next time 😭", discord.Color.red()
        elif roll <= 94:
            result, emoji, msg, color = "Normal Cars", "🚘", "not bad", discord.Color.blue()
            ticket, ticket_error = await create_win_ticket(interaction, result, emoji)
        elif roll <= 99:
            result, emoji, msg, color = "Hard Trade", "✨", "nice", discord.Color.gold()
            ticket, ticket_error = await create_win_ticket(interaction, result, emoji)
        else:
            result, emoji, msg, color = "Very Hard Trade", "💎", "🎰🎰💎🔥", discord.Color.purple()
            ticket, ticket_error = await create_win_ticket(interaction, result, emoji)

        e = make_embed("🎰 Slot Machine Result", msg, color)
        e.add_field(name="Result", value=f"{emoji} {result}", inline=False)
        e.add_field(name="Coin Cost", value="1 coin", inline=True)
        e.add_field(name="Balance", value=f"{coin_count(user.id)} valid coin(s)", inline=True)

        if coin_count(user.id) > 0:
            e.add_field(name="Next Coin Expires", value=next_expiry(user.id), inline=False)

        if result != "Nothing":
            if ticket:
                e.add_field(name="Win Ticket", value=ticket.mention, inline=False)
            else:
                e.add_field(name="Win Ticket", value=f"❌ Could not create ticket: {ticket_error}", inline=False)

        await interaction.followup.send(embed=e)

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(SlotView())
    bot.add_view(CloseWinTicketView())

    print("----------------------------")
    print(f"🤖 Yapster2000 logged in as {bot.user}")
    print("----------------------------")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVES_CHANNEL_ID)

    if channel is None:
        return

    e = make_embed(
        "⚖️ Board of Guilt",
        f"💀 **{member.name}** left the server...\n\nTheir name shall stay here forever.",
        discord.Color.red()
    )

    e.add_field(name="Username", value=member.name, inline=True)
    e.add_field(name="Display Name", value=member.display_name, inline=True)
    e.add_field(name="User ID", value=str(member.id), inline=False)
    e.set_thumbnail(url=member.display_avatar.url)

    await channel.send(f"bye I guess... <@{member.id}>", embed=e)

@bot.event
async def on_guild_channel_delete(channel):
    cid = str(channel.id)

    if cid not in tickets_store:
        return

    data = tickets_store[cid]
    user_id = None

    if isinstance(data, dict):
        user_id = data.get("user_id")
    elif isinstance(data, str):
        user_id = data

    if user_id:
        add_coins(user_id, 1)
        print(f"Ticket closed. Added 1 coin to user ID {user_id}")

    del tickets_store[cid]
    save_tickets()

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    await ctx.send(
        embed=make_embed("🎟️ Ticket Machine", "Click below to create a ticket.", discord.Color.green()),
        view=TicketView()
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def slotpanel(ctx):
    await ctx.send(
        embed=make_embed(
            "🎰 Slot Machine",
            "Click below to spin.\n\n"
            "🚫 Nothing — **70%**\n"
            "🚘 Normal Cars — **24%**\n"
            "✨ Hard Trade — **5%**\n"
            "💎 Very Hard Trade — **1%**\n\n"
            "Each spin costs **1 coin**.\n"
            "Coins expire after **1 hour**.",
            discord.Color.green()
        ),
        view=SlotView()
    )

@bot.command(name="coins", aliases=["balance", "bal"])
async def coins_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(
        f"🪙 {member.mention} has **{coin_count(member.id)}** valid coin(s).\n"
        f"⏰ Next coin expires: **{next_expiry(member.id)}**"
    )

@bot.command(name="addcoins", aliases=["givecoins"])
@commands.has_permissions(administrator=True)
async def addcoins_command(ctx, amount: int, member: discord.Member = None):
    member = member or ctx.author
    add_coins(member.id, amount)
    await ctx.send(f"✅ Added **{amount}** coin(s) to {member.mention}. They expire in **1 hour**.")

@bot.command(name="removecoins", aliases=["takecoins"])
@commands.has_permissions(administrator=True)
async def removecoins_command(ctx, amount: int, member: discord.Member = None):
    member = member or ctx.author

    if remove_coins(member.id, amount):
        await ctx.send(f"✅ Removed **{amount}** coin(s) from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have enough valid coins.")

@bot.command(name="sallyspeak", aliases=["say", "speak", "yap"])
@commands.has_permissions(administrator=True)
async def sallyspeak(ctx, *, message: str):
    await ctx.send(message)
    await delete_cmd(ctx)

@bot.command(name="embed", aliases=["panel"])
@commands.has_permissions(administrator=True)
async def embed_command(ctx, *, text: str):
    if "|" in text:
        title, body = text.split("|", 1)
    else:
        title, body = "📌 Info", text

    await ctx.send(embed=make_embed(title.strip(), body.strip()))
    await delete_cmd(ctx)

@bot.command()
@commands.has_permissions(administrator=True)
async def slotinfo(ctx):
    await ctx.send(embed=make_embed(
        "🎰 Slot Machine Info 🎰",
        "Use your coins to spin the Sloty machine and try your luck 🍀\n\n"
        "Each spin costs **1 coin**.\n\n"
        "🚫 **Nothing — 70%**\n"
        "🚘 **Normal Cars — 24%**\n"
        "✨ **Hard Trade — 5%**\n"
        "💎 **Very Hard Trade — 1%**\n\n"
        "If you win anything except **Nothing**, a win ticket opens under **Game Corner**.\n\n"
        "Send a pic of what car you want 🚗📸"
    ))
    await delete_cmd(ctx)

@bot.command()
@commands.has_permissions(administrator=True)
async def rules(ctx):
    await ctx.send(embed=make_embed(
        "📜 Server Rules",
        "**1.** No BS.\n"
        "**2.** No NSFW.\n"
        "**3.** English only.\n"
        "**4.** No scams.\n"
        "**5.** Respect staff.\n"
        "**6.** Use tickets for trades.",
        discord.Color.red()
    ))
    await delete_cmd(ctx)

@bot.command()
async def testguilt(ctx):
    await ctx.send("⚖️ Board of Guilt is alive. Nobody is safe.")

@bot.command()
async def yapsterhelp(ctx):
    await ctx.send(
        "**🤖 Yapster2000 Commands**\n\n"
        "`!ticket` — ticket panel\n"
        "`!slotpanel` — slot machine panel\n"
        "`!coins` — check coins\n"
        "`!addcoins 5` — add coins to yourself\n"
        "`!addcoins 5 @user` — add coins to user\n"
        "`!removecoins 5 @user` — remove coins\n"
        "`!sallyspeak message` — bot says message\n"
        "`!embed Title | Message` — clean embed\n"
        "`!slotinfo` — slot info panel\n"
        "`!rules` — rules panel\n"
        "`!testguilt` — test Board of Guilt"
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!yapsterhelp`.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing something. Try `!yapsterhelp`.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")

token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found.")
else:
    bot.run(token)
