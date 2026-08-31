import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bakım", description="Botu bakım moduna alır veya bakımdan çıkarır.")
    @app_commands.describe(durum="Bakım durumunu seçin")
    @app_commands.choices(durum=[
        app_commands.Choice(name="Bakıma Al", value="al"),
        app_commands.Choice(name="Bakımdan Çıkar", value="cikar")
    ])
    async def bakım(self, interaction: discord.Interaction, durum: app_commands.Choice[str]):
        OWNER_ID = 651765260579241984
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Bu komutu sadece botun sahibi kullanabilir.", ephemeral=True)

        if durum.value == "al":
            self.bot.is_under_maintenance = True
            embed = discord.Embed(
                title="⚙️ Bot Bakım Moduna Alındı",
                description="Bot şu an bakım modundadır. Sahip dışında kimse komut kullanamaz.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await interaction.response.send_message(embed=embed)
        else:
            self.bot.is_under_maintenance = False
            embed = discord.Embed(
                title="🟢 Bot Bakımdan Çıkarıldı",
                description="Bot normal çalışma düzenine geri döndü.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Maintenance(bot))
