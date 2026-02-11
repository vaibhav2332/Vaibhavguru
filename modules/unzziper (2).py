import os
import shutil
import asyncio
import re
import time
import zipfile
import tarfile
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserIsBlocked, PeerIdInvalid

from utils.misc import modules_help, prefix
from utils.scripts import format_exc

# --- Helper for Progress Callback ---
async def progress_callback(current, total, message, status):
    """Custom progress callback to show animated status for uploads."""
    try:
        percentage = current * 100 / total
        progress_bar = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))
        
        status_text = (
            f"<b>{status}</b>\n"
            f"<code>{progress_bar} {percentage:.2f}%</code>"
        )
        await message.edit_text(status_text)
    except Exception:
        pass

# --- Core Compression Logic ---
async def compress_files(client: Client, message: Message, compression_format: str):
    """Shared logic for zipping and taring files, now aware of groups."""
    
    is_owner = message.from_user.is_self
    target_user = message.from_user
    
    # --- 1. Determine where to send status updates and final files ---
    status_chat_id = message.chat.id if is_owner else target_user.id
    output_chat_id = status_chat_id
    
    # --- 2. Initialize Status Message ---
    status_msg = None
    try:
        # If not the owner, first try to send a message to the user's DM
        if not is_owner:
            await message.reply_text(f"✅ Working on it, {target_user.mention}! I will send the results to your DMs.")
            status_msg = await client.send_message(status_chat_id, "<b>Initializing archiver...</b>")
        else:
            status_msg = await message.edit_text("<b>Initializing archiver...</b>")
    except (UserIsBlocked, PeerIdInvalid):
        return await message.reply_text("<b>Error:</b> I cannot send you a message. Please unblock me or adjust your privacy settings.")
    except Exception as e:
        return await message.edit_text(f"<b>Initialization Error:</b> <code>{e}</code>")

    # --- 3. Gather Files ---
    try:
        if not message.reply_to_message:
            return await status_msg.edit_text("<b>Error:</b> Please reply to a file to mark the end of the sequence.")

        await status_msg.edit_text("<b>🔎 Searching for files to compress...</b>")
        message_ids = range(message.reply_to_message.id, message.id + 1)
        messages_in_range = await client.get_messages(message.chat.id, message_ids)
        files_to_process = [msg for msg in messages_in_range if msg.media]
        
        if not files_to_process:
            return await status_msg.edit_text("<b>Error:</b> No downloadable files found in the selected range.")
        
        await status_msg.edit_text(f"<b>✅ Found {len(files_to_process)} files. Starting download...</b>")
    except Exception as e:
        return await status_msg.edit_text(f"<b>Error gathering files:</b>\n<code>{format_exc(e)}</code>\n\n(I may need admin rights to read message history).")

    # --- 4. Process and Cleanup ---
    temp_dir = f"./downloads/{message.chat.id}_{message.id}/"
    os.makedirs(temp_dir, exist_ok=True)
    downloaded_paths = []
    
    try:
        # Download files
        for i, doc_msg in enumerate(files_to_process):
            filename = getattr(doc_msg, 'document', None) or getattr(doc_msg, 'video', None) or getattr(doc_msg, 'audio', None) or getattr(doc_msg, 'photo', None)
            display_name = filename.file_name if hasattr(filename, 'file_name') else "photo.jpg"
            await status_msg.edit_text(f"<b>Downloading {i + 1}/{len(files_to_process)}...</b>\n<code>{display_name}</code>")
            path = await client.download_media(doc_msg, file_name=os.path.join(temp_dir, display_name))
            downloaded_paths.append(path)

        # Determine archive name and path
        output_filename = f"archive.{compression_format}" if compression_format != 'tar.gz' else "archive.tar.gz"
        if len(message.command) > 1: output_filename = message.command[1]
        archive_path = os.path.join(temp_dir, output_filename)

        # Compress files
        await status_msg.edit_text(f"<b>Compressing {len(downloaded_paths)} files...</b>")
        if compression_format == 'zip':
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in downloaded_paths: zf.write(file, os.path.basename(file))
        elif compression_format == 'tar.gz':
            with tarfile.open(archive_path, "w:gz") as tar:
                for file in downloaded_paths: tar.add(file, arcname=os.path.basename(file))
        
        # Upload the final archive
        await client.send_document(
            output_chat_id, document=archive_path,
            caption=f"<b>Archive Complete!</b>\n<code>{os.path.basename(archive_path)}</code>",
            progress=progress_callback, progress_args=(status_msg, f"Uploading...")
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"<b>An error occurred:</b>\n<code>{format_exc(e)}</code>")
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

# --- Command Handlers ---
@Client.on_message(filters.command("zip", prefix))
async def zip_files_command(client: Client, message: Message):
    await compress_files(client, message, "zip")

@Client.on_message(filters.command("tar", prefix))
async def tar_files_command(client: Client, message: Message):
    await compress_files(client, message, "tar.gz")

@Client.on_message(filters.command("unzip", prefix) & filters.reply)
async def unzip_files_command(client: Client, message: Message):
    is_owner = message.from_user.is_self
    target_user = message.from_user
    
    # --- 1. Determine where to send updates and files ---
    status_chat_id = message.chat.id if is_owner else target_user.id
    output_chat_id = status_chat_id

    # --- 2. Initialize Status Message ---
    status_msg = None
    try:
        if not is_owner:
            await message.reply_text(f"✅ Working on it, {target_user.mention}! I will send the extracted files to your DMs.")
            status_msg = await client.send_message(status_chat_id, "<b>Initializing extraction...</b>")
        else:
            status_msg = await message.edit_text("<b>Initializing extraction...</b>")
    except (UserIsBlocked, PeerIdInvalid):
        return await message.reply_text("<b>Error:</b> I cannot send you a message. Please unblock me or adjust your privacy settings.")
    
    # --- 3. Validate Input ---
    archive_msg = message.reply_to_message
    if not (archive_msg and archive_msg.document):
        return await status_msg.edit_text("<b>Error:</b> Please reply to a supported archive file.")
    file_name = archive_msg.document.file_name
    if not (file_name.endswith((".zip", ".tar", ".tar.gz", ".rar"))):
        return await status_msg.edit_text("<b>Unsupported File!</b>")
    
    # --- 4. Process and Cleanup ---
    temp_dir = f"./downloads/{message.chat.id}_{message.id}/"
    extract_path = os.path.join(temp_dir, "extracted/")
    os.makedirs(extract_path, exist_ok=True)
    
    try:
        await status_msg.edit_text(f"<b>Downloading archive...</b>\n<code>{file_name}</code>")
        archive_path = await client.download_media(archive_msg, file_name=os.path.join(temp_dir, file_name))

        await status_msg.edit_text("<b>Extracting files...</b>")
        if file_name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zf: zf.extractall(extract_path)
        elif file_name.endswith((".tar", ".tar.gz")):
            with tarfile.open(archive_path, 'r:*') as tar: tar.extractall(extract_path)
        elif file_name.endswith(".rar"):
            process = await asyncio.create_subprocess_shell(
                f'unrar x -o+ "{archive_path}" "{extract_path}"',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()
            if process.returncode != 0: raise Exception(f"Unrar failed: {stderr.decode().strip()}")
        
        extracted_files = [os.path.join(root, file) for root, _, files in os.walk(extract_path) for file in files]
        
        if not extracted_files:
            return await status_msg.edit_text("<b>Archive is empty or contains only empty folders.</b>")
            
        await status_msg.edit_text(f"<b>Found {len(extracted_files)} files. Uploading...</b>")

        for i, file in enumerate(extracted_files):
            await client.send_document(
                output_chat_id, document=file, caption=f"<code>{os.path.basename(file)}</code>",
                progress=progress_callback, progress_args=(status_msg, f"Uploading {i+1}/{len(extracted_files)}...")
            )
            await asyncio.sleep(1)
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"<b>An error occurred:</b>\n<code>{format_exc(e)}</code>")
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

# --- Help Section ---
modules_help["archiver"] = {
    "zip [name.zip]": "Reply to the last file in a sequence to compress all files into a zip archive.",
    "tar [name.tar.gz]": "Reply to the last file in a sequence to compress all files into a .tar.gz archive.",
    "unzip": "Reply to a .zip, .tar, .tar.gz, or .rar file to extract its contents.",
}

