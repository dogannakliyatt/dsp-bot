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

    @app_commands.command(
        name="eskikayitlaricek", 
        description="Nors botunun attığı eski kayıt loglarını tarayarak veritabanına aktarır (Yalnızca Bot Sahibi)."
    )
    @app_commands.describe(limit="Taranacak maksimum mesaj sayısı (Varsayılan: 2000)")
    @is_bot_owner()
    async def migrate_logs(self, interaction: discord.Interaction, limit: int = 2000):
        channel = interaction.guild.get_channel(TARGET_LOG_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(f"❌ Hedef kayıt kanalı (`ID: {TARGET_LOG_CHANNEL_ID}`) bulunamadı!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        success_count = 0
        skipped_count = 0
        processed_messages = 0

        async for msg in channel.history(limit=limit, oldest_first=True):
            if msg.author.id != NORS_BOT_ID:
                continue

            processed_messages += 1
            embed = msg.embeds[0] if msg.embeds else None
            embed_desc = embed.description if embed and embed.description else ""
            full_text = f"{msg.content}\n{embed_desc}"

            # 1. Kaydedilen Kullanıcı ID'si
            target_user_id = None
            if msg.raw_mentions:
                target_user_id = msg.raw_mentions[0]
            else:
                user_match = re.search(r'<@!?(\d{17,20})>', full_text)
                if user_match:
                    target_user_id = int(user_match.group(1))

            if not target_user_id:
                skipped_count += 1
                continue

            # 2. Kayıt Eden Yetkili ID'si
            staff_id = None
            staff_match = re.search(r'Kayd[ıi]\s*gerçekleştiren\s*yetkili[^\d<]*<@!?(\d{17,20})>', full_text, re.IGNORECASE)
            if staff_match:
                staff_id = int(staff_match.group(1))
            elif len(msg.raw_mentions) > 1:
                staff_id = msg.raw_mentions[1]

            # 3. İsim ve Rol Bilgileri
            target_member = interaction.guild.get_member(target_user_id)
            username = str(target_member) if target_member else f"Kullanıcı_{target_user_id}"
            new_nick = target_member.display_name if target_member else username

            # Metindeki olası Parti ve RP makam kodlarını tespit etme
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

            # 4. Veritabanına Yazma
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
            title="📥 Eski Kayıtlar Başarıyla Aktarıldı",
            color=config.COLOR_HEX
        )
        embed_result.add_field(name="🔍 Taranan Nors Mesajı", value=f"`{processed_messages}`", inline=True)
        embed_result.add_field(name="✅ Eklenen Kayıt", value=f"`{success_count}`", inline=True)
        embed_result.add_field(name="⏭️ Atlanan / Zaten Ekli", value=f"`{skipped_count}`", inline=True)
        embed_result.set_footer(text="Veriler /kayıttop, /sicil ve /kayıtdışaaktar sistemine entegre edildi.")

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
