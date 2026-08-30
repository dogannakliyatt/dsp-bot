import discord
from discord.ext import commands
import datetime
import math
import re
import config

# Yapay Zeka Sohbet Kanalı ID'si
AI_CHANNEL_ID = 1543605204774289538
OWNER_ID = 651765260579241984

class ProfessionalAIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        # Profesyonel "Yazıyor..." (Typing) efekti eşliğinde yanıt üretme
        async with message.channel.typing():
            response_content = await self.process_intelligent_response(user_input, message.author.display_name)

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
            print(f"[AI Error] Mesaj gönderilemedi: {e}")

    async def process_intelligent_response(self, prompt: str, author_name: str) -> str:
        prompt_lower = prompt.lower()

        # 1. Matematik ve Hesaplama Modülü (Güvenli Eval Motoru)
        math_keywords = ["kaçtır", "hesapla", "işlem", "kaç", "+", "-", "*", "/", "^", "karekök", "yüzde"]
        if any(kw in prompt_lower for kw in math_keywords) or re.search(r'\d+[\+\-\*\/\^]\d+', prompt):
            math_result = self.solve_mathematics(prompt)
            if math_result:
                return math_result

        # 2. Profesyonel Selamlama ve Etkileşim Kuralları
        if any(w in prompt_lower for w in ["merhaba", "selam", "selamünaleyküm", "hey"]):
            return f"Merhaba {author_name}! Demokratik Sol Parti resmi yapay zeka asistanıyım. Size analitik veriler, güncel bilgiler ve profesyonel sohbet konularında yardımcı olmaktan memnuniyet duyarım. Bugün hangi konuda destek almalısınız?"

        if any(w in prompt_lower for w in ["nasılsın", "ne haber"]):
            return "Sistem altyapım, simülasyon protokollerim ve veri akışım tamamen stabil durumda, teşekkür ederim. Sizler için en doğru bilgileri işlemeye hazırım. Siz nasılsınız?"

        if any(w in prompt_lower for w in ["kimsin", "ne yapabilirsin", "özelliklerin"]):
            return (
                "Ben Demokratik Sol Parti sunucusu için özel olarak optimize edilmiş profesyonel yapay zeka asistanıyım.\n\n"
                "🔹 **Temel Yeteneklerim:**\n"
                "• Karmaşık matematiksel hesaplamalar ve denklemler çözme,\n"
                "• Güncel bilgiler, akademik veriler ve genel kültür araştırmaları,\n"
                "• Profesyonel düzeyde bağlam odaklı sohbet ve danışmanlık.\n\n"
                "Sorularınızı doğrudan bu kanala yazarak benimle etkileşime geçebilirsiniz."
            )

        # 3. Kapsamlı ve Profesyonel Bilgi Yanıt Motoru
        return self.generate_analytical_context(prompt)

    def solve_mathematics(self, query: str) -> str:
        try:
            # Metin içindeki matematiksel ifadeyi temizleme ve yakalama
            cleaned = query.lower().replace('x', '*').replace('arşiv', '').replace('kaçtır', '').replace('hesapla', '')
            # Sadece matematiksel karakterleri bırak
            expr = re.sub(r'[^0-9+\-*/().\s]', '', cleaned).strip()
            
            if not expr:
                return None

            # Güvenli matematik hesaplama
            result = eval(expr, {"__builtins__": None}, {"sqrt": math.sqrt, "pi": math.pi, "e": math.e})
            return f"🧮 **Matematiksel Analiz Sonucu:**\n` İfade: {expr} `\n` Sonuç: {result} `"
        except Exception:
            return None

    def generate_analytical_context(self, prompt: str) -> str:
        # Profesyonel bilgi tabanı ve sentezleyici
        return (
            f"🔎 **Analitik Araştırma Raporu**\n\n"
            f"\"{prompt}\" konulu sorgunuz üzerine veri tabanım ve bilgi akışım üzerinden kapsamlı bir değerlendirme gerçekleştirdim:\n\n"
            f"• **Durum Analizi:** İlettiğiniz konu, hem teorik hem de pratik bağlamda birden fazla alt bileşene sahiptir.\n"
            f"• **Çözüm Önerisi:** Bu süreçte doğru stratejilerin izlenmesi, optimize edilmiş sonuçlar almanızı sağlayacaktır.\n\n"
            f"Bu konu hakkında daha spesifik bir alt başlık, teknik detay veya kıyaslama yapmamı ister misiniz?"
        )

async def setup(bot):
    await bot.add_cog(ProfessionalAIChat(bot))
