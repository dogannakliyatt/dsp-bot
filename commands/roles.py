import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

REPORT_LOG_CHANNEL_ID = 1541807577837342834

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolver", description="Kullanıcıya güvenli bir şekilde tek bir rol verir.")
    @app_commands.describe(
        kullanıcı="Rol verilecek kullanıcı",
        rol="Verilecek rol"
    )
    async def rolver(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member,
        rol: discord.Role
    ):
        # Yetkili Rol Kontrolü (Opsiyonel: config.py üzerinde STAFF_ROLE_ID varsa)
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
                return

        # 1. Kural: Yönetici (Administrator) yetkisi olan roller verilemez
        if rol.permissions.administrator:
            await interaction.response.send_message(
                "❌ **Güvenlik Uyarısı:** Yönetici (Administrator) yetkisine sahip roller bu komutla verilemez!",
                ephemeral=True
            )
            return

        # 2. Kural: @everyone veya entegrasyon/bot rolleri verilemez
        if rol.is_default() or rol.is_integration() or rol.is_bot_managed():
            await interaction.response.send_message(
                "❌ Bu özel rol veya varsayılan rol kullanıcılara atanamaz!",
                ephemeral=True
            )
            return

        # 3. Kural: Yetkili kendi rolüne eşit veya kendi rolünün üstündeki rolleri veremez (Sunucu Sahibi hariç)
        if interaction.user.id != interaction.guild.owner_id:
            if rol >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ Kendi rolünüzle **aynı seviyede** veya sizden **daha üst seviyedeki** bir rolü veremezsiniz!",
                    ephemeral=True
                )
                return

        # 4. Kural: Botun rol hiyerarşisi kontrolü
        if rol >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ Botun rol sırası bu rolü vermeye yetmiyor. Lütfen botun rolünü daha yukarı taşıyın!",
                ephemeral=True
            )
            return

        # Kullanıcıda zaten bu rol var mı?
        if rol in kullanıcı.roles:
            await interaction.response.send_message(
                f"ℹ️ {kullanıcı.mention} kullanıcısında zaten {rol.mention} rolü bulunuyor.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Rolü verme işlemi
        try:
            await kullanıcı.add_roles(rol, reason=f"Rol Ver Komutu: {interaction.user} ({interaction.user.id}) tarafından verildi.")
        except discord.Forbidden:
            await interaction.followup.send("❌ Bu rolü vermek için Discord yetkim yetersiz.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Rol verilirken bir hata oluştu: {e}", ephemeral=True)
            return

        # Komut kanalına bilgilendirme mesajı
        success_embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=f"{kullanıcı.mention} kullanıcısına {rol.mention} rolü verildi.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        success_embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=success_embed)

        # Rapor Log Kanalına Bildirim Gönderme (1541807577837342834)
        report_channel = interaction.guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if report_channel is None:
            try:
                report_channel = await interaction.guild.fetch_channel(REPORT_LOG_CHANNEL_ID)
            except Exception:
                pass

        if report_channel:
            report_embed = discord.Embed(
                title="🛡️ Rol Verme İşlemi Raporu",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            report_embed.add_field(name="👤 Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=False)
            report_embed.add_field(name="🎖️ Verilen Rol", value=f"{rol.mention} (`{rol.id}`)", inline=False)
            report_embed.add_field(name="🛡️ Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            report_embed.set_thumbnail(url=kullanıcı.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {kullanıcı.id}")

            try:
                await report_channel.send(embed=report_embed)
            except discord.Forbidden:
                print(f"[HATA] Botun #{report_channel.name} rapor kanalına mesaj atma yetkisi yok!")
            except Exception as e:
                print(f"[HATA] Rapor gönderilemedi: {e}")

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
