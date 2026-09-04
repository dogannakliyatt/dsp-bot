import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import re
import config
import database

def clean_text(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("İ", "i")
        .replace("I", "ı")
        .replace("Ş", "ş")
        .replace("Ğ", "ğ")
        .replace("Ü", "ü")
        .replace("Ö", "ö")
        .replace("Ç", "ç")
        .lower()
        .strip()
    )

def match_party_role(text: str):
    c = clean_text(text)
    if not c or c in ["yok", "uye", "sivil", "-", "düz üye", "duz uye"]:
        return "Üye", "Üye"
    for code in config.PARTY_ROLES.keys():
        if code == "Üye":
            continue
        if clean_text(code) in c or c in clean_text(code):
            return code, code
    for full_name, role_id in config.PARTY_STRUCTURE_ROLES.items():
        if clean_text(full_name) in c:
            for code, ids in config.PARTY_ROLES.items():
                if role_id in ids:
                    return code, full_name
    return "Üye", text.strip()

def match_rp_role(text: str):
    c = clean_text(text)
    if not c or c in ["yok", "sivil", "-", "yok / sivil"]:
        return "Yok", "Yok"
    for code in config.RP_ROLES.keys():
        if code == "Yok":
            continue
        if clean_text(code) in c or c in clean_text(code):
            return code, code
    for full_name, role_id in {**config.CABINET_ROLES, **config.PARLIAMENT_ROLES}.items():
        if clean_text(full_name) in c:
            for code, ids in config.RP_ROLES.items():
                if role_id in ids:
                    return code, full_name
    return "Yok", text.strip()

class RetModal(discord.ui.Modal, title="Kayıt Başvurusunu Reddet"):
    sebep = discord.ui.TextInput(
        label="Reddedilme Sebebi",
        placeholder="Örn: Geçersiz isim veya makam beyanı...",
        style=discord.TextStyle.paragraph,
        min_length=3,
        max_length=300
    )

    def __init__(self, target_user: discord.Member, original_message: discord.Message):
        super().__init__()
        self.target_user = target_user
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.original_message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Kayıt Başvurusu Reddedildi"
        embed.add_field(name="🛡️ Reddeden Yetkili", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 Ret Sebebi", value=self.sebep.value, inline=False)
        
        await self.original_message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ Başvuru reddedildi ve kullanıcı bilgilendirildi.", ephemeral=True)

        try:
            dm_embed = discord.Embed(
                title="Kayıt Başvurunuz Reddedildi",
                description=f"Demokratik Sol Parti sunucusundaki kayıt başvurunuz reddedilmiştir.\n\n**Sebep:** {self.sebep.value}",
                color=discord.Color.red()
            )
            await self.target_user.send(embed=dm_embed)
        except Exception:
            pass

class BasvuruOnayView(discord.ui.View):
    def __init__(self, target_user_id: int, isim: str, parti_input: str, rp_input: str):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.isim = isim
        self.parti_input = parti_input
        self.rp_input = rp_input

    def is_staff(self, member: discord.Member, guild: discord.Guild) -> bool:
        if member.guild_permissions.administrator or member.id == guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", 1537129117152055426)
        return any(r.id == staff_id for r in member.roles)

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_kayit_onayla")
    async def onayla_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_staff(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu işlemi sadece kayıt yetkilileri yapabilir!", ephemeral=True)

        await interaction.response.defer()
        target = interaction.guild.get_member(self.target_user_id)
        if not target:
            return await interaction.followup.send("❌ Kullanıcı artık sunucuda bulunmuyor!", ephemeral=True)

        p_code, p_name = match_party_role(self.parti_input)
        r_code, r_name = match_rp_role(self.rp_input)

        titles = []
        if p_code != "Üye":
            titles.append(p_code)
        if r_code != "Yok":
            titles.append(r_code)

        new_nick = f"{self.isim} / {' / '.join(titles)}" if titles else self.isim
        new_nick = new_nick[:32]

        if target.id != interaction.guild.owner_id and target.top_role < interaction.guild.me.top_role:
            try:
                await target.edit(nick=new_nick)
            except Exception:
                pass

        unreg_role = interaction.guild.get_role(config.UNREGISTERED_ROLE_ID)
        if unreg_role and unreg_role in target.roles:
            try:
                await target.remove_roles(unreg_role)
            except Exception:
                pass

        roles_to_add = set()
        base_role = interaction.guild.get_role(config.BASE_MEMBER_ROLE_ID)
        if base_role:
            roles_to_add.add(base_role)

        for r_id in config.PARTY_ROLES.get(p_code, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj and role_obj < interaction.guild.me.top_role:
                roles_to_add.add(role_obj)

        for r_id in config.RP_ROLES.get(r_code, []):
            role_obj = interaction.guild.get_role(r_id)
            if role_obj and role_obj < interaction.guild.me.top_role:
                roles_to_add.add(role_obj)

        if roles_to_add:
            try:
                await target.add_roles(*list(roles_to_add), reason=f"Kayıt Formu Onaylandı: {interaction.user}")
            except Exception:
                pass

        role_names = [r.name for r in roles_to_add if r.id != config.BASE_MEMBER_ROLE_ID]
        roles_text = ", ".join(dict.fromkeys(["DSP Üyesi"] + role_names))

        try:
            await asyncio.to_thread(
                database.add_register,
                user_id=target.id,
                username=str(target),
                new_nick=new_nick,
                parti_name=p_name,
                parti_code=p_code,
                rp_name=r_name,
                rp_code=r_code,
                roles_given=roles_text,
                staff_id=interaction.user.id
            )
        except Exception as e:
            print(f"[HATA] Başvuru kaydı eklenemedi: {e}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Kayıt Başvurusu Onaylandı"
        embed.add_field(name="🛡️ Onaylayan Yetkili", value=interaction.user.mention, inline=True)
        embed.add_field(name="🏷️ Verilen Takma Ad", value=f"`{new_nick}`", inline=True)
        embed.add_field(name="🎖️ Tanımlanan Roller", value=roles_text, inline=False)

        await interaction.message.edit(embed=embed, view=None)

        log_ch = interaction.guild.get_channel(config.REGISTER_LOG_CHANNEL_ID)
        if log_ch:
            try:
                log_embed = discord.Embed(
                    title="📋 Kayıt Formu Onay Logu",
                    description=(
                        f"**Kayıt Olan:** {target.mention} (`{target.id}`)\n"
                        f"**Yetkili:** {interaction.user.mention}\n"
                        f"**İsim / Unvan:** `{new_nick}`\n"
                        f"**Parti Makamı:** `{p_name}`\n"
                        f"**RP Makamı:** `{r_name}`\n"
                        f"**Roller:** {roles_text}"
                    ),
                    color=config.COLOR_HEX,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                await log_ch.send(embed=log_embed)
            except Exception:
                pass

        try:
            await target.send(f"🎉 Tebrikler! **Demokratik Sol Parti** sunucusundaki kaydınız **{interaction.user.display_name}** tarafından onaylandı. Aramıza hoş geldiniz!")
        except Exception:
            pass

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="btn_kayit_reddet")
    async def reddet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_staff(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu işlemi sadece kayıt yetkilileri yapabilir!", ephemeral=True)

        target = interaction.guild.get_member(self.target_user_id)
        if not target:
            return await interaction.response.send_message("❌ Kullanıcı artık sunucuda bulunmuyor!", ephemeral=True)

        await interaction.response.send_modal(RetModal(target, interaction.message))

class KayitModal(discord.ui.Modal, title="Kayıt Formu"):
    isim = discord.ui.TextInput(
        label="İsim:",
        placeholder="Sunucumuzda kullandığınız ismi yazınız.",
        min_length=2,
        max_length=32
    )
    parti_makami = discord.ui.TextInput(
        label="Parti İçi Makam:",
        placeholder="Üye, GBV, GBY, MYK Üyesi...",
        min_length=2,
        max_length=50,
        default="Üye"
    )
    rp_makami = discord.ui.TextInput(
        label="RP İçi Makam:",
        placeholder="TBMM Başkanı, Adalet Bakanı, Milletvekili, MGB...",
        min_length=2,
        max_length=50,
        default="Yok"
    )

    async def on_submit(self, interaction: discord.Interaction):
        staff_ch_id = getattr(config, "REGISTER_STAFF_CHANNEL_ID", 1545435073208385607)
        staff_role_id = getattr(config, "STAFF_ROLE_ID", 1537129117152055426)
        staff_channel = interaction.guild.get_channel(staff_ch_id)

        if not staff_channel:
            return await interaction.response.send_message("❌ Yetkili onay kanalı bulunamadı! Lütfen yöneticiye bildirin.", ephemeral=True)

        embed = discord.Embed(
            title="📥 Yeni Kayıt Başvurusu Geldi!",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Kullanıcı", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="📛 Belirtilen İsim", value=f"`{self.isim.value}`", inline=False)
        embed.add_field(name="📌 Parti İçi Makam", value=f"`{self.parti_makami.value}`", inline=True)
        embed.add_field(name="🏛️ RP İçi Makam", value=f"`{self.rp_makami.value}`", inline=True)
        embed.set_footer(text="Aşağıdaki butonları kullanarak başvuruyu değerlendirebilirsiniz.")

        view = BasvuruOnayView(
            target_user_id=interaction.user.id,
            isim=self.isim.value,
            parti_input=self.parti_makami.value,
            rp_input=self.rp_makami.value
        )

        await staff_channel.send(content=f"<@&{staff_role_id}> Yeni bir kayıt formu iletildi!", embed=embed, view=view)
        await interaction.response.send_message("✅ Başvurunuz başarıyla yetkililere iletildi. İncelendikten sonra kaydınız tamamlanacaktır.", ephemeral=True)

class KayitPaneliView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, emoji="📝", custom_id="btn_kayit_formu_ac")
    async def kayit_ol_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        base_role_id = getattr(config, "BASE_MEMBER_ROLE_ID", 1537153933305315328)
        if any(r.id == base_role_id for r in interaction.user.roles):
            return await interaction.response.send_message("ℹ️ Zaten sunucuya kayıtlısınız! Bilgi değişikliği için yetkililere danışın.", ephemeral=True)

        await interaction.response.send_modal(KayitModal())

class RegisterPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kayitpaneli-kur", description="Belirlenen kanala butonlu kayıt panelini kurar.")
    async def kur_panel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ Bu komutu yalnızca sunucu yöneticileri kullanabilir.", ephemeral=True)

        target_ch_id = getattr(config, "REGISTER_FORM_CHANNEL_ID", 1537157370264944690)
        channel = interaction.guild.get_channel(target_ch_id)
        if not channel:
            return await interaction.response.send_message(f"❌ Hedef kanal (`{target_ch_id}`) bulunamadı!", ephemeral=True)

        embed = discord.Embed(
            title="🕊️ DEMOKRATİK SOL PARTİ KAYIT ALANI",
            description=(
                "Sunucumuza ve partimize hoş geldiniz!\n\n"
                "Sunucumuzdaki kanallara erişebilmek, siyasi ve meclis çalışmalarına katılabilmek için lütfen aşağıdaki **Kayıt Ol** butonuna tıklayarak formu eksiksiz doldurunuz.\n\n"
                "📝 **Form Kuralları:**\n"
                "• İsminizi gerçekçi veya RP'de kullandığınız şekilde giriniz.\n"
                "• Bulunduğunuz Parti ve RP makamlarını doğru belirtiniz.\n"
                "• Başvurunuz yetkililerimizce onaylandığında rolleriniz ve takma adınız otomatik tanımlanacaktır."
            ),
            color=config.COLOR_HEX
        )
        embed.set_footer(text="Demokratik Sol Parti Kayıt ve Kabul Sistemi")
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        await channel.send(embed=embed, view=KayitPaneliView())
        await interaction.response.send_message(f"✅ Kayıt paneli başarıyla {channel.mention} kanalına kuruldu!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RegisterPanelCog(bot))
