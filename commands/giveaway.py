import discord
from discord import app_commands, ui
from discord.ext import commands

# 1. Aşama: Form (Modal)
class GiveawayModal(ui.Modal, title="Çekiliş Oluştur"):
    prize = ui.TextInput(label="Ödül Gir", placeholder="Örn: deneme", required=True)
    duration = ui.TextInput(label="Süreyi Gir (1 gün 5 saat 45 dakika)", placeholder="Örn: 1 gün", required=True)
    winners = ui.TextInput(label="Kazanan Sayısını Gir", default="1", required=True)

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        view = SetupView(
            prize=self.prize.value,
            duration_str=self.duration.value,
            winners=self.winners.value,
            target_channel=self.target_channel,
            author=interaction.user
        )
        embed = discord.Embed(title="⚙️ Çekiliş Ayarları", color=discord.Color.gold())
        embed.add_field(name="⏰ Çekiliş Süresi", value=f"**{self.duration.value}**", inline=False)
        embed.add_field(name="🎉 Çekilişin Ödülü", value=f"**{self.prize.value}**", inline=False)
        embed.add_field(name="📢 Çekiliş Kanalı", value=self.target_channel.mention, inline=False)
        embed.add_field(name="👑 Kazanan Sayısı", value=f"**{self.winners.value}**", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# 2. Aşama: Şartlar Menüsü (Select Menu)
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

# 3. Aşama: Kurulum Paneli Butonları
class SetupView(ui.View):
    def __init__(self, prize, duration_str, winners, target_channel, author):
        super().__init__(timeout=None)
        self.prize = prize
        self.duration_str = duration_str
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

    @ui.button(label="📌 Çekiliş Bitir", style=discord.ButtonStyle.danger, row=3)
    async def start_giveaway(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title=f"🎉 {self.prize}",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Çekilişi Başlatan:", value=self.author.mention, inline=False)
        embed.add_field(name="⏰ Çekiliş Süresi:", value=self.duration_str, inline=False)
        embed.add_field(name="👑 Kazanan Sayısı:", value=self.winners, inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6828/6828694.png")

        view = GiveawayPublicView()
        
        # Seçilen Hedef Kanala Gönder
        await self.target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Çekiliş başarıyla {self.target_channel.mention} kanalında yayınlandı!", ephemeral=True)

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

# Slash Komutu (Kanal Parametreli)
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
