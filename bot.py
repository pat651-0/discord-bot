import discord
from discord.ext import commands
import os
import json

TOKEN_NAME = "TOKEN"

STAFF_ROLE_ID = 1470379426297548957

# Your server category + your friend's server category
CATEGORY_IDS = [
    1472860643475329096,  # your server
    1507876447467995226   # friend's server
]

SETTINGS_FILE = "yapper_settings.json"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------- JSON HELPERS ----------------
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}

    try:
        with open(SETTINGS_FILE, "r") as file:
            return json.load(file)
    except Exception:
        return {}


def save_settings(data):
    with open(SETTINGS_FILE, "w") as file:
        json.dump(data, file, indent=4)


settings = load_settings()


# ---------------- CATEGORY FINDER ----------------
def get_ticket_category(guild):
    guild_id = str(guild.id)

    # First check saved category from !setcategory
    if guild_id in settings:
        saved_category_id = int(settings[guild_id])
        category = guild.get_channel(saved_category_id)

        if isinstance(category, discord.CategoryChannel):
            return category

    # Then check your hardcoded category IDs
    for category_id in CATEGORY_IDS:
        category = guild.get_channel(category_id)

        if isinstance(category, discord.CategoryChannel):
            return category

    return None


def clean_channel_name(name):
    name = name.lower()
    cleaned = ""

    for char in name:
        if char.isalnum():
            cleaned += char
        elif char in ["-", "_", " "]:
            cleaned += "-"

    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")

    return cleaned.strip("-")[:40]


# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(TicketButton())
    bot.add_view(CloseButton())

    print("----------------------------")
    print(f"🎫 Yapper logged in as {bot.user}")
    print("----------------------------")


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
        label="🎫 Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="yapper_create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ This only works inside a server.",
                ephemeral=True
            )
            return

        category = get_ticket_category(guild)

        if category is None:
            await interaction.response.send_message(
                "❌ Ticket category not found.\n"
                "An admin needs to run !setcategory inside the ticket category/server.",
                ephemeral=True
            )
            return

        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        if staff_role is not None:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

        channel_name = f"ticket-{clean_channel_name(user.name)}"

        existing = discord.utils.get(
            category.text_channels,
            name=channel_name
        )

        if existing:
            await interaction.response.send_message(
                f"❌ You already have a ticket: {existing.mention}",
                ephemeral=True
            )
            return

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I do not have permission to create ticket channels.",
                ephemeral=True
            )
            return

        await channel.send(
            f"{user.mention} welcome to your ticket!",
            view=CloseButton()
        )

        await interaction.response.send_message(
            f"✅ Created {channel.mention}",
            ephemeral=True
        )


# ---------------- SEND TICKET PANEL ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = discord.Embed(
        title="🎫 Ticket Machine",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TicketButton())


# ---------------- SET CATEGORY COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setcategory(ctx, category_id: int = None):
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    if category_id is None:
        if ctx.channel.category is None:
            await ctx.send(
                "❌ This channel is not inside a category.\n"
                "Use !setcategory CATEGORY_ID instead."
            )
            return

        category = ctx.channel.category

    else:
        category = ctx.guild.get_channel(category_id)

        if not isinstance(category, discord.CategoryChannel):
            await ctx.send("❌ That ID is not a valid category in this server.")
            return

    settings[str(ctx.guild.id)] = category.id
    save_settings(settings)

    await ctx.send(f"✅ Ticket category set to *{category.name}*.")


# ---------------- CHECK CATEGORY COMMAND ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def checkcategory(ctx):
    if ctx.guild is None:
        await ctx.send("❌ This command only works inside a server.")
        return

    category = get_ticket_category(ctx.guild)

    if category is None:
        await ctx.send("❌ No ticket category found for this server.")
    else:
        await ctx.send(f"✅ Current ticket category: *{category.name}*")


# ---------------- ERROR HANDLER ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permission to use this command.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid ID. Use a real category ID.")
        return

    print(error)
    await ctx.send("❌ Something went wrong. Check Railway logs.")


# ---------------- RUN BOT ----------------
token = os.getenv(TOKEN_NAME)

if token is None:
    print(f"❌ {TOKEN_NAME} not found in Railway variables.")
else:
    bot.run(token)
