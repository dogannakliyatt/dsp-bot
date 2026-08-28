import discord
from discord.ext import commands
from discord import app_commands
import datetime
import difflib
import asyncio
import config

REPORT_LOG_CHANNEL_ID = 1541807577837342834

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def find_role(self, guild: discord.Guild, query: str):
        query = query.strip()
        clean_id = query.replace("<@&", "").replace(">", "").strip()
        if clean_id.isdigit():
            role_by_id = guild.get_role(int(clean_id))
            if role_by_id:
                return role_by_id

        query_lower = query.lower()
        for role in guild.roles:
            if role.name.lower() == query_lower:
                return role

        for role in guild.roles:
            if role.is_default():
                continue
            if query_lower in role.name.lower() or role.name.lower() in query_lower:
                return role

        role_names = [r.name for r in guild.roles if not r.is_default()]
        matches = difflib.get_close_matches(query, role_names, n=1, cutoff=0.6)
        if matches:
            return discord.utils.get(guild.roles, name=matches[0])

        return None

    async def process_role_give(self, author: discord.Member, target: discord.Member, role: discord.Role, guild: discord.Guild):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role and staff_role not in author.roles and not author.guild_permissions.administrator:
                return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        if role.permissions.administrator:
            return False, "❌ **Güvenlik Uyarısı:** Yönetici yetkisine sahip roller bu komutla verilemez!"

        if role.is_default() or role.is_integration() or role.is_bot_managed():
            return False, "❌ Bu özel veya varsayılan rol kullanıcılara atanamaz!"

        if author.id != guild.owner_id and role >= author.top_role:
            return False, "❌ Kendi rolünüzle **aynı seviyede** veya sizden **daha üst seviyedeki** bir rolü veremezsiniz!"

        if role >= guild.me.top_role:
            return False, "❌ Botun rol yetkisi bu rolü vermeye yetmiyor. Botun rolünü sunucu ayarlarından daha yukarı taşıyın!"

        if role in target.roles:
            return False, f"ℹ️ {target.mention} kullanıcısında zaten {role.mention} rolü bulunuyor."

        try:
            await target.add_roles(role, reason=f"Rol Ver: {author} ({author.id}) tarafından verildi.")
        except discord.Forbidden:
            return False, "❌ Discord izinleri nedeniyle rol verilemedi."
        except Exception as e:
            return False, f"❌ Rol verilirken bir hata oluştu: {e}"

        await self.send_report(guild, target, role, author, action_type="Verildi")
        return True, f"{target.mention} kullanıcısına {role.mention} rolü başarıyla verildi."

    async def process_role_remove(self, author: discord.Member, target: discord.Member, role: discord.Role, guild: discord.Guild):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role and staff_role not in author.roles and not author.guild_permissions.administrator:
                return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        if role.permissions.administrator:
            return False, "❌ **Güvenlik Uyarısı:** Yönetici yetkisine sahip roller bu komutla alınamaz!"

        if role.is_default() or role.is_integration() or role.is_bot_managed():
            return False, "❌ Bu özel veya varsayılan rol kullanıcıdan alınamaz!"

        if author.id != guild.owner_id and role >= author.top_role:
            return False, "❌ Kendi rolünüzle **aynı seviyede** veya sizden **daha üst seviyedeki** bir rolü alamazsınız!"

        if role >= guild.me.top_role:
            return False, "❌ Botun rol yetkisi bu rolü almaya yetmiyor. Botun rolünü sunucu ayarlarından daha yukarı taşıyın!"

        if role not in target.roles:
            return False, f"ℹ️ {target.mention} kullanıcısında zaten {role.mention} rolü bulunmuyor."

        try:
            await target.remove_roles(role, reason=f"Rol Al: {author} ({author.id}) tarafından alındı.")
        except discord.Forbidden:
            return False, "❌ Discord izinleri nedeniyle rol alınamadı."
        except Exception as e:
            return False, f"❌ Rol alınırken bir hata oluştu: {e}"

        await self.send_report(guild, target, role, author, action_type="Alındı")
        return True, f"{target.mention} kullanıcısından {role.mention} rolü başarıyla alındı."

    async def send_report(self, guild: discord.Guild, target: discord.Member, role: discord.Role, author: discord.Member, action_type: str):
        report_channel = guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if report_channel is None:
            try:
                report_channel = await guild.fetch_channel(REPORT_LOG_CHANNEL_ID)
            except Exception:
                pass

        if report_channel:
            is_give = action_type == "Verildi"
            report_embed = discord.Embed(
                title=f"🛡️ Rol {action_type} Raporu",
                color=discord.Color.blue() if is_give else discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            report_embed.add_field(name="👤 Kullanıcı", value=f"{target.mention} (`{target.id}`)", inline=False)
            report_embed.add_field(name=f"🎖️ {action_type} Rol", value=f"{role.mention} (`{role.id}`)", inline=False)
            report_embed.add_field(name="🛡️ Yetkili", value=f"{author.mention} (`{author.id}`)", inline=False)
            report_embed.set_thumbnail(url=target.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {target.id}")

            try:
                await report_channel.send(embed=report_embed)
            except Exception as e:
                print(f"[HATA] Rapor gönderilemedi: {e}")

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

    # ================== TOPLU ROL VER / AL KOMUTLARI ==================
    @app_commands.command(name="toplurolver", description="Hedef role sahip tüm kullanıcılara yeni bir rol verir.")
    @app_commands.describe(kaynak_rol="Hangi role sahip olanlar etkilenecek?", verilecek_rol="Verilecek yeni rol")
    async def toplu_rol_ver(self, interaction: discord.Interaction, kaynak_rol: discord.Role, verilecek_rol: discord.Role):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Bu komutu yalnızca Yöneticiler kullanabilir.", ephemeral=True)

        if verilecek_rol >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Botun yetkisi bu rolü vermeye yetmiyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        members = [m for m in kaynak_rol.members if verilecek_rol not in m.roles]
        count = 0

        for member in members:
            try:
                await member.add_roles(verilecek_rol, reason=f"Toplu Rol Ver: {interaction.user}")
                count += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass

        await interaction.followup.send(f"✅ {kaynak_rol.mention} rolüne sahip toplam **{count}** kullanıcıya {verilecek_rol.mention} rolü başarıyla verildi.", ephemeral=True)

    @app_commands.command(name="toplurolal", description="Hedef role sahip tüm kullanıcılardan belirtilen bir rolü alır.")
    @app_commands.describe(kaynak_rol="Hangi role sahip olanlar etkilenecek?", alinacak_rol="Kullanıcılardan alınacak rol")
    async def toplu_rol_al(self, interaction: discord.Interaction, kaynak_rol: discord.Role, alinacak_rol: discord.Role):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Bu komutu yalnızca Yöneticiler kullanabilir.", ephemeral=True)

        if alinacak_rol >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Botun yetkisi bu rolü almaya yetmiyor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        members = [m for m in kaynak_rol.members if alinacak_rol in m.roles]
        count = 0

        for member in members:
            try:
                await member.remove_roles(alinacak_rol, reason=f"Toplu Rol Al: {interaction.user}")
                count += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass

        await interaction.followup.send(f"✅ {kaynak_rol.mention} rolüne sahip toplam **{count}** kullanıcıdan {alinacak_rol.mention} rolü başarıyla alındı.", ephemeral=True)

    # ================== TEKİL ROL VER KOMUTLARI ==================
    @app_commands.command(name="rolver", description="Kullanıcıya güvenli bir şekilde tek bir rol verir.")
    @app_commands.describe(kullanıcı="Rol verilecek kullanıcı", rol="Verilecek rolü seçin veya ismini yazın")
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolver_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, rol: str):
        target_role = self.find_role(interaction.guild, rol)
        if not target_role:
            return await interaction.response.send_message(f"❌ Sunucuda `{rol}` adında veya benzer bir rol bulunamadı!", ephemeral=True)

        await interaction.response.defer()
        success, msg = await self.process_role_give(interaction.user, kullanıcı, target_role, interaction.guild)
        if not success:
            return await interaction.followup.send(msg, ephemeral=True)

        embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @commands.command(name="rolver", aliases=["Rolver", "ROLVER", "rol", "Rol", "ROL"])
    async def rolver_prefix(self, ctx: commands.Context, kullanıcı: discord.Member = None, *, rol_metni: str = None):
        if kullanıcı is None or rol_metni is None:
            return await ctx.reply("❌ **Hatalı Kullanım!**\nDoğru format: `d!rol @kullanıcı <Rol İsmi veya @Rol>`\nÖrnek: `d!rol @üye Cumhurbaşkanı Yardımcısı`", mention_author=False)

        target_role = self.find_role(ctx.guild, rol_metni)
        if not target_role:
            return await ctx.reply(f"❌ Sunucuda `{rol_metni}` adında veya benzer bir rol bulunamadı!", mention_author=False)

        success, msg = await self.process_role_give(ctx.author, kullanıcı, target_role, ctx.guild)
        if not success:
            return await ctx.reply(msg, mention_author=False)

        embed = discord.Embed(
            title="✅ Rol Başarıyla Verildi",
            description=msg,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {ctx.author.display_name}")
        await ctx.reply(embed=embed, mention_author=False)

    # ================== TEKİL ROL AL KOMUTLARI ==================
    @app_commands.command(name="rolal", description="Kullanıcıdan güvenli bir şekilde tek bir rolü alır.")
    @app_commands.describe(kullanıcı="Rolü alınacak kullanıcı", rol="Alınacak rolü seçin veya ismini yazın")
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolal_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, rol: str):
        target_role = self.find_role(interaction.guild, rol)
        if not target_role:
            return await interaction.response.send_message(f"❌ Sunucuda `{rol}` adında veya benzer bir rol bulunamadı!", ephemeral=True)

        await interaction.response.defer()
        success, msg = await self.process_role_remove(interaction.user, kullanıcı, target_role, interaction.guild)
        if not success:
            return await interaction.followup.send(msg, ephemeral=True)

        embed = discord.Embed(
            title="🗑️ Rol Başarıyla Alındı",
            description=msg,
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @commands.command(name="rolal", aliases=["Rolal", "ROLAL"])
    async def rolal_prefix(self, ctx: commands.Context, kullanıcı: discord.Member = None, *, rol_metni: str = None):
        if kullanıcı is None or rol_metni is None:
            return await ctx.reply("❌ **Hatalı Kullanım!**\nDoğru format: `d!rolal @kullanıcı <Rol İsmi veya @Rol>`\nÖrnek: `d!rolal @üye Cumhurbaşkanı Yardımcısı`", mention_author=False)

        target_role = self.find_role(ctx.guild, rol_metni)
        if not target_role:
            return await ctx.reply(f"❌ Sunucuda `{rol_metni}` adında veya benzer bir rol bulunamadı!", mention_author=False)

        success, msg = await self.process_role_remove(ctx.author, kullanıcı, target_role, ctx.guild)
        if not success:
            return await ctx.reply(msg, mention_author=False)

        embed = discord.Embed(
            title="🗑️ Rol Başarıyla Alındı",
            description=msg,
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"İşlemi Yapan: {ctx.author.display_name}")
        await ctx.reply(embed=embed, mention_author=False)

    @rolver_prefix.error
    @rolal_prefix.error
    async def role_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Belirtilen kullanıcı sunucuda bulunamadı!", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Geçersiz bir kullanıcı etiketlediniz!", mention_author=False)

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
