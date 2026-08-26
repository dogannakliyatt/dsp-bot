import os
import asyncio
import traceback
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# Web Server (Render Web Service desteği için dinamik port)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Aktif!", 200

def run_flask():
    # Render'ın atadığı portu al, yoksa 8080 kullan
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Discord Bot Tanımlamaları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak giriş yapıldı.")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 {len(synced)} adet slash komutu senkronize edildi.")
    except Exception as e:
        print(f"❌ Komutlar senkronize edilirken hata oluştu: {e}")

async def load_extensions():
    if os.path.exists('./commands'):
        for filename in os.listdir('./commands'):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = f'commands.{filename[:-3]}'
                try:
                    await bot.load_extension(cog_name)
                    print(f"📦 Yüklendi: {cog_name}")
                except Exception as e:
                    print(f"❌ {cog_name} yüklenirken HATA oluştu:")
                    traceback.print_exc()

async def main():
    keep_alive()
    async with bot:
        await load_extensions()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ HATA: DISCORD_TOKEN ortam değişkeni bulunamadı! Render Environment ayarlarını kontrol edin.")
            return
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
