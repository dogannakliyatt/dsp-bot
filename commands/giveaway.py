import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random

class RequirementsModal(discord.ui.Modal, title="Katılım Şartları"):
    requirements = discord.ui.TextInput(
        label="Şartları Girin",
        style=discord.TextStyle.paragraph,
        placeholder="Örn: Abone olmak, belirli bir role sahip olmak...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Çekiliş Katılım Şartları",
            description=self.requirements.value,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Katılım Şartları", style=discord.ButtonStyle.primary, custom_id="giveaway_req_btn")
    async def requirements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RequirementsModal())

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="çekiliş", description="Yeni bir çekiliş başlatır.")
    @app_commands.checks.has_permissions(administrator=True)
    async def giveaway(self, interaction: discord.Interaction, ödül: str, kazanan_sayısı: int, süre_dakika: int):
        await interaction.response.defer(ephemeral=False)

        embed = discord.Embed(
            title="🎉 ÇEKİLİŞ BAŞLADI! 🎉",
            description=f"**Ödül:** {ödül}\n**Kazanan Sayısı:** {kazanan_sayısı}\n**Süre:** {süre_dakika} dakika",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=süre_dakika)
        )
        embed.set_footer(text="Bitiş Zamanı")

        view = GiveawayView()
        message = await interaction.followup.send(embed=embed, view=view)
        await message.add_reaction("🎉")

        await asyncio.sleep(süre_dakika * 60)

        fetch_msg = await interaction.channel.fetch_message(message.id)
        reaction = discord.utils.get(fetch_msg.reactions, emoji="🎉")

        users = [user async for user in reaction.users() if not user.bot]

        if not users:
            await interaction.channel.send(f"❌ **{ödül}** çekilişine yeterli katılım olmadı.")
            return

        winners = random.sample(users, min(len(users), kazanan_sayısı))
        winner_mentions = ", ".join([w.mention for w in winners])

        end_embed = discord.Embed(
            title="🎉 ÇEKİLİŞ SONUÇLANDI! 🎉",
            description=f"**Ödül:** {ödül}\n**Kazanan(lar):** {winner_mentions}",
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=end_embed)

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
