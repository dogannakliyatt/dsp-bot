import discord
from discord.ext import commands
import datetime
import config

LOG_CHANNEL_ID = getattr(config, "MEMBER_LOG_CHANNEL_ID", 1537161700380377138)
AUTOPING_CHANNEL_ID = getattr(config, "AUTOPING_CHANNEL_ID", 1545438496213311488)
WELCOME_CHANNEL_ID = getattr(config, "WELCOME_CHANNEL_ID", 1537157370264944690)

def calculate_account_age(created_at: datetime.datetime):
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - created_at
    total_days = delta.days
    
    years = total_days // 365
    remaining_days = total_days % 365
    months = remaining_days // 30
    days = remaining_days % 30
    
    formatted_date = created_at.strftime("%d/%m/%Y")
    return f"{formatted_date} & {days} Gün {months} Ay {years} Yıl önce"

class MemberLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        unreg_role_id = getattr(config, "UNREGISTERED_ROLE_ID", None)
        if unreg_role_id:
            unreg_role = member.guild.get_role(unreg_role_id)
            if unreg_role and unreg_role < member.guild.me.top_role:
                try:
                    await member.add_roles(unreg_role, reason="Yeni üye katıldı (Oto Kayıtsız Rol).")
                except Exception:
                    pass

        log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            total_members = member.guild.member_count
            msg = f"<a:erensigiris:1537179743445712926> {member.mention} Katıldı! {total_members}"
            try:
                await log_channel.send(msg)
            except Exception:
                pass

        ping_channel = member.guild.get_channel(AUTOPING_CHANNEL_ID)
        if ping_channel:
            welcome_text = f"*👋🏻 {member.mention} Hoş Geldiniz, Bu Formu Doldurarak Kayıt Olabilirsiniz.*"
            try:
                await ping_channel.send(welcome_text, delete_after=10)
            except Exception:
                pass

        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            age_str = calculate_account_age(member.created_at)
            
            embed = discord.Embed(
                description=(
                    f"👋🏻 Yeni Bir Kullanıcı Katıldı, {member.mention}\n\n"
                    f"☺️ Sunucumuza Hoş Geldin!\n\n"
                    f"🙂 Seninle Birlikte {member.guild.member_count} Kişiyiz.\n\n"
                    f"**Hesap Oluşturulma Tarihi:** {age_str}"
                ),
                color=discord.Color.from_rgb(0, 168, 243)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            mention_content = f"{member.mention} sunucuya giriş yaptı."
            try:
                await welcome_channel.send(content=mention_content, embed=embed)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            total_members = member.guild.member_count
            msg = f"<a:erensicikis:1537179768641028168> {member.mention} Ayrıldı! {total_members}"
            try:
                await log_channel.send(msg)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(MemberLogs(bot))
