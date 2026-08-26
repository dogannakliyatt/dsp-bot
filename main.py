import os
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config
from keep_alive import keep_alive

# Raporlama / Genel Log Kanalı ID
AUDIT_LOG_CHANNEL_ID = 1541807577837342834

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

        # 2. Komutları Global olarak senkronize et
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

# ==========================================
# 📊 MERKEZİ LOG VE RAPORLAMA SİSTEMİ
# ==========================================

# 1. TÜM SLASH ( / ) KOMUTLARININ RAPORU
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Hata durumunda da sessizce hata logu atabilir veya pas geçebilir
    pass

async def log_app_command(interaction: discord.Interaction, command: app_commands.Command):
    # Kayıt komutu kendi özel kanalına gittiği için hariç tutuldu
    if command.name.lower() in ["kayıt", "kayit"]:
        return

    log_channel = interaction.guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not log_channel:
        return

    # Girilen parametreleri topla
    options = interaction.data.get("options", [])
    params_list = []
    for opt in options:
        name = opt.get("name", "")
        val = opt.get("value", "")
        params_list.append(f"**{name}**: `{val}`")
    
    params_str = ", ".join(params_list) if params_list else "Parametre yok"

    embed = discord.Embed(
        title="⚡ Slash Komutu Kullanıldı",
        color=discord.Color.from_rgb(0, 168, 243),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="• Komut", value=f"`/{command.name}`", inline=True)
    embed.add_field(name="• Kullanan Yetkili", value=interaction.user.mention, inline=True)
    embed.add_field(name="• Kanal", value=interaction.channel.mention if interaction.channel else "Bilinmiyor", inline=True)
    embed.add_field(name="• Girilen Detaylar", value=params_str, inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text=f"Kullanıcı ID: {interaction.user.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass

# Komut başarıyla tamamlandığında tetiklenir
bot.tree.on_app_command_completion = log_app_command


# 2. TÜM PREFIX ( d! / D! ) KOMUTLARININ RAPORU (Örn: d!sil)
@bot.event
async def on_command_completion(ctx: commands.Context):
    log_channel = ctx.guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not log_channel:
        return

    args_str = " ".join([str(arg) for arg in ctx.args[2:]]) if len(ctx.args) > 2 else "Parametre yok"
    if ctx.kwargs:
        kwargs_str = ", ".join([f"{k}: `{v}`" for k, v in ctx.kwargs.items()])
        args_str = f"{args_str} | {kwargs_str}" if args_str != "Parametre yok" else kwargs_str

    embed = discord.Embed(
        title="🛠️ Metin Komutu Çalıştırıldı",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="• Komut", value=f"`{ctx.prefix}{ctx.command.name}`", inline=True)
    embed.add_field(name="• Kullanan Yetkili", value=ctx.author.mention, inline=True)
    embed.add_field(name="• Kanal", value=ctx.channel.mention, inline=True)
    embed.add_field(name="• Girilen Değerler", value=args_str, inline=False)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Kullanıcı ID: {ctx.author.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass


# 3. TOPLU MESAJ SİLME RAPORU
@bot.event
async def on_bulk_message_delete(messages):
    if not messages:
        return
    guild = messages[0].guild
    channel = messages[0].channel
    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        title="🗑️ Toplu Mesaj Silindi",
        description=f"{channel.mention} kanalında toplam **{len(messages)}** adet mesaj temizlendi.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text=f"Kanal ID: {channel.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass


if __name__ == "__main__":
    # Render Webhook / 7/24 Keep Alive Sunucusu
    keep_alive()
    
    # Botu Başlat
    token = getattr(config, "DISCORD_TOKEN", None) or os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ HATA: DISCORD_TOKEN bulunamadı! Lütfen config.py veya Environment Variables alanını kontrol edin.")
