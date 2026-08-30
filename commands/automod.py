import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Engellenecek kelime ve kalıplar
        self.forbidden_words = ["küfür1", "küfür2", "reklamkelimesi"] 
        self.invite_links = ["discord.gg/", "discord.com/invite/"]

    def is_authorized(self, member: discord.Member, guild: discord.Guild) -> bool:
        if member.guild_permissions.administrator or member.id == guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in member.roles)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Yöneticiler automod denetiminden muaftır
        if self.is_authorized(message.author, message.guild):
            return

        content_lower = message.content.lower()

        # 1. Davet Linki Kontrolü
        if any(link in content_lower for link in self.invite_links):
            try:
                await message.delete()
                warning = await message.channel.send(f"❌ {message.author.mention}, bu sunucuda reklam / davet linki paylaşmak yasaktır!")
                await discord.utils.sleep_until(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5))
                await warning.delete()
            except Exception:
                pass
            return

        # 2. Yasaklı Kelime Kontrolü
        if any(word in content_lower for word in self.forbidden_words):
            try:
                await message.delete()
                warning = await message.channel.send(f"❌ {message.author.mention}, mesajınız yasaklı kelime içerdiği için engellendi.")
                await discord.utils.sleep_until(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5))
                await warning.delete()
            except Exception:
                pass
            return

    @app_commands.command(name="yasaklikelime", description="Otomatik moderasyon listesine yasaklı kelime ekler veya çıkarır.")
    @app_commands.describe(islem="Ekle veya Kaldır", kelime="İşlem yapılacak kelime")
    @app_commands.choices(islem=[
        app_commands.Choice(name="Ekle", value="ekle"),
        app_commands.Choice(name="Kaldır", value="kaldir")
    ])
    async def yasakli_kelime(self, interaction: discord.Interaction, islem: app_commands.Choice[str], kelime: str):
        if not self.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        clean_word = kelime.lower().strip()
        if islem.value == "ekle":
            if clean_word not in self.forbidden_words:
                self.forbidden_words.append(clean_word)
            await interaction.response.send_message(f"✅ `{clean_word}` kelimesi yasaklılar listesine eklendi.", ephemeral=True)
        else:
            if clean_word in self.forbidden_words:
                self.forbidden_words.remove(clean_word)
            await interaction.response.send_message(f"✅ `{clean_word}` kelimesi yasaklılar listesinden çıkarıldı.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
