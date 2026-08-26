import discord
from discord.ext import commands
import config

LOG_CHANNEL_ID = 1537161700380377138

class MemberLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Sunucuya Biri Katıldığında
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # 1. Otomatik Kayıtsız Rolü Verme
        unreg_role_id = getattr(config, "UNREGISTERED_ROLE_ID", None)
        if unreg_role_id:
            unreg_role = member.guild.get_role(unreg_role_id)
            if unreg_role:
                try:
                    await member.add_roles(unreg_role, reason="Yeni üye katıldı (Oto Kayıtsız Rol).")
                except Exception:
                    pass

        # 2. Giriş Mesajını Gönderme
        channel = member.guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            total_members = member.guild.member_count
            msg = f"<a:erensigiris:1537179743445712926> {member.mention} Katıldı! {total_members}"
            try:
                await channel.send(msg)
            except Exception:
                pass

    # Sunucudan Biri Ayrıldığında
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = member.guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            total_members = member.guild.member_count
            msg = f"<a:erensicikis:1537179768641028168> {member.mention} Ayrıldı! {total_members}"
            try:
                await channel.send(msg)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(MemberLogs(bot))
