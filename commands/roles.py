import discord
from discord.ext import commands
from discord import app_commands
import datetime
import difflib
import config

REPORT_LOG_CHANNEL_ID = 1541807577837342834

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Akıllı Rol Bulucu (Etiket, ID, Tam İsim, Kısmi İsim ve Benzerlik)
    def find_role(self, guild: discord.Guild, query: str):
        query = query.strip()
        
        # 1. Rol Etiket veya ID Kontrolü (<@&123...> veya 123...)
        clean_id = query.replace("<@&", "").replace(">", "").strip()
        if clean_id.isdigit():
            role_by_id = guild.get_role(int(clean_id))
            if role_by_id:
                return role_by_id

        # 2. Tam Birebir İsim Eşleşmesi (Küçük/Büyük Harf Duyarsız)
        query_lower = query.lower()
        for role in guild.roles:
            if role.name.lower() == query_lower:
                return role

        # 3. Kısmi İsim Eşleşmesi (Örn: 'Cumhurbaşkanı Yardımcısı' -> 'T.C. Cumhurbaşkanı Yardımcısı')
        for role in guild.roles:
            if role.is_default():
                continue
            if query_lower in role.name.lower() or role.name.lower() in query_lower:
                return role

        # 4. Yazım Hatası / Yakın Benzerlik Eşleşmesi (Fuzzy Match)
        role_names = [r.name for r in guild.roles if not r.is_default()]
        matches = difflib.get_close_matches(query, role_names, n=1, cutoff=0.6)
        if matches:
            return discord.utils.get(guild.roles, name=matches[0])

        return None

    # Ortak Güvenlik ve Rol Verme Mantığı
    async def process_role_give(self, author: discord.Member, target: discord.Member, role: discord.Role, guild: discord.Guild):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role and staff_role not in author.roles and not author.guild_permissions.administrator:
                return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        if role.permissions.administrator:
            return False, "❌ **Güvenlik Uyarısı:** Yönetici (Administrator) yetkisine sahip roller bu komutla verilemez!"

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

        # Rapor Gönderme
        await self.send_report(guild, target, role, author, action_type="Verildi")
        return True, f"{target.mention} kullanıcısına {role.mention} rolü başarıyla verildi."

    # Ortak Güvenlik ve Rol Alma Mantığı
    async def process_role_remove(self, author: discord.Member, target: discord.Member, role: discord.Role, guild: discord.Guild):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role and staff_role not in author.roles and not author.guild_permissions.administrator:
                return False, "❌ Bu komutu kullanmak için yetkiniz yok!"

        if role.permissions.administrator:
            return False, "❌ **Güvenlik Uyarısı:** Yönetici (Administrator) yetkisine sahip roller bu komutla alınamaz!"

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

        # Rapor Gönderme
        await self.send_report(guild, target, role, author, action_type="Alındı")
        return True, f"{target.mention} kullanıcısından {role.mention} rolü başarıyla alındı."

    # Rapor Gönderme Yardımcısı
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

    # Otomatik Tamamlama
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

    # ================== ROL VER KOMUTLARI ==================
    @app_commands.command(name="rolver", description="Kullanıcıya güvenli bir şekilde tek bir rol verir.")
    @app_commands.describe(kullanıcı="Rol verilecek kullanıcı", rol="Verilecek rolü seçin veya ismini yazın")
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolver_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, rol: str):
        target_role = self.find_role(interaction.guild, rol)
        if not target_role:
            await interaction.response.send_message(f"❌ Sunucuda `{rol}` adında veya benzer bir rol bulunamadı!", ephemeral=True)
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

    @commands.command(name="rolver", aliases=["Rolver", "ROLVER", "rol", "Rol", "ROL"])
    async def rolver_prefix(self, ctx: commands.Context, kullanıcı: discord.Member = None, *, rol_metni: str = None):
        if kullanıcı is None or rol_metni is None:
            await ctx.reply(
                "❌ **Hatalı Kullanım!**\nDoğru format: `d!rol @kullanıcı <Rol İsmi veya @Rol>`\nÖrnek: `d!rol @üye Cumhurbaşkanı Yardımcısı`",
                mention_author=False
            )
            return

        target_role = self.find_role(ctx.guild, rol_metni)
        if not target_role:
            await ctx.reply(f"❌ Sunucuda `{rol_metni}` adında veya benzer bir rol bulunamadı!", mention_author=False)
            return

        success, msg = await self.process_role_give(ctx.author, kullanıcı, target_role, ctx.guild)
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

    # ================== ROL AL KOMUTLARI ==================
    @app_commands.command(name="rolal", description="Kullanıcıdan güvenli bir şekilde tek bir rolü alır.")
    @app_commands.describe(kullanıcı="Rolü alınacak kullanıcı", rol="Alınacak rolü seçin veya ismini yazın")
    @app_commands.autocomplete(rol=role_autocomplete)
    async def rolal_slash(self, interaction: discord.Interaction, kullanıcı: discord.Member, rol: str):
        target_role = self.find_role(interaction.guild, rol)
        if not target_role:
            await interaction.response.send_message(f"❌ Sunucuda `{rol}` adında veya benzer bir rol bulunamadı!", ephemeral=True)
            return

        await interaction.response.defer()
        success, msg = await self.process_role_remove(interaction.user, kullanıcı, target_role, interaction.guild)
        if not success:
            await interaction.followup.send(msg, ephemeral=True)
            return

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
            await ctx.reply(
                "❌ **Hatalı Kullanım!**\nDoğru format: `d!rolal @kullanıcı <Rol İsmi veya @Rol>`\nÖrnek: `d!rolal @üye Cumhurbaşkanı Yardımcısı`",
                mention_author=False
            )
            return

        target_role = self.find_role(ctx.guild, rol_metni)
        if not target_role:
            await ctx.reply(f"❌ Sunucuda `{rol_metni}` adında veya benzer bir rol bulunamadı!", mention_author=False)
            return

        success, msg = await self.process_role_remove(ctx.author, kullanıcı, target_role, ctx.guild)
        if not success:
            await ctx.reply(msg, mention_author=False)
            return

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
