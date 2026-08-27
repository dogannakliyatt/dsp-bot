import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random
import config

active_giveaways = {}

# --- MODAL PENCERELERİ (GİRDİ ALMA MENÜLERİ) ---

class EditPrizeModal(discord.ui.Modal, title="🎁 Ödülü Düzenle"):
    new_prize = discord.ui.TextInput(
        label="Yeni Ödül",
        placeholder="Örn: 1 Aylık Nitro / Bakanlık Makamı",
        min_length=1,
        max_length=100
    )

    def __init__(self, giveaway_data):
        super().__init__()
        self.data = giveaway_data
        self.new_prize.default = self.data["prize"]

    async def on_submit(self, interaction: discord.Interaction):
        self.data["prize"] = self.new_prize.value
        await self.data["update_embed"]()
        await interaction.response.send_message(f"✅ Çekiliş ödülü **{self.new_prize.value}** olarak güncellendi.", ephemeral=True)


class EditWinnersModal(discord.ui.Modal, title="🏆 Kazanan Sayısını Düzenle"):
    new_winners = discord.ui.TextInput(
        label="Yeni Kazanan Sayısı",
        placeholder="Örn: 1, 2, 5",
        min_length=1,
        max_length=3
    )

    def __init__(self, giveaway_data):
        super().__init__()
        self.data = giveaway_data
        self.new_winners.default = str(self.data["winners_count"])

    async def on_submit(self, interaction: discord.Interaction):
        val = self.new_winners.value.strip()
        if not val.isdigit() or int(val) < 1:
            return await interaction.response.send_message("❌ Lütfen 1 veya daha büyük geçerli bir sayı giriniz.", ephemeral=True)

        self.data["winners_count"] = int(val)
        await self.data["update_embed"]()
        await interaction.response.send_message(f"✅ Kazanan sayısı **{val}** olarak güncellendi.", ephemeral=True)


class EditRequirementsModal(discord.ui.Modal, title="📋 Şartları Düzenle"):
    new_reqs = discord.ui.TextInput(
        label="Katılım Şartları",
        style=discord.TextStyle.paragraph,
        placeholder="Örn: Sunucuda en az 3 gün bulunmak...",
        min_length=1,
        max_length=300
    )

    def __init__(self, giveaway_data):
        super().__init__()
        self.data = giveaway_data
        self.new_reqs.default = self.data["requirements"]

    async def on_submit(self, interaction: discord.Interaction):
        self.data["requirements"] = self.new_reqs.value
        await self.data["update_embed"]()
        await interaction.response.send_message("✅ Katılım şartları başarıyla güncellendi.", ephemeral=True)


class EditTimeModal(discord.ui.Modal, title="⏳ Süre Ekle veya Azalt"):
    minute_diff = discord.ui.TextInput(
        label="Eklenecek / Çıkarılacak Dakika",
        placeholder="Örn: +10 (ekle) veya -5 (azalt)",
        min_length=1,
        max_length=6
    )

    def __init__(self, giveaway_data):
        super().__init__()
        self.data = giveaway_data

    async def on_submit(self, interaction: discord.Interaction):
        val = self.minute_diff.value.strip().replace("+", "")
        try:
            minutes = int(val)
        except ValueError:
            return await interaction.response.send_message("❌ Geçerli bir sayı giriniz (Örn: 10 veya -5).", ephemeral=True)

        new_end = self.data["end_time"] + datetime.timedelta(minutes=minutes)
        now = datetime.datetime.now(datetime.timezone.utc)

        if new_end <= now:
            return await interaction.response.send_message("❌ Çekiliş bitiş zamanı şu andan daha geriye alınamaz!", ephemeral=True)

        self.data["end_time"] = new_end
        await self.data["update_embed"]()
        await interaction.response.send_message(f"✅ Çekiliş süresi güncellendi. Yeni Bitiş: <t:{int(new_end.timestamp())}:R>", ephemeral=True)


# --- ÇEKİLİŞ YÖNETİM PANELİ VIEW ---

class GiveawayManageView(discord.ui.View):
    def __init__(self, giveaway_data):
        super().__init__(timeout=120)
        self.data = giveaway_data

    @discord.ui.button(label="Ödülü Düzenle", style=discord.ButtonStyle.primary, emoji="🎁")
    async def edit_prize(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditPrizeModal(self.data))

    @discord.ui.button(label="Kazanan Sayısı", style=discord.ButtonStyle.primary, emoji="🏆")
    async def edit_winners(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditWinnersModal(self.data))

    @discord.ui.button(label="Süreyi Düzenle", style=discord.ButtonStyle.primary, emoji="⏳")
    async def edit_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTimeModal(self.data))

    @discord.ui.button(label="Şartları Düzenle", style=discord.ButtonStyle.primary, emoji="📋")
    async def edit_reqs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditRequirementsModal(self.data))


# --- TEKRAR ÇEK BUTONU VIEW ---

class RerollView(discord.ui.View):
    def __init__(self, prize: str, host: discord.Member, participants: set, won_users: set):
        super().__init__(timeout=None)
        self.prize = prize
        self.host = host
        self.participants = participants
        self.won_users = won_users

    def is_authorized(self, member: discord.Member, guild: discord.Guild) -> bool:
        if member.guild_permissions.administrator or member.id == guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in member.roles)

    @discord.ui.button(label="Tekrar Çek", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="btn_reroll_giveaway")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu butonu sadece yetkililer kullanabilir.", ephemeral=True)

        # Henüz kazanmamış adayları filtrele
        available_pool = [uid for uid in self.participants if uid not in self.won_users]

        if not available_pool:
            return await interaction.response.send_message("❌ Çekilişe katılan ve henüz kazanmamış başka kimse bulunmuyor!", ephemeral=True)

        new_winner_id = random.choice(available_pool)
        self.won_users.add(new_winner_id)
        winner_mention = f"<@{new_winner_id}>"

        reroll_embed = discord.Embed(
            title="🎉 ÇEKİLİŞ YENİDEN ÇEKİLDİ!",
            description=(
                f"🎁 **Ödül:** `{self.prize}`\n\n"
                f"🏆 **Tebrikler:** {winner_mention}\n\n"
                f"📌 *Ödülünüzü teslim almak için lütfen {self.host.mention} ile iletişime geçin.*"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        reroll_embed.set_footer(text="Demokratik Sol Parti Çekiliş Sistemi")

        # Yeni kazanan mesajını altına tekrar butonunu ekleyerek gönder
        await interaction.channel.send(
            content=f"🎉 {winner_mention}",
            embed=reroll_embed,
            view=RerollView(self.prize, self.host, self.participants, self.won_users)
        )
        await interaction.response.send_message(f"✅ Yeni kazanan belirlendi: {winner_mention}", ephemeral=True)


# --- ANA ÇEKİLİŞ KATILIM VIEW ---

class GiveawayView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Çekilişe Katıl (0)", style=discord.ButtonStyle.success, emoji="🎉", custom_id="btn_live_giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = active_giveaways.get(self.guild_id)
        if not data or data.get("cancelled", False):
            return await interaction.response.send_message("❌ Bu çekiliş artık aktif değil.", ephemeral=True)

        user_id = interaction.user.id
        participants = data["participants"]

        if user_id in participants:
            participants.remove(user_id)
            await interaction.response.send_message("❌ Çekilişten ayrıldınız.", ephemeral=True)
        else:
            participants.add(user_id)
            await interaction.response.send_message("✅ Çekilişe başarıyla katıldınız! Şansınız bol olsun.", ephemeral=True)

        button.label = f"Çekilişe Katıl ({len(participants)})"
        try:
            embed = data["create_embed"]()
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            pass


# --- COG SINIFI ---

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in interaction.user.roles)

    async def run_giveaway_loop(self, guild_id: int):
        while guild_id in active_giveaways:
            data = active_giveaways[guild_id]
            if data.get("cancelled", False):
                active_giveaways.pop(guild_id, None)
                return

            now = datetime.datetime.now(datetime.timezone.utc)
            if now >= data["end_time"]:
                break
            await asyncio.sleep(2)

        data = active_giveaways.pop(guild_id, None)
        if not data or data.get("cancelled", False):
            return

        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        try:
            message = await channel.fetch_message(data["message_id"])
        except Exception:
            return

        view = data["view"]
        for item in view.children:
            item.disabled = True
            if isinstance(item, discord.ui.Button):
                item.label = f"Çekiliş Sona Erdi ({len(data['participants'])})"
                item.style = discord.ButtonStyle.secondary

        participants = list(data["participants"])
        if not participants:
            winners_text = "❌ Yetersiz katılım sebebiyle kazanan belirlenemedi."
            end_embed = data["create_embed"](is_ended=True, winners_str=winners_text)
            await message.edit(embed=end_embed, view=view)
            return await channel.send(f"⚠️ **{data['prize']}** çekilişine kimse katılmadığı için kazanan seçilemedi.")

        winners_count = min(len(participants), data["winners_count"])
        selected_ids = random.sample(participants, winners_count)
        won_users = set(selected_ids)
        winners_mentions = ", ".join([f"<@{uid}>" for uid in selected_ids])

        end_embed = data["create_embed"](is_ended=True, winners_str=winners_mentions)
        await message.edit(embed=end_embed, view=view)

        celebrate_embed = discord.Embed(
            title="🎊 ÇEKİLİŞ KAZANANLARI BELİRLENDİ!",
            description=(
                f"🎁 **Ödül:** `{data['prize']}`\n\n"
                f"🏆 **Tebrikler:** {winners_mentions}\n\n"
                f"📌 *Ödülünüzü teslim almak için lütfen {data['host'].mention} ile iletişime geçin.*"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        celebrate_embed.set_footer(text="Demokratik Sol Parti Çekiliş Sistemi")
        
        # Kutunun altına Tekrar Çek butonunu ekle
        reroll_view = RerollView(
            prize=data["prize"], 
            host=data["host"], 
            participants=data["participants"], 
            won_users=won_users
        )
        await channel.send(content=f"🎉 {winners_mentions}", embed=celebrate_embed, view=reroll_view)

    # ------------------ /çekiliş KOMUTU ------------------
    @app_commands.command(name="çekiliş", description="Modern butonlu yeni bir çekiliş başlatır.")
    @app_commands.describe(
        ödül="Çekilişte verilecek hediye / ödül / makam",
        kazanan_sayısı="Kazanacak kişi sayısı",
        süre_dakika="Çekiliş süresi (dakika)",
        şartlar="İsteğe bağlı katılım şartları (Boş bırakılırsa 'Şart Yok' yazar)"
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        ödül: str,
        kazanan_sayısı: int,
        süre_dakika: int,
        şartlar: str = None
    ):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        guild_id = interaction.guild.id
        if guild_id in active_giveaways:
            return await interaction.response.send_message("❌ **Zaten aktif bir çekiliş bulunmakta!** Sunucuda aynı anda yalnızca 1 adet çekiliş yürütülebilir.", ephemeral=True)

        if kazanan_sayısı < 1 or süre_dakika < 1:
            return await interaction.response.send_message("❌ Kazanan sayısı ve süre en az 1 olmalıdır.", ephemeral=True)

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=süre_dakika)
        view = GiveawayView(guild_id=guild_id)

        giveaway_data = {
            "prize": ödül,
            "winners_count": kazanan_sayısı,
            "end_time": end_time,
            "host": interaction.user,
            "requirements": şartlar if şartlar else "Şart Yok (Herkese Açık)",
            "participants": set(),
            "channel_id": interaction.channel_id,
            "message_id": None,
            "view": view,
            "cancelled": False
        }

        def create_embed(is_ended: bool = False, winners_str: str = None, is_cancelled: bool = False, cancel_reason: str = None) -> discord.Embed:
            end_ts = int(giveaway_data["end_time"].timestamp())
            if is_cancelled:
                embed = discord.Embed(
                    title="🚫 ÇEKİLİŞ İPTAL EDİLDİ",
                    description=f"🎁 **Ödül:** `{giveaway_data['prize']}`\n\n**İptal Sebebi:** {cancel_reason}",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_footer(text=f"İptal Eden: {interaction.user.display_name}")
                return embed

            if not is_ended:
                embed = discord.Embed(
                    title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
                    description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
                    color=config.COLOR_HEX,
                    timestamp=giveaway_data["end_time"]
                )
                embed.add_field(name="🎉 Ödül", value=f"```fix\n{giveaway_data['prize']}\n```", inline=False)
                embed.add_field(name="📋 Katılım Şartları", value=f"> {giveaway_data['requirements']}", inline=False)
                embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{giveaway_data['winners_count']} Kişi`", inline=True)
                embed.add_field(name="👥 Katılımcılar", value=f"`{len(giveaway_data['participants'])} Kişi`", inline=True)
                embed.add_field(name="⏳ Bitiş", value=f"<t:{end_ts}:R>", inline=True)
                embed.set_footer(text=f"Düzenleyen: {giveaway_data['host'].display_name} • Bitiş Zamanı", icon_url=giveaway_data['host'].display_avatar.url)
            else:
                embed = discord.Embed(
                    title="🔒 ÇEKİLİŞ SONUÇLANDI",
                    description=f"🎁 **Ödül:** `{giveaway_data['prize']}`\n",
                    color=discord.Color.green() if winners_str and "Yetersiz" not in winners_str else discord.Color.red(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.add_field(name="🏆 Kazanan(lar)", value=winners_str, inline=False)
                embed.add_field(name="👥 Toplam Katılımcı", value=f"`{len(giveaway_data['participants'])} Kişi`", inline=True)
                embed.add_field(name="📋 Aranan Şartlar", value=f"> {giveaway_data['requirements']}", inline=True)
                embed.set_footer(text=f"Düzenleyen: {giveaway_data['host'].display_name} • Sona Erdi", icon_url=giveaway_data['host'].display_avatar.url)
            return embed

        giveaway_data["create_embed"] = create_embed

        async def update_embed():
            ch = self.bot.get_channel(giveaway_data["channel_id"])
            if ch and giveaway_data["message_id"]:
                try:
                    msg = await ch.fetch_message(giveaway_data["message_id"])
                    await msg.edit(embed=giveaway_data["create_embed"](), view=giveaway_data["view"])
                except Exception:
                    pass

        giveaway_data["update_embed"] = update_embed

        embed = create_embed()
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        giveaway_data["message_id"] = message.id

        active_giveaways[guild_id] = giveaway_data
        asyncio.create_task(self.run_giveaway_loop(guild_id))

    # ------------------ /çekilişiptal KOMUTU ------------------
    @app_commands.command(name="çekilişiptal", description="Aktif olan çekilişi bir sebep belirterek iptal eder.")
    @app_commands.describe(sebep="Çekilişin iptal edilme sebebi")
    async def cancel_giveaway(self, interaction: discord.Interaction, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        guild_id = interaction.guild.id
        data = active_giveaways.get(guild_id)

        if not data:
            return await interaction.response.send_message("❌ Şu anda sunucuda devam eden aktif bir çekiliş bulunmuyor.", ephemeral=True)

        data["cancelled"] = True
        active_giveaways.pop(guild_id, None)

        channel = self.bot.get_channel(data["channel_id"])
        if channel and data["message_id"]:
            try:
                msg = await channel.fetch_message(data["message_id"])
                view = data["view"]
                for item in view.children:
                    item.disabled = True
                    if isinstance(item, discord.ui.Button):
                        item.label = "Çekiliş İptal Edildi"
                        item.style = discord.ButtonStyle.danger
                
                cancelled_embed = data["create_embed"](is_cancelled=True, cancel_reason=sebep)
                await msg.edit(embed=cancelled_embed, view=view)
            except Exception:
                pass

        await interaction.response.send_message(f"✅ Çekiliş başarıyla iptal edildi.\n**Sebep:** {sebep}", ephemeral=True)

    # ------------------ /çekilişyönet KOMUTU ------------------
    @app_commands.command(name="çekilişyönet", description="Aktif çekilişin süresini, ödülünü, şartlarını ve kazanan sayısını düzenler.")
    async def manage_giveaway(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        guild_id = interaction.guild.id
        data = active_giveaways.get(guild_id)

        if not data:
            return await interaction.response.send_message("❌ Yönetilebilecek aktif bir çekiliş bulunamadı.", ephemeral=True)

        end_ts = int(data["end_time"].timestamp())
        embed = discord.Embed(
            title="⚙️ Çekiliş Yönetim Paneli",
            description=(
                f"Aşağıdaki butonlara tıklayarak aktif çekilişin bilgilerini anlık olarak değiştirebilirsiniz.\n\n"
                f"🎁 **Mevcut Ödül:** `{data['prize']}`\n"
                f"🏆 **Kazanan Sayısı:** `{data['winners_count']} Kişi`\n"
                f"⏳ **Bitiş:** <t:{end_ts}:R>\n"
                f"📋 **Şartlar:** {data['requirements']}\n"
                f"👥 **Katılımcı Sayısı:** `{len(data['participants'])} Kişi`"
            ),
            color=config.COLOR_HEX
        )
        embed.set_footer(text="Düzenlemeler canlı olarak çekiliş mesajına aktarılır.")

        view = GiveawayManageView(giveaway_data=data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
