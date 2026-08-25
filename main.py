import discord
from discord.ext import commands
import config
import keep_alive
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

initial_extensions = [
    'commands.admin',
    'commands.register',
    'commands.counter',
    'commands.poll'
]

@bot.event
async def on_ready():
    print(f'{bot.user.name} olarak giriş yapıldı!')
    try:
        synced = await bot.tree.sync()
        print(f"Toplam {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronizasyon hatası: {e}")

async def main():
    async with bot:
        for extension in initial_extensions:
            try:
                await bot.load_extension(extension)
                print(f"Yüklendi: {extension}")
            except Exception as e:
                print(f"Yükleme hatası ({extension}): {e}")
        
        keep_alive.keep_alive()
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
