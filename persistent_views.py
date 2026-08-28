import discord
import config
import database
import datetime

# --- OYLAMA / SEÇİM KALICI GÖRÜNÜMLERİ ---

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
                label=str(c["name"])[:100],
                value=str(c["candidate_id"]),
                description=f"{c['name']} için oy ver"[:100]
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
        poll = database.get_poll_by_id(self.poll_id)
        if not poll:
            return await interaction.response.send_message("❌ Oylama bulunamadı.", ephemeral=True)

        target_role_id = poll.get("target_role_id")
        if target_role_id:
            user_has_role = any(r.id == target_role_id for r in interaction.user.roles)
            if not user_has_role and not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
                return await interaction.response.send_message(f"❌ Bu oylamada yalnızca <@&{target_role_id}> rolüne sahip üyeler oy kullanabilir.", ephemeral=True)

        if database.has_voted(self.poll_id, interaction.user.id):
            return await interaction.response.send_message("❌ Daha önce bu oylamada oy kullandınız. Tekrar oy kullanamazsınız!", ephemeral=True)

        selected_candidate_id = int(self.values[0])
        candidates = database.get_candidates(self.poll_id)
        
        candidate_name = "Bilinmeyen Aday"
        for c in candidates:
            if c["candidate_id"] == selected_candidate_id:
                candidate_name = c["name"]
                break

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


# --- ÇEKİLİŞ KALICI GÖRÜNÜMLERİ ---

class GiveawayView(discord.ui.View):
    def __init__(self, guild_id: int = 0):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Çekilişe Katıl", style=discord.ButtonStyle.success, emoji="🎉", custom_id="btn_live_giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_guild_id = self.guild_id or interaction.guild.id
        data = database.get_active_giveaway(target_guild_id)
        if not data:
            return await interaction.response.send_message("❌ Bu çekiliş artık aktif değil.", ephemeral=True)

        user_id = interaction.user.id
        participants = database.get_giveaway_participants(data["giveaway_id"])

        if user_id in participants:
            database.remove_giveaway_participant(data["giveaway_id"], user_id)
            resp_text = "❌ Çekilişten ayrıldınız."
            participants.remove(user_id)
        else:
            database.add_giveaway_participant(data["giveaway_id"], user_id)
            resp_text = "✅ Çekilişe başarıyla katıldınız! Şansınız bol olsun."
            participants.append(user_id)

        button.label = f"Çekilişe Katıl ({len(participants)})"
        
        end_dt = data["end_time"]
        if isinstance(end_dt, str):
            end_dt = datetime.datetime.fromisoformat(end_dt)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)
        end_ts = int(end_dt.timestamp())
        host_user = interaction.guild.get_member(data["host_id"])
        
        embed = discord.Embed(
            title="🎁 ÇEKİLİŞ ETKİNLİĞİ",
            description="Çekilişe katılmak veya katılımınızı geri çekmek için aşağıdaki **Katıl** butonuna tıklayabilirsiniz.\n",
            color=config.COLOR_HEX,
            timestamp=end_dt
        )
        embed.add_field(name="🎉 Ödül", value=f"```fix\n{data['prize']}\n```", inline=False)
        embed.add_field(name="📋 Katılım Şartları", value=f"> {data['requirements']}", inline=False)
        embed.add_field(name="🏆 Kazanan Sayısı", value=f"`{data['winners_count']} Kişi`", inline=True)
        embed.add_field(name="👥 Katılımcılar", value=f"`{len(participants)} Kişi`", inline=True)
        embed.add_field(name="⏳ Bitiş", value=f"<t:{end_ts}:R>", inline=True)
        if host_user:
            embed.set_footer(text=f"Düzenleyen: {host_user.display_name} • Bitiş Zamanı", icon_url=host_user.display_avatar.url)

        try:
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(resp_text, ephemeral=True)
        except Exception:
            pass


# --- OTOMATİK YÜKLEYİCİ FONKSİYON ---

async def register_all_persistent_views(bot: discord.Client):
    """Bot açıldığında veritabanındaki tüm aktif buton ve menüleri tek seferde korumaya alır."""
    # 1. Çekiliş Butonunu Koru
    bot.add_view(GiveawayView())

    # 2. Aktif Oylama Menülerini Koru
    try:
        active_polls = database.get_active_polls()
        for p in active_polls:
            bot.add_view(OylamaView(p["poll_id"], p["title"]))
        print(f"🛡️ [KORUMA] {len(active_polls)} adet oylama ve çekiliş butonu kalıcı hafızaya alındı.")
    except Exception as e:
        print(f"⚠️ [KORUMA HATASI] Oylamalar yüklenemedi: {e}")
