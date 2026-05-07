import discord
from discord.ext import commands
import os
import random
import json

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN2"

COINS_FILE = "coins.json"
TICKETS_FILE = "tickets.json"

GAME_CORNER_CATEGORY_ID = 1500809187595259984

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- FILE HELPERS ----------------
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

coins = load_json(COINS_FILE, {})
tickets = load_json(TICKETS_FILE, {})

def save_coins():
    save_json(COINS_FILE, coins)

def save_tickets():
    save_json(TICKETS_FILE, tickets)

# ---------------- COINS ----------------
def get_coins(user_id):
    uid = str(user_id)

    if uid not in coins:
        coins[uid] = 0
        save_coins()

    return coins[uid]

def add_coins(user_id, amount):
    uid = str(user_id)

    if uid not in coins:
        coins[uid] = 0

    coins[uid] += amount
    save_coins()

def remove_coins(user_id, amount):
    uid = str(user_id)

    if uid not in coins:
        coins[uid] = 0

    if coins[uid] < amount:
        return False

    coins[uid] -= amount
    save_coins()
    return True

# ---------------- SLOT BUTTON ----------------
class SlotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎰 Spin Slot Machine",
        style=discord.ButtonStyle.green,
        custom_id="spin_slot"
    )
    async def spin_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if get_coins(user.id) < 1:
            await interaction.response.send_message(
                "❌ You have no coins!\nClose a Yapper ticket to earn **+1 coin**.",
                ephemeral=True
            )
            return

        remove_coins(user.id, 1)

        roll = random.randint(1, 100)

        if roll <= 70:
            result = "🚫 Nothing"
            msg = "Maybe next time 😭"
            won = False
        elif roll <= 94:
            result = "🚘 Normal Cars"
            msg = "Not bad."
            won = True
        elif roll <= 99:
            result = "✨ Hard Trade"
            msg = "Nice."
            won = True
        else:
            result = "💎 Very Hard Trade"
            msg = "🎰🎰💎🔥"
            won = True

        balance = get_coins(user.id)

        embed = discord.Embed(
            title="🎰 Slot Machine Result",
            description=f"{msg}\n\nYou landed on **{result}**.",
            color=discord.Color.blue()
        )

        embed.add_field(name="Result", value=result, inline=False)
        embed.add_field(name="Coin Cost", value="1 coin", inline=True)
        embed.add_field(name="Balance", value=f"{balance} coins", inline=True)

        await interaction.response.send_message(embed=embed)

        if won:
            await create_win_ticket(interaction, user, result)

# ---------------- CREATE WIN TICKET ----------------
async def create_win_ticket(interaction, user, result):
    guild = interaction.guild
    category = guild.get_channel(GAME_CORNER_CATEGORY_ID)

    if category is None:
        await interaction.followup.send(
            "❌ I won something but couldn't open a ticket because Game Corner category ID is wrong.",
            ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
    }

    channel_name = f"slot-win-{user.name}".lower().replace(" ", "-")

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites
    )

    tickets[str(ticket_channel.id)] = {
        "user_id": user.id,
        "result": result
    }

    save_tickets()

    embed = discord.Embed(
        title="🎰 Slot Win Ticket",
        description=(
            f"{user.mention} won **{result}**!\n\n"
            "Send a pic of what car you want 🚘\n"
            "Staff will sort your prize here."
        ),
        color=discord.Color.gold()
    )

    await ticket_channel.send(content=user.mention, embed=embed)

    await interaction.followup.send(
        f"✅ You won **{result}**! Ticket opened: {ticket_channel.mention}",
        ephemeral=True
    )

# ---------------- COMMANDS ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def slotpanel(ctx):
    embed = discord.Embed(
        title="🎰 Slot Machine",
        description=(
            "Click the button below to spin.\n\n"
            "**Chances:**\n"
            "🚫 Nothing — **70%**\n"
            "Maybe next time 😭\n\n"
            "🚘 Normal Cars — **24%**\n"
            "Not bad.\n\n"
            "✨ Hard Trade — **5%**\n"
            "Nice.\n\n"
            "💎 Very Hard Trade — **1%**\n"
            "🎰🎰💎🔥\n\n"
            "Each spin costs **1 coin**.\n"
            "You earn **1 coin** when your Yapper ticket is closed."
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=SlotView())

@bot.command()
@commands.has_permissions(administrator=True)
async def addcoins(ctx, member: discord.Member, amount: int):
    add_coins(member.id, amount)
    await ctx.send(f"✅ Added **{amount}** coin(s) to {member.mention}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removecoins(ctx, member: discord.Member, amount: int):
    success = remove_coins(member.id, amount)

    if success:
        await ctx.send(f"✅ Removed **{amount}** coin(s) from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have enough coins.")

@bot.command()
async def coins(ctx, member: discord.Member = None):
    member = member or ctx.author
    balance = get_coins(member.id)

    await ctx.send(f"🪙 {member.mention} has **{balance}** coin(s).")

@bot.command()
async def slothelp(ctx):
    await ctx.send(
        "**Sloty Commands**\n"
        "`!slotpanel` — sends the slot machine panel\n"
        "`!coins` — checks your coins\n"
        "`!coins @user` — checks someone else's coins\n"
        "`!addcoins @user amount` — admin only\n"
        "`!removecoins @user amount` — admin only"
    )

# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(SlotView())

    print("----------------------------")
    print(f"🎰 Sloty logged in as {bot.user}")
    print("----------------------------")

# ---------------- ERRORS ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Bad input. Try `!slothelp`.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!slothelp`.")
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")

# ---------------- RUN ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(TOKEN2)
