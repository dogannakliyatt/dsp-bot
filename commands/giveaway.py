import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random
import config
import database

def ensure_utc(dt):
    if dt is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc)
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    return datetime.datetime.now(datetime.timezone.utc)

class EditPrizeModal(discord.ui.Modal, title="🎁 Ödülü Düzenle"):
    new_prize = discord.ui.TextInput(
        label="Yeni Ödül",
        placeholder="Örn: 1 Aylık Nitro / Bakanlık Makamı",
        min_length=1,
        max_length=100
    )

    def __init__(self, cog, giveaway_data):
        super().__init__()
        self.cog = cog
        self.data = giveaway_data
        self.new_prize.default = self.data["prize"]

    async def on_submit(self, interaction: discord.Interaction):
        self.data["prize"] = self.new_prize.value
        await asyncio.to_thread(
            database.update_giveaway_data,
            self.data["giveaway_id"],
            self.data["prize"],
            self.data["winners_count"],
            self.data["end_time"],
            self.data["requirements"]
        )
        await self.cog.update_giveaway_message(self.data["guild_id"])
        await interaction.response.send_message(f"✅ Çekiliş ödülü **{self.new_prize.value}** olarak güncellendi.", ephemeral=True)


class EditWinnersModal(discord.ui.Modal, title="🏆 Kazanan Sayısını Düzenle"):
    new_winners = discord.ui.TextInput(
        label="Yeni Kazanan Sayısı",
        placeholder="Örn: 1, 2, 5",
        min_length=1,
        max_length=3
    )

    def __init__(self, cog, giveaway_data):
        super().__init__()
        self.cog = cog
        self.data = giveaway_data
        self.new_winners.default = str(self.data["winners_count"])

    async def on_submit(self, interaction: discord.Interaction):
        val = self.new_winners.value.strip()
        if not val.isdigit() or int(val) < 1:
            return await interaction.response.send_message("❌ Lütfen 1 veya daha büyük geçerli bir sayı giriniz.", ephemeral=True)

        self.data["winners_count"] = int(val)
        await asyncio.to_thread(
            database.update_giveaway_data,
            self.data["giveaway_id"],
            self.data["prize"],
            self.data["winners_count"],
            self.data["end_time"],
            self.data["requirements"]
        )
        await self.cog.update_giveaway_message(self.data["guild_id"])
        await interaction.response.send_message(f"✅ Kazanan sayısı **{val}** olarak güncellendi.", ephemeral=True)


class EditRequirementsModal(discord.ui.Modal, title="📋 Şartları Düzenle"):
    new_reqs = discord.ui.TextInput(
        label="Katılım Şartları",
        style=discord.TextStyle.paragraph,
        placeholder="Örn: Sunucuda en az 3 gün bulunmak...",
        min_length=1,
        max_length=300
    )

    def __init__(self, cog, giveaway_data):
        super().__init__()
        self.cog = cog
        self.data = giveaway_data
        self.new_reqs.default = self.data["requirements"]

    async def on_submit(self, interaction: discord.Interaction):
        self.data["requirements"] = self.new_reqs.value
        await asyncio.to_thread(
            database.update_giveaway_data,
            self.data["giveaway_id"],
            self.data["prize"],
            self.data["winners_count"],
            self.data["end_time"],
            self.data["requirements"]
        )
        await self.cog.update_giveaway_message(self.data["guild_id"])
        await interaction.response.send_message("✅ Katılım şartları başarıyla güncellendi.", ephemeral=True)


class EditTimeModal(discord.ui.Modal, title="⏳ Süre Ekle veya Azalt"):
    minute_diff = discord.ui.TextInput(
        label="Eklenecek / Çıkarılacak Dakika",
        placeholder="Örn: +10 (ekle) veya -5 (azalt)",
        min_length=1,
        max_length=6
    )

    def __init__(self, cog, giveaway_data):
        super().__init__()
        self.cog = cog
        self.data = giveaway_data

    async def on_submit(self, interaction: discord.Interaction):
        val = self.minute_diff.value.strip().replace("+", "")
        try:
            minutes = int(val)
        except ValueError:
            return await interaction.response.send_message("❌ Geçerli bir sayı giriniz (Örn: 10 veya -5).", ephemeral=True)

        current_end = ensure_utc(self.data["end_time"])
        new_end = current_end + datetime.timedelta(minutes=minutes)
        now = datetime.datetime.now(datetime.timezone.utc)

        if new_end <= now:
            return await interaction.response.send_message("❌ Çekiliş bitiş zamanı şu andan daha geriye alınamaz!", ephemeral=True)

        self.data["end_time"] = new_end
        await asyncio.to_thread(
            database.update_giveaway_data,
            self.data["giveaway_id"],
            self.data["prize"],
            self.data["winners_count"],
            self.data["end_time"],
            self.data["requirements"]
        )
        await self.cog.restart_giveaway_task(self.data["guild_id"], self.data["giveaway_id"])
        await self.cog.update_giveaway_message(self.data["guild_id"])
        await interaction.response.send_message(f"✅ Çekiliş süresi güncellendi. Yeni Bitiş: <t:{int(new_end.timestamp())}:R>", ephemeral=True)


class GiveawayManageView(discord.ui.View):
    def __init__(self, cog, giveaway_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.data = giveaway_data

    @discord.ui.button(label="Ödülü Düzenle", style=discord.ButtonStyle.primary, emoji="🎁")
    async def edit_prize(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditPrizeModal(self.cog, self.data))

    @discord.ui.button(label="Kazanan Sayısı", style=discord.ButtonStyle.primary, emoji="🏆")
    async def edit_winners(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditWinnersModal(self.cog, self.data))

    @discord.ui.button(label="Süreyi Düzenle", style=discord.ButtonStyle.primary, emoji="⏳")
    async def edit_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTimeModal(self.cog, self.data))

    @discord.ui.button(label="Şartları Düzenle", style=discord.ButtonStyle.primary, emoji="📋")
    async def edit_reqs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditRequirementsModal(self.cog, self.data))


class RerollView(discord.ui.View):
    def __init__(self, prize: str, host_id: int, participants: list, won_users: set):
        super().__init__(timeout=None)
        self.prize = prize
        self.host_id = host_id
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
                f"📌 *Ödülünüzü teslim almak için lütfen <@{self.host_id}> ile iletişime geçin.*"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        reroll_embed.set_footer(text="Demokratik Sol Parti Çekiliş Sistemi")

        await interaction.channel.send(
            content=f"🎉 {winner_mention}",
            embed=reroll_embed,
            view=RerollView(self.prize, self.host_id, self.participants, self.won_users)
        )
        await interaction.response.send_message(f"✅ Yeni kazanan belirlendi: {winner_mention}", ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Çekilişe Katıl", style=discord.ButtonStyle.success, emoji="🎉", custom_id="btn_live_giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = await asyncio.to_thread(database.get_active_giveaway, self.guild_id)
        if not data:
            return await interaction.response.send_message("❌ Bu çekiliş artık aktif değil.", ephemeral=True)

        user_id = interaction.user.id
        participants = await asyncio.to_thread(database.get_giveaway_participants, data["giveaway_id"])

        if user_id in participants:
            await asyncio.to_thread(database.remove_giveaway_participant, data["giveaway_id"], user_id)
            resp_text = "❌ Çekilişten ayrıldınız."
            participants.remove(user_id)
        else:
            await asyncio.to_thread(database.add_giveaway_participant, data["giveaway_id"], user_id)
            resp_text = "✅ Çekilişe başarıyla katıldınız! Şansınız bol olsun."
            participants.append(user_id)

        button.label = f"Çekilişe Katıl ({len(participants)})"
        
        end_dt = ensure_utc(data["end_time"])
        end_ts = int(end_dt.timestamp())
        host_user = interaction.guild.get_member(data["host_id"])
        
        embed = discord.Embed(
            title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
            description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
            color=config.COLOR_HEX,
            timestamp=end_dt
        )
        embed.add_field(name="🎉 Ödül", value=f"```fix\n{data['prize']}\n```", inline=False)
        embed.add_field(name="📋 Katılım Şartları", value=f"> {data['requirements']}", inline=False)
        embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{data['winners_count']} Kişi`", inline=True)
        embed.add_field(name="👥 Katılımcılar", value=f"`{len(participants)} Kişi`", inline=True)
        embed.add_field(name="⏳ Bitiş", value=f"<t:{end_ts}:R>", inline=True)
        if host_user:
            embed.set_footer(text=f"Düzenleyen: {host_user.display_name} • Bitiş Zamanı", icon_url=host_user.display_avatar.url)
        else:
            embed.set_footer(text="Bitiş Zamanı")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(resp_text, ephemeral=True)
        except Exception:
            pass


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.running_tasks = {}

    async def cog_load(self):
        self.bot.loop.create_task(self.restore_giveaways())

    async def restore_giveaways(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            data = await asyncio.to_thread(database.get_active_giveaway, guild.id)
            if data and guild.id not in self.running_tasks:
                task = asyncio.create_task(self.run_giveaway_loop(guild.id, data["giveaway_id"]))
                self.running_tasks[guild.id] = task

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in interaction.user.roles)

    async def restart_giveaway_task(self, guild_id: int, giveaway_id: int):
        current_task = self.running_tasks.get(guild_id)
        if current_task and not current_task.done():
            current_task.cancel()
        task = asyncio.create_task(self.run_giveaway_loop(guild_id, giveaway_id))
        self.running_tasks[guild_id] = task

    async def update_giveaway_message(self, guild_id: int):
        data = await asyncio.to_thread(database.get_active_giveaway, guild_id)
        if not data or not data.get("message_id"):
            return

        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            return

        try:
            msg = await channel.fetch_message(data["message_id"])
            participants = await asyncio.to_thread(database.get_giveaway_participants, data["giveaway_id"])
            end_dt = ensure_utc(data["end_time"])
            end_ts = int(end_dt.timestamp())
            host_user = channel.guild.get_member(data["host_id"])

            embed = discord.Embed(
                title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
                description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
                color=config.COLOR_HEX,
                timestamp=end_dt
            )
            embed.add_field(name="🎉 Ödül", value=f"```fix\n{data['prize']}\n```", inline=False)
            embed.add_field(name="📋 Katılım Şartları", value=f"> {data['requirements']}", inline=False)
            embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{data['winners_count']} Kişi`", inline=True)
            embed.add_field(name="👥 Katılımcılar", value=f"`{len(participants)} Kişi`", inline=True)
            embed.add_field(name="⏳ Bitiş", value=f"<t:{end_ts}:R>", inline=True)
            if host_user:
                embed.set_footer(text=f"Düzenleyen: {host_user.display_name} • Bitiş Zamanı", icon_url=host_user.display_avatar.url)

            view = GiveawayView(guild_id=guild_id)
            view.children[0].label = f"Çekilişe Katıl ({len(participants)})"
            await msg.edit(embed=embed, view=view)
        except Exception:
            pass

    async def run_giveaway_loop(self, guild_id: int, giveaway_id: int):
        try:
            data = await asyncio.to_thread(database.get_active_giveaway, guild_id)
            if not data or data["status"] != "active":
                self.running_tasks.pop(guild_id, None)
                return

            end_dt = ensure_utc(data["end_time"])
            now = datetime.datetime.now(datetime.timezone.utc)
            remaining_seconds = max(0.0, (end_dt - now).total_seconds())

            if remaining_seconds > 0:
                await asyncio.sleep(remaining_seconds)

            await asyncio.to_thread(database.end_db_giveaway, giveaway_id, "ended")
            self.running_tasks.pop(guild_id, None)

            channel = self.bot.get_channel(data["channel_id"])
            if not channel:
                return

            try:
                message = await channel.fetch_message(data["message_id"])
            except Exception:
                return

            participants = await asyncio.to_thread(database.get_giveaway_participants, giveaway_id)
            view = GiveawayView(guild_id=guild_id)
            for item in view.children:
                item.disabled = True
                if isinstance(item, discord.ui.Button):
                    item.label = f"Çekiliş Sona Erdi ({len(participants)})"
                    item.style = discord.ButtonStyle.secondary

            if not participants:
                end_embed = discord.Embed(
                    title="🔒 ÇEKİLİŞ SONUÇLANDI",
                    description=f"🎁 **Ödül:** `{data['prize']}`\n\n❌ Yetersiz katılım sebebiyle kazanan belirlenemedi.",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                await message.edit(embed=end_embed, view=view)
                return await channel.send(f"⚠️ **{data['prize']}** çekilişine kimse katılmadığı için kazanan seçilemedi.")

            winners_count = min(len(participants), data["winners_count"])
            selected_ids = random.sample(participants, winners_count)
            won_users = set(selected_ids)
            winners_mentions = ", ".join([f"<@{uid}>" for uid in selected_ids])

            end_embed = discord.Embed(
                title="🔒 ÇEKİLİŞ SONUÇLANDI",
                description=f"🎁 **Ödül:** `{data['prize']}`\n\n🏆 **Kazanan(lar):** {winners_mentions}\n👥 **Toplam Katılımcı:** `{len(participants)} Kişi`",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await message.edit(embed=end_embed, view=view)

            celebrate_embed = discord.Embed(
                title="🎊 ÇEKİLİŞ KAZANANLARI BELİRLENDİ!",
                description=(
                    f"🎁 **Ödül:** `{data['prize']}`\n\n"
                    f"🏆 **Tebrikler:** {winners_mentions}\n\n"
                    f"📌 *Ödülünüzü teslim almak için lütfen <@{data['host_id']}> ile iletişime geçin.*"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            celebrate_embed.set_footer(text="Demokratik Sol Parti Çekiliş Sistemi")

            reroll_view = RerollView(
                prize=data["prize"], 
                host_id=data["host_id"], 
                participants=participants, 
                won_users=won_users
            )
            await channel.send(content=f"🎉 {winners_mentions}", embed=celebrate_embed, view=reroll_view)
        except asyncio.CancelledError:
            pass

    @app_commands.command(name="çekiliş", description="Kalıcı ve modern bir çekiliş başlatır.")
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
        active_gw = await asyncio.to_thread(database.get_active_giveaway, guild_id)
        if active_gw:
            return await interaction.response.send_message("❌ **Zaten aktif bir çekiliş bulunmakta!** Sunucuda aynı anda yalnızca 1 adet çekiliş yürütülebilir.", ephemeral=True)

        if kazanan_sayısı < 1 or süre_dakika < 1:
            return await interaction.response.send_message("❌ Kazanan sayısı ve süre en az 1 olmalıdır.", ephemeral=True)

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=süre_dakika)
        req_text = şartlar if şartlar else "Şart Yok (Herkese Açık)"

        giveaway_id = await asyncio.to_thread(
            database.create_db_giveaway,
            guild_id=guild_id,
            channel_id=interaction.channel_id,
            prize=ödül,
            winners_count=kazanan_sayısı,
            end_time=end_time,
            host_id=interaction.user.id,
            requirements=req_text
        )

        end_ts = int(end_time.timestamp())
        embed = discord.Embed(
            title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
            description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
            color=config.COLOR_HEX,
            timestamp=end_time
        )
        embed.add_field(name="🎉 Ödül", value=f"```fix\n{ödül}\n```", inline=False)
        embed.add_field(name="📋 Katılım Şartları", value=f"> {req_text}", inline=False)
        embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{kazanan_sayısı} Kişi`", inline=True)
        embed.add_field(name="👥 Katılımcılar", value="`0 Kişi`", inline=True)
        embed.add_field(name="⏳ Bitiş", value=f"<t:{end_ts}:R>", inline=True)
        embed.set_footer(text=f"Düzenleyen: {interaction.user.display_name} • Bitiş Zamanı", icon_url=interaction.user.display_avatar.url)

        view = GiveawayView(guild_id=guild_id)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        await asyncio.to_thread(database.set_giveaway_message_id, giveaway_id, message.id)
        self.running_tasks[guild_id] = asyncio.create_task(self.run_giveaway_loop(guild_id, giveaway_id))

    @app_commands.command(name="çekilişiptal", description="Aktif olan çekilişi iptal eder.")
    @app_commands.describe(sebep="Çekilişin iptal edilme sebebi")
    async def cancel_giveaway(self, interaction: discord.Interaction, sebep: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        guild_id = interaction.guild.id
        data = await asyncio.to_thread(database.get_active_giveaway, guild_id)

        if not data:
            return await interaction.response.send_message("❌ Şu anda sunucuda devam eden aktif bir çekiliş bulunmuyor.", ephemeral=True)

        task = self.running_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
        self.running_tasks.pop(guild_id, None)

        await asyncio.to_thread(database.end_db_giveaway, data["giveaway_id"], "cancelled")

        channel = self.bot.get_channel(data["channel_id"])
        if channel and data["message_id"]:
            try:
                msg = await channel.fetch_message(data["message_id"])
                view = GiveawayView(guild_id=guild_id)
                for item in view.children:
                    item.disabled = True
                    if isinstance(item, discord.ui.Button):
                        item.label = "Çekiliş İptal Edildi"
                        item.style = discord.ButtonStyle.danger
                
                cancelled_embed = discord.Embed(
                    title="🚫 ÇEKİLİŞ İPTAL EDİLDİ",
                    description=f"🎁 **Ödül:** `{data['prize']}`\n\n**İptal Sebebi:** {sebep}",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                cancelled_embed.set_footer(text=f"İptal Eden: {interaction.user.display_name}")
                await msg.edit(embed=cancelled_embed, view=view)
            except Exception:
                pass

        await interaction.response.send_message(f"✅ Çekiliş başarıyla iptal edildi.\n**Sebep:** {sebep}", ephemeral=True)

    @app_commands.command(name="çekilişyönet", description="Aktif çekilişin bilgilerini düzenler.")
    async def manage_giveaway(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        guild_id = interaction.guild.id
        data = await asyncio.to_thread(database.get_active_giveaway, guild_id)

        if not data:
            return await interaction.response.send_message("❌ Yönetilebilecek aktif bir çekiliş bulunamadı.", ephemeral=True)

        participants = await asyncio.to_thread(database.get_giveaway_participants, data["giveaway_id"])
        end_dt = ensure_utc(data["end_time"])
        end_ts = int(end_dt.timestamp())

        embed = discord.Embed(
            title="⚙️ Çekiliş Yönetim Paneli",
            description=(
                f"Aşağıdaki butonlara tıklayarak aktif çekilişin bilgilerini anlık olarak değiştirebilirsiniz.\n\n"
                f"🎁 **Mevcut Ödül:** `{data['prize']}`\n"
                f"🏆 **Kazanan Sayısı:** `{data['winners_count']} Kişi`\n"
                f"⏳ **Bitiş:** <t:{end_ts}:R>\n"
                f"📋 **Şartlar:** {data['requirements']}\n"
                f"👥 **Katılımcı Sayısı:** `{len(participants)} Kişi`"
            ),
            color=config.COLOR_HEX
        )
        view = GiveawayManageView(self, data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
