import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import config

class ClearCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, member: discord.Member, guild: discord.Guild) -> bool:
        if member.guild_permissions.administrator or member.id == guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in member.roles)

    # Ortak Mesaj Silme Mantığı
    async def purge_messages(self, channel, amount: int):
        deleted_count = 0
        remaining = amount

        while remaining > 0:
            limit = min(remaining, 100)
            try:
                deleted = await channel.purge(limit=limit, bulk=True)
                if not deleted:
                    break
                deleted_count += len(deleted)
                remaining -= len(deleted)
                if len(deleted) < limit:
                    # Daha fazla silinebilecek (14 günden yeni) mesaj kalmadı
                    break
                await asyncio.sleep(1)
            except Exception:
                break

        return deleted_count

    # --- 1. YÖNTEM: Prefix Komutları (!sil / d!sil) ---
    @commands.command(name="sil", aliases=["Sil", "temizle", "clear"])
    @commands.guild_only()
    async def prefix_sil(self, ctx, miktar: str = None):
        # Yetki Kontrolü
        if not self.is_authorized(ctx.author, ctx.guild):
            msg = await ctx.send("❌ Bu komutu kullanmak için yetkiniz yok.")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except Exception:
                pass
            return

        # Bot izin kontrolü
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            msg = await ctx.send("❌ Botun bu kanalda mesajları silme yetkisi bulunmuyor.")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except Exception:
                pass
            return

        # Komutu yazan kullanıcının mesajını sil
        try:
            await ctx.message.delete()
        except Exception:
            pass

        # Sayısal Değer Kontrolü (1-500)
        if not miktar or not miktar.isdigit():
            msg = await ctx.send("❌ Lütfen 1-500 arasında geçerli bir sayı giriniz!")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except Exception:
                pass
            return

        sayi = int(miktar)
        if sayi < 1 or sayi > 500:
            msg = await ctx.send("❌ Lütfen 1-500 arasında bir değer giriniz!")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except Exception:
                pass
            return

        silinen = await self.purge_messages(ctx.channel, sayi)
        success_msg = await ctx.send(f"✅ **{silinen} Adet Mesaj Başarıyla Silinmiştir.**")
        await asyncio.sleep(3)
        try:
            await success_msg.delete()
        except Exception:
            pass

    # --- 2. YÖNTEM: Slash Komutu (/mesajsil) ---
    @app_commands.command(name="mesajsil", description="Belirtilen miktarda mesajı kanaldan siler.")
    @app_commands.describe(mesajsayisi="Silinecek mesaj sayısı (1-500)")
    async def slash_sil(self, interaction: discord.Interaction, mesajsayisi: int):
        # Yetki Kontrolü
        if not self.is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        # Bot izin kontrolü
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            return await interaction.response.send_message("❌ Botun bu kanalda mesajları silme yetkisi bulunmuyor.", ephemeral=True)

        if mesajsayisi < 1 or mesajsayisi > 500:
            return await interaction.response.send_message("❌ Lütfen 1 ile 500 arasında bir değer giriniz!", ephemeral=True)

        # Discord 3 saniye timeout'una takılmamak için ön yanıt
        await interaction.response.defer(ephemeral=True)

        silinen = await self.purge_messages(interaction.channel, mesajsayisi)

        success_msg = await interaction.channel.send(f"✅ **{silinen} Adet Mesaj Başarıyla Silinmiştir.**")
        await interaction.followup.send(f"İşlem tamamlandı: {silinen} mesaj silindi.", ephemeral=True)

        await asyncio.sleep(3)
        try:
            await success_msg.delete()
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(ClearCommands(bot))
