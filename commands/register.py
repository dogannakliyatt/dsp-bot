import discord
from discord.ext import commands
from discord import app_commands
import config

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
            app_commands.Choice(name="Üye (Düz Üyelik)", value="Üye"),
            app_commands.Choice(name="Genel Başkan (GB)", value="GB"),
            app_commands.Choice(name="Genel Başkan Yardımcısı (GBY)", value="GBY"),
            app_commands.Choice(name="Genel Sekreter (GS)", value="GS"),
            app_commands.Choice(name="Genel Sekreter Yardımcısı (GSY)", value="GSY"),
            app_commands.Choice(name="Parti Meclisi Üyesi (PM)", value="PM"),
            app_commands.Choice(name="Merkez Disiplin Kurulu (MDK)", value="MDK"),
            app_commands.Choice(name="İl Başkanı (İl Bşk.)", value="İl Bşk."),
            app_commands.Choice(name="İlçe Başkanı (İlçe Bşk.)", value="İlçe Bşk."),
            app_commands.Choice(name="Parti Sözcüsü (Sözcü)", value="Sözcü"),
            app_commands.Choice(name="Başdanışman", value="Başdanışman")
        ],
        rpmakamı=[
            app_commands.Choice(name="Yok / Sivil", value="Yok"),
            app_commands.Choice(name="Cumhurbaşkanı (CB)", value="CB"),
            app_commands.Choice(name="Cumhurbaşkanı Yardımcısı (CBY)", value="CBY"),
            app_commands.Choice(name="Milletvekili (MV)", value="MV"),
            app_commands.Choice(name="Bakan", value="Bakan"),
            app_commands.Choice(name="Bakan Yardımcısı", value="Bakan Yrd."),
            app_commands.Choice(name="Büyükşehir Belediye Başkanı (BBB)", value="BBB"),
            app_commands.Choice(name="Belediye Başkanı (BB)", value="BB"),
            app_commands.Choice(name="Vali", value="Vali"),
            app_commands.Choice(name="Kaymakam", value="Kaymakam"),
            app_commands.Choice(name="Bürokrat", value="Bürokrat")
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
        # Yetki Kontrolü
        staff_role_id = getattr(config, "STAFF_ROLE_ID", None)
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
                return

        await interaction.response.defer()

        # İsim / Unvan Formatlama Mantığı
        p_val = partimakamı.value
        r_val = rpmakamı.value
        
        titles = []
        if p_val.lower() not in ["üye", "uye", "düz üye"]:
            titles.append(p_val)
            
        if r_val.lower() not in ["yok", "sivil", "none"]:
            titles.append(r_val)

        if titles:
            new_nickname = f"{isim} / {' / '.join(titles)}"
        else:
            new_nickname = isim

        # Discord 32 Karakter Sınırı Kontrolü
        if len(new_nickname) > 32:
            new_nickname = new_nickname[:32]

        try:
            await kullanıcı.edit(nick=new_nickname)
        except Exception:
            pass

        # Kayıtsız Rolünü Kaldır
        unreg_role_id = getattr(config, "UNREGISTERED_ROLE_ID", None)
        if unreg_role_id:
            unreg_role = interaction.guild.get_role(unreg_role_id)
            if unreg_role and unreg_role in kullanıcı.roles:
                try:
                    await kullanıcı.remove_roles(unreg_role, reason="Kayıt tamamlandı.")
                except Exception:
                    pass

        # Üye Rolünü Ver
        member_role_id = getattr(config, "MEMBER_ROLE_ID", None)
        if member_role_id:
            member_role = interaction.guild.get_role(member_role_id)
            if member_role:
                try:
                    await kullanıcı.add_roles(member_role, reason="Kayıt tamamlandı.")
                except Exception:
                    pass

        # Bilgi Embed'i
        embed = discord.Embed(
            title="🕊️ Kayıt Yapıldı!",
            color=discord.Color.from_rgb(0, 168, 243)
        )
        embed.add_field(name="• Kayıt Edilen Kullanıcı", value=kullanıcı.mention, inline=False)
        embed.add_field(name="• Kayıt Eden Kullanıcı", value=interaction.user.mention, inline=False)
        embed.add_field(name="• Yeni İsim", value=new_nickname, inline=False)
        
        roller_metni = f"DSP Üyesi ({p_val})" if p_val != "Üye" else "DSP Üyesi"
        if r_val != "Yok":
            roller_metni += f", {r_val}"
            
        embed.add_field(name="• Verilen Roller / Makamlar", value=roller_metni, inline=False)
        embed.set_thumbnail(url=kullanıcı.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Register(bot))
