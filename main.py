import discord
from discord.ext import commands
import os
import asyncio
from threading import Thread
from flask import Flask

# --- 1. Render 7/24 Aktiflik İçin Flask Web Sunucusu ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 7/24 Aktif!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- 2. Discord Bot Kurulumu ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. Bot Hazır Olduğunda Komutları Senkronize Et ---
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} olarak giriş yaptı!")
    try:
        # Çift komutları temizler ve komut listesini günceller
        synced = await bot.tree.sync()
        print(f"🔄 Toplam {len(synced)} slash komutu başarıyla senkronize edildi.")
    except Exception as e:
        print(f"❌ Komutlar senkronize edilirken hata oluştu: {e}")

# --- 4. Cogs (Komut Dosyalarını) Yükleme ---
async def load_extensions():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'commands.{filename[:-3]}')
            print(f"📦 Yüklendi: commands.{filename[:-3]}")

# --- 5. Botu Başlatma ---
async def main():
    # Flask sunucusunu arka planda başlat
    Thread(target=run_flask).start()
    
    # Komut dosyalarını yükle
    await load_extensions()
    
    # Bot Tokenı ile giriş yap
    token = os.getenv("DISCORD_TOKEN")
    if token:
        await bot.start(token)
    else:
        print("❌ HATA: DISCORD_TOKEN çevre değişkeni bulunamadı!")

if __name__ == "__main__":
    asyncio.run(main())
