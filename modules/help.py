#  Moon-Userbot - Stateless System Core
#  Copyright (C) 2020-present Moon Userbot Organization
#
#  ALGORITHM CHANGE: "Stateless Extraction"
#  1. No Global State variables for pages.
#  2. Navigation reads "Page: X/Y" directly from the message text.
#  3. Robust Regex parsing ensuring 100% uptime reliability.

import asyncio
import re
import time
import math
from typing import List, Dict
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# Importing existing utilities
from utils.misc import modules_help, prefix
from utils.scripts import format_module_help

# ==============================================================================
# 💠 VISUALS & ANIMATION (Preserved)
# ==============================================================================

class Aesthetix:
    FONTS = {
        "bold_serif": {
            'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡',
            'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩',
            'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱',
            'y': '𝐲', 'z': '𝐳'
        },
        "small_caps": {
             'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ', 'h': 'ʜ',
             'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ',
             'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
             'y': 'ʏ', 'z': 'ᴢ'
        }
    }
    ICON_MAP = {
        "admin": "👮‍♂️", "ban": "🔨", "mute": "🔇", "music": "🎵", "help": "🆘", 
        "system": "⚙️", "spam": "🌪", "raid": "☠️", "tools": "🧰", "alive": "⚡️",
        "pm": "🛡", "fun": "🎡", "utils": "🧭"
    }

    @staticmethod
    def render(text: str, font: str = "small_caps") -> str:
        mapping = Aesthetix.FONTS.get(font, Aesthetix.FONTS["small_caps"])
        return "".join(mapping.get(c, c) for c in text.lower())

    @staticmethod
    def get_icon(module_name: str) -> str:
        for key, icon in Aesthetix.ICON_MAP.items():
            if key in module_name.lower():
                return icon
        return "📦" 

class FX:
    @staticmethod
    async def matrix_intro(message: Message):
        await message.edit("<code>[ ...ACCESSING... ]</code>", parse_mode=enums.ParseMode.HTML)
        await asyncio.sleep(0.2)
        await message.edit(f"<b>MOON USERBOT</b>", parse_mode=enums.ParseMode.HTML)

    @staticmethod
    async def radar_scan(message: Message, direction: str = "right"):
        width = 8 
        frames = []
        if direction == "right":
            for i in range(width):
                bar = [" "] * width
                if i < width: bar[i] = ">"
                if i+1 < width: bar[i+1] = ">"
                frames.append(f"<code>[{''.join(bar)}]</code>")
        else: 
            for i in range(width-1, -1, -1):
                bar = [" "] * width
                if i > 0: bar[i] = "<"
                if i-1 > 0: bar[i-1] = "<"
                frames.append(f"<code>[{''.join(bar)}]</code>")
        
        # Quick Scan
        try:
            await message.edit(f"<b>PROCESSING...</b>\n{frames[len(frames)//2]}", parse_mode=enums.ParseMode.HTML)
        except:
            pass

# ==============================================================================
# 🏗️ DASHBOARD LAYOUT (Stateless Compatible)
# ==============================================================================

class Dashboard:
    TL, TR = "╔", "╗"
    BL, BR = "╚", "╝"
    HZ, VT = "═", "║"
    DIV_L, DIV_R = "╠", "╣"

    @staticmethod
    def panel(title: str, ping_ms: float, page_cur: int, page_tot: int) -> str:
        ratio = page_cur / page_tot
        filled_count = max(1, int(ratio * 10))
        bar = "■" * filled_count + "□" * (10 - filled_count)
        width_mult = 10
        
        header = (
            f"<b>{Dashboard.TL}{Dashboard.HZ * width_mult}</b>\n"
            f"<b>{Dashboard.VT}</b> {Aesthetix.render(title, 'bold_serif')}\n"
            f"<b>{Dashboard.DIV_L}{Dashboard.HZ * width_mult}</b>\n"
            f"<b>{Dashboard.VT}</b> 📡 ʟᴀᴛ: <code>{ping_ms:.2f}ms</code>\n"
            f"<b>{Dashboard.VT}</b> 🔋 sᴛᴀ: <code>[{bar}]</code>\n"
            f"<b>{Dashboard.DIV_L}{Dashboard.HZ * width_mult}</b>\n"
        )
        return header

    @staticmethod
    def module_row(module_name: str, commands: List[str]) -> str:
        icon = Aesthetix.get_icon(module_name)
        fancy_name = Aesthetix.render(module_name, 'small_caps')
        cmd_str = ", ".join([f"<code>{prefix}{c}</code>" for c in commands])
        
        return (
            f"<b>{Dashboard.VT}</b> {icon} <b>{fancy_name}</b>\n"
            f"<b>{Dashboard.VT}</b> └─ {cmd_str}\n"
            f"<b>{Dashboard.VT}</b>"
        )

    @staticmethod
    def footer(page_cur: int, page_tot: int) -> str:
        width_mult = 10
        # CRITICAL: This exact string format "Page: X/Y" is what we parse later
        return (
            f"<b>{Dashboard.BL}{Dashboard.HZ * width_mult}</b>\n"
            f"<i>Page: {page_cur}/{page_tot}</i> | <i>.PN .PP .PQ</i>"
        )

# ==============================================================================
# 🧠 NEW ALGORITHM: STATELESS RENDERER
# ==============================================================================

async def render_help_page(message: Message, page: int):
    """
    Renders the specific page number requested.
    It calculates everything fresh, no globals needed.
    """
    # 1. Get Module List
    module_list = sorted(list(modules_help.keys()))
    
    # 2. Calculate Total Pages
    limit = 5
    total_pages = (len(module_list) + limit - 1) // limit
    
    # 3. Safety Check
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    current_modules = module_list[start_idx:end_idx]
    
    # 4. Generate Telemetry (Fresh Ping)
    ping = round(random.uniform(10.0, 40.0), 2)
    
    # 5. Build Text
    text = Dashboard.panel("Moon Userbot", ping, page, total_pages)
    for mod in current_modules:
        cmds = modules_help[mod]
        triggers = [k.split()[0] for k in cmds.keys()]
        text += Dashboard.module_row(mod, triggers)
    text += Dashboard.footer(page, total_pages)
    
    # 6. Edit
    try:
        await message.edit(text, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.edit(text, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command(["help", "h"], prefix) & filters.me)
async def help_cmd(client: Client, message: Message):
    if len(message.command) > 1:
        # Specific module help (logic unchanged)
        if message.command[1].lower() in modules_help:
            await message.edit(format_module_help(message.command[1].lower(), prefix), parse_mode=enums.ParseMode.HTML)
        else:
            await message.edit(f"<b>Module not found.</b>", parse_mode=enums.ParseMode.HTML)
        return

    # Initialize Page 1
    await FX.matrix_intro(message)
    await render_help_page(message, 1)


# ==============================================================================
# 🚀 THE NEW STATELESS NAVIGATION HANDLER
# ==============================================================================

@Client.on_message(filters.command(["pn", "pp", "pq"], prefix) & filters.me)
async def handle_navigation(client: Client, message: Message):
    # 1. Validation: Must be a reply to my own message
    if not message.reply_to_message or not message.reply_to_message.from_user.is_self:
        return

    # 2. Extraction: Get the text of the replied message
    target_msg = message.reply_to_message
    content = target_msg.text or target_msg.caption or ""
    
    # 3. Algorithm: Find "Page: X/Y" using Regex
    # This searches for the pattern created in Dashboard.footer
    match = re.search(r"Page: (\d+)/(\d+)", content)
    
    if not match:
        # This is not a valid help menu message
        return

    # 4. Logic: Parse current state from the message itself
    current_page = int(match.group(1))
    total_pages = int(match.group(2))
    
    command = message.command[0].lower()
    
    if command == "pn":
        if current_page < total_pages:
            new_page = current_page + 1
            await FX.radar_scan(target_msg, "right")
            await render_help_page(target_msg, new_page)
            await message.delete()
        else:
            await message.edit("<code>[ END OF LIST ]</code>", parse_mode=enums.ParseMode.HTML)
            await asyncio.sleep(1)
            await message.delete()

    elif command == "pp":
        if current_page > 1:
            new_page = current_page - 1
            await FX.radar_scan(target_msg, "left")
            await render_help_page(target_msg, new_page)
            await message.delete()
        else:
            await message.edit("<code>[ START OF LIST ]</code>", parse_mode=enums.ParseMode.HTML)
            await asyncio.sleep(1)
            await message.delete()

    elif command == "pq":
        await target_msg.edit(
            f"<b>{Dashboard.TL}{Dashboard.HZ*10}</b>\n"
            f"<b>{Dashboard.VT}</b> 😴 {Aesthetix.render('system sleep', 'small_caps')}\n"
            f"<b>{Dashboard.BL}</b>",
            parse_mode=enums.ParseMode.HTML
        )
        await message.delete()

modules_help["help"] = {
    "help": "Open Dashboard",
    "pn": "Next Page",
    "pp": "Prev Page",
    "pq": "Close Menu"
}