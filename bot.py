import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 🔥 CHANGE THESE
STAFF_ROLE_ID = 1470379426297548957
CATEGORY_NAME = "Tickets"  # EXACT name of your category

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

        # 🔍 find category
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)

        if category is None:
            await interaction.response.send_message("❌ Category not found!", ephemeral=True)
            return

        # 🛡 permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # 📁 create channel in category
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            category=category
        )

        await channel.send(
            f"{user.mention} 🎟 Ticket created!\nPress the button below to close.",
            view=CloseButton()
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# ---------------- PANEL COMMAND ----------------
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟 Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=TicketButton())

# ---------------- RUN ----------------
bot.run(os.getenv("TOKEN"))
