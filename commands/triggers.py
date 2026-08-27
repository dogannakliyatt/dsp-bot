import discord
from discord.ext import commands

class Triggers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        if message.author.bot:
            return

        content = (
            message.content.strip()
            .replace("İ", "i")
            .replace("I", "ı")
            .lower()
        )

        if content in self.selam_kelimeleri:
            cevap = f"Aleykümselam, hoş geldin sefalar getirdin! ☺️🥰☺️ {message.author.mention}"
            await message.channel.send(cevap)

async def setup(bot):
    await bot.add_cog(Triggers(bot))
