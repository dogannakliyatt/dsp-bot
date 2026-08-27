import discord
from discord import app_commands
from discord.ext import commands
import datetime
import config

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in interaction.user.roles)

    @app_commands.command(name="ping", description="Botun anlık gecikme (ping) süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        # Botun websocket gecikmesini hesapla
        latency_ms = round(self.bot.latency * 1000)

        # Gecikmeye göre renk belirleme
        if latency_ms < 100:
            embed_color = discord.Color.green()
            status_text = "Mükemmel 🟢"
        elif latency_ms < 200:
            embed_color = discord.Color.gold()
            status_text = "İyi 🟡"
        else:
            embed_color = discord.Color.red()
            status_text = "Yüksek 🔴"

        embed = discord.Embed(
            title="🏓 Pong!",
            color=embed_color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="📶 Gecikme Süresi", value=f"`{latency_ms} ms`", inline=True)
        embed.add_field(name="📊 Bağlantı Durumu", value=status_text, inline=True)
        embed.set_footer(text=f"Sorgulayan: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        # Herkese açık olarak gönder
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mesajyaz", description="Bot üzerinden şık bir embed formatında mesaj gönderir.")
    @app_commands.describe(
        mesaj="Kutu içine yazılacak ana mesaj metni",
        baslik="İsteğe bağlı kutu başlığı",
        kanal="Mesajın gönderileceği kanal (Belirtilmezse bu kanala atar)"
    )
    async def mesajyaz(
        self,
        interaction: discord.Interaction,
        mesaj: str,
        baslik: str = None,
        kanal: discord.TextChannel = None
    ):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        target_channel = kanal if kanal else interaction.channel

        perms = target_channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            return await interaction.response.send_message(f"❌ Botun {target_channel.mention} kanalına mesaj veya Embed gönderme yetkisi yok!", ephemeral=True)

        embed = discord.Embed(
            title=baslik if baslik else None,
            description=mesaj,
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"Yayınlayan: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        try:
            await target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Mesajınız başarıyla {target_channel.mention} kanalına gönderildi.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Mesaj gönderilirken bir hata oluştu: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
