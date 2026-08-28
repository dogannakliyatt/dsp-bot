import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import config

class AutoNickSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_base_name(self, display_name: str) -> str:
        """Kullanıcının unvanlar haricindeki saf adını ayıklar."""
        if not display_name:
            return "Kullanıcı"
        return display_name.split("/")[0].strip()

    def determine_titles(self, member: discord.Member):
        """Kullanıcının rollerine göre Parti ve RP unvanlarını tespit eder."""
        user_role_ids = {r.id for r in member.roles}
        
        parti_title = None
        rp_title = None

        # 1. Parti Makamı Kontrolü (Üye hariç makamlar)
        for code, req_ids in config.PARTY_ROLES.items():
            if code == "Üye" or not req_ids:
                continue
            # İlgili makamın gerektirdiği TÜM rol ID'lerine sahip mi?
            if all(r_id in user_role_ids for r in req_ids):
                parti_title = code
                break

        # 2. RP Makamı Kontrolü (Yok hariç makamlar)
        for code, req_ids in config.RP_ROLES.items():
            if code == "Yok" or not req_ids:
                continue
            # İlgili makamın gerektirdiği TÜM rol ID'lerine sahip mi?
            if all(r_id in user_role_ids for r in req_ids):
                rp_title = code
                break

        return parti_title, rp_title

    def build_expected_nickname(self, member: discord.Member) -> str:
        """Kullanıcının olması gereken takma adını üretir."""
        base_name = self.get_base_name(member.display_name)
        parti_title, rp_title = self.determine_titles(member)

        titles = []
        if parti_title:
            titles.append(parti_title)
        if rp_title:
            titles.append(rp_title)

        if titles:
            expected = f"{base_name} / {' / '.join(titles)}"
        else:
            expected = base_name

        # Discord 32 karakter sınırı
        return expected[:32]

    # ==========================================
    # ⚡ ANLIK ROL DEĞİŞİKLİĞİ DİNLEYİCİSİ
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot or after.id == after.guild.owner_id:
            return

        # Yalnızca roller değiştiğinde çalışır
        if before.roles == after.roles:
            return

        # Botun hiyerarşik yetkisi kontrolü
        if after.top_role >= after.guild.me.top_role:
            return

        expected_nick = self.build_expected_nickname(after)

        # Mevcut takma ad zaten doğruysa tekrar düzenleme yapma
        current_nick = after.nick if after.nick else after.name
        if current_nick != expected_nick:
            try:
                await after.edit(nick=expected_nick, reason="Otomatik Parti/RP Makam Takma Ad Güncellemesi")
            except Exception:
                pass

    # ==========================================
    # 🔄 TOPLU SUNUCU EŞİTLEME KOMUTU
    # ==========================================
    @app_commands.command(
        name="ototakmaadesitle", 
        description="Sunucudaki tüm üyelerin takma adlarını parti ve RP makamlarına göre senkronize eder."
    )
    async def sync_all_nicknames(self, interaction: discord.Interaction):
        if not config.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        updated_count = 0
        skipped_count = 0

        for member in guild.members:
            if member.bot or member.id == guild.owner_id:
                continue

            if member.top_role >= guild.me.top_role:
                skipped_count += 1
                continue

            expected_nick = self.build_expected_nickname(member)
            current_nick = member.nick if member.nick else member.name

            if current_nick != expected_nick:
                try:
                    await member.edit(nick=expected_nick, reason=f"Toplu Takma Ad Eşitleme: {interaction.user}")
                    updated_count += 1
                    await asyncio.sleep(0.4)  # Discord rate-limit koruması
                except Exception:
                    pass

        embed = discord.Embed(
            title="🔄 Takma Ad Senkronizasyonu Tamamlandı",
            color=config.COLOR_HEX
        )
        embed.add_field(name="✅ Güncellenen Üye Sayısı", value=f"`{updated_count} Kişi`", inline=False)
        embed.add_field(name="⚠️ Yetki Yetersizliği Nedeniyle Atlanan", value=f"`{skipped_count} Kişi (Üst Roller)`", inline=False)
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoNickSync(bot))
