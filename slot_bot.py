import discord
from discord.ext import commands
import os
import random
import json
import re

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN2"

GAME_CORNER_CATEGORY_ID = 1500809187595259984

COINS_FILE = "coins.json"
TICKETS_FILE = "tickets.json"

STAFF_ROLE_ID = None

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- JSON STORAGE ----------------
def load_json(file_name):
    try:
        with open(file_name, "r") as file:
            return json.load(file)
    except:
        return {}

def save_json(file_name, data):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4)

coins = load_json(COINS_FILE)
tickets = load_json(TICKETS_FILE)

def add_coin(user_id, amount=1):
    user_id = str(user_id)
    coins[user_id] = coins.get(user_id, 0) + amount
    save_json(COINS_FILE, coins)

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

# ---------------- CREATE SLOTY WIN TICKET ----------------
async def create_win_ticket(interaction, result_name, result_emoji):
    guild = interaction.guild
    user = interaction.user

    category = guild.get_channel(GAME_CORNER_CATEGORY_ID)

    if category is None:
        return None

    bot_member = guild.me

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )
    }

    if STAFF_ROLE_ID is not None:
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

    safe_name = clean_channel_name(user.name)
    channel_name = f"slot-win-{safe_name}"

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason="Sloty win ticket created"
    )

    embed = discord.Embed(
        title=f"{result_emoji} Sloty Win Ticket",
        description=(
            f"{user.mention} won **{result_name}**!\n\n"
            "Staff can use this ticket to sort the trade/prize."
        ),
        color=discord.Color.green()
    )

    embed.add_field(name="Winner", value=user.mention, inline=False)
    embed.add_field(name="Prize", value=f"{result_emoji} {result_name}", inline=False)

    await channel.send(
        content=f"{user.mention}",
        embed=embed,
        view=CloseWinTicketView()
    )

    return channel

# ---------------- SLOT MACHINE BUTTON ----------------
class SlotMachineView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎰 Spin Slot Machine",
        style=discord.ButtonStyle.green,
        custom_id="sloty_spin_button"
    )
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        balance = coins.get(user_id, 0)

        if balance <= 0:
            await interaction.response.send_message(
                "❌ You have no coins!\nClose a Yapper ticket to earn **+1 coin**.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        coins[user_id] -= 1

        roll = random.randint(1, 100)
        ticket_channel = None

        # 1 - 70 = Nothing, 70%
        if roll <= 70:
            result = "Nothing"
            emoji = "🚫"
            description = "maybe next time"
            color = discord.Color.red()

        # 71 - 94 = Normal Cars, 24%
        elif roll <= 94:
            result = "Normal Cars"
            emoji = "🚘"
            description = "not bad"
            color = discord.Color.blue()
            ticket_channel = await create_win_ticket(interaction, result, emoji)

        # 95 - 99 = Hard Trade, 5%
        elif roll <= 99:
            result = "Hard Trade"
            emoji = "✨"
            description = "nice"
            color = discord.Color.gold()
            ticket_channel = await create_win_ticket(interaction, result, emoji)

        # 100 = Very Hard Trade, 1%
        else:
            result = "Very Hard Trade"
            emoji = "💎"
            description = "🎰🎰💎🔥"
            color = discord.Color.purple()
            ticket_channel = await create_win_ticket(interaction, result, emoji)

        save_json(COINS_FILE, coins)

        embed = discord.Embed(
            title="🎰 Slot Machine Result",
            description=description,
            color=color
        )

        embed.add_field(name="Result", value=f"{emoji} {result}", inline=False)
        embed.add_field(name="Coin Cost", value="1 coin", inline=True)
        embed.add_field(name="Balance", value=f"{coins[user_id]} coins", inline=True)

        if ticket_channel is not None:
            embed.add_field(
                name="Win Ticket",
                value=f"Created: {ticket_channel.mention}",
                inline=False
            )
        elif result != "Nothing":
            embed.add_field(
                name="Win Ticket",
                value="❌ Could not create ticket. Check Sloty's Game Corner permissions.",
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

                tickets[str(message.channel.id)] = str(user.id)
                save_json(TICKETS_FILE, tickets)

                print(f"Saved Yapper ticket owner: #{message.channel} -> {user}")

        return

    await bot.process_commands(message)

@bot.event
async def on_guild_channel_delete(channel):
    channel_id = str(channel.id)

    if channel_id in tickets:
        user_id = tickets[channel_id]

        add_coin(user_id, 1)

        del tickets[channel_id]
        save_json(TICKETS_FILE, tickets)

        print(f"Yapper ticket closed. Added 1 coin to user ID {user_id}")

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
            "🚘 Normal Cars — **24%**\n"
            "✨ Hard Trade — **5%**\n"
            "💎 Very Hard Trade — **1%**\n\n"
            "Each spin costs **1 coin**.\n"
            "You earn **1 coin** when your Yapper ticket is closed.\n\n"
            "Winning anything except **Nothing** automatically opens a win ticket."
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=SlotMachineView())

# ---------------- BALANCE ----------------
@bot.command(aliases=["bal"])
async def balance(ctx):
    user_id = str(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, you have **{coins.get(user_id, 0)}** coins.")

# ---------------- ADMIN ADD COINS TO YOURSELF ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def addcoins(ctx, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    add_coin(ctx.author.id, amount)

    await ctx.send(
        f"✅ Added **{amount}** coins to {ctx.author.mention}.\n"
        f"You now have **{coins[str(ctx.author.id)]}** coins."
    )

# ---------------- ADMIN GIVE COINS ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def givecoins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    add_coin(member.id, amount)

    await ctx.send(
        f"✅ Gave **{amount}** coins to {member.mention}.\n"
        f"They now have **{coins[str(member.id)]}** coins."
    )

# ---------------- ADMIN REMOVE COINS ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def removecoins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be bigger than 0.")
        return

    user_id = str(member.id)
    coins[user_id] = max(coins.get(user_id, 0) - amount, 0)
    save_json(COINS_FILE, coins)

    await ctx.send(
        f"✅ Removed **{amount}** coins from {member.mention}.\n"
        f"They now have **{coins[user_id]}** coins."
    )

# ---------------- HELP ----------------
@bot.command()
async def slothelp(ctx):
    embed = discord.Embed(
        title="🎰 Sloty Commands",
        description="Here are Sloty's commands:",
        color=discord.Color.gold()
    )

    embed.add_field(name="!slotpanel", value="Admin only: sends the slot machine panel.", inline=False)
    embed.add_field(name="!balance / !bal", value="Check your coins.", inline=False)
    embed.add_field(name="!addcoins amount", value="Admin only: add coins to yourself.", inline=False)
    embed.add_field(name="!givecoins @user amount", value="Admin only: give coins.", inline=False)
    embed.add_field(name="!removecoins @user amount", value="Admin only: remove coins.", inline=False)

    await ctx.send(embed=embed)

# ---------------- ERROR HANDLING ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that command.")
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
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway Variables.")
else:
    bot.run(token)
