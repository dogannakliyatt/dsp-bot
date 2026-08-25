import discord
from discord.ext import commands
from discord import app_commands

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="katıl", description="Bulunduğunuz ses kanalına katılır.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Önce bir ses kanalına katılmalısınız!", ephemeral=True)
            return

        target_channel = interaction.user.user_voice if hasattr(interaction.user, 'user_voice') else interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await target_channel.connect(reconnect=True, self_deaf=True)
            await interaction.response.send_message(f"🔊 **{target_channel.name}** kanalına katıldım.")
        elif voice_client.channel.id != target_channel.id:
            await voice_client.move_to(target_channel)
            await interaction.response.send_message(f"🔄 **{target_channel.name}** kanalına taşındım.")
        else:
            await interaction.response.send_message("Zaten bulunduğunuz ses kanalındayım.", ephemeral=True)

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır.")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is not None:
            await voice_client.disconnect()
            await interaction.response.send_message("👋 Ses kanalından ayrıldım.")
        else:
            await interaction.response.send_message("❌ Zaten herhangi bir ses kanalında değilim.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
