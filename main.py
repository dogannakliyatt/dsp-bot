import os
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config
from keep_alive import keep_alive
from persistent_views import register_all_persistent_views

AUDIT_LOG_CHANNEL_ID = getattr(config, "AUDIT_LOG_CHANNEL_ID", 1541807577837342834)
OWNER_ID = 651765260579241984

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
        self.is_under_maintenance = False

    async def setup_hook(self):
        await register_all_persistent_views(self)

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
        
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="Demokratik Sol Parti"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = BotClient()

# ==========================================
# 🛑 BAKIM KONTROL SİSTEMİ
# ==========================================

@bot.check
async def absolute_prefix_block(ctx: commands.Context):
    if bot.is_under_maintenance and ctx.author.id != OWNER_ID:
        await ctx.reply("⚙️ Bot şu an bakım modundadır. İşlem gerçekleştirilemez.", mention_author=False)
        return False
    return True

@bot.tree.interaction_check
async def absolute_slash_block(interaction: discord.Interaction):
    if bot.is_under_maintenance and interaction.user.id != OWNER_ID:
        msg = "⚙️ Bot şu an bakım modundadır. İşlem gerçekleştirilemez."
        if interaction.response.is_done():
            try:
                await interaction.followup.send(msg, ephemeral=True)
            except Exception:
                pass
        else:
            try:
                await interaction.response.send_message(msg, ephemeral=True)
            except Exception:
                pass
        return False
    return True

# ==========================================
# 🛠️ MANUEL SLASH KOMUT SENKRONİZASYONU
# ==========================================
@bot.command(name="sync")
async def sync_commands(ctx: commands.Context):
    if ctx.author.id != OWNER_ID:
        return await ctx.reply("❌ Bu komutu sadece botun sahibi kullanabilir.", mention_author=False)
    try:
        synced = await bot.tree.sync()
        await ctx.reply(f"🔄 **{len(synced)}** adet slash komutu başarıyla senkronize edildi.", mention_author=False)
    except Exception as e:
        await ctx.reply(f"❌ Senkronizasyon hatası: {e}", mention_author=False)

if __name__ == "__main__":
    keep_alive()
    
    token = getattr(config, "DISCORD_TOKEN", None) or getattr(config, "TOKEN", None) or os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ HATA: DISCORD_TOKEN bulunamadı!")
