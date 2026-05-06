import discord
from discord.ext import commands
import os
import random
import json

# ---------------- SETTINGS ----------------
TOKEN_NAME = "TOKEN2"
COINS_FILE = "coins.json"
TICKETS_FILE = "tickets.json"

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


# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(SlotMachineView())

    print("----------------------------")
    print(f"🎰 Sloty logged in as {bot.user}")
    print("----------------------------")


# ---------------- WATCH YAPPER TICKETS ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        # Detect Yapper's ticket welcome message
        if "welcome to your ticket" in message.content.lower():
            if len(message.mentions) > 0:
                user = message.mentions[0]

                tickets[str(message.channel.id)] = str(user.id)
                save_json(TICKETS_FILE, tickets)

                print(f"Saved ticket owner: #{message.channel} -> {user}")

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

        print(f"Ticket closed. Added 1 coin to user ID {user_id}")


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

        coins[user_id] -= 1

        roll = random.randint(1, 100)

        if roll <= 50:
            result = "🚫 Nothing"
            description = "Unlucky! You got nothing this spin."
            color = discord.Color.red()

        elif roll <= 85:
            result = "🚘 Normal Cars"
            description = "Nice! You landed on **Normal Cars**."
            color = discord.Color.blue()

        elif roll <= 95:
            result = "✨ Hard Trade"
            description = "Ooooh, you hit a **Hard Trade**."
            color = discord.Color.gold()

        else:
            result = "💎 Very Hard Trade"
            description = "JACKPOT! You hit a **Very Hard Trade**."
            color = discord.Color.purple()

        save_json(COINS_FILE, coins)

        embed = discord.Embed(
            title="🎰 Slot Machine Result",
            description=description,
            color=color
        )

        embed.add_field(name="Result", value=result, inline=False)
        embed.add_field(name="Coin Cost", value="1 coin", inline=True)
        embed.add_field(name="Balance", value=f"{coins[user_id]} coins", inline=True)

        await interaction.response.send_message(embed=embed)


# ---------------- PANEL COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def slotpanel(ctx):
    embed = discord.Embed(
        title="🎰 Slot Machine",
        description=(
            "Click the button below to spin.\n\n"
            "**Chances:**\n"
            "🚫 Nothing — **50%**\n"
            "🚘 Normal Cars — **35%**\n"
            "✨ Hard Trade — **10%**\n"
            "💎 Very Hard Trade — **5%**\n\n"
            "Each spin costs **1 coin**.\n"
            "You earn **1 coin** when your Yapper ticket is closed."
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=SlotMachineView())


# ---------------- BALANCE ----------------
@bot.command(aliases=["bal"])
async def balance(ctx):
    user_id = str(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, you have **{coins.get(user_id, 0)}** coins.")


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
