#  Moon-Userbot - telegram userbot
#  Copyright (C) 2020-present Moon Userbot Organization
#
#  This program is free software: you can redistribute it and/or modify
#  ... [License headers preserved] ...

import asyncio
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# Importing your existing utilities
from utils.misc import modules_help, prefix
from utils.scripts import format_module_help, with_reply

# --- GLOBAL VARIABLES (Algorithm Preserved) ---
current_page = 0
total_pages = 0

# --- CONSTANTS & ASSETS ---
# Invisible character + banner image for a beautiful preview
BANNER_URL = "https://i.ibb.co/vpzvt0X/image.jpg"  # Replace with your Moon Userbot Banner
INVISIBLE_LINK = f"<a href='{BANNER_URL}'>&#8203;</a>"

# --- HELPER FUNCTIONS ---

async def send_reaction(message: Message, emoji: str):
    """Safely attempts to send a reaction to the message."""
    try:
        await message.react(emoji)
    except Exception:
        pass  # Fail silently if reactions are disabled in chat

async def send_page(message, module_list, page, total_page):
    """
    Renders the help page with high-end formatting.
    """
    start_index = (page - 1) * 10
    end_index = start_index + 10
    page_modules = module_list[start_index:end_index]

    # -- HEADER GRAPHICS --
    text = f"{INVISIBLE_LINK}"
    text += f"<b>✨ 𝐌𝐎𝐎𝐍 𝐔𝐒𝐄𝐑𝐁𝐎𝐓 ✘ 𝐇𝐄𝐋𝐏</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<i>❝ 𝐸𝑙𝑒𝑔𝑎𝑛𝑐𝑒 𝑖𝑠 𝑡ℎ𝑒 𝑜𝑛𝑙𝑦 𝑏𝑒𝑎𝑢𝑡𝑦 𝑡ℎ𝑎𝑡 𝑛𝑒𝑣𝑒𝑟 𝑓𝑎𝑑𝑒𝑠. ❞</i>\n\n"

    # -- NAVIGATION INFO --
    text += f"<b>🔮 𝐂𝐨𝐦𝐦𝐚𝐧𝐝 𝐆𝐮𝐢𝐝𝐞:</b> <code>{prefix}help [module]</code>\n"
    text += f"<b>📖 𝐏𝐚𝐠𝐞 𝐍𝐮𝐦𝐛𝐞𝐫:</b> <code>{page}</code> <b>/</b> <code>{total_page}</code>\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # -- MODULE LISTING --
    for module_name in page_modules:
        commands = modules_help[module_name]
        # Visual bullet point and title casing
        text += f"<b>🪐 {module_name.title()}</b>\n"
        
        # Formatting commands in a clean, pill-like structure
        cmd_list = [f"<code>{prefix + cmd_name.split()[0]}</code>" for cmd_name in commands.keys()]
        text += f"   ╰ {' <b>|</b> '.join(cmd_list)}\n"
    
    # -- FOOTER --
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<b>💾 𝐓𝐨𝐭𝐚𝐥 𝐌𝐨𝐝𝐮𝐥𝐞𝐬:</b> {len(modules_help)} | <b>🤖 𝐒𝐲𝐬𝐭𝐞𝐦:</b> <i>Online</i>"
    
    await message.edit(text, disable_web_page_preview=False)


# --- COMMAND HANDLERS ---

@Client.on_message(filters.command(["help", "h"], prefix) & filters.me)
async def help_cmd(_, message: Message):
    # 1. Reaction Magic: Acknowledge receipt
    await send_reaction(message, "⚡")

    if len(message.command) == 1:
        global current_page, total_pages
        
        # 2. Animation: Loading effect
        await message.edit("<b>⚡ <i>Accessing Neural Archives...</i></b>")
        await asyncio.sleep(0.5) # Short delay for the animation to be felt
        
        module_list = list(modules_help.keys())
        total_pages = (len(module_list) + 9) // 10
        current_page = 1
        
        await send_page(message, module_list, current_page, total_pages)
        
    elif message.command[1].lower() in modules_help:
        # Specific module help
        await send_reaction(message, "🔍")
        await message.edit("<b>🔍 <i>Fetching Module Data...</i></b>")
        await asyncio.sleep(0.3)
        await message.edit(format_module_help(message.command[1].lower(), prefix))
        
    else:
        # Deep Search for command
        command_name = message.command[1].lower()
        module_found = False
        
        for module_name, commands in modules_help.items():
            for command in commands.keys():
                if command.split()[0] == command_name:
                    cmd = command.split(maxsplit=1)
                    cmd_desc = commands[command]
                    module_found = True
                    
                    # Aesthetic Command Detail View
                    await send_reaction(message, "💡")
                    detail_text = (
                        f"<b>💠 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐈𝐍𝐒𝐏𝐄𝐂𝐓𝐎𝐑</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"<b>📂 𝐌𝐨𝐝𝐮𝐥𝐞:</b> {module_name.title()} \n"
                        f"   ╰ <i>Try:</i> <code>{prefix}help {module_name}</code>\n\n"
                        f"<b>🕹 𝐓𝐫𝐢𝐠𝐠𝐞𝐫:</b> <code>{prefix}{cmd[0]}</code>\n"
                    )
                    
                    if len(cmd) > 1:
                        detail_text += f"<b>🧩 𝐀𝐫𝐠𝐮𝐦𝐞𝐧𝐭𝐬:</b> <code>{cmd[1]}</code>\n"
                        
                    detail_text += f"━━━━━━━━━━━━━━━━━━━━\n"
                    detail_text += f"<b>📝 𝐃𝐞𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧:</b>\n<i>{cmd_desc}</i>"
                    
                    return await message.edit(detail_text)
                    
        if not module_found:
            await send_reaction(message, "❌")
            await message.edit(
                f"<b>🚫 𝐄𝐫𝐫𝐨𝐫 𝟒𝟎𝟒</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"The command or module <code>{command_name}</code> vanished into the void."
            )


@Client.on_message(filters.command(["pn", "pp", "pq"], prefix) & filters.me)
@with_reply
async def handle_navigation(_, message: Message):
    # Check if replying to the specific Help Menu
    if message.reply_to_message and "𝐌𝐎𝐎𝐍 𝐔𝐒𝐄𝐑𝐁𝐎𝐓" in message.reply_to_message.text:
        global current_page
        
        # 1. Reaction for navigation
        await send_reaction(message, "🖱")
        
        cmd = message.command[0].lower()
        
        if cmd == "pn":
            if current_page < total_pages:
                current_page += 1
                await message.reply_to_message.edit("<b>🌊 <i>Flipping Page...</i></b>") 
                await send_page(
                    message.reply_to_message, # Edit the original help message
                    list(modules_help.keys()), 
                    current_page, 
                    total_pages
                )
                return await message.delete() # Clean up the command
            
            await send_reaction(message, "🚫")
            await message.edit("<b>⚠️ End of Archives.</b>")
            await asyncio.sleep(2)
            await message.delete()

        elif cmd == "pp":
            if current_page > 1:
                current_page -= 1
                await message.reply_to_message.edit("<b>🌊 <i>Flipping Page...</i></b>")
                await send_page(
                    message.reply_to_message, 
                    list(modules_help.keys()), 
                    current_page, 
                    total_pages
                )
                return await message.delete()
                
            await send_reaction(message, "🚫")
            await message.edit("<b>⚠️ This is the Genesis page.</b>")
            await asyncio.sleep(2)
            await message.delete()

        elif cmd == "pq":
            await send_reaction(message, "👋")
            await message.reply_to_message.edit(
                "<b>🔒 <i>Closing Interface...</i></b>"
            )
            await asyncio.sleep(0.5)
            await message.reply_to_message.delete()
            await message.delete()


# --- HELP DICTIONARY REGISTRATION ---
modules_help["help"] = {
    "help [module]": "Open the aesthetic help menu or inspect a specific module.",
    "pn": "Navigate to the **Next** page.",
    "pp": "Navigate to the **Previous** page.",
    "pq": "<b>Quit</b> and close the help menu.",
}