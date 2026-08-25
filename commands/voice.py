import discord
from discord.ext import commands, tasks

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_channel_id = 1541892351411101827  # Ses kanalı ID'niz
        self.voice_check_loop.start()

    def cog_unload(self):
        self.voice_check_loop.cancel()

    @tasks.loop(seconds=15)
    async def voice_check_loop(self):
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.voice_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return

        guild = channel.guild
        voice_client = guild.voice_client

        # Eğer bot kanalda DEĞİLSE veya bağlantısı kopmuşsa bağlan
        if voice_client is None or not voice_client.is_connected():
            try:
                await channel.connect(reconnect=True, self_deaf=True)
                print(f"🔊 {channel.name} ses kanalına başarıyla bağlandı.")
            except Exception as e:
                print(f"❌ Ses kanalına bağlanırken hata: {e}")

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
