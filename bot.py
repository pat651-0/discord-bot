import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# YOUR ROLE ID (optional but recommended)
STAFF_ROLE_ID = 123456789012345678  # replace or remove if you want

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # OPTIONAL: add staff role access
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

@bot.command()
async def setup(ctx):
    embed = discord.Embed(
        title="🎟 Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketButton())

bot.run(os.getenv("TOKEN"))
