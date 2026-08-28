import discord
from discord import app_commands
from discord.ext import commands
import io
import csv
import datetime
import config
import database

class ResmiGazeteModal(discord.ui.Modal, title="📜 Resmî Gazete / Bildiri Yayınla"):
    sayi_no = discord.ui.TextInput(
        label="Karar / Sayı No",
        placeholder="Örn: 2026/04",
        min_length=1,
        max_length=20
    )
    bildiri_baslik = discord.ui.TextInput(
        label="Bildiri Başlığı",
        placeholder="Örn: Kabine Revizyonu ve Atama Kararı",
        min_length=3,
        max_length=100
    )
    bildiri_icerik = discord.ui.TextInput(
        label="Bildiri Metni",
        style=discord.TextStyle.paragraph,
        placeholder="Yayınlanacak resmi karar ve açıklamaları buraya yazınız...",
        min_length=10,
        max_length=3500
    )

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📜 RESMÎ BİLDİRİ — Sayı: {self.sayi_no.value}",
            description=f"### {self.bildiri_baslik.value}\n\n{self.bildiri_icerik.value}",
            color=discord.Color.dark_teal(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text=f"Yayınlayan Makam: {interaction.user.display_name} • Demokratik Sol Parti", icon_url=interaction.user.display_avatar.url)
        
        try:
            await self.target_channel.send(content="@everyone" if interaction.guild else None, embed=embed)
            await interaction.response.send_message(f"✅ Bildiri başarıyla {self.target_channel.mention} kanalında yayınlandı.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Bildiri gönderilirken bir hata oluştu: {str(e)}", ephemeral=True)

class RPTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in interaction.user.roles)

    @app_commands.command(name="resmigazete", description="Resmî gazete veya parti bildirisi yayınlar.")
    @app_commands.describe(kanal="Bildirinin gönderileceği kanal (Belirtilmezse bu kanala atar)")
    async def resmigazete(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        target_channel = kanal if kanal else interaction.channel
        await interaction.response.send_modal(ResmiGazeteModal(target_channel=target_channel))

    @app_commands.command(name="kabine", description="Mevcut T.C. Kabinesini ve makam sahiplerini listeler.")
    async def kabine(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🇹🇷 TÜRKİYE CUMHURİYETİ HÜKÜMETİ & KABİNE",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        rp_roles_map = {
            "Cumhurbaşkanı": 1537149921541492836,
            "Cumhurbaşkanı Yardımcısı": 1537595817429569706,
            "Başbakan": 1537149991146229810,
            "Kabine Üyeleri (Bakanlar)": 1537150254833467502,
            "İstanbul Büyükşehir Belediye Başkanı": 1537151635170525334,
            "Ankara Büyükşehir Belediye Başkanı": 1537151839881924691,
            "İzmir Büyükşehir Belediye Başkanı": 1537151887231426620,
            "Bursa Büyükşehir Belediye Başkanı": 1537151950884175872,
        }

        for title, role_id in rp_roles_map.items():
            role = interaction.guild.get_role(role_id)
            if role and role.members:
                members_str = "\n".join([f"• {m.mention} (`{m.display_name}`)" for m in role.members])
            else:
                members_str = "*Makam Boşta*"
            embed.add_field(name=title, value=members_str, inline=False)

        embed.set_footer(text="Demokratik Sol Parti Hükümet Protokolü")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="partidüzeni", description="Demokratik Sol Parti Genel Merkez yönetimini listeler.")
    async def partiliste(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🕊️ DEMOKRATİK SOL PARTİ GENEL MERKEZ DÜZENİ",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        party_roles_map = {
            "Genel Başkan": 1537148955840741376,
            "Genel Başkanvekili": 1537149075194118248,
            "Parti Genel Sekreteri": 1537149226990182450,
            "MYK Başkanı": 1537149324473929778,
            "Genel Başkan Yardımcıları": 1537149477796970686,
            "Parti Sözcüsü": 1537149604343316572,
            "Gençlik Kolları Başkanı": 1537149684345475123,
        }

        for title, role_id in party_roles_map.items():
            role = interaction.guild.get_role(role_id)
            if role and role.members:
                members_str = "\n".join([f"• {m.mention} (`{m.display_name}`)" for m in role.members])
            else:
                members_str = "*Atama Yapılmadı*"
            embed.add_field(name=title, value=members_str, inline=True)

        embed.set_footer(text="Demokratik Sol Parti Resmi Yönetim Şeması")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meclis", description="TBMM Başkanlık Divanı ve Meclis Grubunu listeler.")
    async def meclis(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏛️ TÜRKİYE BÜYÜK MİLLET MECLİSİ PROTOKOLÜ",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        tbmm_map = {
            "TBMM Başkanı": 1537150038512242740,
            "TBMM Başkanvekili": 1537150202857787402,
            "TBMM Kâtibi": 1537154296737701960,
            "Meclis Grup Başkanı": 1537150788533485578,
            "Meclis Grup Başkanvekili": 1537150854786719875,
            "Milletvekilleri": 1537150966535553035
        }

        for title, role_id in tbmm_map.items():
            role = interaction.guild.get_role(role_id)
            if role and role.members:
                members_str = f"**{len(role.members)} Kişi:** " + ", ".join([m.mention for m in role.members[:12]])
                if len(role.members) > 12:
                    members_str += f" *ve {len(role.members) - 12} kişi daha...*"
            else:
                members_str = "*Boşta*"
            embed.add_field(name=title, value=members_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sicil", description="Bir kullanıcının sunucudaki kayıt geçmişini ve sicilini görüntüler.")
    @app_commands.describe(kullanıcı="Sicili sorgulanacak kullanıcı")
    async def sicil(self, interaction: discord.Interaction, kullanıcı: discord.Member):
        records = database.get_user_history(kullanıcı.id)

        embed = discord.Embed(
            title=f"📋 Kullanıcı Sicil ve Kayıt Kartı: {kullanıcı.display_name}",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=kullanıcı.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=True)
        embed.add_field(name="Sunucuya Katılım", value=f"<t:{int(kullanıcı.joined_at.timestamp())}:R>" if kullanıcı.joined_at else "Bilinmiyor", inline=True)

        if not records:
            embed.add_field(name="Kayıt Geçmişi", value="*Veritabanında kayıt işlemi bulunamadı (Eski veya manuel kaydedilmiş).*", inline=False)
        else:
            rec_str = ""
            for idx, r in enumerate(records[:5], start=1):
                staff_user = interaction.guild.get_member(r["staff_id"]) if r.get("staff_id") else None
                staff_text = staff_user.mention if staff_user else f"`ID: {r.get('staff_id')}`"
                date_str = r["timestamp"].strftime("%d/%m/%Y %H:%M") if hasattr(r["timestamp"], "strftime") else str(r["timestamp"])
                rec_str += f"**{idx}.** `{r['parti_name']}` & `{r['rp_name']}` — Yetkili: {staff_text} ({date_str})\n"
            embed.add_field(name="Geçmiş Kayıt İşlemleri", value=rec_str, inline=False)

        roles_list = [r.mention for r in kullanıcı.roles if not r.is_default()]
        embed.add_field(name="Mevcut Rolleri", value=", ".join(roles_list) if roles_list else "*Rolü yok*", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kayıtdışaaktar", description="Tüm kayıt geçmişini .csv dosyası olarak aktarır.")
    async def export_registers(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        records = database.export_all_registers()

        if not records:
            return await interaction.followup.send("❌ Veritabanında kayıt bulunamadı.", ephemeral=True)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User ID", "Kullanici Adi", "Takma Ad", "Parti Makami", "RP Makami", "Verilen Roller", "Yetkili ID", "Tarih"])

        for r in records:
            writer.writerow([r["id"], r["user_id"], r["username"], r["new_nick"], r["parti_name"], r["rp_name"], r["roles_given"], r["staff_id"], r["timestamp"]])

        output.seek(0)
        file = discord.File(io.BytesIO(output.getvalue().encode('utf-8-sig')), filename=f"kayit_verileri_{datetime.date.today()}.csv")
        await interaction.followup.send("✅ Tüm kayıt verileri CSV dosyası olarak hazırlandı:", file=file, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RPTools(bot))
