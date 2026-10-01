import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import MessageProtected, FloodWait

from utils.misc import modules_help, prefix

@Client.on_message(filters.command("forward", prefix) & filters.me)
async def forward_restricted(client: Client, message: Message):
    args = message.command
    
    # Check if we have both arguments
    if len(args) < 3:
        await message.edit(
            "<b>Usage:</b> <code>.forward {from_chat} {how_many}</code>\n<i>Example: .forward @somechannel 10</i>", 
            parse_mode=enums.ParseMode.HTML
        )
        return

    from_chat = args[1]
    
    try:
        limit = int(args[2])
    except ValueError:
        await message.edit("<b>Error:</b> {how_many} must be a valid number.", parse_mode=enums.ParseMode.HTML)
        return

    # Handle negative numeric chat IDs (Pyrogram needs them as integers)
    if from_chat.lstrip("-").isdigit():
        from_chat = int(from_chat)

    status_msg = await message.edit(
        f"⏳ <b>Fetching {limit} messages from {from_chat}...</b>", 
        parse_mode=enums.ParseMode.HTML
    )

    try:
        messages = []
        # Fetch chat history
        async for msg in client.get_chat_history(from_chat, limit=limit):
            messages.append(msg)
    except Exception as e:
        await status_msg.edit(f"❌ <b>Error fetching chat:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)
        return

    # Reverse the list so we forward the oldest messages first, keeping chronological order
    messages.reverse() 
    
    total = len(messages)
    success = 0
    failed = 0

    for i, msg in enumerate(messages, 1):
        if msg.empty:
            failed += 1
            continue

        try:
            # 1. Try Pyrogram's native copy (instant, works if chat isn't restricted)
            await msg.copy(message.chat.id)
            success += 1
            
        except MessageProtected:
            # 2. Bypass restriction: manually download and re-upload
            try:
                if msg.media:
                    # Download to local storage
                    file_path = await client.download_media(msg)
                    caption = msg.caption.html if msg.caption else ""
                    
                    # Upload based on media type
                    if msg.photo:
                        await client.send_photo(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    elif msg.video:
                        await client.send_video(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    elif msg.document:
                        await client.send_document(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    elif msg.audio:
                        await client.send_audio(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    elif msg.animation:
                        await client.send_animation(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    elif msg.voice:
                        await client.send_voice(message.chat.id, file_path, caption=caption, parse_mode=enums.ParseMode.HTML)
                    
                    # Cleanup file after sending to save storage
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                
                elif msg.text:
                    await client.send_message(message.chat.id, msg.text.html, parse_mode=enums.ParseMode.HTML)
                
                success += 1
                
            except Exception:
                failed += 1
                
        except FloodWait as e:
            # Telegram rate limit. Wait it out, then count as failed so it doesn't crash the loop.
            await asyncio.sleep(e.value)
            failed += 1 
            
        except Exception:
            failed += 1

        # Update stats every 5 messages to avoid Telegram flood limits on message edits
        if i % 5 == 0 or i == total:
            try:
                await status_msg.edit(
                    f"🚀 <b>Forwarding in progress...</b>\n\n"
                    f"📥 <b>Total:</b> {total}\n"
                    f"✅ <b>Success:</b> {success}\n"
                    f"❌ <b>Failed:</b> {failed}",
                    parse_mode=enums.ParseMode.HTML
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                pass

    # Final success message
    await status_msg.edit(
        f"🎉 <b>Forwarding Completed!</b>\n\n"
        f"📥 <b>Total Fetched:</b> {total}\n"
        f"✅ <b>Successfully Sent:</b> {success}\n"
        f"❌ <b>Failed:</b> {failed}",
        parse_mode=enums.ParseMode.HTML
    )

# Add module instructions
modules_help["forward"] = {
    "forward [chat_id/username] [limit]": "Forwards messages (bypasses restricted content) to the current chat with live stats."
}
