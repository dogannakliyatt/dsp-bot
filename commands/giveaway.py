import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timedelta

def parse_duration(duration_str: str) -> int:
    """Girilen Türkçe süre metnini saniyeye çevirir."""
    total_seconds = 0
    days = re.search(r'(\d+)\s*(gün|g)', duration_str, re.IGNORECASE)
    hours = re.search(r'(\d+)\s*(saat|sa|s)', duration_str, re.IGNORECASE)
    minutes = re.search(r'(\d+)\s*(dakika|dk|d)', duration_str, re.IGNORECASE)
    seconds = re.search(r'(\d+)\s*(saniye|sn)', duration_str, re.IGNORECASE)

    if days:
        total_seconds += int(days.group(1)) * 86400
    if hours:
        total_seconds += int(hours.group(1)) * 3600
    if minutes:
        total_seconds += int(minutes.group(1)) * 60
    if seconds:
        total_seconds += int(seconds.group(1))

    if total_seconds == 0:
        digits = re.findall(r'\d+', duration_str)
        if digits:
            total_seconds = int(digits[0]) * 60
        else:
            total_seconds = 60
    return total_seconds

# 1. Aşama: Form (Modal)
class GiveawayModal(ui.Modal, title="Çekiliş Oluştur"):
    prize = ui.TextInput(label="Ödül Gir", placeholder="Örn: deneme", required=True)
    duration = ui.TextInput(label="Süreyi Gir (1 gün 5 saat 45 dakika)", placeholder="Örn: 1 gün / 10 dakika", required=True)
    winners = ui.TextInput(label="Kazanan Sayısını Gir", default="1", required=True)

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            winner_count = int(self.winners.value)
        except ValueError:
            winner_count = 1

        seconds = parse_duration(self.duration.value)

        view = SetupView(
            prize=self.prize.value,
            duration_str=self.duration.value,
            duration_seconds=seconds,
            winners=winner_count,
            target_channel=self.target_channel,
            author=interaction.user
        )
        embed = discord.Embed(title="⚙️ Çekiliş Ayarları", color=discord.Color.gold())
        embed.add_field(name="⏰ Çekiliş Süresi", value=f"**{self.duration.value}**", inline=False)
        embed.add_field(name="🎉 Çekilişin Ödülü", value=f"**{self.prize.value}**", inline=False)
        embed.add_field(name="📢 Çekiliş Kanalı", value=self.target_channel.mention, inline=False)
        embed.add_field(name="👑 Kazanan Sayısı", value=f"**{winner_count}**", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# 2. Aşama: Şartlar Menüsü
class RequirementsSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Tag Şartı", emoji="井", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Davet Şartı", emoji="🔗", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Seviye Şartı", emoji="🎖️", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Mesaj Şartı", emoji="💬", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Rol Şartı", emoji="@", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Ses Şartı", emoji="🔊", description="Ayarlamak için tıkla"),
            discord.SelectOption(label="Durum Şartı", emoji="📇", description="Ayarlamak için tıkla"),
        ]
        super().__init__(placeholder="Katılım Şartları:", min_values=0, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = ", ".join(self.values) if self.values else "Hiçbiri"
        await interaction.response.send_message(f"Seçilen Şartlar: {selected}", ephemeral=True)

class RequirementsView(ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(RequirementsSelect())

# 3. Aşama: Kurulum Paneli
class SetupView(ui.View):
    def __init__(self, prize, duration_str, duration_seconds, winners, target_channel, author):
        super().__init__(timeout=None)
        self.prize = prize
        self.duration_str = duration_str
        self.duration_seconds = duration_seconds
        self.winners = winners
        self.target_channel = target_channel
        self.author = author

    @ui.button(label="Çekiliş Ayarları", style=discord.ButtonStyle.secondary, row=0)
    async def settings(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Çekiliş ayarları menüsü.", ephemeral=True)

    @ui.button(label="Çekilişin Ödülü", style=discord.ButtonStyle.secondary, row=0)
    async def edit_prize(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"Mevcut Ödül: {self.prize}", ephemeral=True)

    @ui.button(label="Çekiliş Süresi", style=discord.ButtonStyle.secondary, row=1)
    async def edit_time(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"Mevcut Süre: {self.duration_str}", ephemeral=True)

    @ui.button(label="Kazanan Sayısı", style=discord.ButtonStyle.secondary, row=1)
    async def edit_winners(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"Kazanan Sayısı: {self.winners}", ephemeral=True)

    @ui.button(label="Katılım Şartları:", style=discord.ButtonStyle.secondary, row=2)
    async def reqs(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Katılım Şartları Menüsü:", view=RequirementsView(), ephemeral=True)

    @ui.button(label="🎉 Çekiliş Başlat", style=discord.ButtonStyle.danger, row=3)
    async def start_giveaway(self, interaction: discord.Interaction, button: ui.Button):
        end_time = datetime.now() + timedelta(seconds=self.duration_seconds)
        end_timestamp = int(end_time.timestamp())

        embed = discord.Embed(
            title=f"🎉 {self.prize}",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Çekilişi Başlatan:", value=self.author.mention, inline=False)
        embed.add_field(name="⏰ Çekiliş Süresi:", value=self.duration_str, inline=False)
        embed.add_field(name="📅 Çekilişin Biteceği Tarih:", value=f"<t:{end_timestamp}:F> (<t:{end_timestamp}:R>)", inline=False)
        embed.add_field(name="👑 Kazanan Sayısı:", value=str(self.winners), inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6828/6828694.png")

        public_view = GiveawayPublicView()
        msg = await self.target_channel.send(embed=embed, view=public_view)
        await interaction.response.send_message(f"✅ Çekiliş başarıyla {self.target_channel.mention} kanalında yayınlandı!", ephemeral=True)

        # Arka Planda Zamanlayıcı Başlat
        asyncio.create_task(self.run_timer(msg, public_view, end_timestamp))

    async def run_timer(self, msg: discord.Message, view: 'GiveawayPublicView', end_timestamp: int):
        now = datetime.now().timestamp()
        wait_seconds = end_timestamp - now
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        # Süre Bitti - Kazananları Seç
        participants = list(view.participants)
        
        # Katılan Butonunu Devre Dışı Bırak
        for child in view.children:
            child.disabled = True
        await msg.edit(view=view)

        if not participants:
            end_embed = discord.Embed(
                title=f"🎉 {self.prize} (Sona Erdi)",
                description="❌ Çekilişe kimse katılmadığı için kazanan seçilemedi.",
                color=discord.Color.red()
            )
            await msg.edit(embed=end_embed)
            await msg.channel.send(f"❌ **{self.prize}** çekilişine yeterli katılım olmadı.")
            return

        # Belirlenen sayıda kazanan seç
        winner_count = min(self.winners, len(participants))
        winners = random.sample(participants, winner_count)
        winners_mentions = ", ".join([f"<@{user_id}>" for user_id in winners])

        end_embed = discord.Embed(
            title=f"🎉 {self.prize} (Sona Erdi)",
            color=discord.Color.gold()
        )
        end_embed.add_field(name="💰 Çekilişi Başlatan:", value=self.author.mention, inline=False)
        end_embed.add_field(name="👑 Kazanan(lar):", value=winners_mentions, inline=False)
        end_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6828/6828694.png")

        await msg.edit(embed=end_embed)
        await msg.channel.send(f"🎊 Tebrikler {winners_mentions}! **{self.prize}** ödülünü kazandınız!")

# 4. Aşama: Yayınlanan Çekiliş Butonları
class GiveawayPublicView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participants = set()

    @ui.button(label="🎉 Çekilişe katılmak için tıkla!", style=discord.ButtonStyle.secondary)
    async def join(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in self.participants:
            self.participants.remove(interaction.user.id)
            await interaction.response.send_message("❌ Çekilişten ayrıldınız.", ephemeral=True)
        else:
            self.participants.add(interaction.user.id)
            await interaction.response.send_message("✅ Çekilişe başarıyla katıldınız!", ephemeral=True)

# Slash Komutu
class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="çekiliş", description="Çekiliş oluşturma panelini açar.")
    @app_commands.describe(kanal="Çekilişin yayınlanacağı kanalı seçin.")
    async def giveaway_cmd(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        target = kanal or interaction.channel
        await interaction.response.send_modal(GiveawayModal(target_channel=target))

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
