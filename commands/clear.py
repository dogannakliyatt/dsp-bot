import discord
from discord import app_commands
from discord.ext import commands

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mesajsil", description="Belirtilen miktarda mesajı kanaldan siler.")
    @app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
    async def mesajsil(self, interaction: discord.Interaction, miktar: int):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Bu komutu kullanmak için `Mesajları Yönet` yetkiniz olmalı.", ephemeral=True)

        if miktar < 1 or miktar > 100:
            return await interaction.response.send_message("❌ Lütfen 1 ile 100 arasında bir miktar belirtin.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=miktar)
            await interaction.followup.send(f"🗑️ Başarıyla **{len(deleted)}** adet mesaj silindi.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Mesajlar silinirken hata oluştu: {e}", ephemeral=True)

    @commands.command(name="sil", aliases=["mesajsil"])
    @commands.has_permissions(manage_messages=True)
    async def sil_prefix(self, ctx: commands.Context, miktar: int = 5):
        if miktar < 1 or miktar > 100:
            return await ctx.reply("❌ Lütfen 1 ile 100 arasında bir miktar belirtin.", mention_author=False)
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=miktar)
            msg = await ctx.send(f"🗑️ Başarıyla **{len(deleted)}** adet mesaj silindi.")
            await msg.delete(delay=4)
        except Exception as e:
            await ctx.reply(f"❌ Hata: {e}", mention_author=False)

async def setup(bot):
    await bot.add_cog(Clear(bot))
