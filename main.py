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

    async def is_bot_owner(self, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return True
        try:
            app = await self.application_info()
            if app.owner and app.owner.id == user_id:
                return True
        except Exception:
            pass
        return False

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
# 🛑 TÜM COG VE KOMUTLARI ENGELLEYEN MERKEZİ KONTROL
# ==========================================

async def global_maintenance_check(ctx_or_interaction) -> bool:
    if not bot.is_under_maintenance:
        return True
    
    user = getattr(ctx_or_interaction, "author", None) or getattr(ctx_or_interaction, "user", None)
    if not user:
        return False

    is_owner = await bot.is_bot_owner(user.id)
    if is_owner:
        return True

    msg = "⚙️ Bot şu an bakım modundadır. İşlem gerçekleştirilemez."
    try:
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.reply(msg, mention_author=False)
        elif isinstance(ctx_or_interaction, discord.Interaction):
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

    return False

@bot.check
async def ancient_prefix_check(ctx: commands.Context):
    return await global_maintenance_check(ctx)

@bot.tree.interaction_check
async def ancient_slash_check(interaction: discord.Interaction):
    return await global_maintenance_check(interaction)

# ==========================================
# 🛠️ MANUEL SLASH KOMUT SENKRONİZASYON KOMUTU
# ==========================================
@bot.command(name="sync")
async def sync_commands(ctx: commands.Context):
    if not await bot.is_bot_owner(ctx.author.id):
        return await ctx.reply("❌ Bu komutu sadece botun sahibi kullanabilir.", mention_author=False)
    try:
        synced = await bot.tree.sync()
        await ctx.reply(f"🔄 **{len(synced)}** adet slash komutu başarıyla senkronize edildi.", mention_author=False)
    except Exception as e:
        await ctx.reply(f"❌ Senkronizasyon hatası: {e}", mention_author=False)

# ==========================================
# 📊 MERKEZİ LOG VE RAPORLAMA SİSTEMİ
# ==========================================

@bot.listen("on_interaction")
async def log_interaction_listener(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        if bot.is_under_maintenance and not await bot.is_bot_owner(interaction.user.id):
            return

        cmd_name = interaction.data.get("name", "bilinmeyen-komut")
        
        if cmd_name.lower() in ["kayıt", "kayit", "isimdegistir", "kayıtsızver"]:
            return

        log_channel = interaction.guild.get_channel(AUDIT_LOG_CHANNEL_ID) if interaction.guild else None
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

@bot.listen("on_command_completion")
async def log_command_listener(ctx: commands.Context):
    if bot.is_under_maintenance and not await bot.is_bot_owner(ctx.author.id):
        return

    if ctx.command.name in ["isimdeğistir", "isimdegistir", "rolver", "rolal", "sil", "temizle", "clear", "sync"]:
        return

    log_channel = ctx.guild.get_channel(AUDIT_LOG_CHANNEL_ID) if ctx.guild else None
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

@bot.listen("on_bulk_message_delete")
async def log_bulk_delete_listener(messages):
    if not messages:
        return
    guild = messages[0].guild
    channel = messages[0].channel
    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID) if guild else None
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
