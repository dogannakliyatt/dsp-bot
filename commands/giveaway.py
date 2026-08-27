import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random
import config

class GiveawayView(discord.ui.View):
    def __init__(self, prize: str, winners_count: int, end_time: datetime.datetime, host: discord.Member, requirements: str = None):
        super().__init__(timeout=None)
        self.prize = prize
        self.winners_count = winners_count
        self.end_time = end_time
        self.host = host
        self.requirements = requirements if requirements else "Şart Yok (Herkese Açık)"
        self.participants = set()

    def create_embed(self, is_ended: bool = False, winners_str: str = None) -> discord.Embed:
        end_timestamp = int(self.end_time.timestamp())
        
        if not is_ended:
            embed = discord.Embed(
                title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
                description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
                color=config.COLOR_HEX,
                timestamp=self.end_time
            )
            embed.add_field(name="🎉 Ödül", value=f"```fix\n{self.prize}\n```", inline=False)
            embed.add_field(name="📋 Katılım Şartları", value=f"> {self.requirements}", inline=False)
            embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{self.winners_count} Kişi`", inline=True)
            embed.add_field(name="👥 Katılımcılar", value=f"`{len(self.participants)} Kişi`", inline=True)
            embed.add_field(name="⏳ Bitiş", value=f"<t:{end_timestamp}:R>", inline=True)
            embed.set_footer(text=f"Düzenleyen: {self.host.display_name} • Bitiş Zamanı", icon_url=self.host.display_avatar.url)
        else:
            embed = discord.Embed(
                title="🔒 ÇEKİLİŞ SONUÇLANDI",
                description=f"🎁 **Ödül:** `{self.prize}`\n",
                color=discord.Color.green() if winners_str and "Yetersiz" not in winners_str else discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.add_field(name="🏆 Kazanan(lar)", value=winners_str, inline=False)
            embed.add_field(name="👥 Toplam Katılımcı", value=f"`{len(self.participants)} Kişi`", inline=True)
            embed.add_field(name="📋 Aranan Şartlar", value=f"> {self.requirements}", inline=True)
            embed.set_footer(text=f"Düzenleyen: {self.host.display_name} • Sona Erdi", icon_url=self.host.display_avatar.url)
            
        return embed

    @discord.ui.button(label="Çekilişe Katıl (0)", style=discord.ButtonStyle.success, emoji="🎉", custom_id="btn_modern_giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id in self.participants:
            self.participants.remove(user_id)
            await interaction.response.send_message("❌ Çekilişten ayrıldınız.", ephemeral=True)
        else:
            self.participants.add(user_id)
            await interaction.response.send_message("✅ Çekilişe başarıyla katıldınız! Şansınız bol olsun.", ephemeral=True)

        # Buton üzerindeki ve embed içindeki katılımcı sayısını canlı güncelle
        button.label = f"Çekilişe Katıl ({len(self.participants)})"
        try:
            embed = self.create_embed()
            await interaction.message.edit(embed=embed, view=self)
        except Exception:
            pass


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        staff_id = getattr(config, "STAFF_ROLE_ID", None) or getattr(config, "AUTHORIZED_ROLE_ID", None)
        return any(role.id == staff_id for role in interaction.user.roles)

    async def run_giveaway(self, channel_id: int, message_id: int, view: GiveawayView, duration_seconds: int):
        await asyncio.sleep(duration_seconds)
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            return

        # Butonu devre dışı bırak ve son haline getir
        for item in view.children:
            item.disabled = True
            if isinstance(item, discord.ui.Button):
                item.label = f"Çekiliş Sona Erdi ({len(view.participants)})"
                item.style = discord.ButtonStyle.secondary

        # Katılımcı yoksa
        if not view.participants:
            winners_text = "❌ Yetersiz katılım sebebiyle kazanan belirlenemedi."
            end_embed = view.create_embed(is_ended=True, winners_str=winners_text)
            await message.edit(embed=end_embed, view=view)
            return await channel.send(f"⚠️ **{view.prize}** çekilişine kimse katılmadığı için kazanan seçilemedi.")

        # Kazananları belirle
        winners_count = min(len(view.participants), view.winners_count)
        selected_ids = random.sample(list(view.participants), winners_count)
        winners_mentions = ", ".join([f"<@{uid}>" for uid in selected_ids])

        end_embed = view.create_embed(is_ended=True, winners_str=winners_mentions)
        await message.edit(embed=end_embed, view=view)

        # Kazananlar için özel tebrik kutusu
        celebrate_embed = discord.Embed(
            title="🎊 ÇEKİLİŞ KAZANANLARI BELİRLENDİ!",
            description=(
                f"🎁 **Ödül:** `{view.prize}`\n\n"
                f"🏆 **Tebrikler:** {winners_mentions}\n\n"
                f"📌 *Ödülünüzü teslim almak için lütfen {view.host.mention} ile iletişime geçin.*"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        celebrate_embed.set_footer(text="Demokratik Sol Parti Çekiliş Sistemi")
        await channel.send(content=f"🎉 {winners_mentions}", embed=celebrate_embed)

    @app_commands.command(name="çekiliş", description="Modern butonlu yeni bir çekiliş başlatır.")
    @app_commands.describe(
        ödül="Çekilişte verilecek hediye / ödül / makam",
        kazanan_sayısı="Kazanacak kişi sayısı",
        süre_dakika="Çekiliş süresi (dakika)",
        şartlar="İsteğe bağlı katılım şartları (Boş bırakılırsa 'Şart Yok' yazar)"
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        ödül: str,
        kazanan_sayısı: int,
        süre_dakika: int,
        şartlar: str = None
    ):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz bulunmuyor.", ephemeral=True)

        if kazanan_sayısı < 1 or süre_dakika < 1:
            return await interaction.response.send_message("❌ Kazanan sayısı ve süre en az 1 olmalıdır.", ephemeral=True)

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=süre_dakika)
        view = GiveawayView(
            prize=ödül, 
            winners_count=kazanan_sayısı, 
            end_time=end_time, 
            host=interaction.user, 
            requirements=şartlar
        )
        embed = view.create_embed()

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        # Sayacı arka planda başlat
        asyncio.create_task(
            self.run_giveaway(
                channel_id=interaction.channel_id,
                message_id=message.id,
                view=view,
                duration_seconds=süre_dakika * 60
            )
        )

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
