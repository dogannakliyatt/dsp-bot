import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random
import config

class GiveawayView(discord.ui.View):
    def __init__(self, requirements: str = None):
        super().__init__(timeout=None)
        self.requirements = requirements
        if not requirements:
            self.clear_items()

    @discord.ui.button(label="📋 Katılım Şartları", style=discord.ButtonStyle.secondary, custom_id="giveaway_req_view_btn")
    async def requirements_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.requirements:
            return await interaction.response.send_message("Bu çekiliş için özel bir katılım şartı belirtilmedi.", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 Çekiliş Katılım Şartları",
            description=self.requirements,
            color=config.COLOR_HEX
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles)

    async def run_giveaway_timer(self, channel_id: int, message_id: int, ödül: str, kazanan_sayısı: int, süre_saniye: int):
        await asyncio.sleep(süre_saniye)
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            fetch_msg = await channel.fetch_message(message_id)
        except Exception:
            return

        reaction = discord.utils.get(fetch_msg.reactions, emoji="🎉")
        users = []
        if reaction:
            users = [user async for user in reaction.users() if not user.bot]

        if not users:
            end_embed = discord.Embed(
                title="🎉 ÇEKİLİŞ SONUÇLANDI! 🎉",
                description=f"**Ödül:** {ödül}\n❌ Yeterli katılım olmadığı için kazanan belirlenemedi.",
                color=discord.Color.red()
            )
            return await channel.send(embed=end_embed)

        winners = random.sample(users, min(len(users), kazanan_sayısı))
        winner_mentions = ", ".join([w.mention for w in winners])

        end_embed = discord.Embed(
            title="🎉 ÇEKİLİŞ SONUÇLANDI! 🎉",
            description=f"🎁 **Ödül:** {ödül}\n🏆 **Kazanan(lar):** {winner_mentions}\n👏 Tebrikler!",
            color=discord.Color.green()
        )
        await channel.send(embed=end_embed)

    @app_commands.command(name="çekiliş", description="Yeni bir çekiliş başlatır.")
    @app_commands.describe(
        ödül="Çekilişte verilecek ödül",
        kazanan_sayısı="Kazanacak kişi sayısı",
        süre_dakika="Çekiliş süresi (dakika)",
        şartlar="İsteğe bağlı katılım şartları"
    )
    async def giveaway(self, interaction: discord.Interaction, ödül: str, kazanan_sayısı: int, süre_dakika: int, şartlar: str = None):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        if kazanan_sayısı < 1 or süre_dakika < 1:
            return await interaction.response.send_message("❌ Kazanan sayısı ve süre en az 1 olmalıdır.", ephemeral=True)

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=süre_dakika)
        timestamp_str = f"<t:{int(end_time.timestamp())}:R>"

        desc = (
            f"🎁 **Ödül:** {ödül}\n"
            f"👥 **Kazanan Sayısı:** `{kazanan_sayısı}`\n"
            f"⏳ **Bitiş:** {timestamp_str}\n"
            f"🎉 **Katılmak için aşağıdaki 🎉 emojisine tıklayın!**"
        )

        embed = discord.Embed(
            title="🎉 ÇEKİLİŞ BAŞLADI! 🎉",
            description=desc,
            color=config.COLOR_HEX,
            timestamp=end_time
        )
        embed.set_footer(text="Bitiş Zamanı")

        view = GiveawayView(requirements=şartlar)
        await interaction.response.send_message(embed=embed, view=view if şartlar else None)
        message = await interaction.original_response()

        try:
            await message.add_reaction("🎉")
        except Exception:
            pass

        # Çekiliş sayacını arka planda çalıştır (Komutun donmasını önler)
        asyncio.create_task(
            self.run_giveaway_timer(
                channel_id=interaction.channel_id,
                message_id=message.id,
                ödül=ödül,
                kazanan_sayısı=kazanan_sayısı,
                süre_saniye=süre_dakika * 60
            )
        )

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
