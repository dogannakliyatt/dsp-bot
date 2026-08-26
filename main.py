import os
import discord
from discord.ext import commands
import config
from keep_alive import keep_alive

class BotClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        
        prefix = getattr(config, "PREFIX", ["d!", "D!"])
        
        super().__init__(
            command_prefix=prefix,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # commands/ klasöründeki tüm modülleri yükle
        commands_dir = os.path.join(os.path.dirname(__file__), "commands")
        if os.path.exists(commands_dir):
            for filename in os.listdir(commands_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = f"commands.{filename[:-3]}"
                    try:
                        await self.load_extension(cog_name)
                        print(f"📦 Yüklendi: {cog_name}")
                    except Exception as e:
                        print(f"❌ {cog_name} yüklenemedi: {e}")

    async def on_ready(self):
        print(f"✅ Bot Başarıyla Giriş Yaptı: {self.user} (ID: {self.user.id})")
        print("--------------------------------------------------")
        
        # 1. Eski sunucu-özel (Guild) artıklarını temizle
        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)

        # 2. Komutları doğrudan Global olarak senkronize et
        synced = await self.tree.sync()
        print(f"🔄 {len(synced)} adet komut başarıyla senkronize edildi.")
        print("--------------------------------------------------")
        
        # Bot Durumu (Aktivite)
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="Demokratik Sol Parti"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = BotClient()

if __name__ == "__main__":
    # Render Webhook / 7/24 Keep Alive Sunucusu
    keep_alive()
    
    # Botu Başlat
    token = getattr(config, "DISCORD_TOKEN", None) or os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ HATA: DISCORD_TOKEN bulunamadı! Lütfen config.py veya Environment Variables alanını kontrol edin.")
