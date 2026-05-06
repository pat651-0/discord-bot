import discord
from discord.ext import commands
import os
import random
import json
import traceback

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- COINS STORAGE ----------------
COINS_FILE = "coins.json"

def load_coins():
    try:
        with open(COINS_FILE, "r") as file:
            return json.load(file)
    except:
        return {}

def save_coins():
    with open(COINS_FILE, "w") as file:
        json.dump(coins, file, indent=4)

coins = load_coins()

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print("----------------------------")
    print(f"🎰 Sloty logged in as {bot.user}")
    print("----------------------------")

# ---------------- DEBUG MESSAGE CHECK ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"Got message in #{message.channel}: {message.content}")

    # This proves Sloty can send messages
    if message.content.lower() == "!ping":
        try:
            await message.channel.send("🏓 Sloty can send messages!")
            print("Sent ping reply successfully.")
        except Exception as e:
            print("FAILED TO SEND MESSAGE:")
            print(e)
            traceback.print_exc()

    await bot.process_commands(message)

# ---------------- BALANCE ----------------
@bot.command(aliases=["bal"])
async def balance(ctx):
    user_id = str(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, you have **{coins.get(user_id, 0)}** coins.")

# ---------------- ADD COIN ----------------
@bot.command()
async def addcoin(ctx):
    user_id = str(ctx.author.id)

    coins[user_id] = coins.get(user_id, 0) + 1
    save_coins()

    await ctx.send(f"💰 {ctx.author.mention}, you now have **{coins[user_id]}** coins.")

# ---------------- SLOTS ----------------
@bot.command()
async def slots(ctx, bet: int = 1):
    user_id = str(ctx.author.id)

    if bet <= 0:
        await ctx.send("❌ Bet must be bigger than 0.")
        return

    if coins.get(user_id, 0) < bet:
        await ctx.send("❌ You do not have enough coins. Use `!addcoin`.")
        return

    coins[user_id] -= bet

    symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]

    slot1 = random.choice(symbols)
    slot2 = random.choice(symbols)
    slot3 = random.choice(symbols)

    result = f"🎰 | {slot1} | {slot2} | {slot3} | 🎰"

    if slot1 == "7️⃣" and slot2 == "7️⃣" and slot3 == "7️⃣":
        winnings = bet * 10
        coins[user_id] += winnings
        msg = f"{result}\n\n💎 **JACKPOT!** You won **{winnings}** coins!"
    elif slot1 == slot2 == slot3:
        winnings = bet * 5
        coins[user_id] += winnings
        msg = f"{result}\n\n🔥 **BIG WIN!** You won **{winnings}** coins!"
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        winnings = bet * 2
        coins[user_id] += winnings
        msg = f"{result}\n\n🍒 **Small win!** You won **{winnings}** coins!"
    else:
        msg = f"{result}\n\n❌ You lost **{bet}** coin."

    save_coins()

    await ctx.send(f"{ctx.author.mention}\n{msg}\n\n💰 Balance: **{coins[user_id]}** coins")

# ---------------- HELP ----------------
@bot.command()
async def slothelp(ctx):
    embed = discord.Embed(
        title="🎰 Sloty Commands",
        description="Use these commands:",
        color=discord.Color.gold()
    )

    embed.add_field(name="!ping", value="Check if Sloty can reply.", inline=False)
    embed.add_field(name="!addcoin", value="Get 1 coin.", inline=False)
    embed.add_field(name="!balance / !bal", value="Check your balance.", inline=False)
    embed.add_field(name="!slots", value="Spin with 1 coin.", inline=False)
    embed.add_field(name="!slots 5", value="Spin with 5 coins.", inline=False)

    await ctx.send(embed=embed)

# ---------------- ERRORS ----------------
@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")

    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Bad input. Try `!slothelp`.")
    else:
        await ctx.send("❌ Something went wrong. Check Railway logs.")

# ---------------- RUN ----------------
token = os.getenv("TOKEN")

if token is None:
    print("❌ TOKEN not found. Add TOKEN in Railway Variables.")
else:
    bot.run(token)
