import discord
from discord import app_commands
from discord.ext import commands
import config
import database
import datetime

# Rol ID: Oylama bitince kanalı görmesi engellenecek rol
TARGET_ROLE_ID = 1537153933305315328

# --- OY VERME VE ONAY VIEW BİLEŞENLERİ ---

class OyOnayView(discord.ui.View):
    def __init__(self, poll_id, candidate_id, candidate_name, poll_title):
        super().__init__(timeout=60)
        self.poll_id = poll_id
        self.candidate_id = candidate_id
        self.candidate_name = candidate_name
        self.poll_title = poll_title

    @discord.ui.button(label="Evet, Oy Ver", style=discord.ButtonStyle.green, custom_id="btn_evet_oy")
    async def evet_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if database.has_voted(self.poll_id, interaction.user.id):
            return await interaction.response.send_message("❌ Zaten bu oylamada oy kullandınız! Oyunuz değiştirilemez.", ephemeral=True)

        success = database.cast_vote(self.poll_id, interaction.user.id, self.candidate_id)
        if success:
            await interaction.response.edit_message(content=f"✅ Oy verme işleminiz başarıyla kaydedildi! Tercihiniz: **{self.candidate_name}**", view=None)
            
            # Log Kanalına Bildirim Gönderme
            log_channel = interaction.guild.get_channel(config.POLL_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🗳️ Yeni Oy Kullanıldı",
                    color=config.COLOR_HEX,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                log_embed.add_field(name="Oy Veren Kullanıcı", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
                log_embed.add_field(name="Oylama Başlığı", value=self.poll_title, inline=False)
                log_embed.add_field(name="Verilen Oy (Aday)", value=f"**{self.candidate_name}**", inline=False)
                await log_channel.send(embed=log_embed)
        else:
            await interaction.response.edit_message(content="❌ Oy kaydı sırasında bir hata oluştu.", view=None)

    @discord.ui.button(label="Hayır, İptal Et", style=discord.ButtonStyle.red, custom_id="btn_hayir_oy")
    async def hayir_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Onay mesajını doğrudan düzenler ve butonları kaldırır
        await interaction.response.edit_message(content="Oy verme işlemi iptal edildi.", view=None)


class AdaySelect(discord.ui.Select):
    def __init__(self, poll_id, candidates, poll_title):
        options = [
            discord.SelectOption(label=c[1], value=str(c[0]), description=f"{c[1]} için oy ver")
            for c in candidates
        ]
        super().__init__(placeholder="Oy vermek istediğiniz adayı seçin...", min_values=1, max_values=1, options=options)
        self.poll_id = poll_id
        self.poll_title = poll_title

    async def callback(self, interaction: discord.Interaction):
        if database.has_voted(self.poll_id, interaction.user.id):
            return await interaction.response.send_message("❌ Daha önce bu oylamada oy kullandınız. Tekrar oy kullanamazsınız!", ephemeral=True)

        selected_candidate_id = int(self.values[0])
        candidates = database.get_candidates(self.poll_id)
        candidate_name = next((c[1] for c in candidates if c[0] == selected_candidate_id), "Bilinmeyen Aday")

        # Seçim yapıldıktan sonra ana menüdeki seçimi sıfırlamak için View'ı yeniden güncelliyoruz
        reset_view = OylamaView(self.poll_id, self.poll_title)
        await interaction.response.edit_message(view=reset_view)

        # Kullanıcıya onay penceresini gizli (ephemeral) olarak gönderiyoruz
        view = OyOnayView(self.poll_id, selected_candidate_id, candidate_name, self.poll_title)
        await interaction.followup.send(
            content=f"**{candidate_name}** isimli adaya oy vermek istediğinize emin misiniz?",
            view=view,
            ephemeral=True
        )


class OylamaView(discord.ui.View):
    def __init__(self, poll_id, poll_title):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.poll_title = poll_title
        candidates = database.get_candidates(poll_id)
        if candidates:
            self.add_item(AdaySelect(poll_id, candidates, poll_title))


class İptalOnayView(discord.ui.View):
    def __init__(self, poll_id, poll_title):
        super().__init__(timeout=60)
        self.poll_id = poll_id
        self.poll_title = poll_title

    @discord.ui.button(label="Evet, İptal Et", style=discord.ButtonStyle.green)
    async def evet_iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        poll = database.get_poll_by_id(self.poll_id)
        if poll and poll[2] and poll[3]:
            try:
                ch = interaction.guild.get_channel(poll[2])
                if ch:
                    msg = await ch.fetch_message(poll[3])
                    await msg.delete()
            except:
                pass
        
        database.delete_poll(self.poll_id)
        await interaction.response.edit_message(content=f"✅ **{self.poll_title}** isimli oylama tamamen iptal edildi ve silindi.", view=None)

    @discord.ui.button(label="Hayır, Vazgeç", style=discord.ButtonStyle.red)
    async def hayir_iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="İptal işlemi vazgeçildi.", view=None)


# --- KOMUT SINIFI ---

class PollCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def active_poll_autocomplete(self, interaction: discord.Interaction, current: str):
        polls = database.get_active_polls()
        return [
            app_commands.Choice(name=p[1], value=str(p[0]))
            for p in polls if current.lower() in p[1].lower()
        ][:25]

    @app_commands.command(name="oylamabaşlat", description="Yeni bir oylama başlatır.")
    @app_commands.describe(baslik="Oylama başlığı / konusu", kanal="Oylama panelinin gönderileceği kanal")
    async def oylama_baslat(self, interaction: discord.Interaction, baslik: str, kanal: discord.TextChannel):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        poll_id = database.add_poll(baslik, kanal.id)

        embed = discord.Embed(
            title=f"🗳️ {baslik}",
            description="Aşağıdaki açılır menüden oy vermek istediğiniz adayı seçebilirsiniz.\n\n*Adaylar eklendikçe menü güncellenecektir.*",
            color=config.COLOR_HEX
        )
        embed.set_footer(text="Her kullanıcının 1 oy hakkı vardır ve kullanılan oylar değiştirilemez.")

        view = OylamaView(poll_id, baslik)
        msg = await kanal.send(embed=embed, view=view)
        database.set_poll_message_id(poll_id, msg.id)

        await interaction.response.send_message(f"✅ Oylama başarıyla {kanal.mention} kanalında başlatıldı! Aday eklemek için `/adayekle` komutunu kullanabilirsiniz.", ephemeral=True)

    @app_commands.command(name="adayekle", description="Aktif bir oylamaya aday ekler.")
    @app_commands.describe(oylama="Aday eklenecek oylama", aday_ismi="Eklenecek adayın adı")
    @app_commands.autocomplete(oylama=active_poll_autocomplete)
    async def aday_ekle(self, interaction: discord.Interaction, oylama: str, aday_ismi: str):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        poll_id = int(oylama)
        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        database.add_candidate(poll_id, aday_ismi)

        channel = interaction.guild.get_channel(poll[2])
        if channel and poll[3]:
            try:
                msg = await channel.fetch_message(poll[3])
                candidates = database.get_candidates(poll_id)
                
                embed = discord.Embed(
                    title=f"🗳️ {poll[1]}",
                    description="Aşağıdaki açılır menüden oy vermek istediğiniz adayı seçip oyunuzu kullanabilirsiniz.",
                    color=config.COLOR_HEX
                )
                cand_list = "\n".join([f"• **{c[1]}**" for c in candidates])
                embed.add_field(name="Mevcut Adaylar", value=cand_list, inline=False)
                embed.set_footer(text="Her kullanıcının 1 oy hakkı vardır ve kullanılan oylar değiştirilemez.")

                view = OylamaView(poll_id, poll[1])
                await msg.edit(embed=embed, view=view)
            except Exception as e:
                print(f"Mesaj güncelleme hatası: {e}")

        await interaction.response.send_message(f"✅ **{aday_ismi}** adayı **{poll[1]}** oylamasına başarıyla eklendi!", ephemeral=True)

    @app_commands.command(name="oylamabitir", description="Oylamayı sonlandırır, log kanalına sonuçları iletir ve kanalı kapatır.")
    @app_commands.describe(oylama="Sonlandırılacak oylama")
    @app_commands.autocomplete(oylama=active_poll_autocomplete)
    async def oylama_bitir(self, interaction: discord.Interaction, oylama: str):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        poll_id = int(oylama)
        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        candidates = database.get_candidates(poll_id)
        database.close_poll(poll_id)

        total_votes = sum(c[2] for c in candidates)

        res_embed = discord.Embed(
            title=f"📊 OYLAMA SONUÇLARI: {poll[1]}",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        res_embed.add_field(name="Toplam Kullanılan Geçerli Oy", value=f"**{total_votes}**", inline=False)

        if candidates:
            sorted_cand = sorted(candidates, key=lambda x: x[2], reverse=True)
            result_text = ""
            for c in sorted_cand:
                pct = (c[2] / total_votes * 100) if total_votes > 0 else 0
                result_text += f"• **{c[1]}:** {c[2]} Oy (%{pct:.1f})\n"
            res_embed.add_field(name="Aday Oy Dağılımı", value=result_text, inline=False)
        else:
            res_embed.add_field(name="Aday Oy Dağılımı", value="Hiç aday yoktu.", inline=False)

        channel = interaction.guild.get_channel(poll[2])
        if channel:
            if poll[3]:
                try:
                    msg = await channel.fetch_message(poll[3])
                    ended_embed = discord.Embed(
                        title=f"🔒 OYLAMA SONLANDI: {poll[1]}",
                        description="Bu oylama süresi dolduğu için erişime kapatılmıştır.",
                        color=discord.Color.red()
                    )
                    await msg.edit(embed=ended_embed, view=None)
                except Exception as e:
                    print(f"Mesaj düzenleme hatası: {e}")

            target_role = interaction.guild.get_role(TARGET_ROLE_ID)
            if target_role:
                try:
                    await channel.set_permissions(target_role, view_channel=False)
                except Exception as e:
                    print(f"Kanal izinleri güncellenirken hata oluştu: {e}")

        log_channel = interaction.guild.get_channel(config.POLL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=res_embed)

        await interaction.response.send_message(f"✅ **{poll[1]}** oylaması başarıyla sonlandırıldı. Sonuçlar log kanalına gönderildi ve ilgili rol için kanal erişimi kapatıldı.", ephemeral=True)

    @app_commands.command(name="oylamaiptal", description="Oylamayı sonuçlandırmadan siler.")
    @app_commands.describe(oylama="İptal edilecek oylama")
    @app_commands.autocomplete(oylama=active_poll_autocomplete)
    async def oylama_iptal(self, interaction: discord.Interaction, oylama: str):
        if not any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        poll_id = int(oylama)
        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        view = İptalOnayView(poll_id, poll[1])
        await interaction.response.send_message(
            content=f"⚠️ **{poll[1]}** isimli oylamayı silmek istediğinize emin misiniz?",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(PollCommands(bot))
