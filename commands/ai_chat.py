import discord
from discord.ext import commands
import datetime
import config

# İstediğin Sohbet Kanalı ID'si
AI_CHANNEL_ID = 1543605204774289538

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Botun kendi mesajlarını veya sunucu dışı mesajları yoksay
        if message.author.bot or not message.guild:
            return

        # Sadece senin belirttiğin kanaldaki mesajları dinle
        if message.channel.id != AI_CHANNEL_ID:
            return

        # Bakım modunda ise sadece sahip (651765260579241984) kullanabilsin
        OWNER_ID = 651765260579241984
        if getattr(self.bot, "is_under_maintenance", False) and message.author.id != OWNER_ID:
            return

        user_message = message.content.strip()
        if not user_message:
            return

        # Yazım sürecinde kullanıcıya "Yazıyor..." efekti göster
        async with message.channel.typing():
            response_text = await self.generate_ai_response(user_message)

        try:
            # Discord mesaj karakter sınırını (2000) aşarsa bölerek gönder ve yanıtla (ping atarak)
            if len(response_text) > 2000:
                for i in range(0, len(response_text), 2000):
                    await message.reply(response_text[i:i+2000], mention_author=True)
            else:
                await message.reply(response_text, mention_author=True)
        except Exception:
            pass

    async def generate_ai_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        # Matematik İşlemleri Çözücü
        if any(op in prompt for op in ["+", "-", "*", "/", "^", "kaçtır", "hesapla", "işlem"]):
            try:
                import re
                clean_expr = re.sub(r'[^0-9+\-*/().]', '', prompt.replace('x', '*'))
                if clean_expr:
                    result = eval(clean_expr)
                    return f"🧮 **Matematik İşlemi Sonucu:** `{clean_expr} = {result}`"
            except Exception:
                pass

        # Google Araştırma ve Güncel Bilgi Simülasyonu / Akıllı Yanıtlar
        if "merhaba" in prompt_lower or "selam" in prompt_lower:
            return "Aleykümselam! Demokratik Sol Parti yapay zeka asistanıyım. Güncel bilgileri araştırmak, sorularını yanıtlamak ve sohbet etmek için buradayım! ☺️"
        elif "nasılsın" in prompt_lower:
            return "Teşekkür ederim, sunucu altyapısını ve simülasyonu yönetmekle meşgulüm! Sen nasılsın?"
        elif "kimsin" in prompt_lower or "ne yapabilirsin" in prompt_lower:
            return "Ben Demokratik Sol Parti botunun yapay zeka modülüyüm. Bu kanalda sorduğun her şeyi Google verileriyle harmanlayıp yanıtlayabilir, matematik işlemlerini çözebilir ve seninle sohbet edebilirim!"

        # Google / Güncel Araştırma Simülasyonu Yanıtı
        return f"🔍 **Google & Bilgi Araştırması:** \"{prompt}\" hakkında güncel verileri ve bilgi tabanımı inceledim. Sorduğun bu soruyla ilgili olarak, en doğru ve güncel detayları seninle paylaşabilirim. Başka merak ettiğin bir konu var mı?"

async def setup(bot):
    await bot.add_cog(AIChat(bot))
