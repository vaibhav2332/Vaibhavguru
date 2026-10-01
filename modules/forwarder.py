import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from utils.misc import modules_help, prefix

@Client.on_message(filters.command("forward", prefix) & filters.me)
async def forward_restricted(client: Client, message: Message):
    args = message.command
    
    if len(args) < 3:
        await message.edit(
            "<b>Usage:</b> <code>.forward {chat_id/link} {how_many}</code>\n"
            "<i>Example: .forward https://t.me/c/4394523374/3 2</i>", 
            parse_mode=enums.ParseMode.HTML
        )
        return

    raw_chat = args[1]
    
    try:
        limit = int(args[2])
    except ValueError:
        await message.edit("<b>Error:</b> {how_many} must be a valid number.", parse_mode=enums.ParseMode.HTML)
        return

    chat_id = raw_chat
    start_msg_id = None

    # --- SMART LINK PARSER ---
    if raw_chat.startswith("https://t.me/c/"):
        # Parses private links like: https://t.me/c/1234567890/3
        parts = raw_chat.split("/")
        if len(parts) >= 5:
            chat_id = int(f"-100{parts[4]}") # Private chats require -100 prefix
        if len(parts) >= 6 and parts[5].isdigit():
            start_msg_id = int(parts[5])
            
    elif raw_chat.startswith("https://t.me/"):
        # Parses public links like: https://t.me/username/3
        parts = raw_chat.split("/")
        if len(parts) >= 4:
            chat_id = parts[3]
        if len(parts) >= 5 and parts[4].isdigit():
            start_msg_id = int(parts[4])
            
    elif str(raw_chat).lstrip("-").isdigit():
        # Parses raw numeric IDs
        chat_id = int(raw_chat)

    status_msg = await message.edit(
        f"⏳ <b>Fetching messages...</b>", 
        parse_mode=enums.ParseMode.HTML
    )

    try:
        messages = []
        if start_msg_id:
            # If a specific message link was given, fetch a range starting from there
            msg_ids = list(range(start_msg_id, start_msg_id + limit))
            fetched = await client.get_messages(chat_id, msg_ids)
            
            if not isinstance(fetched, list):
                fetched = [fetched]
            messages = [m for m in fetched if m and not m.empty]
        else:
            # If just a chat ID/username was given, fetch the latest history
            async for msg in client.get_chat_history(chat_id, limit=limit):
                messages.append(msg)
            messages.reverse()
            
    except Exception as e:
        await status_msg.edit(f"❌ <b>Error fetching chat:</b> <code>{e}</code>", parse_mode=enums.ParseMode.HTML)
        return

    if not messages:
        await status_msg.edit("❌ <b>Could not find any messages. Ensure you are in the channel.</b>", parse_mode=enums.ParseMode.HTML)
        return

    total = len(messages)
    success = 0
    failed = 0

    for i, msg in enumerate(messages, 1):
        try:
            # 1. Try instant Pyrogram copy first
            await msg.copy(message.chat.id)
            success += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            failed += 1 
            
        except Exception:
            # 2. RESTRICTED BYPASS: Download media and re-upload with captions intact
            try:
                if msg.media:
                    # Download file to local storage
                    file_path = await client.download_media(msg)
                    
                    kwargs = {}
                    if msg.caption:
                        kwargs["caption"] = msg.caption
                        # Preserve bold, italic, links, etc.
                        if hasattr(msg, "caption_entities") and msg.caption_entities:
                            kwargs["caption_entities"] = msg.caption_entities
                        elif hasattr(msg, "entities") and msg.entities:
                            kwargs["caption_entities"] = msg.entities
                    
                    # Upload based on media type
                    if msg.photo:
                        await client.send_photo(message.chat.id, file_path, **kwargs)
                    elif msg.video:
                        await client.send_video(message.chat.id, file_path, **kwargs)
                    elif msg.document:
                        await client.send_document(message.chat.id, file_path, **kwargs)
                    elif msg.audio:
                        await client.send_audio(message.chat.id, file_path, **kwargs)
                    elif msg.animation:
                        await client.send_animation(message.chat.id, file_path, **kwargs)
                    elif msg.voice:
                        await client.send_voice(message.chat.id, file_path, **kwargs)
                    
                    # Delete the file immediately after sending to save space
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                
                elif msg.text:
                    kwargs = {}
                    if hasattr(msg, "entities") and msg.entities:
                        kwargs["entities"] = msg.entities
                        
                    await client.send_message(message.chat.id, msg.text, **kwargs)
                
                success += 1
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
                failed += 1
                
            except Exception:
                failed += 1

        # Live stats update
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

    await status_msg.edit(
        f"🎉 <b>Forwarding Completed!</b>\n\n"
        f"📥 <b>Total Fetched:</b> {total}\n"
        f"✅ <b>Successfully Sent:</b> {success}\n"
        f"❌ <b>Failed:</b> {failed}",
        parse_mode=enums.ParseMode.HTML
    )

modules_help["forward"] = {
    "forward [chat_id/username/link] [limit]": "Forwards restricted messages (extracts files + captions) starting from a link or chat ID."
}
