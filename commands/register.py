import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

# Taban Üye Rolü ve Kayıt Log Kanalı ID'si
BASE_MEMBER_ROLE_ID = 1537153933305315328
REGISTRATION_LOG_CHANNEL_ID = 1537159620374564875

# Parti Makam Rol Eşleşmeleri
PARTY_ROLES = {
    "GB": [1537148955840741376, 1537153445067489321],
    "GBV": [1537149075194118248],
    "PGS": [1537149226990182450],
    "MYKB": [1537149324473929778, 1537153235935174757],
    "OB": [1537149401649381417],
    "GBY": [1537149477796970686],
    "İB": [1537149544289275987],
    "SZC": [1537149604343316572],
    "GKB": [1537149684345475123],
    "MYKÜ": [1537149762913046568, 1537153235935174757],
    "Üye": [1537153933305315328]
}

# RP Makam Rol Eşleşmeleri
RP_ROLES = {
    "CB": [1537149921541492836],
    "CBY": [1537595817429569706],
    "BB": [1537149991146229810],
    "TBMMB": [1537150038512242740],
    "TBMMBV": [1537150202857787402],
    "TBMMK": [1537154296737701960],
    "TCK": [1537150254833467502],
    "İBB": [1537150309300838490, 1537151635170525334],
    "ABB": [1537150309300838490, 1537151839881924691],
    "İZBB": [1537150309300838490, 1537151887231426620],
    "BBB": [1537150309300838490, 1537151950884175872],
    "MGB": [1537150966535553035, 1537153295150350466, 1537150788533485578],
    "MGBV": [1537150966535553035, 1537150854786719875, 1537153295150350466],
    "MV": [1537150966535553035, 1537153295150350466],
    "Yok": []
}

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
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
                return

        await interaction.response.defer()

        p_val = partimakamı.value
        r_val = rpmakamı.value

        # İsim / Takma Ad Düzenleme
        titles = []
        if p_val != "Üye":
            titles.append(p_val)
        if r_val != "Yok":
            titles.append(r_val)

        new_nickname = f"{isim} / {' / '.join(titles)}" if titles else isim

        if len(new_nickname) > 32:
            new_nickname = new_nickname[:32]

        try:
            await kullanıcı.edit(nick=new_nickname)
        except Exception as e:
            print(f"Takma ad güncellenemedi: {e}")

        # Kayıtsız Rolünü Kaldırma
        unreg_role_id = getattr(config, "UNREGISTERED_ROLE_ID", None)
        if unreg_role_id:
            unreg_role = interaction.guild.get_role(unreg_role_id)
            if unreg_role and unreg_role in kullanıcı.roles:
                try:
                    await kullanıcı.remove_roles(unreg_role, reason="Kayıt tamamlandı.")
                except Exception as e:
                    print(f"Kayıtsız rolü kaldırılamadı: {e}")

        # Rolleri Belirleme
        roles_to_add = set()
        
        # Taban Rol (DSP Üyesi)
        base_role = interaction.guild.get_role(BASE_MEMBER_ROLE_ID)
        if base_role:
            roles_to_add.add(base_role)

        # Parti Makam Rolleri
        for r_id in PARTY_ROLES.get(p_val, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj:
                roles_to_add.add(role_obj)

        # RP Makam Rolleri
        for r_id in RP_ROLES.get(r_val, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj:
                roles_to_add.add(role_obj)

        # Rolleri Kullanıcıya Ekleme
        if roles_to_add:
            try:
                await kullanıcı.add_roles(*list(roles_to_add), reason=f"Kayıt: {partimakamı.name} | {rpmakamı.name}")
            except Exception as e:
                print(f"Roller verilemedi: {e}")

        # Verilen Roller Metni Hazırlığı
        role_names = [r.name for r in roles_to_add if r.id != BASE_MEMBER_ROLE_ID]
        roles_text_list = ["DSP Üyesi"] + role_names
        roles_text = ", ".join(dict.fromkeys(roles_text_list))

        # İstenen Görsel Formatındaki Embed
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

        # 1. Komutun yazıldığı kanala yanıt ver
        await interaction.followup.send(embed=embed)

        # 2. 1537159620374564875 ID'li Log Kanalına Gönder
        log_channel = interaction.guild.get_channel(REGISTRATION_LOG_CHANNEL_ID)
        if log_channel is None:
            try:
                log_channel = await interaction.guild.fetch_channel(REGISTRATION_LOG_CHANNEL_ID)
            except Exception as e:
                print(f"[HATA] Kayıt log kanalı bulunamadı/fetch edilemedi (ID: {REGISTRATION_LOG_CHANNEL_ID}): {e}")

        if log_channel and log_channel.id != interaction.channel_id:
            try:
                await log_channel.send(embed=embed)
                print(f"[BAŞARILI] Kayıt logu #{log_channel.name} kanalına atıldı.")
            except discord.Forbidden:
                print(f"[HATA] Botun #{log_channel.name} kanalına mesaj gönderme veya Embed bağlantısı izni yok!")
            except Exception as e:
                print(f"[HATA] Log gönderilirken hata oluştu: {e}")

async def setup(bot):
    await bot.add_cog(Register(bot))
