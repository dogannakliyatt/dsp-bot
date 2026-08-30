import discord
from discord import app_commands
from discord.ext import commands
import datetime
import config

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="yardım", description="Botta bulunan tüm komutları ve ne işe yaradıklarını gösterir.")
    async def yardim(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Demokratik Sol Parti - Yardım Menüsü",
            description="Aşağıda botumuzda yer alan tüm komutlar ve açıklamaları listelenmiştir. Herkes bu komutları kullanabilir.",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Moderasyon Komutları
        embed.add_field(
            name="🛡️ Moderasyon Komutları",
            value=(
                "`/kilit` — Bulunulan kanalı mesaj yazımına kapatır/açar.\n"
                "`/yasakla` — Kullanıcıyı sunucudan yasaklar.\n"
                "`/yasaklamakaldır` — Kullanıcının yasağını kaldırır.\n"
                "`/sustur` — Kullanıcıyı süreli olarak susturur (timeout).\n"
                "`/susturmakaldır` — Kullanıcının susturmasını kaldırır.\n"
                "`/at` — Kullanıcıyı sunucudan atar.\n"
                "`/mesajsil` veya `d!sil` — Belirtilen miktarda mesajı siler."
            ),
            inline=False
        )

        # Rol ve Kayıt Komutları
        embed.add_field(
            name="📋 Kayıt & Rol Yönetimi",
            value=(
                "`/kayıt` — Kullanıcıyı partiye ve makamlarına kaydeder.\n"
                "`/kayıtsızver` — Kullanıcının rollerini alıp kayıtsıza atar.\n"
                "`/isimdegistir` veya `d!isimdeğistir` — Takma adı günceller.\n"
                "`/rolver` veya `d!rol` — Kullanıcıya tekil rol verir.\n"
                "`/rolal` veya `d!rolal` — Kullanıcıdan tekil rol alır.\n"
                "`/toplurolver` — Hedef role sahip olanlara toplu rol verir.\n"
                "`/toplurolal` — Hedef role sahip olanlardan toplu rol alır.\n"
                "`/ototakmaadesitle` — Üyelerin takma adlarını şablona göre eşitler."
            ),
            inline=False
        )

        # Siyasi & RP Komutları
        embed.add_field(
            name="🏛️ Siyasi & RP Araçları",
            value=(
                "`/resmigazete` — Resmî gazete veya parti bildirisi yayınlar.\n"
                "`/kabine` — T.C. Kabinesini ve makam sahiplerini listeler.\n"
                "`/partidüzeni` — DSP Teşkilat Şemasını listeler.\n"
                "`/meclis` — TBMM Başkanlık Divanı ve grubunu listeler.\n"
                "`/sicil` — Kullanıcının kayıt geçmişini ve sicilini gösterir.\n"
                "`/kayıtdışaaktar` — Tüm kayıtları CSV dosyası olarak aktarır."
            ),
            inline=False
        )

        # Oylama, Çekiliş ve Diğer Komutlar
        embed.add_field(
            name="🎉 Oylama, Çekiliş & Diğer",
            value=(
                "`/oylamabaşlat` — Yeni bir seçim/oylama başlatır.\n"
                "`/adayekle` / `/adaykaldır` — Oylamaya aday ekler/çıkarır.\n"
                "`/oylamabitir` — Oylamayı sonlandırıp sonuçları loglar.\n"
                "`/çekiliş` — Yeni bir çekiliş başlatır.\n"
                "`/çekilişyönet` / `/çekilişiptal` — Çekilişi yönetir/iptal eder.\n"
                "`/kayıttop` — En çok kayıt yapan yetkilileri sıralar.\n"
                "`/ping` — Botun gecikme süresini gösterir.\n"
                "`/mesajyaz` — Embed formatında duyuru mesajı atar.\n"
                "`/ideolojidegistir` / `/pusuladegistir` — Bilgi kanallarını günceller."
            ),
            inline=False
        )

        embed.set_footer(text=f"İsteyen herkes kullanabilir • İsteyen: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
