import discord
from discord.ext import commands
from discord import app_commands
import config

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kayıt", description="Kullanıcıyı sunucuya ve partiye kaydeder.")
    @app_commands.describe(
        kullanıcı="Kayıt edilecek üye",
        isim="Kullanıcının adı soyadı",
        rpmakamı="Kullanıcının parti/RP içindeki makamı"
    )
    @app_commands.choices(rpmakamı=[
        app_commands.Choice(name="Üye (Düz Üyelik)", value="Üye"),
        app_commands.Choice(name="Genel Başkan (GB)", value="GB"),
        app_commands.Choice(name="Genel Başkan Yardımcısı (GBY)", value="GBY"),
        app_commands.Choice(name="Genel Sekreter (GS)", value="GS"),
        app_commands.Choice(name="Parti Meclisi Üyesi (PM)", value="PM"),
        app_commands.Choice(name="Merkez Disiplin Kurulu (MDK)", value="MDK"),
        app_commands.Choice(name="İl Başkanı", value="İl Bşk."),
        app_commands.Choice(name="İlçe Başkanı", value="İlçe Bşk."),
        app_commands.Choice(name="Basın Sözcüsü", value="Sözcü"),
        app_commands.Choice(name="Danışman", value="Danışman")
    ])
    async def kayit(
        self, 
        interaction: discord.Interaction, 
        kullanıcı: discord.Member, 
        isim: str, 
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

        # İsim Mantığı: Düz üye seçildiyse unvan ekleme, makam varsa İsim / Makam
        secilen_makam = rpmakamı.value
        if secilen_makam.lower() in ["üye", "uye", "düz üye", "duz uye"]:
            new_nickname = isim
        else:
            new_nickname = f"{isim} / {secilen_makam}"

        try:
            await kullanıcı.edit(nick=new_nickname)
        except Exception:
            pass

        # Kayıtsız Rolünü Al
        unreg_role_id = getattr(config, "UNREGISTERED_ROLE_ID", None)
        if unreg_role_id:
            unreg_role = interaction.guild.get_role(unreg_role_id)
            if unreg_role and unreg_role in kullanıcı.roles:
                try:
                    await kullanıcı.remove_roles(unreg_role, reason="Kayıt tamamlandı.")
                except Exception:
                    pass

        # Üye / Parti Rolünü Ver
        member_role_id = getattr(config, "MEMBER_ROLE_ID", None)
        if member_role_id:
            member_role = interaction.guild.get_role(member_role_id)
            if member_role:
                try:
                    await kullanıcı.add_roles(member_role, reason="Kayıt tamamlandı.")
                except Exception:
                    pass

        # Kayıt Bilgi Embed'i
        embed = discord.Embed(
            title="🕊️ Kayıt Yapıldı!",
            color=discord.Color.from_rgb(0, 168, 243)
        )
        embed.add_field(name="• Kayıt Edilen Kullanıcı", value=kullanıcı.mention, inline=False)
        embed.add_field(name="• Kayıt Eden Kullanıcı", value=interaction.user.mention, inline=False)
        embed.add_field(name="• Yeni İsim", value=new_nickname, inline=False)
        embed.add_field(name="• Verilen Roller", value="DSP Üyesi", inline=False)
        embed.set_thumbnail(url=kullanıcı.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Register(bot))
