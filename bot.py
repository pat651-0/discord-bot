import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# CHANGE THIS to your role ID (staff/support role)
STAFF_ROLE_ID = 1470379426297548957  # <-- replace if needed


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# BUTTON VIEW
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Create channel name
        channel_name = f"ticket-{user.name}".lower()

        # Check if already exists
        for channel in guild.text_channels:
            if channel.name == channel_name:
                await interaction.response.send_message("You already have a ticket!", ephemeral=True)
                return

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # Create channel
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

        await channel.send(
            f"{user.mention} welcome to your ticket!\n"
            f"<@&{STAFF_ROLE_ID}> will assist you.\n\n"
            f"Use `!close` to close this ticket."
        )


# SEND PANEL COMMAND
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=TicketView())


# CLOSE COMMAND
@bot.command()
async def close(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("Closing ticket...")
        await ctx.channel.delete()
    else:
        await ctx.send("This is not a ticket channel.")


bot.run(os.getenv("TOKEN"))
