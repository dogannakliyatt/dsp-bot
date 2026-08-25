import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import config

class ClearCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ortak Mesaj Silme Mantığı
    async def purge_messages(self, channel, amount: int):
        deleted_count = 0
        remaining = amount

        # Discord API tek seferde max 100 mesaj siler, bu yüzden parçalayarak siliyoruz
        while remaining > 0:
            limit = min(remaining, 100)
            deleted = await channel.purge(limit=limit)
            if not deleted:
                break
            deleted_count += len(deleted)
            remaining -= len(deleted)
            await asyncio.sleep(1) # API kısıtlamasına takılmamak için kısa bekleme

        return deleted_count

    # --- 1. YÖNTEM: Prefix Komutları (D!sil / d!sil) ---
    @commands.command(name="sil", aliases=["Sil"])
    async def prefix_sil(self, ctx, Miktar: str = None):
        # Yetki Kontrolü
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in ctx.author.roles):
            msg = await ctx.send("❌ Bu komutu kullanmak için yetkiniz yok.")
            await asyncio.sleep(3)
            await msg.delete()
            return

        # Komutu yazan kullanıcının `d!sil` mesajını da silmeye çalışalım
        try:
            await ctx.message.delete()
        except:
            pass

        # Değer Girilmediyse veya Sayı Değilse
        if not Miktar or not Miktar.isdigit():
            msg = await ctx.send("❌ Lütfen geçerli bir değer giriniz!")
            await asyncio.sleep(3)
            await msg.delete()
            return

        sayi = int(Miktar)

        # 1-500 Arasında Değilse
        if sayi < 1 or sayi > 500:
            msg = await ctx.send("❌ Lütfen geçerli bir değer giriniz!")
            await asyncio.sleep(3)
            await msg.delete()
            return

        # Mesajları Sil
        silinen = await self.purge_messages(ctx.channel, sayi)

        # Başarı Mesajı Gönder ve 3 Saniye Sonra Sil
        success_msg = await ctx.send(f"✅ **{silinen} Adet Mesaj Başarıyla Silinmiştir.**")
        await asyncio.sleep(3)
        await success_msg.delete()


    # --- 2. YÖNTEM: Slash Komutu (/mesajsil) ---
    @app_commands.command(name="mesajsil", description="Belirtilen miktarda mesajı kanaldan siler.")
    @app_commands.describe(mesajsayisi="Silinecek mesaj sayısı (1-500)")
    async def slash_sil(self, interaction: discord.Interaction, mesajsayisi: str):
        # Yetki Kontrolü
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        # Sayısal Değer Kontrolü
        if not mesajsayisi.isdigit():
            await interaction.response.send_message("❌ Lütfen geçerli bir değer giriniz!")
            await asyncio.sleep(3)
            await interaction.delete_original_response()
            return

        sayi = int(mesajsayisi)

        # 1-500 Arasında Değilse
        if sayi < 1 or sayi > 500:
            await interaction.response.send_message("❌ Lütfen geçerli bir değer giriniz!")
            await asyncio.sleep(3)
            await interaction.delete_original_response()
            return

        # İşlem Başladı Bildirimi
        await interaction.response.send_message("⏳ Mesajlar siliniyor...", ephemeral=True)

        # Mesajları Sil
        silinen = await self.purge_messages(interaction.channel, sayi)

        # Başarı Mesajı Gönder ve 3 Saniye Sonra Sil
        success_msg = await interaction.channel.send(f"✅ **{silinen} Adet Mesaj Başarıyla Silinmiştir.**")
        
        # İlk gizli yanıtı kaldır
        try:
            await interaction.delete_original_response()
        except:
            pass

        await asyncio.sleep(3)
        await success_msg.delete()

async def setup(bot):
    await bot.add_cog(ClearCommands(bot))
