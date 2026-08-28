import discord
from discord import app_commands
from discord.ext import commands
import config
import database
import datetime

TARGET_ROLE_ID = 1537153933305315328

class OyOnayView(discord.ui.View):
    def __init__(self, poll_id: int, candidate_id: int, candidate_name: str, poll_title: str):
        super().__init__(timeout=60)
        self.poll_id = poll_id
        self.candidate_id = candidate_id
        self.candidate_name = candidate_name
        self.poll_title = poll_title

    @discord.ui.button(label="Evet, Oy Ver", style=discord.ButtonStyle.green, custom_id="btn_evet_oy")
    async def evet_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if database.has_voted(self.poll_id, interaction.user.id):
            return await interaction.response.edit_message(content="❌ Zaten bu oylamada oy kullandınız! Oyunuz değiştirilemez.", view=None)

        success = database.cast_vote(self.poll_id, interaction.user.id, self.candidate_id)
        if success:
            await interaction.response.edit_message(content=f"✅ Oy verme işleminiz başarıyla kaydedildi! Tercihiniz: **{self.candidate_name}**", view=None)
            
            log_channel = interaction.guild.get_channel(config.POLL_LOG_CHANNEL_ID) if interaction.guild else None
            if log_channel:
                log_embed = discord.Embed(
                    title="🗳️ Yeni Oy Kullanıldı",
                    color=config.COLOR_HEX,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                log_embed.add_field(name="Oy Veren Kullanıcı", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
                log_embed.add_field(name="Oylama Başlığı", value=self.poll_title, inline=False)
                log_embed.add_field(name="Verilen Oy (Aday)", value=f"**{self.candidate_name}**", inline=False)
                try:
                    await log_channel.send(embed=log_embed)
                except Exception:
                    pass
        else:
            await interaction.response.edit_message(content="❌ Oy kaydı sırasında bir hata oluştu veya zaten oy kullandınız.", view=None)

    @discord.ui.button(label="Hayır, İptal Et", style=discord.ButtonStyle.red, custom_id="btn_hayir_oy")
    async def hayir_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Oy verme işlemi iptal edildi.", view=None)


class AdaySelect(discord.ui.Select):
    def __init__(self, poll_id: int, candidates: list, poll_title: str):
        options = [
            discord.SelectOption(
                label=str(c["name"]),
                value=str(c["candidate_id"]),
                description=f"{c['name']} için oy ver"
            )
            for c in candidates
        ]
        super().__init__(
            placeholder="Oy vermek istediğiniz adayı seçin...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"poll_select_{poll_id}"
        )
        self.poll_id = poll_id
        self.poll_title = poll_title

    async def callback(self, interaction: discord.Interaction):
        if database.has_voted(self.poll_id, interaction.user.id):
            return await interaction.response.send_message("❌ Daha önce bu oylamada oy kullandınız. Tekrar oy kullanamazsınız!", ephemeral=True)

        selected_candidate_id = int(self.values[0])
        candidates = database.get_candidates(self.poll_id)
        
        candidate_name = "Bilinmeyen Aday"
        for c in candidates:
            if c["candidate_id"] == selected_candidate_id:
                candidate_name = c["name"]
                break

        # Onay modal/panelini direkt aç
        view = OyOnayView(self.poll_id, selected_candidate_id, candidate_name, self.poll_title)
        await interaction.response.send_message(
            content=f"**{candidate_name}** isimli adaya oy vermek istediğinize emin misiniz?",
            view=view,
            ephemeral=True
        )


class OylamaView(discord.ui.View):
    def __init__(self, poll_id: int, poll_title: str):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.poll_title = poll_title
        candidates = database.get_candidates(poll_id)
        if candidates:
            self.add_item(AdaySelect(poll_id, candidates, poll_title))


class İptalOnayView(discord.ui.View):
    def __init__(self, poll_id: int, poll_title: str):
        super().__init__(timeout=60)
        self.poll_id = poll_id
        self.poll_title = poll_title

    @discord.ui.button(label="Evet, İptal Et", style=discord.ButtonStyle.green)
    async def evet_iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        poll = database.get_poll_by_id(self.poll_id)
        if poll:
            ch_id = poll["channel_id"]
            msg_id = poll["message_id"]
            if ch_id and msg_id:
                try:
                    ch = interaction.guild.get_channel(ch_id)
                    if ch:
                        msg = await ch.fetch_message(msg_id)
                        await msg.delete()
                except Exception:
                    pass
        
        database.delete_poll(self.poll_id)
        await interaction.response.edit_message(content=f"✅ **{self.poll_title}** isimli oylama tamamen iptal edildi ve silindi.", view=None)

    @discord.ui.button(label="Hayır, Vazgeç", style=discord.ButtonStyle.red)
    async def hayir_iptal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="İptal işlemi vazgeçildi.", view=None)


class PollCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles)

    async def active_poll_autocomplete(self, interaction: discord.Interaction, current: str):
        polls = database.get_active_polls()
        choices = []
        for p in polls:
            p_id = p["poll_id"]
            p_title = p["title"]
            if current.lower() in p_title.lower():
                choices.append(app_commands.Choice(name=p_title[:100], value=str(p_id)))
        return choices[:25]

    @app_commands.command(name="oylamabaşlat", description="Yeni bir oylama başlatır.")
    @app_commands.describe(baslik="Oylama başlığı / konusu", kanal="Oylama panelinin gönderileceği kanal")
    async def oylama_baslat(self, interaction: discord.Interaction, baslik: str, kanal: discord.TextChannel):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

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
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        try:
            poll_id = int(oylama)
        except ValueError:
            return await interaction.response.send_message("❌ Geçersiz oylama seçimi.", ephemeral=True)

        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        p_title = poll["title"]
        p_chid = poll["channel_id"]
        p_msgid = poll["message_id"]

        database.add_candidate(poll_id, aday_ismi)

        channel = interaction.guild.get_channel(p_chid)
        if channel and p_msgid:
            try:
                msg = await channel.fetch_message(p_msgid)
                candidates = database.get_candidates(poll_id)
                
                embed = discord.Embed(
                    title=f"🗳️ {p_title}",
                    description="Aşağıdaki açılır menüden oy vermek istediğiniz adayı seçip oyunuzu kullanabilirsiniz.",
                    color=config.COLOR_HEX
                )
                cand_list = "\n".join([f"• **{c['name']}**" for c in candidates])
                embed.add_field(name="Mevcut Adaylar", value=cand_list, inline=False)
                embed.set_footer(text="Her kullanıcının 1 oy hakkı vardır ve kullanılan oylar değiştirilemez.")

                view = OylamaView(poll_id, p_title)
                await msg.edit(embed=embed, view=view)
            except Exception as e:
                print(f"Mesaj güncelleme hatası: {e}")

        await interaction.response.send_message(f"✅ **{aday_ismi}** adayı **{p_title}** oylamasına başarıyla eklendi!", ephemeral=True)

    @app_commands.command(name="oylamabitir", description="Oylamayı sonlandırır, log kanalına sonuçları iletir ve kanalı kapatır.")
    @app_commands.describe(oylama="Sonlandırılacak oylama")
    @app_commands.autocomplete(oylama=active_poll_autocomplete)
    async def oylama_bitir(self, interaction: discord.Interaction, oylama: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        try:
            poll_id = int(oylama)
        except ValueError:
            return await interaction.response.send_message("❌ Geçersiz oylama seçimi.", ephemeral=True)

        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        p_title = poll["title"]
        p_chid = poll["channel_id"]
        p_msgid = poll["message_id"]

        candidates = database.get_candidates(poll_id)
        database.close_poll(poll_id)

        total_votes = sum(c["votes"] for c in candidates)

        res_embed = discord.Embed(
            title=f"📊 OYLAMA SONUÇLARI: {p_title}",
            color=config.COLOR_HEX,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        res_embed.add_field(name="Toplam Kullanılan Geçerli Oy", value=f"**{total_votes}**", inline=False)

        if candidates:
            sorted_cand = sorted(candidates, key=lambda x: x["votes"], reverse=True)
            result_text = ""
            for c in sorted_cand:
                c_name = c["name"]
                c_votes = c["votes"]
                pct = (c_votes / total_votes * 100) if total_votes > 0 else 0
                result_text += f"• **{c_name}:** {c_votes} Oy (%{pct:.1f})\n"
            res_embed.add_field(name="Aday Oy Dağılımı", value=result_text, inline=False)
        else:
            res_embed.add_field(name="Aday Oy Dağılımı", value="Hiç aday yoktu.", inline=False)

        channel = interaction.guild.get_channel(p_chid)
        if channel:
            if p_msgid:
                try:
                    msg = await channel.fetch_message(p_msgid)
                    ended_embed = discord.Embed(
                        title=f"🔒 OYLAMA SONLANDI: {p_title}",
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
            try:
                await log_channel.send(embed=res_embed)
            except Exception:
                pass

        await interaction.response.send_message(f"✅ **{p_title}** oylaması başarıyla sonlandırıldı. Sonuçlar log kanalına gönderildi ve ilgili rol için kanal erişimi kapatıldı.", ephemeral=True)

    @app_commands.command(name="oylamaiptal", description="Oylamayı sonuçlandırmadan siler.")
    @app_commands.describe(oylama="İptal edilecek oylama")
    @app_commands.autocomplete(oylama=active_poll_autocomplete)
    async def oylama_iptal(self, interaction: discord.Interaction, oylama: str):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        try:
            poll_id = int(oylama)
        except ValueError:
            return await interaction.response.send_message("❌ Geçersiz oylama seçimi.", ephemeral=True)

        poll = database.get_poll_by_id(poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        p_title = poll["title"]
        view = İptalOnayView(poll_id, p_title)
        await interaction.response.send_message(
            content=f"⚠️ **{p_title}** isimli oylamayı silmek istediğinize emin misiniz?",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(PollCommands(bot))
