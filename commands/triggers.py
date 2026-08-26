import discord
from discord.ext import commands

class Triggers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Tetikleyici kelimeler listesi
        self.selam_kelimeleri = [
            "selam",
            "selamm",
            "merhaba",
            "mrb",
            "selamınaleyküm",
            "selamunaleyküm",
            "sa"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot kendi mesajlarına veya diğer botlara cevap vermesin
        if message.author.bot:
            return

        # Türkçe büyük/küçük harf dönüşümünü güvenli yap
        content = (
            message.content.strip()
            .replace("İ", "i")
            .replace("I", "ı")
            .lower()
        )

        # Mesaj listedeki kelimelerden biriyse tetikle
        if content in self.selam_kelimeleri:
            cevap = f"Aleykümselam, hoş gelsin sefalar getirdin! ☺️🥰☺️ {message.author.mention}"
            await message.channel.send(cevap)

async def setup(bot):
    await bot.add_cog(Triggers(bot))
