import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 🔥 YOUR SETTINGS
STAFF_ROLE_ID = 1470379426297548957  # yapper role ID
CATEGORY_ID = 1472860643475329096     # 🔁 REPLACE WITH YOUR TICKETS CATEGORY ID

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- CLOSE BUTTON ----------------
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await interaction.channel.delete()

# ---------------- CREATE BUTTON ----------------
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # 📂 Get category
        category = guild.get_channel(CATEGORY_ID)
        if category is None:
            await interaction.response.send_message("❌ Category not found!", ephemeral=True)
            return

        # 🔐 Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # 🆕 Create channel
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            category=category
        )

        # 📩 Send message inside ticket
        await channel.send(
            f"{user.mention} welcome to your ticket!",
            view=CloseButton()
        )

        await interaction.response.send_message(f"✅ Created {channel.mention}", ephemeral=True)

# ---------------- COMMAND TO SEND PANEL ----------------
@bot.command()
async def ticket(ctx):
    embed = discord.Embed(
        title="🎟 Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketButton())

# 🔑 RUN BOT (Railway uses env variable)
bot.run(os.getenv("TOKEN"))
