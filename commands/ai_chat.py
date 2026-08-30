import os
import discord
from discord.ext import commands
import datetime
import config
from google import genai

# Yapay Zeka Sohbet Kanalı ID'si ve Sahibin ID'si
AI_CHANNEL_ID = 1543605204774289538
OWNER_ID = 651765260579241984

class GeminiAIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Google GenAI İstemcisini Başlatma (GEMINI_API_KEY değişkenini okur)
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.channel.id != AI_CHANNEL_ID:
            return

        if getattr(self.bot, "is_under_maintenance", False) and message.author.id != OWNER_ID:
            return

        user_input = message.content.strip()
        if not user_input:
            return

        if not self.client:
            try:
                await message.reply("❌ **Gemini API Anahtarı Bulunamadı!** Lütfen Render/Replit paneline `GEMINI_API_KEY` değişkenini ekleyin.", mention_author=True)
            except Exception:
                pass
            return

        async with message.channel.typing():
            response_content = await self.fetch_gemini_response(user_input, message.author.display_name)

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
            print(f"[Gemini AI Error] Mesaj gönderilemedi: {e}")

    async def fetch_gemini_response(self, prompt: str, author_name: str) -> str:
        try:
            # Güncel ve aktif olan model adı kullanıldı
            system_instruction = (
                f"Sen Demokratik Sol Parti Discord sunucusunun resmi ve profesyonel yapay zeka asistanısın. "
                f"Kullanıcılara son derece kibar, bilgili, net ve akıcı bir dille Türkçe yanıtlar veriyorsun. "
                f"Şu an soru soran kullanıcının adı: {author_name}."
            )
            
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            return response.text.strip()
        except Exception as e:
            return f"⚠️ Gemini API bağlantı hatası oluştu: `{str(e)[:150]}`"

async def setup(bot):
    await bot.add_cog(GeminiAIChat(bot))
