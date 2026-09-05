import discord
from discord import app_commands
from discord.ext import commands
import io
import csv
import datetime
import asyncio
import config
import database

PARTY_CHOICES = {
    "Üye": "Üye (Düz Üye)",
    "GB": "Genel Başkan (GB)",
    "GBV": "Genel Başkanvekili (GBV)",
    "PGS": "Parti Genel Sekreteri (PGS)",
    "MYKB": "Merkez Yürütme Kurulu Başkanı (MYKB)",
    "OB": "Onursal Başkan (OB)",
    "GBY": "Genel Başkan Yardımcısı (GBY)",
    "İB": "İl Başkanı (İB)",
    "SZC": "Sözcü (SZC)",
    "GKB": "Gençlik Kolları Başkanı (GKB)",
    "MYKÜ": "Merkez Yürütme Kurulu Üyesi (MYKÜ)"
}

RP_CHOICES = {
    "Yok": "Yok / Sivil",
    "CB": "Cumhurbaşkanı (CB)",
    "CBY": "Cumhurbaşkanı Yardımcısı (CBY)",
    "BB": "Başbakan (BB)",
    "TBMMB": "TBMM Başkanı (TBMMB)",
    "TBMMBV": "TBMM Başkanvekili (TBMMBV)",
    "TBMMK": "TBMM Kâtibi (TBMMK)",
    "TCK": "T.C. Kabinesi (TCK)",
    "İBB": "İBB Başkanı (İBB)",
    "ABB": "ABB Başkanı (ABB)",
    "İZBB": "İZBB Başkanı (İZBB)",
    "BBB": "BBB Başkanı (BBB)",
    "MGB": "Meclis Grup Başkanı (MGB)",
    "MGBV": "Meclis Grup Başkanvekili (MGBV)",
    "MV": "Milletvekili (MV)"
}

PARTY_TITLE_PRIORITY = [
    ("GB", 1537148955840741376),
    ("GBV", 1537149075194118248),
    ("PGS", 1537149226990182450),
    ("MYKB", 1537149324473929778),
    ("OB", 1537149401649381417),
    ("GBY", 1537149477796970686),
    ("İB", 1537149544289275987),
    ("SZC", 1537149604343316572),
    ("GKB", 1537149684345475123),
    ("MYKÜ", 1537149762913046568)
]

RP_TITLE_PRIORITY = [
    ("CBY", 1537595817429569706),
    ("CB", 1537149921541492836),
    ("BB", 1537149991146229810),
    ("TBMMBV", 1537150202857787402),
    ("TBMMB", 1537150038512242740),
    ("TBMMK", 1537154296737701960),
    ("TCK", 1537150254833467502),
    ("İBB", 1537151635170525334),
    ("ABB", 1537151839881924691),
    ("İZBB", 1537151887231426620),
    ("BBB", 1537151950884175872),
    ("MGBV", 1537150854786719875),
    ("MGB", 1537150788533485578),
    ("MV", 1537150966535553035)
]

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

    async def makam_autocomplete(self, interaction: discord.Interaction, current: str):
        secilen_tur = interaction.namespace.tür

        if not secilen_tur:
            return [app_commands.Choice(name="⚠️ Lütfen önce Tür seçiniz!", value="none")]

        choices = []
        if secilen_tur == "parti":
            for code, name in PARTY_CHOICES.items():
                if current.lower() in name.lower() or current.lower() in code.lower():
                    choices.append(app_commands.Choice(name=name[:100], value=code))
        elif secilen_tur == "rp":
            for code, name in RP_CHOICES.items():
                if current.lower() in name.lower() or current.lower() in code.lower():
                    choices.append(app_commands.Choice(name=name[:100], value=code))

        return choices[:25]

    @app_commands.command(name="adaylar", description="Sunucudaki tüm Aday ve Adayı rollerini ve sahiplerini listeler.")
    async def adaylar(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if not guild.chunked:
            await guild.chunk()

        candidate_roles = [
            r for r in guild.roles 
            if not r.is_default() and (r.name.strip().endswith("Aday") or r.name.strip().endswith("Adayı") or r.name.strip().endswith("Adayi"))
        ]

        if not candidate_roles:
            return await interaction.followup.send("ℹ️ Sunucuda sonu **Aday** veya **Adayı** ile biten herhangi bir rol bulunamadı.", ephemeral=True)

        candidate_roles.sort(key=lambda r: r.position, reverse=True)

        embed = discord.Embed(
            title="🗳️ AKTİF SEÇİM & ADAY LİSTESİ",
            description="Sunucuda tanımlı olan tüm adaylık rolleri ve adaylar aşağıda belirtilmiştir.\n",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        for role in candidate_roles:
            members = [m for m in role.members if not m.bot]
            if members:
                members_str = "\n".join([f"• {m.mention} (`{m.display_name}`)" for m in members])
            else:
                members_str = "*Aday bulunmuyor (Boş)*"
            
            embed.add_field(
                name=f"📌 {role.name} ({len(members)} Kişi)", 
                value=f"{members_str}\n\u200b", 
                inline=False
            )

        embed.set_footer(text=f"Sorgulayan: {interaction.user.display_name} • Demokratik Sol Parti", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="teskilat", description="Parti ve Meclis/Kabine teşkilatlanma durumunu genel rapor halinde listeler.")
    async def teskilat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if not guild.chunked:
            await guild.chunk()

        embed = discord.Embed(
            title="🇹🇷 DEMOKRATİK SOL PARTİ & DEVLET TEŞKİLATI RAPORU",
            description="Sunucudaki güncel parti yönetimi, hükümet ve meclis görev dağılımı aşağıda listelenmiştir.\n",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        party_roles_map = getattr(config, "PARTY_STRUCTURE_ROLES", {})
        party_text = ""
        for title, r_id in party_roles_map.items():
            role = guild.get_role(r_id)
            if role and role.members:
                members_str = ", ".join([m.mention for m in role.members])
            else:
                members_str = "*Boşta / Atanmadı*"
            party_text += f"• **{title}:** {members_str}\n"

        embed.add_field(name="🕊️ Parti Merkez Yönetimi", value=party_text if party_text else "*Rol tanımlanmadı*", inline=False)

        cabinet_map = getattr(config, "CABINET_ROLES", {})
        cabinet_text = ""
        for title, r_id in cabinet_map.items():
            role = guild.get_role(r_id)
            if role and role.members:
                members_str = ", ".join([m.mention for m in role.members])
            else:
                members_str = "*Boşta*"
            cabinet_text += f"• **{title}:** {members_str}\n"

        embed.add_field(name="🏛️ Kabine & Yerel Yönetimler", value=cabinet_text if cabinet_text else "*Rol tanımlanmadı*", inline=False)

        parliament_map = getattr(config, "PARLIAMENT_ROLES", {})
        parliament_text = ""
        for title, r_id in parliament_map.items():
            role = guild.get_role(r_id)
            if role and role.members:
                if len(role.members) > 8:
                    members_str = ", ".join([m.mention for m in role.members[:8]]) + f" *(+{len(role.members)-8} vekil)*"
                else:
                    members_str = ", ".join([m.mention for m in role.members])
            else:
                members_str = "*Boşta*"
            parliament_text += f"• **{title}:** {members_str}\n"

        embed.add_field(name="⚖️ TBMM Protokolü", value=parliament_text if parliament_text else "*Rol tanımlanmadı*", inline=False)
        embed.set_footer(text="Demokratik Sol Parti Teşkilat İnceleme")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="makamdegis", description="Bir üyenin Parti veya RP makamını değiştirir ve rollerini günceller.")
    @app_commands.describe(
        kullanıcı="Makamı değiştirilecek üye",
        tür="Değiştirilecek makam kategorisi",
        makam="Atanacak yeni makam"
    )
    @app_commands.choices(tür=[
        app_commands.Choice(name="Parti Makamı", value="parti"),
        app_commands.Choice(name="RP Makamı", value="rp")
    ])
    @app_commands.autocomplete(makam=makam_autocomplete)
    async def makamdegis(
        self,
        interaction: discord.Interaction,
        kullanıcı: discord.Member,
        tür: app_commands.Choice[str],
        makam: str
    ):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        if makam == "none" or (tür.value == "parti" and makam not in PARTY_CHOICES) or (tür.value == "rp" and makam not in RP_CHOICES):
            return await interaction.response.send_message("❌ Lütfen geçerli bir makam seçiniz!", ephemeral=True)

        if kullanıcı.top_role >= interaction.guild.me.top_role and kullanıcı.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Botun yetkisi bu kullanıcıyı düzenlemeye yetmiyor!", ephemeral=True)

        await interaction.response.defer()

        # 1. Eski Makam Rollerini Temizle
        roles_to_remove = set()
        if tür.value == "parti":
            for p_code, r_ids in config.PARTY_ROLES.items():
                if p_code == "Üye":
                    continue
                for rid in r_ids:
                    r_obj = interaction.guild.get_role(rid)
                    if r_obj and r_obj in kullanıcı.roles and r_obj < interaction.guild.me.top_role:
                        roles_to_remove.add(r_obj)
        else:
            for r_code, r_ids in config.RP_ROLES.items():
                if r_code == "Yok":
                    continue
                for rid in r_ids:
                    r_obj = interaction.guild.get_role(rid)
                    if r_obj and r_obj in kullanıcı.roles and r_obj < interaction.guild.me.top_role:
                        roles_to_remove.add(r_obj)

        if roles_to_remove:
            try:
                await kullanıcı.remove_roles(*list(roles_to_remove), reason=f"Makam Değişimi: {interaction.user}")
            except Exception:
                pass

        # 2. Yeni Makam Rollerini Tanımla
        roles_to_add = set()
        base_member_role = interaction.guild.get_role(config.BASE_MEMBER_ROLE_ID)
        if base_member_role and base_member_role not in kullanıcı.roles:
            roles_to_add.add(base_member_role)

        target_role_ids = config.PARTY_ROLES.get(makam, []) if tür.value == "parti" else config.RP_ROLES.get(makam, [])
        for rid in target_role_ids:
            r_obj = interaction.guild.get_role(rid)
            if r_obj and r_obj < interaction.guild.me.top_role:
                roles_to_add.add(r_obj)

        if roles_to_add:
            try:
                await kullanıcı.add_roles(*list(roles_to_add), reason=f"Yeni Makam Ataması: {interaction.user}")
            except Exception:
                pass

        # 3. Takma Ad Kurallarını Uygula
        base_name = kullanıcı.display_name.split("/")[0].strip()
        if not base_name:
            base_name = kullanıcı.name

        current_role_ids = {r.id for r in kullanıcı.roles if r not in roles_to_remove}
        current_role_ids.update(r.id for r in roles_to_add)

        if tür.value == "parti":
            parti_tag = makam if makam != "Üye" else None
        else:
            parti_tag = None
            for p_tag, p_rid in PARTY_TITLE_PRIORITY:
                if p_rid in current_role_ids:
                    parti_tag = p_tag
                    break

        if tür.value == "rp":
            rp_tag = makam if makam != "Yok" else None
        else:
            rp_tag = None
            for r_tag, r_rid in RP_TITLE_PRIORITY:
                if r_rid in current_role_ids:
                    rp_tag = r_tag
                    break

        titles = []
        if parti_tag:
            titles.append(parti_tag)
        if rp_tag:
            titles.append(rp_tag)

        new_nick = f"{base_name} / {' / '.join(titles)}" if titles else base_name
        new_nick = new_nick[:32]

        if kullanıcı.id != interaction.guild.owner_id and kullanıcı.top_role < interaction.guild.me.top_role:
            try:
                await kullanıcı.edit(nick=new_nick, reason=f"Makam Değişimi Takma Ad Güncellemesi: {interaction.user}")
            except Exception:
                pass

        assigned_name = PARTY_CHOICES.get(makam) if tür.value == "parti" else RP_CHOICES.get(makam)
        try:
            await asyncio.to_thread(
                database.add_register,
                user_id=kullanıcı.id,
                username=str(kullanıcı),
                new_nick=new_nick,
                parti_name=f"[Makam Değişimi] {assigned_name}" if tür.value == "parti" else "Mevcut",
                parti_code=makam if tür.value == "parti" else "Üye",
                rp_name=f"[Makam Değişimi] {assigned_name}" if tür.value == "rp" else "Mevcut",
                rp_code=makam if tür.value == "rp" else "Yok",
                roles_given=assigned_name,
                staff_id=interaction.user.id
            )
        except Exception:
            pass

        embed = discord.Embed(
            title="🎖️ Makam Değişikliği Tamamlandı",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="👤 Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=False)
        embed.add_field(name="📂 Kategori", value=tür.name, inline=True)
        embed.add_field(name="📌 Yeni Makam", value=f"**{assigned_name}**", inline=True)
        embed.add_field(name="🏷️ Güncel Takma Ad", value=f"`{new_nick}`", inline=False)
        embed.set_footer(text=f"İşlemi Yapan: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

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

        rp_roles_map = getattr(config, "CABINET_ROLES", {})
        for title, role_id in rp_roles_map.items():
            role = interaction.guild.get_role(role_id)
            if role and role.members:
                members_str = "\n".join([f"• {m.mention} (`{m.display_name}`)" for m in role.members])
            else:
                members_str = "*Makam Boşta*"
            embed.add_field(name=title, value=members_str, inline=False)

        embed.set_footer(text="Demokratik Sol Parti Hükümet Protokolü")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="partidüzeni", description="Demokratik Sol Parti Teşkilat Şemasını listeler.")
    async def partiliste(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🕊️ DEMOKRATİK SOL PARTİ TEŞKİLAT ŞEMASI",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        party_roles_map = getattr(config, "PARTY_STRUCTURE_ROLES", {})
        for title, role_id in party_roles_map.items():
            role = interaction.guild.get_role(role_id)
            if role and role.members:
                members_str = "\n".join([f"• {m.mention} (`{m.display_name}`)" for m in role.members])
            else:
                members_str = "*Atama Yapılmadı*"
            
            embed.add_field(name=f"📌 {title}", value=f"{members_str}\n\u200b", inline=False)

        embed.set_footer(text="Demokratik Sol Parti Resmi Yönetim Şeması")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meclis", description="TBMM Başkanlık Divanı ve Meclis Grubunu listeler.")
    async def meclis(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏛️ TÜRKİYE BÜYÜK MİLLET MECLİSİ PROTOKOLÜ",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        tbmm_map = getattr(config, "PARLIAMENT_ROLES", {})
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
        records = await asyncio.to_thread(database.get_user_history, kullanıcı.id)

        created_ts = int(kullanıcı.created_at.timestamp())
        joined_ts = int(kullanıcı.joined_at.timestamp()) if kullanıcı.joined_at else None

        embed = discord.Embed(
            title=f"📋 Kullanıcı Sicil ve Kayıt Kartı: {kullanıcı.display_name}",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=kullanıcı.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=f"{kullanıcı.mention} (`{kullanıcı.id}`)", inline=False)
        embed.add_field(name="Hesap Oluşturulma", value=f"<t:{created_ts}:F>\n(<t:{created_ts}:R>)", inline=True)
        embed.add_field(name="Sunucuya Katılım", value=f"<t:{joined_ts}:F>\n(<t:{joined_ts}:R>)" if joined_ts else "Bilinmiyor", inline=True)

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
        records = await asyncio.to_thread(database.export_all_registers)

        if not records:
            return await interaction.followup.send("❌ Veritabanında kayıt bulunamadı.", ephemeral=True)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User ID", "Kullanici Adi", "Takma Ad", "Parti Makami", "RP Makami", "Verilen Roller", "Yetkili ID", "Tarih"])

        for r in records:
            writer.writerow([r["id"], r["user_id"], r["username"], r["new_nick"], r["parti_name"], r["rp_name"], r["roles_given"], r["staff_id"], r["timestamp"]])

        output.seek(0)
        bytes_data = io.BytesIO(output.getvalue().encode('utf-8-sig'))
        bytes_data.seek(0)
        
        file = discord.File(fp=bytes_data, filename=f"kayit_verileri_{datetime.date.today()}.csv")
        await interaction.followup.send("✅ Tüm kayıt verileri CSV dosyası olarak hazırlandı:", file=file, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RPTools(bot))
