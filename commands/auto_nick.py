import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import config

TARGET_ROLE_ID = getattr(config, "BASE_MEMBER_ROLE_ID", 1537153933305315328)

PARTY_TITLE_PRIORITY = [
    ("GB", 1537148955840741376),
    ("GBV", 1537149075194118248),
    ("PGS", 1537149226990182450),
    ("MYKB", 1537149324473929778),
    ("OB", 1537149401649381417),
    ("GBY", 1537149477796970686),
    ("İB", 1537149544289275987),
    ("SZC", 1537149604343316572),
    ("GKB", 1537149684345475123),
    ("MYKÜ", 1537149762913046568)
]

RP_TITLE_PRIORITY = [
    ("CBY", 1537595817429569706),
    ("CB", 1537149921541492836),
    ("BB", 1537149991146229810),
    ("TBMMBV", 1537150202857787402),
    ("TBMMB", 1537150038512242740),
    ("TBMMK", 1537154296737701960),
    ("TCK", 1537150254833467502),
    ("İBB", 1537151635170525334),
    ("ABB", 1537151839881924691),
    ("İZBB", 1537151887231426620),
    ("BBB", 1537151950884175872),
    ("MGBV", 1537150854786719875),
    ("MGB", 1537150788533485578),
    ("MV", 1537150966535553035)
]

CANDIDATE_TAG_MAP = [
    ("Cumhurbaşkanı Adayı", "CBA"),
    ("Cumhurbaskani Adayi", "CBA"),
    ("Cumhurbaşkanı Aday", "CBA"),
    ("Milletvekili Adayı", "MVA"),
    ("Milletvekili Adayi", "MVA"),
    ("Milletvekili Aday", "MVA"),
    ("Başbakan Adayı", "BBA"),
    ("Başbakan Aday", "BBA"),
    ("İstanbul Büyükşehir Belediye Başkanı Adayı", "İBBA"),
    ("Ankara Büyükşehir Belediye Başkanı Adayı", "ABBA"),
    ("İzmir Büyükşehir Belediye Başkanı Adayı", "İZBBA"),
    ("Bursa Büyükşehir Belediye Başkanı Adayı", "BBBA"),
    ("Genel Başkan Adayı", "GBA"),
    ("Genel Başkan Aday", "GBA")
]

class AutoNickSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._updating_members = set()

    def get_base_name(self, display_name: str) -> str:
        if not display_name:
            return "Kullanıcı"
        return display_name.split("/")[0].strip()

    def get_candidate_title(self, member: discord.Member):
        for role in member.roles:
            r_name = role.name.strip()
            for cand_name, cand_tag in CANDIDATE_TAG_MAP:
                if cand_name.lower() in r_name.lower():
                    return cand_tag
            if r_name.endswith("Adayı") or r_name.endswith("Aday") or r_name.endswith("Adayi"):
                clean = re.sub(r'[^a-zA-ZçğıöşüÇĞİÖŞÜ ]', '', r_name).strip()
                words = [w for w in clean.split() if w.lower() not in ["aday", "adayı", "adayi"]]
                tag = "".join([w[0].upper() for w in words]) + "A"
                if len(tag) >= 2:
                    return tag
        return None

    def determine_titles(self, member: discord.Member):
        user_role_ids = {r.id for r in member.roles}
        parti_title = None
        rp_title = None

        for title, role_id in PARTY_TITLE_PRIORITY:
            if role_id in user_role_ids:
                parti_title = title
                break

        for title, role_id in RP_TITLE_PRIORITY:
            if role_id in user_role_ids:
                rp_title = title
                break

        cand_title = self.get_candidate_title(member)
        if cand_title:
            rp_title = cand_title

        return parti_title, rp_title

    def build_expected_nickname(self, member: discord.Member) -> str:
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

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot or after.id == after.guild.owner_id:
            return

        if after.id in self._updating_members:
            return

        if before.nick == after.nick and before.roles == after.roles:
            return

        has_target_role = any(r.id == TARGET_ROLE_ID for r in after.roles)
        had_target_role = any(r.id == TARGET_ROLE_ID for r in before.roles)
        if not has_target_role and not had_target_role:
            return

        if after.top_role >= after.guild.me.top_role:
            return

        expected_nick = self.build_expected_nickname(after)
        current_nick = after.nick if after.nick else after.name

        if current_nick != expected_nick:
            self._updating_members.add(after.id)
            try:
                await after.edit(nick=expected_nick, reason="Otomatik Parti/RP/Aday Takma Ad Güncellemesi")
            except Exception:
                pass
            finally:
                await asyncio.sleep(1)
                self._updating_members.discard(after.id)

    @app_commands.command(
        name="ototakmaadesitle", 
        description="DSP Üyelerinin makam ve aday takma adlarını güncel rollere göre baştan eşitler."
    )
    async def sync_all_nicknames(self, interaction: discord.Interaction):
        if not config.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        target_role = guild.get_role(TARGET_ROLE_ID)

        if not target_role:
            return await interaction.followup.send(f"❌ Hedef rol (`ID: {TARGET_ROLE_ID}`) sunucuda bulunamadı!", ephemeral=True)

        if not guild.chunked:
            await guild.chunk()

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

        batch_size = 2
        for i in range(0, len(eligible_members), batch_size):
            batch = eligible_members[i:i + batch_size]
            await asyncio.gather(*(process_member(m) for m in batch))
            await asyncio.sleep(1.0)

        embed = discord.Embed(
            title="⚡ Takma Ad Senkronizasyonu Tamamlandı",
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
