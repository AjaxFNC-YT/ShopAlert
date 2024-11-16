import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, SlashOption
import requests
import tracemalloc
import json
import os
import uuid
from datetime import datetime


tracemalloc.start()

TOKEN = ''
API_URL = 'https://fortnite-api.com/v2/shop'
COSMETIC_API_URL = 'https://fortnite-api.com/v2/cosmetics/br/'
REMINDERS_FILE = 'reminders.json'

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)
start_time = datetime.now()

def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return {}
    with open(REMINDERS_FILE, 'r') as f:
        return json.load(f)

def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, indent=4)

def fetch_cosmetic_name(cosmetic_id):
    response = requests.get(f"{COSMETIC_API_URL}{cosmetic_id}")
    data = response.json()
    return data['data'].get('name', 'Unknown')

def fetch_cosmetic_image_url(cosmetic_id):
    response = requests.get(f"{COSMETIC_API_URL}{cosmetic_id}")
    data = response.json()
    return data['data']["images"].get('icon', 'https://cdn.ajaxfnc.com/uploads/noImageFound.png')


def check_reminder_exists(reminders, user_id, id_of_item):
    user_reminders = reminders.get(user_id, {}).get('reminders', [])
    return any(reminder['idOfItem'] == id_of_item for reminder in user_reminders)

@bot.command(name="addmulti", help="Add multiple reminders by IDs separated by ';'.")
async def add_multi(ctx, *, ids: str):
    user_id = str(ctx.author.id)
    reminders = load_reminders()
    new_reminders = []

    if user_id not in reminders:
        reminders[user_id] = {
            "lastUpdated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "remindUserId": user_id,
            "reminders": []
        }

    for cosmetic_id in ids.split(';'):
        cosmetic_name = fetch_cosmetic_name(cosmetic_id)

        if not check_reminder_exists(reminders, user_id, cosmetic_id):
            reminder = {
                "idOfItem": cosmetic_id,
                "cosmeticName": cosmetic_name,
                "dateAdded": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "remindId": str(uuid.uuid4())
            }
            reminders[user_id]['reminders'].append(reminder)
            new_reminders.append(cosmetic_name)

    if new_reminders:
        reminders[user_id]['lastUpdated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_reminders(reminders)
        await ctx.send(f"Added new reminders: {', '.join(new_reminders)}")
    else:
        await ctx.send("No new reminders were added. All IDs were already in your reminders.")

@bot.slash_command(name="add-reminder", description="Add a reminder for a cosmetic item.")
async def add_reminder(interaction: Interaction, id: str):
    user_id = str(interaction.user.id)
    reminders = load_reminders()

    if user_id not in reminders:
        reminders[user_id] = {
            "lastUpdated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "remindUserId": user_id,
            "reminders": []
        }

    if len(reminders[user_id]['reminders']) >= 30:
        await interaction.response.send_message("You can only have a maximum of 30 reminders.", ephemeral=True)
        return

    if check_reminder_exists(reminders, user_id, id):
        await interaction.response.send_message("This item is already in your reminders.", ephemeral=True)
        return

    cosmetic_name = fetch_cosmetic_name(id)
    cosmetic_image_url = fetch_cosmetic_image_url(id)

    reminder = {
        "idOfItem": id,
        "cosmeticName": cosmetic_name,
        "dateAdded": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "remindId": str(uuid.uuid4())
    }

    reminders[user_id]['reminders'].append(reminder)
    reminders[user_id]['lastUpdated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_reminders(reminders)

    embed = nextcord.Embed(title="Reminder Added", description=f"Reminder for '{cosmetic_name}' added!", color=0x00FF00)
    embed.add_field(name="Cosmetic Name", value=cosmetic_name)
    embed.add_field(name="Item ID", value=id)
    embed.set_thumbnail(cosmetic_image_url)
    embed.set_footer(text="Reminder added successfully.")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="remove-reminder", description="Remove a reminder for a cosmetic item.")
async def remove_reminder(interaction: Interaction, remind_id: str = SlashOption(required=False), name: str = SlashOption(required=False), id: str = SlashOption(required=False)):
    user_id = str(interaction.user.id)
    reminders = load_reminders()

    if user_id not in reminders:
        await interaction.response.send_message("You have no reminders.", ephemeral=True)
        return

    found = False
    for reminder in reminders[user_id]['reminders']:
        if reminder['remindId'] == remind_id or reminder['idOfItem'] == id:
            reminders[user_id]['reminders'].remove(reminder)
            found = True
            break

    if found:
        save_reminders(reminders)
        embed = nextcord.Embed(title="Reminder Removed", description="Your reminder has been removed.", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("No matching reminder found.", ephemeral=True)

@bot.slash_command(name="reminders", description="Show all reminders.")
async def reminders(interaction: Interaction):
    user_id = str(interaction.user.id)
    reminders = load_reminders()

    if user_id not in reminders or not reminders[user_id]['reminders']:
        await interaction.response.send_message("You have no reminders.", ephemeral=True)
        return

    embed = nextcord.Embed(title="Your Reminders", color=0x1E90FF)
    for reminder in reminders[user_id]['reminders']:
        embed.add_field(
            name=reminder['cosmeticName'],
            value=f"ID: {reminder['idOfItem']}\nAdded: {reminder['dateAdded']}\nRemindId: {reminder['remindId']}",
            inline=False
        )
    embed.set_footer(text="Data from Fortnite API")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="bot-info", description="Show bot information including ping, uptime, and reminder count.")
async def bot_info(interaction: Interaction):
    latency = round(bot.latency * 1000)
    current_time = datetime.now()
    uptime_duration = str(current_time - start_time).split('.')[0]  # Remove microseconds
    reminders = load_reminders()
    reminder_count = sum(len(user_data['reminders']) for user_data in reminders.values())

    embed = nextcord.Embed(title="Bot Information", color=0x1E90FF)
    embed.add_field(name="Ping", value=f"{latency}ms", inline=True)
    embed.add_field(name="Uptime", value=uptime_duration, inline=True)
    embed.add_field(name="Total Reminders", value=reminder_count, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="id-by-name", description="Gets a cosmetic id by name")
async def get_cosmetic_id(interaction: Interaction, name: str):
    try:
        response = requests.get(f"https://fortnite-api.com/v2/cosmetics/br/search?matchMethod=full&name={name}")
        data = response.json()

        if data['status'] != 200:
            embed = nextcord.Embed(title="Cosmetic Not Found", description=f"No cosmetic found with the name '{name}'", color=0xff0000)
            embed.set_thumbnail(url="https://cdn.ajaxfnc.com/uploads/1281858196260130826.webp")
            embed.add_field(name="Try Again", value="Please check the spelling or try a different name", inline=True)
            await interaction.response.send_message(embed=embed)
            return

        if data["data"]:
            cosmetic = data["data"]
            cosmetic_id = cosmetic["id"]
            cosmetic_name = cosmetic["name"]
            cosmetic_icon = cosmetic["images"]["icon"]
            cosmetic_description = cosmetic["description"]

            embed = nextcord.Embed(title=cosmetic_name, description=cosmetic_description, color=0x00ff00)
            embed.set_thumbnail(url=cosmetic_icon)
            embed.add_field(name="ID", value=cosmetic_id, inline=True)

            await interaction.response.send_message(embed=embed)
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f"Failed to retrieve data. Error: {e}")

def is_item_in_shop(entries, item_id):
    def search_item(data, item_id):
        if isinstance(data, dict):
            for key, value in data.items():
                if search_item(value, item_id):
                    return True
        elif isinstance(data, list):
            for item in data:
                if search_item(item, item_id):
                    return True
        elif data == item_id:
            return True
        return False

    return search_item(entries, item_id)

async def check_shop():
    response = requests.get(API_URL)
    data = response.json()

    if not data or 'data' not in data:
        return
    
    shop_data = data['data']

    shop_entries = shop_data.get('entries', [])

    reminders = load_reminders()
    
    for user_id, user_data in reminders.items():
        user = bot.get_user(int(user_id))
        if user is None:
            continue

        found_items = []
        
        for reminder in list(user_data['reminders']):
            if any(reminder['idOfItem'] in item.get('id', '') for entry in shop_entries if 'brItems' in entry for item in entry['brItems']):
                found_items.append(reminder)
                user_data['reminders'].remove(reminder)

        if found_items:
            try:
                embed = nextcord.Embed(title=":warning: Item Shop Reminder", description="The following item(s) are now in the shop:", color=0xFFD700)
                for reminder in found_items:
                    embed.add_field(name=reminder['cosmeticName'], value=f"ID: {reminder['idOfItem']}", inline=False)
                await user.send(f"<@{user_id}>", embed=embed)
            except nextcord.HTTPException as e:
                print(f"Failed to send DM to user {user_id}: {e}")

        save_reminders(reminders)

@tasks.loop(minutes=7)
async def periodic_shop_check():
    print("Checking item shop!")
    await check_shop()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    periodic_shop_check.start()

bot.run(TOKEN)
