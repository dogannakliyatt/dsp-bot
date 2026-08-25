import discord
from discord import app_commands
from discord.ext import commands
import datetime
import config

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles)

    async def log_admin_action(self, guild, staff, target, action_type, reason, status="Başarılı"):
        log_channel = guild.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"🛡️ Yönetim İşlemi - {action_type}",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="İşlemi Yapan Yetkili", value=f"{staff.mention} (`{staff.id}`)", inline=False)
        embed.add_field(name="İşlem Yapılan Kullanıcı", value=f"{target} (`{getattr(target, 'id', 'N/A')}`)", inline=False)
        embed.add_field(name="İşlem Türü", value=action_type, inline=True)
        embed.add_field(name="Durum", value=status, inline=True)
        embed.add_field(name="Sebep", value=reason, inline=False)
        
        await log_channel.send(embed=embed)

    @app_commands.command(name="yasakla", description="Kullanıcıyı sunucudan yasaklar.")
    @app_commands.describe(kullanici="Yasaklanacak kullanıcı", sebep="Yasaklama sebebi")
    async def yasakla(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)
        
        if kullanici.top_role >= interaction.user.top_role or kullanici.id == self.bot.user.id:
            return await interaction.response.send_message("Bot bu kullanıcıya işlem uygulayacak yetkiye sahip değil.", ephemeral=True)

        try:
            await kullanici.ban(reason=sebep)
            await interaction.response.send_message(f"{kullanici.mention} sunucudan yasaklandı. Sebep: {sebep}")
            await self.log_admin_action(interaction.guild, interaction.user, kullanici, "Yasaklama", sebep)
        except Exception as e:
            await interaction.response.send_message("Hatalı Komut Girişi Yaptınız, Tekrar Deneyiniz.", ephemeral=True)
            await self.log_admin_action(interaction.guild, interaction.user, kullanici, "Yasaklama", f"Hata: {str(e)}", "Başarısız")

    @app_commands.command(name="yasaklamakaldır", description="Kullanıcının yasağını kaldırır.")
    @app_commands.describe(kullanici_id="Yasağı kaldırılacak kullanıcı ID", sebep="Kaldırma sebebi")
    async def yasaklamakaldır(self, interaction: discord.Interaction, kullanici_id: str, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        try:
            user = await self.bot.fetch_user(int(kullanici_id))
            await interaction.guild.unban(user, reason=sebep)
            await interaction.response.send_message(f"{user.mention} yasağı kaldırıldı. Sebep: {sebep}")
            await self.log_admin_action(interaction.guild, interaction.user, user, "Yasak Kaldırma", sebep)
        except Exception:
            await interaction.response.send_message("Kullanıcı bulunamadı veya yasaklı değil.", ephemeral=True)

    @app_commands.command(name="sustur", description="Kullanıcıyı süreli olarak susturur.")
    @app_commands.describe(kullanici="Susturulacak kullanıcı", sure_dakika="Dakika cinsinden süre", sebep="Susturma sebebi")
    async def sustur(self, interaction: discord.Interaction, kullanici: discord.Member, sure_dakika: int, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        duration = datetime.timedelta(minutes=sure_dakika)
        try:
            await kullanici.timeout(duration, reason=sebep)
            await interaction.response.send_message(f"{kullanici.mention} {sure_dakika} dakika susturuldu. Sebep: {sebep}")
            await self.log_admin_action(interaction.guild, interaction.user, kullanici, f"Susturma ({sure_dakika} dk)", sebep)
        except Exception:
            await interaction.response.send_message("Bot bu kullanıcıya işlem uygulayacak yetkiye sahip değil.", ephemeral=True)

    @app_commands.command(name="susturmakaldır", description="Kullanıcının susturmasını kaldırır.")
    @app_commands.describe(kullanici="Susturması kaldırılacak kullanıcı", sebep="Kaldırma sebebi")
    async def susturmakaldır(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        try:
            await kullanici.timeout(None, reason=sebep)
            await interaction.response.send_message(f"{kullanici.mention} susturması kaldırıldı.")
            await self.log_admin_action(interaction.guild, interaction.user, kullanici, "Susturma Kaldırma", sebep)
        except Exception:
            await interaction.response.send_message("Hatalı Komut Girişi Yaptınız, Tekrar Deneyiniz.", ephemeral=True)

    @app_commands.command(name="at", description="Kullanıcıyı sunucudan atar.")
    @app_commands.describe(kullanici="Atılacak kullanıcı", sebep="Atılma sebebi")
    async def at(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        try:
            await kullanici.kick(reason=sebep)
            await interaction.response.send_message(f"{kullanici.mention} sunucudan atıldı. Sebep: {sebep}")
            await self.log_admin_action(interaction.guild, interaction.user, kullanici, "Sunucudan Atma", sebep)
        except Exception:
            await interaction.response.send_message("Bot bu kullanıcıya işlem uygulayacak yetkiye sahip değil.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
