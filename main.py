import os
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config
from keep_alive import keep_alive

AUDIT_LOG_CHANNEL_ID = getattr(config, "AUDIT_LOG_CHANNEL_ID", 1541807577837342834)

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
        # commands/ klasöründeki cog modüllerini yükle
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

# 1. TÜM SLASH ( / ) ETKİLEŞİMLERİNİ YAKALAYIP RAPORLAMA (bot.listen kullanılmalı!)
@bot.listen("on_interaction")
async def log_interaction_listener(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        cmd_name = interaction.data.get("name", "bilinmeyen-komut")
        
        # Kayıt ve İsim Değiştirme kendi özel raporunu attığı için çift log önleme
        if cmd_name.lower() in ["kayıt", "kayit", "isimdegistir", "kayıtsızver"]:
            return

        log_channel = interaction.guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if log_channel:
            options = interaction.data.get("options", [])
            params_list = []
            
            def parse_options(opts):
                for opt in opts:
                    if "value" in opt:
                        params_list.append(f"**{opt.get('name')}**: `{opt.get('value')}`")
                    elif "options" in opt:
                        parse_options(opt.get("options"))
                        
            parse_options(options)
            params_str = "\n".join(params_list) if params_list else "Parametre girilmedi"

            if cmd_name in ["yasakla", "at", "sustur"]:
                embed_color = discord.Color.red()
            elif cmd_name in ["yasaklamakaldır", "susturmakaldır"]:
                embed_color = discord.Color.green()
            elif "oylama" in cmd_name:
                embed_color = discord.Color.purple()
            elif cmd_name in ["çekiliş", "katıl"]:
                embed_color = discord.Color.gold()
            elif cmd_name in ["mesajsil", "sil"]:
                embed_color = discord.Color.dark_red()
            else:
                embed_color = discord.Color.from_rgb(0, 168, 243)

            embed = discord.Embed(
                title="⚡ Slash Komutu Kullanıldı",
                color=embed_color,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.add_field(name="• Komut", value=f"`/{cmd_name}`", inline=True)
            embed.add_field(name="• Yetkili / Kullanıcı", value=interaction.user.mention, inline=True)
            embed.add_field(name="• Kanal", value=interaction.channel.mention if interaction.channel else "Bilinmiyor", inline=True)
            embed.add_field(name="• Girilen Bilgiler", value=params_str, inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Kullanıcı ID: {interaction.user.id}")

            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass


# 2. TÜM PREFIX ( d! / D! ) KOMUTLARININ RAPORLANMASI
@bot.listen("on_command_completion")
async def log_command_listener(ctx: commands.Context):
    if ctx.command.name in ["isimdeğistir", "isimdegistir", "rolver", "rolal"]:
        return

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
    embed.add_field(name="• Yetkili", value=ctx.author.mention, inline=True)
    embed.add_field(name="• Kanal", value=ctx.channel.mention, inline=True)
    embed.add_field(name="• Girilen Değerler", value=f"`{args_str}`", inline=False)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Kullanıcı ID: {ctx.author.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass


# 3. TOPLU MESAJ SİLME RAPORU
@bot.listen("on_bulk_message_delete")
async def log_bulk_delete_listener(messages):
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
        color=discord.Color.dark_red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text=f"Kanal ID: {channel.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass


if __name__ == "__main__":
    keep_alive()
    
    token = getattr(config, "DISCORD_TOKEN", None) or getattr(config, "TOKEN", None) or os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ HATA: DISCORD_TOKEN bulunamadı!")
