import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

REPORT_LOG_CHANNEL_ID = 1541807577837342834

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Roller için Dinamik Otomatik Tamamlama (Sunucudaki Tüm Verilebilir Rolleri Listeler)
    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        user_top_role = interaction.user.top_role
        is_owner = interaction.user.id == interaction.guild.owner_id

        for role in interaction.guild.roles:
            # Filtreler: @everyone, Bot rolleri, Yönetici rolleri listelenmez
            if role.is_default() or role.is_integration() or role.is_bot_managed() or role.permissions.administrator:
                continue

            # Yetkilinin kendi rolü ve üstü listelenmez (Sunucu sahibi hariç)
            if not is_owner and role >= user_top_role:
                continue

            # Arama filtresi
            if current.lower() in role.name.lower():
                choices.append(app_commands.Choice(name=role.name, value=str(role.id)))
                if len(choices) >= 25:  # Discord maksimum 25 seçim önerisi sunar
                    break

        return choices

    @app_commands.command(name="rolver", description="Kullanıcıya güvenli bir şekilde tek bir rol verir.")
    @app_commands.describe(
        kullanıcı="Rol verilecek kullanıcı",
        rol="Verilecek rolü seçin veya ismini yazın"
    )
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolver(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member,
        rol: str
    ):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
                return

        # Rol ID veya İsmi üzerinden rolü bul
        target_role = None
        if rol.isdigit():
            target_role = interaction.guild.get_role(int(rol))
        if not target_role:
            target_role = discord.utils.get(interaction.guild.roles, name=rol)

        if not target_role:
            await interaction.response.send_message("❌ Belirtilen rol sunucuda bulunamadı!", ephemeral=True)
            return

        # 1. Kural: Yönetici yetkisi kontrolü
        if target_role.permissions.administrator:
            await interaction.response.send_message("❌ **Güvenlik:** Yönetici yetkisine sahip roller bu komutla verilemez!", ephemeral=True)
            return

        # 2. Kural: @everyone ve entegrasyon kontrolü
        if target_role.is_default() or target_role.is_integration() or target_role.is_bot_managed():
            await interaction.response.send_message("❌ Bu rol kullanıcılara atanamaz!", ephemeral=True)
            return

        # 3. Kural: Kendi rolü ve üstü kontrolü
        if interaction.user.id != interaction.guild.owner_id and target_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ Kendi rolünüzle aynı veya daha üst seviyedeki bir rolü veremezsiniz!", ephemeral=True)
            return

        # 4. Kural: Bot hiyerarşisi
        if target_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ Botun yetkisi bu rolü vermeye yetmiyor (Botun rolü daha üstte olmalıdır).", ephemeral=True)
            return

        # Kullanıcıda zaten var mı?
        if target_role in kullanıcı.roles:
            await interaction.response.send_message(f"ℹ️ {kullanıcı.mention} kullanıcısında zaten {target_role.mention} rolü var.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await kullanıcı.add_roles(target_role, reason=f"Rol Ver Komutu: {interaction.user} ({interaction.user.id}) tarafından verildi.")
        except discord.Forbidden:
            await interaction.followup.send("❌ Discord izinleri nedeniyle rol verilemedi.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Hata oluştu: {e}", ephemeral=True)
            return

        # Başarı Yanıtı
        success_embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=f"{kullanıcı.mention} kullanıcısına {target_role.mention} rolü verildi.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        success_embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=success_embed)

        # Rapor Log Kanalı Bildirimi (1541807577837342834)
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
            report_embed.add_field(name="🎖️ Verilen Rol", value=f"{target_role.mention} (`{target_role.id}`)", inline=False)
            report_embed.add_field(name="🛡️ Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            report_embed.set_thumbnail(url=kullanıcı.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {kullanıcı.id}")

            try:
                await report_channel.send(embed=report_embed)
            except Exception as e:
                print(f"[HATA] Rapor gönderilemedi: {e}")

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
