import discord
from discord import app_commands
from discord.ext import commands
import database
import config

class CounterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles)

    @app_commands.command(name="kayıttop", description="En çok kayıt yapan yetkilileri listeler.")
    async def kayittop(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        try:
            rows = database.get_top_staff()
        except Exception as e:
            return await interaction.response.send_message(f"❌ Veritabanı hatası: {str(e)}", ephemeral=True)

        if not rows:
            return await interaction.response.send_message("📊 Henüz herhangi bir kayıt verisi bulunmuyor.", ephemeral=True)

        msg = ""
        for idx, row in enumerate(rows[:10], start=1):
            staff_id = row["staff_id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            count = row["count"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
            
            user = interaction.guild.get_member(staff_id)
            user_str = user.mention if user else f"`ID: {staff_id}`"
            msg += f"**{idx}.** {user_str} — **{count}** kayıt\n"

        embed = discord.Embed(
            title="🏆 Kayıt Yetkilisi Sıralaması",
            description=msg,
            color=config.COLOR_HEX
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CounterCommands(bot))
