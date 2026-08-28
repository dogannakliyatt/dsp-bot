import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import config

TARGET_ROLE_ID = 1537153933305315328

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

        # 1. Parti Makamı Kontrolü
        for code, req_ids in config.PARTY_ROLES.items():
            if code == "Üye" or not req_ids:
                continue
            if all(r_id in user_role_ids for r_id in req_ids):
                parti_title = code
                break

        # 2. RP Makamı Kontrolü
        for code, req_ids in config.RP_ROLES.items():
            if code == "Yok" or not req_ids:
                continue
            if all(r_id in user_role_ids for r_id in req_ids):
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

        return expected[:32]

    # ==========================================
    # ⚡ ANLIK ROL DEĞİŞİKLİĞİ DİNLEYİCİSİ
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot or after.id == after.guild.owner_id:
            return

        if before.roles == after.roles:
            return

        # Sadece hedef role sahipse veya bu rolün değişiminde çalış
        has_target_role = any(r.id == TARGET_ROLE_ID for r in after.roles)
        had_target_role = any(r.id == TARGET_ROLE_ID for r in before.roles)
        if not has_target_role and not had_target_role:
            return

        if after.top_role >= after.guild.me.top_role:
            return

        expected_nick = self.build_expected_nickname(after)
        current_nick = after.nick if after.nick else after.name

        if current_nick != expected_nick:
            try:
                await after.edit(nick=expected_nick, reason="Otomatik Parti/RP Makam Takma Ad Güncellemesi")
            except Exception:
                pass

    # ==========================================
    # 🚀 HIZLANDIRILMIŞ TOPLU EŞİTLEME KOMUTU
    # ==========================================
    @app_commands.command(
        name="ototakmaadesitle", 
        description="Yalnızca DSP Üye rolüne sahip üyelerin takma adlarını hızlıca senkronize eder."
    )
    async def sync_all_nicknames(self, interaction: discord.Interaction):
        if not config.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        target_role = guild.get_role(TARGET_ROLE_ID)

        if not target_role:
            return await interaction.followup.send(f"❌ Hedef rol (`ID: {TARGET_ROLE_ID}`) sunucuda bulunamadı!", ephemeral=True)

        # Sunucunun tüm üyelerini önbelleğe al
        if not guild.chunked:
            await guild.chunk()

        # Sadece hedef role sahip, bot olmayan ve botun değiştirebileceği üyeleri filtrele
        eligible_members = [
            m for m in target_role.members 
            if not m.bot and m.id != guild.owner_id and m.top_role < guild.me.top_role
        ]

        if not eligible_members:
            return await interaction.followup.send("ℹ️ Hedef role sahip veya düzenlenebilecek üye bulunamadı.", ephemeral=True)

        updated_count = 0
        failed_count = 0

        async def process_member(member: discord.Member):
            nonlocal updated_count, failed_count
            expected_nick = self.build_expected_nickname(member)
            current_nick = member.nick if member.nick else member.name

            if current_nick != expected_nick:
                try:
                    await member.edit(nick=expected_nick, reason=f"Hızlı Takma Ad Eşitleme: {interaction.user}")
                    updated_count += 1
                except discord.RateLimited as r:
                    await asyncio.sleep(r.retry_after)
                    try:
                        await member.edit(nick=expected_nick, reason=f"Hızlı Takma Ad Eşitleme: {interaction.user}")
                        updated_count += 1
                    except Exception:
                        failed_count += 1
                except Exception:
                    failed_count += 1

        # 5'erli paralel demetler (Batch) halinde hızlı işlem
        batch_size = 5
        for i in range(0, len(eligible_members), batch_size):
            batch = eligible_members[i:i + batch_size]
            await asyncio.gather(*(process_member(m) for m in batch))
            await asyncio.sleep(0.3)

        embed = discord.Embed(
            title="⚡ Hızlı Takma Ad Senkronizasyonu Tamamlandı",
            color=config.COLOR_HEX
        )
        embed.add_field(name="🎯 Taranan Hedef Üye", value=f"`{len(eligible_members)} Kişi`", inline=False)
        embed.add_field(name="✅ Güncellenen Takma Ad", value=f"`{updated_count} Kişi`", inline=True)
        embed.add_field(name="👌 Zaten Doğru Olan", value=f"`{len(eligible_members) - updated_count - failed_count} Kişi`", inline=True)
        if failed_count > 0:
            embed.add_field(name="⚠️ Hata / Atlanan", value=f"`{failed_count} Kişi`", inline=True)

        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoNickSync(bot))
