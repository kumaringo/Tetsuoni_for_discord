import os
import threading
from flask import Flask
import discord
from add_station import handle_registration_logic

# Renderポート監視回避用ダミーFlask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

try:
    REQUIRED_USERS = int(os.environ.get('REQUIRED_USERS', '15'))
except ValueError:
    REQUIRED_USERS = 15

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

participant_data = {}
users_participated = {}

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} ({client.user.id})')

@client.event
async def on_message(message):
    if message.author.bot or message.content.startswith('/'):
        return

    await handle_registration_logic(message, participant_data, users_participated, REQUIRED_USERS)

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
    else:
        print("エラー: DISCORD_BOT_TOKEN が環境変数に設定されていません。")