import discord
from discord.ext import commands
import os

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- SETTINGS ----------------
STAFF_ROLE_ID = 1470379426297548957
CATEGORY_ID = 1472896391717195807

# ---------------- CLOSE BUTTON ----------------
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="yapper_close_ticket"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await interaction.channel.delete()


# ---------------- CREATE TICKET BUTTON ----------------
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎟️ Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="yapper_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(CATEGORY_ID)

        if category is None:
            await interaction.response.send_message("❌ Ticket category not found!", ephemeral=True)
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)

        if staff_role is None:
            await interaction.response.send_message("❌ Staff role not found!", ephemeral=True)
            return

        # Stop users making duplicate open tickets
        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.name}".lower()
        )

        if existing_channel is not None:
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing_channel.mention}",
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
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎟️ Ticket Created",
            description=f"{user.mention} welcome to your ticket!\n\nStaff will help you soon.",
            color=discord.Color.green()
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseButton()
        )

        await interaction.response.send_message(
            f"✅ Created {channel.mention}",
            ephemeral=True
        )


# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(TicketButton())
    bot.add_view(CloseButton())

    print("----------------------------")
    print(f"🎟️ Yapper logged in as {bot.user}")
    print("----------------------------")


# ---------------- TICKET PANEL COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = discord.Embed(
        title="🎟️ Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketButton())


# ---------------- ERROR HANDLING ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use that command.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN ----------------
token = os.getenv("TOKEN")

if token is None:
    print("❌ TOKEN not found. Add TOKEN in Railway Variables.")
else:
    bot.run(token)
