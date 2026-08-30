import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

class GlobalErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Yerel hata yönetimleri (local error) varsa pas geçebilir
        if hasattr(ctx.command, 'on_error'):
            return

        embed = discord.Embed(
            title="⚠️ Bir Hata Oluştu",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text="Demokratik Sol Parti Sistem Koruması")

        if isinstance(error, commands.MissingPermissions):
            embed.description = "❌ Bu komutu kullanabilmek için gerekli yetkilere sahip değilsiniz."
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"❌ Komutu eksik kullandınız. Lütfen gerekli parametreleri doldurun."
        elif isinstance(error, commands.BadArgument):
            embed.description = "❌ Girilen argüman geçerli bir formatta değil. Lütfen kontrol edip tekrar deneyin."
        elif isinstance(error, commands.CommandOnCooldown):
            embed.description = f"⏳ Bu komut bekleme süresindedir. Lütfen **{error.retry_after:.1f}** saniye sonra tekrar deneyin."
        elif isinstance(error, commands.CheckFailure):
            embed.description = "❌ Bu komutu çalıştırmak için yetkiniz yetersiz."
        else:
            embed.description = f"❌ Beklenmeyen bir hata oluştu:\n```py\n{str(error)[:300]}\n```"

        try:
            await ctx.reply(embed=embed, mention_author=False)
        except Exception:
            pass

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        embed = discord.Embed(
            title="⚠️ Slash Komut Hatası",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text="Demokratik Sol Parti Sistem Koruması")

        if isinstance(error, app_commands.MissingPermissions):
            embed.description = "❌ Bu komutu kullanmak için yetkiniz bulunmuyor."
        elif isinstance(error, app_commands.CheckFailure):
            embed.description = "❌ Bu komutu çalıştırma koşullarını sağlamıyorsunuz."
        else:
            embed.description = f"❌ İşlem sırasında bir hata oluştu:\n```py\n{str(error)[:300]}\n```"

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(GlobalErrorHandler(bot))
