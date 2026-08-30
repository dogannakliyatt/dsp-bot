import os
import discord
from discord.ext import commands
import datetime
import config
from openai import AsyncOpenAI

# Yapay Zeka Sohbet Kanalı ID'si ve Sahibin ID'si
AI_CHANNEL_ID = 1543605204774289538
OWNER_ID = 651765260579241984

class GPTAIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # OpenAI İstemcisini Başlatma (Ortam değişkeninden veya config'den API key alır)
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Botun kendi mesajlarını ve sunucu dışı mesajları filtrele
        if message.author.bot or not message.guild:
            return

        # Yalnızca belirlenen yapay zeka kanalında çalışır
        if message.channel.id != AI_CHANNEL_ID:
            return

        # Bakım modu kontrolü: Sadece bot sahibi kullanabilir
        if getattr(self.bot, "is_under_maintenance", False) and message.author.id != OWNER_ID:
            return

        user_input = message.content.strip()
        if not user_input:
            return

        if not self.client:
            try:
                await message.reply("❌ **OpenAI API Anahtarı Bulunamadı!** Lütfen Render/Replit paneline `OPENAI_API_KEY` değişkenini ekleyin.", mention_author=True)
            except Exception:
                pass
            return

        # Profesyonel "Yazıyor..." (Typing) efekti eşliğinde GPT yanıtı üretme
        async with message.channel.typing():
            response_content = await self.fetch_gpt_response(user_input, message.author.display_name)

        # Discord mesaj limitine (2000 karakter) uyumlu parça yönetimi ve yanıtla ping atma
        try:
            if len(response_content) > 2000:
                chunks = [response_content[i:i+1990] for i in range(0, len(response_content), 1990)]
                for chunk in chunks:
                    await message.reply(chunk, mention_author=True)
            else:
                await message.reply(response_content, mention_author=True)
        except discord.HTTPException:
            pass
        except Exception as e:
            print(f"[GPT AI Error] Mesaj gönderilemedi: {e}")

    async def fetch_gpt_response(self, prompt: str, author_name: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Hızlı, akıllı ve ekonomik güncel GPT altyapısı
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Sen Demokratik Sol Parti Discord sunucusunun resmi ve profesyonel yapay zeka asistanısın. "
                            f"Kullanıcılara son derece kibar, bilgili, net ve akıcı bir dille Türkçe yanıtlar veriyorsun. "
                            f"Şu an soru soran kullanıcının adı: {author_name}."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ OpenAI API bağlantı hatası oluştu: `{str(e)[:150]}`"

async def setup(bot):
    await bot.add_cog(GPTAIChat(bot))
