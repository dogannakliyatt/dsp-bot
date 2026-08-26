import discord
from discord.ext import commands, tasks
from discord import app_commands
import config

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_voice_checker.start()

    def cog_unload(self):
        self.auto_voice_checker.cancel()

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        return any(role.id == config.AUTHORIZED_ROLE_ID for role in interaction.user.roles)

    # Botun sabit ses kanalında 7/24 kalmasını sağlayan otomatik kontrol
    @tasks.loop(seconds=30)
    async def auto_voice_checker(self):
        await self.bot.wait_until_ready()
        target_channel_id = getattr(config, "VOICE_CHANNEL_ID", None)
        if not target_channel_id:
            return

        channel = self.bot.get_channel(target_channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return

        guild = channel.guild
        voice_client = guild.voice_client

        if voice_client is None or not voice_client.is_connected():
            try:
                await channel.connect(reconnect=True, self_deaf=True)
            except Exception:
                pass
        elif voice_client.channel.id != channel.id:
            try:
                await voice_client.move_to(channel)
            except Exception:
                pass

    @app_commands.command(name="katıl", description="Bulunduğunuz ses kanalına katılır.")
    async def join(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ Önce bir ses kanalına katılmalısınız!", ephemeral=True)

        target_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            if voice_client is None:
                await target_channel.connect(reconnect=True, self_deaf=True)
                await interaction.response.send_message(f"🔊 **{target_channel.name}** kanalına katıldım.")
            elif voice_client.channel.id != target_channel.id:
                await voice_client.move_to(target_channel)
                await interaction.response.send_message(f"🔄 **{target_channel.name}** kanalına taşındım.")
            else:
                await interaction.response.send_message("Zaten bulunduğunuz ses kanalındayım.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Sese bağlanırken hata oluştu: {str(e)}", ephemeral=True)

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır.")
    async def leave(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)

        voice_client = interaction.guild.voice_client

        if voice_client is not None:
            await voice_client.disconnect(force=True)
            await interaction.response.send_message("👋 Ses kanalından ayrıldım.")
        else:
            await interaction.response.send_message("❌ Zaten herhangi bir ses kanalında değilim.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
