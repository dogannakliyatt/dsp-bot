import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import config
import database

BASE_MEMBER_ROLE_ID = getattr(config, "BASE_MEMBER_ROLE_ID", 1537153933305315328)
UNREGISTERED_ROLE_ID = getattr(config, "UNREGISTERED_ROLE_ID", 1537154022497329233)
REGISTRATION_LOG_CHANNEL_ID = getattr(config, "REGISTER_LOG_CHANNEL_ID", 1537159620374564875)
REPORT_LOG_CHANNEL_ID = getattr(config, "REPORT_LOG_CHANNEL_ID", 1541807577837342834)
MISAFIR_ROLE_ID = getattr(config, "MISAFIR_ROLE_ID", 1543955147120709694)

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kayıt", description="Kullanıcıyı partiye ve makamlarına kaydeder.")
    @app_commands.describe(
        kullanıcı="Kayıt edilecek üye",
        isim="Kullanıcının adı soyadı",
        partimakamı="Kullanıcının parti içi görevi",
        rpmakamı="Kullanıcının RP / Devlet makamı"
    )
    @app_commands.choices(
        partimakamı=[
            app_commands.Choice(name="Üye (Düz Üye)", value="Üye"),
            app_commands.Choice(name="Genel Başkan (GB)", value="GB"),
            app_commands.Choice(name="Genel Başkanvekili (GBV)", value="GBV"),
            app_commands.Choice(name="Parti Genel Sekreteri (PGS)", value="PGS"),
            app_commands.Choice(name="Merkez Yürütme Kurulu Başkanı (MYKB)", value="MYKB"),
            app_commands.Choice(name="Onursal Başkan (OB)", value="OB"),
            app_commands.Choice(name="Genel Başkan Yardımcısı (GBY)", value="GBY"),
            app_commands.Choice(name="İl Başkanı (İB)", value="İB"),
            app_commands.Choice(name="Sözcü (SZC)", value="SZC"),
            app_commands.Choice(name="Gençlik Kolları Başkanı (GKB)", value="GKB"),
            app_commands.Choice(name="Merkez Yürütme Kurulu Üyesi (MYKÜ)", value="MYKÜ")
        ],
        rpmakamı=[
            app_commands.Choice(name="Yok / Sivil", value="Yok"),
            app_commands.Choice(name="Cumhurbaşkanı (CB)", value="CB"),
            app_commands.Choice(name="Cumhurbaşkanı Yardımcısı (CBY)", value="CBY"),
            app_commands.Choice(name="Başbakan (BB)", value="BB"),
            app_commands.Choice(name="TBMM Başkanı (TBMMB)", value="TBMMB"),
            app_commands.Choice(name="TBMM Başkanvekili (TBMMBV)", value="TBMMBV"),
            app_commands.Choice(name="TBMM Kâtibi (TBMMK)", value="TBMMK"),
            app_commands.Choice(name="T.C. Kabinesi (TCK)", value="TCK"),
            app_commands.Choice(name="İBB Başkanı (İBB)", value="İBB"),
            app_commands.Choice(name="ABB Başkanı (ABB)", value="ABB"),
            app_commands.Choice(name="İZBB Başkanı (İZBB)", value="İZBB"),
            app_commands.Choice(name="BBB Başkanı (BBB)", value="BBB"),
            app_commands.Choice(name="Meclis Grup Başkanı (MGB)", value="MGB"),
            app_commands.Choice(name="Meclis Grup Başkanvekili (MGBV)", value="MGBV"),
            app_commands.Choice(name="Milletvekili (MV)", value="MV")
        ]
    )
    async def kayit(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member,
        isim: str,
        partimakamı: app_commands.Choice[str],
        rpmakamı: app_commands.Choice[str]
    ):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)

        if kullanıcı.top_role >= interaction.guild.me.top_role and kullanıcı.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Botun yetkisi bu kullanıcıyı düzenlemeye yetmiyor!", ephemeral=True)

        await interaction.response.defer()

        p_val = partimakamı.value
        r_val = rpmakamı.value

        titles = []
        if p_val != "Üye":
            titles.append(p_val)
        if r_val != "Yok":
            titles.append(r_val)

        new_nickname = f"{isim} / {' / '.join(titles)}" if titles else isim
        if len(new_nickname) > 32:
            new_nickname = new_nickname[:32]

        if kullanıcı.id != interaction.guild.owner_id:
            try:
                await kullanıcı.edit(nick=new_nickname)
            except Exception:
                pass

        unreg_role = interaction.guild.get_role(UNREGISTERED_ROLE_ID)
        if unreg_role and unreg_role in kullanıcı.roles:
            try:
                await kullanıcı.remove_roles(unreg_role, reason="Kayıt tamamlandı.")
            except Exception:
                pass

        roles_to_add = set()
        base_role = interaction.guild.get_role(BASE_MEMBER_ROLE_ID)
        if base_role:
            roles_to_add.add(base_role)

        for r_id in config.PARTY_ROLES.get(p_val, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj and role_obj < interaction.guild.me.top_role:
                roles_to_add.add(role_obj)

        for r_id in config.RP_ROLES.get(r_val, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj and role_obj < interaction.guild.me.top_role:
                roles_to_add.add(role_obj)

        if roles_to_add:
            try:
                await kullanıcı.add_roles(*list(roles_to_add), reason=f"Kayıt: {partimakamı.name} | {rpmakamı.name}")
            except Exception:
                pass

        role_names = [r.name for r in roles_to_add if r.id != BASE_MEMBER_ROLE_ID]
        roles_text_list = ["DSP Üyesi"] + role_names
        roles_text = ", ".join(dict.fromkeys(roles_text_list))

        try:
            await asyncio.to_thread(
                database.add_register,
                user_id=kullanıcı.id,
                username=str(kullanıcı),
                new_nick=new_nickname,
                parti_name=partimakamı.name,
                parti_code=p_val,
                rp_name=rpmakamı.name,
                rp_code=r_val,
                roles_given=roles_text,
                staff_id=interaction.user.id
            )
        except Exception as e:
            print(f"[HATA] Kayıt veritabanına eklenemedi: {e}")

        embed_desc = (
            f"**Kayıt Edilen Kullanıcı**\n"
            f"{kullanıcı.mention} ( `{kullanıcı.id}` )\n\n"
            f"**Kayıt Eden Yetkili**\n"
            f"{interaction.user.mention}\n"
            f"( `{interaction.user.id}` )\n\n"
            f"**Parti Makamı**\n"
            f"{partimakamı.name} ({partimakamı.value})\n\n"
            f"**RP Makamı**\n"
            f"{rpmakamı.name} ({rpmakamı.value})\n\n"
            f"**Verilen Roller**\n"
            f"{roles_text}\n\n"
            f"**Yeni Discord Takma Adı**\n"
            f"{new_nickname}"
        )

        embed = discord.Embed(
            title="📋 Yeni Kayıt Logu",
            description=embed_desc,
            color=discord.Color.from_rgb(0, 168, 243),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await interaction.followup.send(embed=embed)

        log_channel = interaction.guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
        if log_channel is None:
            try:
                log_channel = await interaction.guild.fetch_channel(REGISTRATION_LOG_CHANNEL_ID)
            except Exception:
                pass

        if log_channel and log_channel.id != interaction.channel_id:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"[HATA] Kayıt log gönderilemedi: {e}")

    @app_commands.command(name="misafirkaydet", description="Kullanıcının tüm rollerini alır ve misafir rolü verir.")
    @app_commands.describe(kullanıcı="İşlem yapılacak kullanıcı")
    async def misafirkaydet(self, interaction: discord.Interaction, kullanıcı: discord.Member):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)

        if interaction.user.id != interaction.guild.owner_id and kullanıcı.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ Sizden eşit veya daha üst roldeki birine bu işlemi yapamazsınız!", ephemeral=True)

        if kullanıcı.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Bu kullanıcının rolü botun rolünden yüksek veya eşit olduğu için işlem yapılamaz!", ephemeral=True)

        misafir_rolü = interaction.guild.get_role(MISAFIR_ROLE_ID)
        if not misafir_rolü:
            return await interaction.response.send_message("❌ Sistemde 1543955147120709694 ID'li misafir rolü bulunamadı!", ephemeral=True)

        await interaction.response.defer()

        roles_to_remove = [r for r in kullanıcı.roles if r != interaction.guild.default_role and not r.is_integration() and not r.is_bot_managed() and r < interaction.guild.me.top_role]

        if roles_to_remove:
            try:
                await kullanıcı.remove_roles(*roles_to_remove, reason=f"Misafir kaydedildi - Yetkili: {interaction.user}")
            except Exception as e:
                print(f"Misafir kaydedilirken roller alınırken hata: {e}")

        try:
            await kullanıcı.add_roles(misafir_rolü, reason=f"Misafir kaydedildi - Yetkili: {interaction.user}")
        except Exception as e:
            print(f"Misafir rolü verilirken hata: {e}")

        clean_nick = kullanıcı.nick if kullanıcı.nick else kullanıcı.name
        try:
            await asyncio.to_thread(
                database.add_register,
                user_id=kullanıcı.id,
                username=str(kullanıcı),
                new_nick=clean_nick,
                parti_name="Misafir",
                parti_code="Misafir",
                rp_name="Misafir",
                rp_code="Misafir",
                roles_given=misafir_rolü.name,
                staff_id=interaction.user.id
            )
        except Exception as e:
            print(f"[HATA] Misafir kaydı veritabanına eklenemedi: {e}")

        log_embed = discord.Embed(
            title="👤 Misafir Kaydı Gerçekleştirildi",
            color=discord.Color.teal(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.set_thumbnail(url=kullanıcı.display_avatar.url)
        log_embed.add_field(name="Kayıt Edilen Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=False)
        log_embed.add_field(name="İşlemi Yapan Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        log_embed.add_field(name="Tanımlanan Rol", value=misafir_rolü.mention, inline=True)
        log_embed.add_field(name="Alınan Rol Sayısı", value=f"`{len(roles_to_remove)} adet`", inline=True)
        log_embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=log_embed)

        log_channel = interaction.guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
        if log_channel is None:
            try:
                log_channel = await interaction.guild.fetch_channel(REGISTRATION_LOG_CHANNEL_ID)
            except Exception:
                pass

        if log_channel and log_channel.id != interaction.channel_id:
            try:
                await log_channel.send(embed=log_embed)
            except Exception as e:
                print(f"[HATA] Misafir kayıt logu gönderilemedi: {e}")

    @app_commands.command(name="kayıtsızver", description="Kullanıcının tüm rollerini ve takma adını sıfırlayıp kayıtsıza atar.")
    @app_commands.describe(
        kullanıcı="Kayıtsıza atılacak kullanıcı",
        sebep="Kayıtsıza atılma sebebi"
    )
    async def kayitsizver(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member,
        sebep: str
    ):
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)

        if interaction.user.id != interaction.guild.owner_id and kullanıcı.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ Sizden eşit veya daha üst roldeki birine bu işlemi yapamazsınız!", ephemeral=True)

        if kullanıcı.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ Bu kullanıcının rolü botun rolünden yüksek veya eşit olduğu için işlem yapılamaz!", ephemeral=True)

        unreg_role = interaction.guild.get_role(UNREGISTERED_ROLE_ID)
        if not unreg_role:
            return await interaction.response.send_message("❌ Kayıtsız rolü sunucuda bulunamadı!", ephemeral=True)

        await interaction.response.defer()

        if kullanıcı.nick and kullanıcı.id != interaction.guild.owner_id:
            try:
                await kullanıcı.edit(nick=None, reason=f"Kayıtsıza atıldı: {sebep}")
            except Exception as e:
                print(f"Takma ad sıfırlanırken hata: {e}")

        roles_to_remove = [r for r in kullanıcı.roles if r != interaction.guild.default_role and not r.is_integration() and not r.is_bot_managed() and r < interaction.guild.me.top_role]

        if roles_to_remove:
            try:
                await kullanıcı.remove_roles(*roles_to_remove, reason=f"Kayıtsıza atıldı: {sebep}")
            except Exception as e:
                print(f"Roller alınırken hata: {e}")

        try:
            await kullanıcı.add_roles(unreg_role, reason=f"Kayıtsıza atıldı: {sebep}")
        except Exception as e:
            print(f"Kayıtsız rolü verilirken hata: {e}")

        reply_embed = discord.Embed(
            title="⚠️ Kullanıcı Kayıtsıza Atıldı",
            description=(
                f"{kullanıcı.mention} kullanıcısının rolleri temizlendi, takma adı sıfırlandı ve {unreg_role.mention} rolü verildi.\n\n"
                f"**Sebep:** {sebep}"
            ),
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        reply_embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")
        await interaction.followup.send(embed=reply_embed)

        report_channel = interaction.guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if report_channel is None:
            try:
                report_channel = await interaction.guild.fetch_channel(REPORT_LOG_CHANNEL_ID)
            except Exception:
                pass

        if report_channel:
            report_embed = discord.Embed(
                title="📑 Kayıtsıza Atma Raporu",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            report_embed.add_field(name="👤 Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=False)
            report_embed.add_field(name="🛡️ Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            report_embed.add_field(name="📝 Sebep", value=sebep, inline=False)
            report_embed.set_thumbnail(url=kullanıcı.display_avatar.url)
            report_embed.set_footer(text=f"Kullanıcı ID: {kullanıcı.id}")

            try:
                await report_channel.send(embed=report_embed)
            except Exception as e:
                print(f"[HATA] Rapor log gönderilemedi: {e}")

async def setup(bot):
    await bot.add_cog(Register(bot))
