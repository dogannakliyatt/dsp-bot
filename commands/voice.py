import discord
from discord.ext import commands, tasks
import config
import traceback

class VoiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_check_loop.start()

    def cog_unload(self):
        self.voice_check_loop.cancel()

    @tasks.loop(seconds=15)
    async def voice_check_loop(self):
        await self.bot.wait_until_ready()
        
        target_channel_id = getattr(config, "VOICE_CHANNEL_ID", None)
        if not target_channel_id:
            return

        channel = self.bot.get_channel(target_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            print(f"❌ Ses kanalı bulunamadı! Girilen ID: {target_channel_id}")
            return

        guild = channel.guild
        voice_client = guild.voice_client

        if voice_client is None or not voice_client.is_connected():
            try:
                await channel.connect(reconnect=True, self_deaf=True)
                print(f"✅ Bot ses kanalına başarıyla katıldı: {channel.name}")
            except Exception as e:
                print(f"❌ Ses kanalına bağlanırken HATA oluştu: {e}")
                traceback.print_exc()
        elif voice_client.channel.id != target_channel_id:
            try:
                await voice_client.move_to(channel)
            except Exception as e:
                print(f"❌ Kanal değiştirilirken HATA oluştu: {e}")

    @voice_check_loop.before_loop
    async def before_voice_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VoiceSystem(bot))
