import os
import time
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from utils.misc import modules_help, prefix

# ----------------- REAL-TIME PROGRESS BAR -----------------
async def progress_bar(current, total, action_text, status_msg, last_edit_time):
    now = time.time()
    # Har 3 second me update karega (Telegram limit se bachne ke liye)
    if now - last_edit_time[0] > 3 or current == total:
        try:
            percent = round(current * 100 / total, 1) if total > 0 else 0
            curr_mb = round(current / (1024 * 1024), 2)
            total_mb = round(total / (1024 * 1024), 2)
            
            # Progress bar visualization (e.g., [█████░░░░░])
            filled = int(percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            text = (
                f"⚡ <b>{action_text}</b>\n\n"
                f"📊 <b>Progress:</b> [{bar}] {percent}%\n"
                f"💾 <b>Size:</b> <code>{curr_mb}MB / {total_mb}MB</code>"
            )
            await status_msg.edit(text, parse_mode=enums.ParseMode.HTML)
            last_edit_time[0] = now
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
# ----------------------------------------------------------

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
        parts = raw_chat.split("/")
        if len(parts) >= 5:
            chat_id = int(f"-100{parts[4]}") 
        if len(parts) >= 6 and parts[5].isdigit():
            start_msg_id = int(parts[5])
            
    elif raw_chat.startswith("https://t.me/"):
        parts = raw_chat.split("/")
        if len(parts) >= 4:
            chat_id = parts[3]
        if len(parts) >= 5 and parts[4].isdigit():
            start_msg_id = int(parts[4])
            
    elif str(raw_chat).lstrip("-").isdigit():
        chat_id = int(raw_chat)

    status_msg = await message.edit(
        f"⏳ <b>Fetching messages from source...</b>", 
        parse_mode=enums.ParseMode.HTML
    )

    try:
        messages = []
        if start_msg_id:
            msg_ids = list(range(start_msg_id, start_msg_id + limit))
            fetched = await client.get_messages(chat_id, msg_ids)
            
            if not isinstance(fetched, list):
                fetched = [fetched]
            messages = [m for m in fetched if m and not m.empty]
        else:
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
        # Update immediately so you know it moved past "Fetching"
        await status_msg.edit(f"🚀 <b>Processing message {i} of {total}...</b>", parse_mode=enums.ParseMode.HTML)

        try:
            # 1. Instant copy try (if it's not strictly restricted)
            await msg.copy(message.chat.id)
            success += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            failed += 1 
            
        except Exception:
            # 2. RESTRICTED BYPASS: Download media and re-upload with captions
            try:
                if msg.media:
                    last_edit = [time.time()]
                    
                    # 📥 DOWNLOADING WITH LIVE PROGRESS
                    file_path = await client.download_media(
                        msg,
                        progress=progress_bar,
                        progress_args=(f"📥 Downloading Media ({i}/{total})", status_msg, last_edit)
                    )
                    
                    kwargs = {}
                    if msg.caption:
                        kwargs["caption"] = msg.caption
                        if hasattr(msg, "caption_entities") and msg.caption_entities:
                            kwargs["caption_entities"] = msg.caption_entities
                        elif hasattr(msg, "entities") and msg.entities:
                            kwargs["caption_entities"] = msg.entities
                    
                    last_edit = [time.time()]
                    upload_text = f"📤 Uploading Media ({i}/{total})"

                    # 📤 UPLOADING WITH LIVE PROGRESS
                    if msg.photo:
                        await client.send_photo(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    elif msg.video:
                        await client.send_video(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    elif msg.document:
                        await client.send_document(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    elif msg.audio:
                        await client.send_audio(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    elif msg.animation:
                        await client.send_animation(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    elif msg.voice:
                        await client.send_voice(message.chat.id, file_path, **kwargs, progress=progress_bar, progress_args=(upload_text, status_msg, last_edit))
                    
                    # File delete and limit protection
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                        await asyncio.sleep(1.5) # Flood protection delay
                
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

    await status_msg.edit(
        f"🎉 <b>Forwarding Completed!</b>\n\n"
        f"📥 <b>Total Processed:</b> {total}\n"
        f"✅ <b>Successfully Sent:</b> {success}\n"
        f"❌ <b>Failed:</b> {failed}",
        parse_mode=enums.ParseMode.HTML
    )

modules_help["forward"] = {
    "forward [chat_id/username/link] [limit]": "Forwards restricted messages (extracts files + captions) starting from a link or chat ID with Live Progress."
}
