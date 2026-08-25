        # Kayıt Başarı Mesajı
        embed = discord.Embed(
            title="<:dspkus:1537179044049588284> Kayıt Yapıldı!",
            color=config.COLOR_HEX
        )
        embed.description = (
            f"**• Kayıt Edilen Kullanıcı:** {kullanici.mention}\n"
            f"**• Kayıt Eden Kullanıcı:** {interaction.user.mention}\n"
            f"**• Yeni İsim:** {new_nick}\n"
            f"**• Verilen Roller:** {', '.join(added_role_names)}"
        )
        await interaction.response.send_message(embed=embed)
