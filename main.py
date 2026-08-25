import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime

import config
import database
from keep_alive import keep_alive

load_dotenv()

class DSPBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        database.init_db()
        await self.load_extension("commands.admin")
        await self.load_extension("commands.register")
        await self.load_extension("commands.counter")
        
        guild = discord.Object(id=config.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = DSPBot()

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    for g in bot.guilds:
        if g.id != config.GUILD_ID:
            print(f"Yetkisiz sunucu tespit edildi: {g.name} ({g.id}). Ayrılınıyor...")
            await g.leave()

@bot.event
async def on_guild_join(guild):
    if guild.id != config.GUILD_ID:
        print(f"Yetkisiz sunucuya eklendi: {guild.name} ({guild.id}). Ayrılınıyor...")
        await guild.leave()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Otomatik Selamlama (Sunucunun BÜTÜN kanallarında çalışır)
    triggers = ["SA", "sa", "Sa", "sA", "selamunaleyküm", "Selamunaleyküm", 
                "selamınaleyküm", "Selamınaleyküm", "Merhaba", "Selam", 
                "selam", "selamm", "Selamm", "mrb", "MRB", "Mrb"]
    if message.content.strip() in triggers:
        await message.channel.send(f"Aleykümselam, hoş geldin sefalar getirdin. ☺️🥰☺️ {message.author.mention}")

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if member.guild.id != config.GUILD_ID:
        return

    # Otomatik Kayıtsız Rolü
    unreg_role = member.guild.get_role(config.UNREGISTERED_ROLE_ID)
    if unreg_role:
        try:
            await member.add_roles(unreg_role)
        except Exception:
            pass

    # Giriş Mesajı
    welcome_ch = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
    if welcome_ch:
        total = member.guild.member_count
        await welcome_ch.send(f"<a:erensigiris:1537179743445712926> {member.mention} Katıldı! {total}")

    # Kayıt Karşılama Mesajı
    reg_ch = member.guild.get_channel(config.REGISTER_CHANNEL_ID)
    if reg_ch:
        total = member.guild.member_count
        created_at = member.created_at
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - created_at

        days = diff.days
        months = days // 30
        years = days // 365
        date_str = created_at.strftime("%d/%m/%Y")

        text = (
            f"<@&{config.AUTHORIZED_ROLE_ID}>,{member.mention} sunucuya giriş yaptı.\n\n"
            f"<:dspkus:1537179044049588284> Yeni Bir Kullanıcı Katıldı, 👋🏻 {member.mention}\n\n"
            f"☺️ Sunucumuza Hoş Geldin!\n\n"
            f"🙂 Seninle Birlikte {total} Kişiyiz.\n\n"
            f"Hesap Oluşturulma Tarihi: {date_str} & {days % 30} Gün {months % 12} Ay {years} Yıl önce"
        )
        await reg_ch.send(text)

@bot.event
async def on_member_remove(member):
    if member.guild.id != config.GUILD_ID:
        return

    welcome_ch = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
    if welcome_ch:
        total = member.guild.member_count
        await welcome_ch.send(f"<a:erensicikis:1537179768641028168> {member.mention} Ayrıldı! {total}")

keep_alive()
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("HATA: DISCORD_TOKEN bulunamadı!")
