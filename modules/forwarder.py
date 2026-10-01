```python
# This Module is a part of MoonUserbot and is used here for example
import time
import os

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserAlreadyParticipant, ChatForwardsRestricted

from utils.misc import modules_help, prefix
from utils.scripts import progress, format_exc

@Client.on_message(filters.command("rdl", prefix) & filters.me)
async def dl(client: Client, message: Message):
    # Extract command arguments
    args = message.command[1:]

    # Check if the required arguments are provided
    if len(args) < 2:
        await message.edit_text(
            "Kindly use `.rdl channel_link message_id [number_of_messages]`"
        )
        return

    chat_id = message.chat.id
    c_time = time.time()
    ch_gp_link = args[0]
    selected_id = int(args[1])
    num_messages = int(args[2]) if len(args) > 2 else 1

    try:
        # Join the chat if not already a participant
        await client.join_chat(ch_gp_link)
    except UserAlreadyParticipant:
        pass
    except Exception as e:
        await message.edit_text(format_exc(e))
        return

    try:
        # Get the chat object
        chat = await client.get_chat(ch_gp_link)
        from_chat = chat.id

        # Download and re-upload the specified number of messages
        for _ in range(num_messages):
            ms = await message.edit_text(f"Working on message {selected_id}...")
            selected_message = await client.get_messages(from_chat, selected_id)
            file_text = selected_message.caption

            try:
                # Check for and download the thumbnail from the original message
                thumb_path = None
                try:
                    if getattr(selected_message, "video", None) and selected_message.video.thumbs:
                        thumb_path = await client.download_media(selected_message.video.thumbs[0].file_id)
                    elif getattr(selected_message, "document", None) and selected_message.document.thumbs:
                        thumb_path = await client.download_media(selected_message.document.thumbs[0].file_id)
                except Exception:
                    pass

                # Try to download the media
                file = await client.download_media(
                    selected_message,
                    progress=progress,
                    progress_args=(ms, c_time, f"`Trying to download...`"),
                )
                
                # Directly check if Telegram identifies the original message as a video
                is_video = getattr(selected_message, "video", None) is not None
                
                if is_video:
                    # Force .mp4 extension locally so Pyrogram API doesn't mistake it for a document during upload
                    if not str(file).lower().endswith((".mp4", ".mkv", ".webm", ".avi", ".mov")):
                        new_file = f"{file}.mp4"
                        os.rename(file, new_file)
                        file = new_file

                    video_kwargs = {
                        "caption": file_text,
                        "progress": progress,
                        "progress_args": (ms, c_time, f"`Uploading Video...`")
                    }
                    
                    # Pass the thumbnail and original video dimensions
                    if thumb_path:
                        video_kwargs["thumb"] = thumb_path
                    if selected_message.video.width:
                        video_kwargs["width"] = selected_message.video.width
                    if selected_message.video.height:
                        video_kwargs["height"] = selected_message.video.height
                    if selected_message.video.duration:
                        video_kwargs["duration"] = selected_message.video.duration

                    await client.send_video(
                        chat_id,
                        file,
                        **video_kwargs
                    )
                else:
                    doc_kwargs = {
                        "caption": file_text,
                        "progress": progress,
                        "progress_args": (ms, c_time, f"`Uploading Document...`")
                    }
                    if thumb_path:
                        doc_kwargs["thumb"] = thumb_path

                    await client.send_document(
                        chat_id,
                        file,
                        **doc_kwargs
                    )
                
                # Cleanup files to save space
                if os.path.exists(file):
                    os.remove(file)
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    
            except ValueError:
                # If downloading is restricted or media is missing, try to copy the message
                await client.copy_message(chat_id, from_chat, selected_id)
            except ChatForwardsRestricted:
                # If forward restricted is caught during copy fallback
                pass

            selected_id += 1

        await ms.delete()
    except Exception as e:
        await message.edit_text(format_exc(e))

modules_help["rdl"] = {
    "rdl channel_link message_id [number_of_messages]": "download restricted content. Note that number_of_messages is optional if you only want a single message to be downloaded, then don't provide it",
}
```