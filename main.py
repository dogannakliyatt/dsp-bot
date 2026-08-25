@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Otomatik Selamlama
    if message.channel.id == config.GREETING_CHANNEL_ID:
        triggers = ["SA", "sa", "Sa", "sA", "selamunaleyküm", "Selamunaleyküm", 
                    "selamınaleyküm", "Selamınaleyküm", "Merhaba", "Selam", 
                    "selam", "selamm", "Selamm", "mrb", "MRB", "Mrb"]
        if message.content.strip() in triggers:
            await message.channel.send(f"Aleykümselam, hoş geldin sefalar getirdin. ☺️🥰☺️ {message.author.mention}")

    await bot.process_commands(message)
