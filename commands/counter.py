import discord
from discord import app_commands
from discord.ext import commands
import database
import config

class CounterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kayıttop", description="En çok kayıt yapan yetkilileri listeler.")
    async def kayittop(self, interaction: discord.Interaction):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True)

        rows = database.get_top_staff()
        if not rows:
            return await interaction.response.send_message("Henüz kayıt verisi bulunmuyor.", ephemeral=True)

        msg = "🏆 **Kayıt Toplamları**\n"
        idx = 1
        for staff_id, count in rows[:10]:
            user = interaction.guild.get_member(staff_id)
            user_str = user.mention if user else f"ID: {staff_id}"
            msg += f"\t{idx}. {user_str} — {count} kayıt\n"
            idx += 1

        embed = discord.Embed(description=msg, color=config.COLOR_HEX)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CounterCommands(bot))
