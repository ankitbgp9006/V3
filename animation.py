from typing import Union
from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified
import asyncio

class Style:
    @staticmethod
    def small_caps(text: str) -> str:
        """Convert text to small caps"""
        normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        small_caps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ₀₁₂₃₄₅₆₇₈₉"
        for n, s in zip(normal, small_caps):
            text = text.replace(n, s)
        return text

class BotMessages:
    @staticmethod
    async def show_progress(message: Message, text: str = "ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ") -> None:
        """Show quick progress bar animation"""
        progress = ["⬜⬜⬜⬜⬜", "⬛⬜⬜⬜⬜", "⬛⬛⬜⬜⬜", "⬛⬛⬛⬜⬜", "⬛⬛⬛⬛⬜", "⬛⬛⬛⬛⬛"]
        for bar in progress:
            try:
                await message.edit(f"{text}\n{bar}")
                await asyncio.sleep(0.5)  # Increased delay to avoid rate limits
            except FloodWait as e:
                await asyncio.sleep(e.value)  # Use proper FloodWait handling
            except MessageNotModified:
                continue  # Skip if message is the same
            except Exception as e:
                print(f"Error updating progress: {str(e)}")
                break

    @staticmethod
    def get_welcome_message(user_name: str, days_left: Union[int, str], expiry_date: str) -> str:
        """Get simple welcome message with small caps"""
        return (
            f"╭─❰ {Style.small_caps('ᴡᴇʟᴄᴏᴍᴇ')} ❱\n"
            f"├• {Style.small_caps('Hello')} {user_name}\n"
            f"├• {Style.small_caps('Premium User')}\n"
            f"├• ᴅᴀʏs ʟᴇғᴛ: {days_left}\n"
            f"├• ᴠᴀʟɪᴅ ᴛɪʟʟ: {expiry_date}\n"
            f"╰─❰ {Style.small_caps('Premium Bot')} ❱\n\n"
            f"┏━━━━━━━━━━━━━━┓\n"
            f"┣ ⚡ ғᴇᴀᴛᴜʀᴇs:\n"
            f"┣ • 📚 ᴀᴘᴘx + ᴇɴᴄʀʏᴘᴛᴇᴅ + ɴᴏɴ ᴅʀᴍ\n"
            f"┣ • 🎓 ᴄʟᴀssᴘʟᴜs ᴅʀᴍ + ɴᴏɴ ᴅʀᴍ\n"
            f"┣ • 🧑‍🏫 ᴘʜʏsɪᴄsᴡᴀʟʟᴀʜ\n"
            f"┣ • 📚 ᴄᴀʀᴇᴇʀᴡɪʟʟ + ᴘᴅғ\n"
            f"┗━━━━━━━━━━━━━━┛"
        )

    @staticmethod
    def get_unauthorized_message(user_name: str) -> str:
        """Get unauthorized message with small caps"""
        return (
            f"╭─❰ {Style.small_caps('Access Denied')} ❱\n"
            f"├• {Style.small_caps('Hello')} {user_name}\n"
            f"├• {Style.small_caps('This is a Premium Bot')}\n"
            f"╰─❰ {Style.small_caps('Get Access')} ❱\n\n"
            f"┏━━━━━━━━━━━━━━┓\n"
            f"┣ ⚡ ғᴇᴀᴛᴜʀᴇs:\n"
            f"┣ • 📚 ᴀᴘᴘx + ᴇɴᴄʀʏᴘᴛᴇᴅ + ɴᴏɴ ᴅʀᴍ\n"
            f"┣ • 🎓 ᴄʟᴀssᴘʟᴜs ᴅʀᴍ + ɴᴏɴ ᴅʀᴍ\n"
            f"┣ • 🧑‍🏫 ᴘʜʏsɪᴄsᴡᴀʟʟᴀʜ\n"
            f"┣ • 📚 ᴄᴀʀᴇᴇʀᴡɪʟʟ + ᴘᴅғ\n"
            f"┗━━━━━━━━━━━━━━┛"
        ) 