import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

REPORT_LOG_CHANNEL_ID = getattr(config, "REPORT_LOG_CHANNEL_ID", 1541807577837342834)
DISCORD_NICK_LIMIT = 32

class NicknameManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def check_staff_permission(self, author: discord.Member) -> bool:
        if author.guild_permissions.administrator or author.guild_permissions.manage_nicknames:
            return True
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        if staff_role_id:
            staff_role = author.guild.get_role(staff_role_id)
            if staff_role and staff_role in author.roles:
                return True
        return False

    async def process_name_change(self, author: discord.Member, target: discord.Member, new_name: str, guild: discord.Guild):
        if not self.check_staff_permission(author):
            return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        if len(new_name) > DISCORD_NICK_LIMIT:
            return False, f"❌ **Karakter Sınırı Aşıldı!**\nDiscord takma ad sınırı en fazla **{DISCORD_NICK_LIMIT}** karakterdir. Girdiğiniz isim **{len(new_name)}** karakter."

        if author.id != guild.owner_id and target.top_role >= author.top_role:
            return False, "❌ Rol hiyerarşisi nedeniyle kendi rolünüzle **aynı seviyede** veya sizden **daha üst seviyedeki** birinin ismini değiştiremezsiniz!"

        if target.id == guild.owner_id:
            return False, "❌ Sunucu sahibinin takma adı Discord kısıtlamaları nedeniyle bot tarafından değiştirilemez!"

        if target.top_role >= guild.me.top_role:
            return False, "❌ Botun rol yetkisi bu kullanıcının ismini değiştirmeye yetmiyor. Lütfen botun rolünü daha yukarı taşıyın!"

        old_name = target.display_name

        try:
            await target.edit(nick=new_name, reason=f"İsim Değiştirme: {author} ({author.id}) tarafından yapıldı.")
        except discord.Forbidden:
            return False, "❌ Discord yetkileri nedeniyle kullanıcının ismi değiştirilemedi."
        except Exception as e:
            return False, f"❌ İsim değiştirilirken bir hata oluştu: {e}"

        report_channel = guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if report_channel is None:
            try:
                report_channel = await guild.fetch_channel(REPORT_LOG_CHANNEL_ID)
            except Exception:
                pass

        if report_channel:
            report_embed = discord.Embed(
                title="📝 Takma Ad Değişikliği Raporu",
                color=discord.Color.from_rgb(0, 168, 243),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            report_embed.add_field(name="👤 Kullanıcı", value=f"{target.mention} (`{target.id}`)", inline=False)
            report_embed.add_field(name="🏷️ Eski İsim", value=f"`{old_name}`", inline=True)
            report_embed.add_field(name="✨ Yeni İsim", value=f"`{new_name}`", inline=True)
            report_embed.add_field(name="🛡️ İşlemi Yapan Yetkili", value=f"{author.mention} (`{author.id}`)", inline=False)
            report_embed.set_thumbnail(url=target.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {target.id}")

            try:
                await report_channel.send(embed=report_embed)
            except Exception as e:
                print(f"[HATA] İsim değiştirme raporu gönderilemedi: {e}")

        return True, f"{target.mention} kullanıcısının ismi başarıyla **{new_name}** olarak güncellendi."

    @app_commands.command(name="isimdegistir", description="Kullanıcının takma adını günceller.")
    @app_commands.describe(
        kullanıcı="İsmi değiştirilecek üye",
        isim="Yeni verilecek takma ad (Maksimum 32 karakter)"
    )
    async def isimdegistir_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, isim: str):
        await interaction.response.defer(ephemeral=True)

        success, msg = await self.process_name_change(interaction.user, kullanıcı, isim, interaction.guild)
        if not success:
            await interaction.followup.send(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Takma Ad Değiştirildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.command(name="isimdeğistir", aliases=["İsimdeğistir", "İSİMDEĞİSTİR", "isimdegistir", "İsimdegistir", "İSİMDEGİSTİR"])
    async def isimdegistir_prefix(self, ctx: commands.Context, kullanıcı: discord.Member = None, *, yeni_isim: str = None):
        if kullanıcı is None or yeni_isim is None:
            await ctx.reply(
                "❌ **Hatalı Kullanım!**\nDoğru format: `d!isimdeğistir @kullanıcı Yeni İsim`\nÖrnek: `d!isimdeğistir @üye Melih Gökçek / GB`",
                mention_author=False
            )
            return

        success, msg = await self.process_name_change(ctx.author, kullanıcı, yeni_isim, ctx.guild)
        if not success:
            await ctx.reply(msg, mention_author=False)
            return

        embed = discord.Embed(
            title="✅ Takma Ad Değiştirildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {ctx.author.display_name}")
        await ctx.reply(embed=embed, mention_author=False)

    @isimdegistir_prefix.error
    async def isimdegistir_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Belirtilen kullanıcı sunucuda bulunamadı!", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Geçersiz bir kullanıcı etiketlediniz!", mention_author=False)

async def setup(bot):
    await bot.add_cog(NicknameManagement(bot))
