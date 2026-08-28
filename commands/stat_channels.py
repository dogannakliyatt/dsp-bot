import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import config
import database

GB_ROLE_IDS = getattr(config, "GB_ROLE_IDS", [1537148955840741376, 1537153445067489321])
GB_CHANNEL_ID = getattr(config, "STAT_GB_CHANNEL_ID", 1542970479520911360)
IDEOLOGY_CHANNEL_ID = getattr(config, "STAT_IDEOLOGY_CHANNEL_ID", 1542970703890878505)
COMPASS_CHANNEL_ID = getattr(config, "STAT_COMPASS_CHANNEL_ID", 1542971033936592906)
MEMBER_CHANNEL_ID = getattr(config, "STAT_MEMBER_COUNT_CHANNEL_ID", 1542970881033371709)

class StatChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats_loop.start()

    def cog_unload(self):
        self.update_stats_loop.cancel()

    def get_clean_name(self, display_name: str) -> str:
        if not display_name:
            return ""
        return display_name.split("/")[0].strip()

    def has_any_gb_role(self, member: discord.Member) -> bool:
        if not member or member.bot:
            return False
        user_role_ids = {r.id for r in member.roles}
        return any(gb_id in user_role_ids for gb_id in GB_ROLE_IDS)

    # ==========================================
    # 🔧 KANAL İSİM GÜNCELLEME MOTORU
    # ==========================================

    async def update_gb_channel(self, guild: discord.Guild):
        channel = guild.get_channel(GB_CHANNEL_ID)
        if not channel:
            return

        if not guild.chunked:
            try:
                await guild.chunk()
            except Exception:
                pass

        gb_members = []
        seen_ids = set()

        for member in guild.members:
            if not member.bot and self.has_any_gb_role(member) and member.id not in seen_ids:
                seen_ids.add(member.id)
                clean = self.get_clean_name(member.display_name)
                if clean:
                    gb_members.append(clean)

        new_name = f"👑︱GB: {' - '.join(gb_members)}" if gb_members else "👑︱GB:"
        new_name = new_name[:99]

        if channel.name != new_name:
            try:
                await channel.edit(name=new_name, reason="Otomatik GB Listesi Senkronizasyonu")
            except discord.HTTPException:
                pass

    async def update_member_count_channel(self, guild: discord.Guild):
        channel = guild.get_channel(MEMBER_CHANNEL_ID)
        if not channel:
            return

        total_members = guild.member_count
        new_name = f"📊︱ÜYE SAYISI: {total_members}"[:99]

        if channel.name != new_name:
            try:
                await channel.edit(name=new_name, reason="Otomatik Üye Sayısı Güncellemesi")
            except discord.HTTPException:
                pass

    async def update_ideology_channel(self, guild: discord.Guild, value: str = None):
        channel = guild.get_channel(IDEOLOGY_CHANNEL_ID)
        if not channel:
            return

        if not value:
            value = await asyncio.to_thread(database.get_stat_setting, "ideology", "Sosyal Demokrasi")

        new_name = f"💬︱İDEOLOJİ: {value}"[:99]
        if channel.name != new_name:
            try:
                await channel.edit(name=new_name, reason="İdeoloji Bilgisi Güncellendi")
            except discord.HTTPException:
                pass

    async def update_compass_channel(self, guild: discord.Guild, value: str = None):
        channel = guild.get_channel(COMPASS_CHANNEL_ID)
        if not channel:
            return

        if not value:
            value = await asyncio.to_thread(database.get_stat_setting, "compass", "Merkez Sol")

        new_name = f"🧭︱SİYASİ PUSULA: {value}"[:99]
        if channel.name != new_name:
            try:
                await channel.edit(name=new_name, reason="Siyasi Pusula Bilgisi Güncellendi")
            except discord.HTTPException:
                pass

    # ==========================================
    # ⚡ PERİYODİK VE ANLIK TETİKLEYİCİLER
    # ==========================================

    @tasks.loop(minutes=10)
    async def update_stats_loop(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.update_gb_channel(guild)
            await self.update_member_count_channel(guild)
            await self.update_ideology_channel(guild)
            await self.update_compass_channel(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.update_member_count_channel(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.update_member_count_channel(member.guild)
        if self.has_any_gb_role(member):
            await self.update_gb_channel(member.guild)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        had_gb = self.has_any_gb_role(before)
        has_gb = self.has_any_gb_role(after)

        if (had_gb != has_gb) or (has_gb and before.display_name != after.display_name):
            await self.update_gb_channel(after.guild)

    # ==========================================
    # 🛠️ YÖNETİM SLASH KOMUTLARI
    # ==========================================

    @app_commands.command(name="ideolojidegistir", description="İdeoloji ses kanalının ismini günceller.")
    @app_commands.describe(ideoloji="Yeni ideoloji metni")
    async def ideolojidegistir(self, interaction: discord.Interaction, ideoloji: str):
        if not config.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await asyncio.to_thread(database.set_stat_setting, "ideology", ideoloji)
        await self.update_ideology_channel(interaction.guild, ideoloji)

        embed = discord.Embed(
            title="✅ İdeoloji Bilgisi Güncellendi",
            description=f"Kanal adı **💬︱İDEOLOJİ: {ideoloji}** olarak ayarlandı.",
            color=config.COLOR_HEX
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="pusuladegistir", description="Siyasi Pusula ses kanalının ismini günceller.")
    @app_commands.describe(pusula="Yeni pusula konumu metni")
    async def pusuladegistir(self, interaction: discord.Interaction, pusula: str):
        if not config.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await asyncio.to_thread(database.set_stat_setting, "compass", pusula)
        await self.update_compass_channel(interaction.guild, pusula)

        embed = discord.Embed(
            title="✅ Siyasi Pusula Güncellendi",
            description=f"Kanal adı **🧭︱SİYASİ PUSULA: {pusula}** olarak ayarlandı.",
            color=config.COLOR_HEX
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatChannels(bot))
