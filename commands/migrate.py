import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
import database
import config

TARGET_LOG_CHANNEL_ID = 1537159620374564875
NORS_BOT_ID = 681137419663441933

def is_bot_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)

class MigrateOldLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return (
            text.replace("İ", "i")
            .replace("I", "ı")
            .replace("Ş", "ş")
            .replace("Ğ", "ğ")
            .replace("Ü", "ü")
            .replace("Ö", "ö")
            .replace("Ç", "ç")
            .lower()
            .strip()
        )

    def find_member_by_raw_name(self, members: list, query_name: str):
        if not query_name:
            return None

        # İsmi / işaretine göre bölüp makamsız ana ismi al
        clean_query = self.clean_text(query_name.split("/")[0].replace("@", "").replace(">", "").strip())
        if len(clean_query) < 2:
            return None

        # 1. Birebir tam eşleşme (Display name veya kullanıcı adı)
        for m in members:
            m_display_base = self.clean_text(m.display_name.split("/")[0])
            m_name = self.clean_text(m.name)
            if clean_query == m_display_base or clean_query == m_name:
                return m

        # 2. Ön ek ve kapsama eşleşmesi
        for m in members:
            m_display_base = self.clean_text(m.display_name.split("/")[0])
            if clean_query in m_display_base or m_display_base in clean_query:
                return m

        return None

    @app_commands.command(
        name="eskikayitlaricek", 
        description="Nors botunun eski kayıtlarını yetkili ID'leriyle birlikte tarayarak veritabanına aktarır."
    )
    @app_commands.describe(limit="Taranacak maksimum mesaj sayısı (Varsayılan: 3000)")
    @is_bot_owner()
    async def migrate_logs(self, interaction: discord.Interaction, limit: int = 3000):
        channel = interaction.guild.get_channel(TARGET_LOG_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(f"❌ Hedef kayıt kanalı (`ID: {TARGET_LOG_CHANNEL_ID}`) bulunamadı!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Sunucudaki üyelerin tamamını Discord API'den eksiksiz çek
        members_cache = []
        try:
            async for m in interaction.guild.fetch_members(limit=None):
                members_cache.append(m)
        except Exception:
            members_cache = interaction.guild.members

        # Daha önce yetkilisiz kaydedilen eski kayıtları temizle
        await asyncio.to_thread(database.clear_empty_migrated_registers)

        success_count = 0
        skipped_count = 0
        processed_messages = 0
        staff_found_count = 0

        async for msg in channel.history(limit=limit, oldest_first=True):
            if msg.author.id != NORS_BOT_ID:
                continue

            processed_messages += 1

            # Embed içeriğindeki tüm veriyi (description + title + fields) topla
            full_text = msg.content or ""
            if msg.embeds:
                emb = msg.embeds[0]
                if emb.title:
                    full_text += f"\n{emb.title}"
                if emb.description:
                    full_text += f"\n{emb.description}"
                for f in emb.fields:
                    full_text += f"\n{f.name}\n{f.value}"

            # --------------------------------------------------
            # 1. KAYDEDİLEN ÜYEYİ TESPİT ETME
            # --------------------------------------------------
            all_mentions = re.findall(r'<@!?(\d{17,20})>', full_text)
            target_user_id = None

            if all_mentions:
                target_user_id = int(all_mentions[0])
            elif msg.raw_mentions:
                target_user_id = msg.raw_mentions[0]

            if not target_user_id:
                skipped_count += 1
                continue

            # --------------------------------------------------
            # 2. KAYIT EDEN YETKİLİYİ TESPİT ETME (KESİN MOTOR)
            # --------------------------------------------------
            staff_id = None

            # Yöntem A: 'Kaydı gerçekleştiren yetkili' metninden sonra gelen ID'yi ara
            staff_mention_match = re.search(r'Kayd[ıi]\s*gerçekleştiren\s*yetkili[\s\S]*?<@!?(\d{17,20})>', full_text, re.IGNORECASE)
            if staff_mention_match:
                staff_id = int(staff_mention_match.group(1))

            # Yöntem B: Eğer etiket yoksa ve düz metin yazılmışsa satırdan ismi çek
            if not staff_id:
                staff_name_match = re.search(r'Kayd[ıi]\s*gerçekleştiren\s*yetkili\s*[\r\n]+[|>\s]*@?([^\r\n]+)', full_text, re.IGNORECASE)
                if staff_name_match:
                    raw_name = staff_name_match.group(1)
                    matched_member = self.find_member_by_raw_name(members_cache, raw_name)
                    if matched_member:
                        staff_id = matched_member.id

            # Yöntem C: Metinde 2. bir etiket varsa ve kaydedilen üyeden farklıysa yetkilidir
            if not staff_id and len(all_mentions) > 1:
                potential_id = int(all_mentions[1])
                if potential_id != target_user_id:
                    staff_id = potential_id

            if staff_id:
                staff_found_count += 1

            # --------------------------------------------------
            # 3. İSİM VE MAKAM BİLGİLERİNİ ÇIKARMA
            # --------------------------------------------------
            target_member = next((m for m in members_cache if m.id == target_user_id), None)
            username = str(target_member) if target_member else f"Kullanıcı_{target_user_id}"
            new_nick = target_member.display_name if target_member else username

            parti_name = "Üye (Eski Kayıt)"
            parti_code = "Üye"
            rp_name = "Yok / Sivil"
            rp_code = "Yok"

            for p_code in config.PARTY_ROLES.keys():
                if p_code in ["Üye", "Yok"]:
                    continue
                if re.search(rf'\b{p_code}\b', full_text):
                    parti_code = p_code
                    parti_name = p_code
                    break

            for r_code in config.RP_ROLES.keys():
                if r_code in ["Yok"]:
                    continue
                if re.search(rf'\b{r_code}\b', full_text):
                    rp_code = r_code
                    rp_name = r_code
                    break

            roles_given = "DSP Üyesi"
            if parti_code != "Üye":
                roles_given += f", {parti_code}"
            if rp_code != "Yok":
                roles_given += f", {rp_code}"

            timestamp = msg.created_at

            # --------------------------------------------------
            # 4. VERİTABANINA AKTARMA
            # --------------------------------------------------
            inserted = await asyncio.to_thread(
                database.add_migrated_register,
                user_id=target_user_id,
                username=username,
                new_nick=new_nick,
                parti_name=parti_name,
                parti_code=parti_code,
                rp_name=rp_name,
                rp_code=rp_code,
                roles_given=roles_given,
                staff_id=staff_id,
                timestamp=timestamp
            )

            if inserted:
                success_count += 1
            else:
                skipped_count += 1

        embed_result = discord.Embed(
            title="📥 Eski Kayıt Aktarımı Tamamlandı",
            color=config.COLOR_HEX
        )
        embed_result.add_field(name="🔍 Taranan Mesaj", value=f"`{processed_messages}`", inline=True)
        embed_result.add_field(name="✅ Eklenen / Güncellenen", value=f"`{success_count}`", inline=True)
        embed_result.add_field(name="🛡️ Yetkilisi Eşleşen", value=f"`{staff_found_count}`", inline=True)
        embed_result.add_field(name="⚠️ Yetkilisi Bulunamayan", value=f"`{processed_messages - staff_found_count}`", inline=True)
        embed_result.set_footer(text="Veriler /kayıttop, /sicil ve /kayıtdışaaktar sistemine başarıyla işlendi.")

        await interaction.followup.send(embed=embed_result, ephemeral=True)

    @migrate_logs.error
    async def migrate_logs_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Bu komutu yalnızca bot sahibi kullanabilir.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Bu komutu yalnızca bot sahibi kullanabilir.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MigrateOldLogs(bot))
