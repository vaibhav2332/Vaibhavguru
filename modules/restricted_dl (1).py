import os
import json
import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatForwardsRestricted

from utils.misc import modules_help, prefix
from utils.scripts import format_exc

# --- Global flags and progress tracking ---
IS_BATCH_RUNNING = False
CANCEL_BATCH = False
PROGRESS_STATUS = {}

# --- THIS FUNCTION REMOVES ALL LINKS AND USERNAMES ---
def clean_caption(caption_text: str) -> str:
    """
    Removes usernames, links, and hyperlinks from a caption string.
    Keeps the text from hyperlinks.
    """
    if not caption_text:
        return ""
    
    # Remove @usernames
    cleaned = re.sub(r'@\w+', '', caption_text)
    # Remove plain http:// and www. URLs
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', cleaned)
    # Remove HTML hyperlinks but keep the text inside them
    cleaned = re.sub(r'<a\s.*?href=.*?>\s*(.*?)\s*</a>', r'\1', cleaned)
    # Remove any other leftover HTML tags for safety
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    return cleaned.strip()

# --- Asynchronous Status Updater Task ---
async def status_updater_task(message: Message, task_id: str):
    """Provides real-time animated updates as a background task."""
    animation_index = 0
    ANIMATION_CHARS = ["|", "/", "-", "\\"]
    
    while task_id in PROGRESS_STATUS and not PROGRESS_STATUS[task_id].get("done", False):
        animation_char = ANIMATION_CHARS[animation_index]
        animation_index = (animation_index + 1) % len(ANIMATION_CHARS)

        status = PROGRESS_STATUS[task_id].get("status", "Initializing...")
        current = PROGRESS_STATUS[task_id].get("current", 0)
        total = PROGRESS_STATUS[task_id].get("total", 1)
        
        text = f"<b>{animation_char} {status}</b>"

        if total > 1:
            percentage = current * 100 / total
            progress_bar = "▰" * int(percentage / 5) + "▱" * (20 - int(percentage / 5))
            text += f"\n<code>{progress_bar}</code>\n<b>Progress:</b> {current / (1024 * 1024):.2f} / {total / (1024 * 1024):.2f} MB"
        try:
            await message.edit_text(text)
        except FloodWait: await asyncio.sleep(5)
        except Exception: break
        await asyncio.sleep(1)

# --- Progress Callback ---
def progress_callback(current, total, task_id, status):
    """Updates the global progress dictionary."""
    if task_id in PROGRESS_STATUS:
        PROGRESS_STATUS[task_id].update({"current": current, "total": total, "status": status})

# --- Main Worker Function (Copy-First Logic with Link Removal) ---
async def process_messages(client: Client, message: Message, chat_id, start_id: int, num_messages: int):
    global IS_BATCH_RUNNING, CANCEL_BATCH, PROGRESS_STATUS
    
    IS_BATCH_RUNNING, CANCEL_BATCH = True, False
    task_id = str(message.chat.id + message.id)
    PROGRESS_STATUS[task_id] = {"status": "Starting..."}
    updater = asyncio.create_task(status_updater_task(message, task_id))
    
    current_id, success_count, processed_count = start_id, 0, 0
    
    while processed_count < num_messages:
        if CANCEL_BATCH:
            PROGRESS_STATUS[task_id]["status"] = "Cancelled!"
            break

        PROGRESS_STATUS[task_id]["status"] = f"Processing message {current_id} ({processed_count + 1}/{num_messages})"
        
        try:
            target_message = await client.get_messages(chat_id, current_id)
            
            if not (target_message.empty or target_message.service):
                # The clean_caption function is called right here
                caption = clean_caption(target_message.caption.html if target_message.caption else "")
                
                # --- STRATEGY 1: ATTEMPT TO COPY THE MESSAGE (FAST & RELIABLE) ---
                try:
                    if target_message.media:
                        await client.copy_message(
                            chat_id=message.chat.id,
                            from_chat_id=chat_id,
                            message_id=target_message.id,
                            caption=caption  # The cleaned caption is used here
                        )
                    elif target_message.text:
                        await client.send_message(message.chat.id, clean_caption(target_message.text.html))
                    
                    success_count += 1
                
                # --- STRATEGY 2: FALLBACK IF COPYING IS RESTRICTED ---
                except ChatForwardsRestricted:
                    PROGRESS_STATUS[task_id]["status"] = f"Copy restricted! Falling back to download for {current_id}..."
                    file_path, thumb_path = None, None
                    try:
                        if target_message.media:
                            dl_progress = lambda c, t: progress_callback(c, t, task_id, f"Downloading {current_id}")
                            file_path = await client.download_media(target_message, progress=dl_progress)
                            
                            media_obj = target_message.video or target_message.document or target_message.photo
                            if hasattr(media_obj, 'thumb') and media_obj.thumb:
                                thumb_path = await client.download_media(media_obj.thumb.file_id)

                            up_progress = lambda c, t: progress_callback(c, t, task_id, f"Uploading {current_id}")
                            # The cleaned caption is also used in this fallback logic
                            if target_message.video or (target_message.document and "video" in getattr(target_message.document, 'mime_type', '')):
                                await client.send_video(message.chat.id, video=file_path, caption=caption, progress=up_progress, thumb=thumb_path)
                            elif target_message.photo:
                                await client.send_photo(message.chat.id, photo=file_path, caption=caption, progress=up_progress)
                            else:
                                await client.send_document(message.chat.id, document=file_path, caption=caption, progress=up_progress)
                            
                            success_count += 1
                    finally:
                        if file_path and os.path.exists(file_path): os.remove(file_path)
                        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

        except FloodWait as fw:
            PROGRESS_STATUS[task_id]["status"] = f"FloodWait... sleeping for {fw.value}s"
            await asyncio.sleep(fw.value + 5)
            continue
        except Exception as e:
            await message.reply_text(f"<b>❗️ Failed on message <code>{current_id}</code>:</b>\n<code>{format_exc(e)}</code>")
        
        current_id += 1
        processed_count += 1
        await asyncio.sleep(1)

    PROGRESS_STATUS[task_id]["done"] = True
    await updater
    final_message = f"<b>✅ Task Completed!</b>\n\n<b>Successfully processed</b> <code>{success_count}</code> of <code>{num_messages}</code> messages."
    if CANCEL_BATCH: final_message = "<b>❗️ Batch operation cancelled by user.</b>"
    await message.edit_text(final_message)
    del PROGRESS_STATUS[task_id]
    IS_BATCH_RUNNING, CANCEL_BATCH = False, False

# --- Command Handlers (No changes) ---
@Client.on_message(filters.command("getp", prefix) & filters.me)
async def download_public(client: Client, message: Message):
    if IS_BATCH_RUNNING: return await message.edit_text("<b>❗️ A batch is already in progress. Use <code>.cancel</code> to stop it first.</b>")
    args = message.command
    if len(args) < 2: return await message.edit_text("<b>Usage:</b> <code>.getp &lt;message_link&gt; [count | end_id]</code>")
    match = re.search(r"https://t.me/([\w.-]+)/(\d+)", args[1])
    if not match: return await message.edit_text("<b>Invalid link format.</b> Use a link like <code>https://t.me/username/1234</code>.")
    chat_id_str, start_id = match.group(1), int(match.group(2))
    num_messages = 1
    if len(args) > 2:
        end_arg = int(args[2])
        num_messages = (end_arg - start_id + 1) if end_arg > start_id else end_arg
    try: await client.get_chat(chat_id_str)
    except Exception: return await message.edit_text(f"<b>❗️ Could not access chat:</b> <code>{chat_id_str}</code>\n\nThis might be a private channel. Try the <code>.getc</code> command.", disable_web_page_preview=True)
    await process_messages(client, message, chat_id_str, start_id, num_messages)

@Client.on_message(filters.command("getc", prefix) & filters.me)
async def download_private(client: Client, message: Message):
    if IS_BATCH_RUNNING: return await message.edit_text("<b>❗️ A batch is already in progress. Use <code>.cancel</code> to stop it first.</b>")
    args = message.command
    if len(args) < 2: return await message.edit_text("<b>Usage:</b> <code>.getc &lt;message_link&gt; [count | end_id]</code>")
    clean_link = args[1].split('?')[0]
    match = re.search(r"https://t.me/c/(\d+)/.*?(\d+)\s*$", clean_link)
    if not match: return await message.edit_text("<b>Invalid <code>/c/</code> link format.</b> Use a link like <code>https://t.me/c/123456/7890</code>.")
    chat_id, start_id = int(f"-100{match.group(1)}"), int(match.group(2))
    num_messages = 1
    if len(args) > 2:
        end_arg = int(args[2])
        num_messages = (end_arg - start_id + 1) if end_arg > start_id else end_arg
    await process_messages(client, message, chat_id, start_id, num_messages)

@Client.on_message(filters.command("cancel", prefix) & filters.me)
async def cancel_download_batch(_, message: Message):
    global CANCEL_BATCH, IS_BATCH_RUNNING
    if not IS_BATCH_RUNNING: return await message.edit_text("<b>No active batch to cancel.</b>")
    CANCEL_BATCH = True
    await message.edit_text("<b>⏳ Cancelling batch operation...</b> Please wait.")

# --- Help Section ---
modules_help["restricted_dl"] = {
    "getp <link> [count|end_id]": "Download from a public channel link or a private channel's invite link.",
    "getc <link> [count|end_id]": "Download from a private channel's '/c/' link. (Supports topic links).",
    "cancel": "Cancel the currently running download batch.",
}