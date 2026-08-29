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

    def find_member_by_name(self, guild: discord.Guild, query_name: str):
        if not query_name:
            return None
        
        query_clean = query_name.strip().lower()
        if len(query_clean) < 2:
            return None

        # 1. Birebir Tam Eşleşme (Makamlar hariç ana isim veya kullanıcı adı)
        for member in guild.members:
            base_display = member.display_name.split("/")[0].strip().lower()
            if base_display == query_clean or member.name.lower() == query_clean:
                return member

        # 2. Ön Eşleşme (İsimle başlayanlar)
        for member in guild.members:
            base_display = member.display_name.split("/")[0].strip().lower()
            if base_display.startswith(query_clean) or member.name.lower().startswith(query_clean):
                return member

        # Uyuşma bulunamazsa zorlama yapmadan None döner
        return None

    @app_commands.command(
        name="eskikayitlaricek", 
        description="Nors botunun eski kayıtlarını tarayarak yetkili bilgileriyle veritabanına aktarır."
    )
    @app_commands.describe(limit="Taranacak maksimum mesaj sayısı (Varsayılan: 3000)")
    @is_bot_owner()
    async def migrate_logs(self, interaction: discord.Interaction, limit: int = 3000):
        channel = interaction.guild.get_channel(TARGET_LOG_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(f"❌ Hedef kayıt kanalı (`ID: {TARGET_LOG_CHANNEL_ID}`) bulunamadı!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if not interaction.guild.chunked:
            try:
                await interaction.guild.chunk()
            except Exception:
                pass

        # Yetkilisiz girilmiş eski kayıtları temizle
        await asyncio.to_thread(database.clear_empty_migrated_registers)

        success_count = 0
        skipped_count = 0
        processed_messages = 0
        staff_found_count = 0

        async for msg in channel.history(limit=limit, oldest_first=True):
            if msg.author.id != NORS_BOT_ID:
                continue

            processed_messages += 1
            embed = msg.embeds[0] if msg.embeds else None
            embed_desc = embed.description if embed and embed.description else ""
            full_text = f"{msg.content}\n{embed_desc}"

            # 1. Kaydedilen Üyeyi Bulma
            target_user_id = None
            target_match = re.search(r'<@!?(\d{17,20})>', full_text)
            if target_match:
                target_user_id = int(target_match.group(1))
            elif msg.raw_mentions:
                target_user_id = msg.raw_mentions[0]

            if not target_user_id:
                skipped_count += 1
                continue

            # 2. Kayıt Eden Yetkiliyi Bulma
            staff_id = None

            # Metin içerisinde etiket var mı kontrolü
            staff_mention_match = re.search(r'Kayd[ıi]\s*gerçekleştiren\s*yetkili[^\d<]*<@!?(\d{17,20})>', full_text, re.IGNORECASE)
            
            # Metin içerisinde düz isim var mı kontrolü (@İsim / Makam)
            staff_section_match = re.search(
                r'Kayd[ıi]\s*gerçekleştiren\s*yetkili\s*[\r\n]+[|>\s]*@?([^\r\n/]+)',
                full_text,
                re.IGNORECASE
            )

            if staff_mention_match:
                staff_id = int(staff_mention_match.group(1))
            elif staff_section_match:
                raw_staff_name = staff_section_match.group(1).replace("@", "").strip()
                matched_member = self.find_member_by_name(interaction.guild, raw_staff_name)
                if matched_member:
                    staff_id = matched_member.id
                else:
                    staff_id = None
            elif len(msg.raw_mentions) > 1 and msg.raw_mentions[1] != target_user_id:
                staff_id = msg.raw_mentions[1]
            else:
                staff_id = None

            if staff_id:
                staff_found_count += 1

            # 3. İsim ve Rol Detayları
            target_member = interaction.guild.get_member(target_user_id)
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

            # 4. Veritabanına Ekleme
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
