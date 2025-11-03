from pyrogram import filters

def register_clean_handler(bot):
    @bot.on_message(filters.command("clean") & filters.private)
    async def clean_handler(client, message):
        await message.reply_text("🧹 Clean command working!")
