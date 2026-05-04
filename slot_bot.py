import discord
from discord.ext import commands
import random
import os

intents = discord.Intents.default()
intents.message_content = True  # IMPORTANT

bot = commands.Bot(command_prefix="?", intents=intents)

# 🪙 Coin system (simple)
coins = {}

def get_coins(user_id):
    return coins.get(user_id, 0)

def add_coin(user_id):
    coins[user_id] = get_coins(user_id) + 1

def remove_coin(user_id):
    if get_coins(user_id) > 0:
        coins[user_id] -= 1


# 🔥 READY EVENT
@bot.event
async def on_ready():
    print(f"🎰 Slot bot ready as {bot.user}")


# 🔍 DEBUG (important)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"Got message: {message.content}")
    await bot.process_commands(message)


# 🎰 SLOT BUTTON
class SlotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎰 Spin (1 coin)", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = interaction.user.id

        if get_coins(user_id) <= 0:
            await interaction.response.send_message("❌ You have no coins!", ephemeral=True)
            return

        remove_coin(user_id)

        roll = random.randint(1, 100)

        if roll <= 50:
            result = "🎰 ❌ ❌ ❌\n❌ Nothing"
        elif roll <= 80:
            result = "🎰 🍒 🍒 🍒\n🙂 Normal"
        elif roll <= 95:
            result = "🎰 🔥 🔥 🔥\n🔥 Hard Trade"
        else:
            result = "🎰 💎 💎 💎\n💎 VERY HARD TRADE!"

        await interaction.response.send_message(result)


# 🎰 SHOW SLOT MACHINE
@bot.command()
async def slot(ctx):
    await ctx.send("🎰 Slot Machine", view=SlotView())


# 🪙 GIVE COIN (test)
@bot.command()
async def addcoin(ctx):
    add_coin(ctx.author.id)
    await ctx.send("🪙 +1 coin")


# 💰 CHECK COINS
@bot.command()
async def coins(ctx):
    await ctx.send(f"🪙 You have {get_coins(ctx.author.id)} coins")


# 🚀 RUN BOT
bot.run(os.getenv("TOKEN2"))