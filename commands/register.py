import discord
from discord import app_commands
from discord.ext import commands
import config
import database
import datetime

class RegisterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    PARTI_CHOICES = [
        app_commands.Choice(name="Genel Başkan (GB)", value="GB"),
        app_commands.Choice(name="Genel Başkanvekili (GBV)", value="GBV"),
        app_commands.Choice(name="Parti Genel Sekreteri (PGS)", value="PGS"),
        app_commands.Choice(name="Merkez Yürütme Kurulu Başkanı (MYKB)", value="MYKB"),
        app_commands.Choice(name="Onursal Başkan (OB)", value="OB"),
        app_commands.Choice(name="Genel Başkan Yardımcısı (GBY)", value="GBY"),
        app_commands.Choice(name="İl Başkanı (İB)", value="İB"),
        app_commands.Choice(name="Sözcü (SZC)", value="SZC"),
        app_commands.Choice(name="Gençlik Kolları Başkanı (GKB)", value="GKB"),
        app_commands.Choice(name="Merkez Yürütme Kurulu Üyesi (MYKÜ)", value="MYKÜ"),
        app_commands.Choice(name="Üye (Düz Üye)", value="Üye")
    ]

    RP_CHOICES = [
        app_commands.Choice(name="Yok", value="Yok"),
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

    @app_commands.command(name="kayıt", description="Yeni kullanıcı kaydı oluşturur.")
    @app_commands.describe(
        kullanici="Kayıt edilecek Discord kullanıcısı",
        isim="Kullanıcının takma adı (Örn: Ahmet)",
        partimakam="Parti makamı seçiniz",
        rpmakam="RP makamı seçiniz (Yoksa 'Yok' seçin)"
    )
    @app_commands.choices(partimakam=PARTI_CHOICES, rpmakam=RP_CHOICES)
    async def kayit(
        self, 
        interaction: discord.Interaction, 
        kullanici: discord.Member, 
        isim: str, 
        partimakam: app_commands.Choice[str], 
        rpmakam: app_commands.Choice[str]
    ):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        roles_to_add = []
        added_role_names = []

        # 1. ZORUNLU DSP ÜYESİ ROLÜ (1537153933305315328 ID'li rol her kayıt olana her zaman verilir)
        dsp_uye_role = interaction.guild.get_role(1537153933305315328)
        if dsp_uye_role:
            roles_to_add.append(dsp_uye_role)
            added_role_names.append(dsp_uye_role.name)

        # 2. Seçilen Parti Rolleri Eşleştirme
        parti_role_ids = config.PARTI_ROLES.get(partimakam.value, [])
        for r_id in parti_role_ids:
            role = interaction.guild.get_role(r_id)
            if role and role not in roles_to_add:
                roles_to_add.append(role)
                added_role_names.append(role.name)

        # 3. Seçilen RP Rolleri Eşleştirme
        if rpmakam.value != "Yok":
            rp_role_ids = config.RP_ROLES.get(rpmakam.value, [])
            for r_id in rp_role_ids:
                role = interaction.guild.get_role(r_id)
                if role and role not in roles_to_add:
                    roles_to_add.append(role)
                    added_role_names.append(role.name)

        # 4. ZORUNLU KAYITSIZ ROLÜNÜ KALDIRMA (1537154022497329233 ID'li rol her zaman alınır)
        unreg_role = interaction.guild.get_role(config.UNREGISTERED_ROLE_ID)
        if unreg_role in kullanici.roles:
            try:
                await kullanici.remove_roles(unreg_role)
            except Exception:
                pass

        # 5. Yeni Rolleri Ekleme
        if roles_to_add:
            try:
                await kullanici.add_roles(*roles_to_add)
            except Exception:
                pass

        # Takma Ad Oluşturma Kuralları
        if rpmakam.value == "Yok":
            new_nick = f"{isim} / {partimakam.value}"
        else:
            new_nick = f"{isim} / {partimakam.value} / {rpmakam.value}"

        try:
            await kullanici.edit(nick=new_nick)
        except Exception:
            pass

        # Veritabanına Kayıt
        database.add_register(
            kullanici.id, kullanici.name, new_nick,
            partimakam.name, partimakam.value,
            rpmakam.name, rpmakam.value,
            ", ".join(added_role_names), interaction.user.id
        )

        # Kayıt Başarı Mesajı
        embed = discord.Embed(
            title="<:dspkus:1537179044049588284> Kayıt Yapıldı!",
            color=config.COLOR_HEX
        )
        embed.description = (
            f"**• Kayıt Edilen Kullanıcı:** {kullanici.mention}\n"
            f"**• Kayıt Eden Kullanıcı:** {interaction.user.mention}\n"
            f"**• Yeni İsim:** {new_nick}\n"
            f"**• Verilen Roller:** {', '.join(added_role_names)}"
        )
        await interaction.response.send_message(embed=embed)

        # Kayıt Log Kanalına Bildirim
        log_channel = interaction.guild.get_channel(config.REGISTER_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📋 Yeni Kayıt Logu",
                color=config.COLOR_HEX,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            log_embed.add_field(name="Kayıt Edilen Kullanıcı", value=f"{kullanici.mention} (`{kullanici.id}`)", inline=False)
            log_embed.add_field(name="Kayıt Eden Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            log_embed.add_field(name="Parti Makamı", value=f"{partimakam.name} ({partimakam.value})", inline=True)
            log_embed.add_field(name="RP Makamı", value=f"{rpmakam.name} ({rpmakam.value})", inline=True)
            log_embed.add_field(name="Verilen Roller", value=", ".join(added_role_names), inline=False)
            log_embed.add_field(name="Yeni Discord Takma Adı", value=new_nick, inline=False)
            await log_channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(RegisterCommands(bot))
