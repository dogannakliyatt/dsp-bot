import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

REPORT_LOG_CHANNEL_ID = 1541807577837342834

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ortak Güvenlik ve Rol Verme Mantığı
    async def process_role_give(self, author: discord.Member, target: discord.Member, role: discord.Role, guild: discord.Guild):
        # Yetkili Kontrolü
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role and staff_role not in author.roles and not author.guild_permissions.administrator:
                return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        # 1. Kural: Yönetici (Administrator) yetkisi olan roller verilemez
        if role.permissions.administrator:
            return False, "❌ **Güvenlik Uyarısı:** Yönetici (Administrator) yetkisine sahip roller bu komutla verilemez!"

        # 2. Kural: @everyone ve entegrasyon/bot rolleri verilemez
        if role.is_default() or role.is_integration() or role.is_bot_managed():
            return False, "❌ Bu özel veya varsayılan rol kullanıcılara atanamaz!"

        # 3. Kural: Yetkili kendi rolüne eşit veya üstündeki rolleri veremez (Sunucu Sahibi hariç)
        if author.id != guild.owner_id and role >= author.top_role:
            return False, "❌ Kendi rolünüzle **aynı seviyede** veya sizden **daha üst seviyedeki** bir rolü veremezsiniz!"

        # 4. Kural: Botun rol sırası kontrolü
        if role >= guild.me.top_role:
            return False, "❌ Botun rol yetkisi bu rolü vermeye yetmiyor. Botun rolünü sunucu ayarlarından daha yukarı taşıyın!"

        # Kullanıcıda zaten bu rol var mı?
        if role in target.roles:
            return False, f"ℹ️ {target.mention} kullanıcısında zaten {role.mention} rolü bulunuyor."

        # Rolü verme işlemi
        try:
            await target.add_roles(role, reason=f"Rol Ver: {author} ({author.id}) tarafından verildi.")
        except discord.Forbidden:
            return False, "❌ Discord izinleri nedeniyle rol verilemedi."
        except Exception as e:
            return False, f"❌ Rol verilirken bir hata oluştu: {e}"

        # 1541807577837342834 ID'li Log Kanalına Rapor Gönderme
        report_channel = guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if report_channel is None:
            try:
                report_channel = await guild.fetch_channel(REPORT_LOG_CHANNEL_ID)
            except Exception:
                pass

        if report_channel:
            report_embed = discord.Embed(
                title="🛡️ Rol Verme İşlemi Raporu",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            report_embed.add_field(name="👤 Kullanıcı", value=f"{target.mention} (`{target.id}`)", inline=False)
            report_embed.add_field(name="🎖️ Verilen Rol", value=f"{role.mention} (`{role.id}`)", inline=False)
            report_embed.add_field(name="🛡️ Yetkili", value=f"{author.mention} (`{author.id}`)", inline=False)
            report_embed.set_thumbnail(url=target.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {target.id}")

            try:
                await report_channel.send(embed=report_embed)
            except Exception as e:
                print(f"[HATA] Rapor gönderilemedi: {e}")

        return True, f"{target.mention} kullanıcısına {role.mention} rolü başarıyla verildi."

    # ------------------ /rolver SLASH KOMUTU ------------------
    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        user_top_role = interaction.user.top_role
        is_owner = interaction.user.id == interaction.guild.owner_id

        for role in interaction.guild.roles:
            if role.is_default() or role.is_integration() or role.is_bot_managed() or role.permissions.administrator:
                continue
            if not is_owner and role >= user_top_role:
                continue
            if current.lower() in role.name.lower():
                choices.append(app_commands.Choice(name=role.name, value=str(role.id)))
                if len(choices) >= 25:
                    break
        return choices

    @app_commands.command(name="rolver", description="Kullanıcıya güvenli bir şekilde tek bir rol verir.")
    @app_commands.describe(kullanıcı="Rol verilecek kullanıcı", rol="Verilecek rolü seçin veya ismini yazın")
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolver_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, rol: str):
        target_role = None
        if rol.isdigit():
            target_role = interaction.guild.get_role(int(rol))
        if not target_role:
            target_role = discord.utils.get(interaction.guild.roles, name=rol)

        if not target_role:
            await interaction.response.send_message("❌ Belirtilen rol sunucuda bulunamadı!", ephemeral=True)
            return

        await interaction.response.defer()

        success, msg = await self.process_role_give(interaction.user, kullanıcı, target_role, interaction.guild)
        if not success:
            await interaction.followup.send(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    # ------------------ d!rolver / D!rolver METİN KOMUTU ------------------
    @commands.command(name="rolver", aliases=["Rolver", "ROLVER"])
    async def rolver_prefix(self, ctx: commands.Context, kullanıcı: discord.Member = None, role: discord.Role = None):
        if kullanıcı is None or role is None:
            await ctx.reply(
                "❌ **Hatalı Kullanım!**\nDoğru format: `d!rolver @kullanıcı @rol` veya `D!rolver @kullanıcı @rol`",
                mention_author=False
            )
            return

        success, msg = await self.process_role_give(ctx.author, kullanıcı, role, ctx.guild)
        if not success:
            await ctx.reply(msg, mention_author=False)
            return

        embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {ctx.author.display_name}")
        await ctx.reply(embed=embed, mention_author=False)

    @rolver_prefix.error
    async def rolver_prefix_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Belirtilen kullanıcı sunucuda bulunamadı!", mention_author=False)
        elif isinstance(error, commands.RoleNotFound):
            await ctx.reply("❌ Belirtilen rol sunucuda bulunamadı!", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Geçersiz bir kullanıcı veya rol etiketlediniz!", mention_author=False)

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
