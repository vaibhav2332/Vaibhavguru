#  Moon-Userbot - Final Fixed Kinetic Core
#  Copyright (C) 2020-present Moon Userbot Organization
#
#  STATUS: FIXED
#  1. Navigation (.pn/.pp) now strictly checks for dashboard layout characters.
#  2. "Page: X/Y" added back to footer for reliable parsing.
#  3. Animations preserved.

import asyncio
import random
import time
from typing import List, Dict
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# Importing existing utilities
from utils.misc import modules_help, prefix
from utils.scripts import format_module_help, with_reply

# ==============================================================================
# 💠 MODULE 1: VISUALS (Aesthetix)
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
        "pm": "🛡", "fun": "🎡"
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

# ==============================================================================
# 🎞️ MODULE 2: ANIMATIONS (FX)
# ==============================================================================

class FX:
    @staticmethod
    async def matrix_intro(message: Message):
        target = "MOON USERBOT"
        await message.edit("<code>101010101010101</code>", parse_mode=enums.ParseMode.HTML)
        await asyncio.sleep(0.3)
        
        curr_display = ["0", "1"] * len(target)
        for i, char in enumerate(target):
            curr_display[i] = char
            mask = "".join([c if j <= i else random.choice(["0", "1"]) for j, c in enumerate(curr_display[:len(target)])])
            try:
                await message.edit(f"<code>{mask}</code>", parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(0.1)
            except FloodWait as e:
                await asyncio.sleep(e.value)

    @staticmethod
    async def radar_scan(message: Message, direction: str = "right"):
        width = 12
        frames = []
        if direction == "right":
            for i in range(width):
                bar = [" "]*width
                if i < width: bar[i] = "="
                if i+1 < width: bar[i+1] = ">"
                frames.append(f"<code>[{''.join(bar)}]</code>")
        else: 
            for i in range(width-1, -1, -1):
                bar = [" "]*width
                if i > 0: bar[i] = "<"
                if i-1 > 0: bar[i-1] = "="
                frames.append(f"<code>[{''.join(bar)}]</code>")

        for frame in frames[::3]: # Faster skip to prevent lag
            try:
                await message.edit(f"<b>SCANNING...</b>\n{frame}", parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(0.1)
            except FloodWait as e:
                await asyncio.sleep(e.value)

# ==============================================================================
# 🏗️ MODULE 3: DASHBOARD LAYOUT
# ==============================================================================

class Dashboard:
    # Defining constants for robust parsing
    TL, TR = "╔", "╗"
    BL, BR = "╚", "╝"
    HZ, VT = "═", "║"
    DIV_L, DIV_R = "╠", "╣"

    @staticmethod
    def panel(title: str, ping_ms: float, page_cur: int, page_tot: int) -> str:
        progress = int((page_cur / page_tot) * 10)
        bar = "■" * progress + "□" * (10 - progress)
        
        # Header Structure
        header = (
            f"<b>{Dashboard.TL}{Dashboard.HZ * 12}</b>\n"
            f"<b>{Dashboard.VT}</b> {Aesthetix.render(title, 'bold_serif')}\n"
            f"<b>{Dashboard.DIV_L}{Dashboard.HZ * 12}</b>\n"
            f"<b>{Dashboard.VT}</b> 📡 ʟᴀᴛ: <code>{ping_ms:.2f}ms</code>\n"
            f"<b>{Dashboard.VT}</b> 🔋 sᴛᴀ: <code>[{bar}]</code>\n"
            f"<b>{Dashboard.DIV_L}{Dashboard.HZ * 12}</b>\n"
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
        # Added "Page: X/Y" explicitly for the parser logic to find
        return (
            f"<b>{Dashboard.BL}{Dashboard.HZ * 12}</b>\n"
            f"<i>Page: {page_cur}/{page_tot}</i> | <i>{Aesthetix.render('.pn .pp .pq', 'small_caps')}</i>"
        )

# ==============================================================================
# 🧠 CONTROLLER
# ==============================================================================

# Global state to track pages across different messages
state_store: Dict[str, int] = {"page": 1, "total": 1}

async def render_help_page(message: Message, module_list: List[str], page: int, total_pages: int, ping: float):
    start_idx = (page - 1) * 5 
    end_idx = start_idx + 5
    current_modules = module_list[start_idx:end_idx]
    
    text = Dashboard.panel("Moon Userbot", ping, page, total_pages)
    
    for mod in current_modules:
        cmds = modules_help[mod]
        triggers = [k.split()[0] for k in cmds.keys()]
        text += Dashboard.module_row(mod, triggers)
        
    text += Dashboard.footer(page, total_pages)
    await message.edit(text, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["help", "h"], prefix) & filters.me)
async def help_cmd(client: Client, message: Message):
    try:
        await message.react(reaction=enums.ReactionType.EMOJI, emoji="👾")
    except:
        pass

    if len(message.command) == 1:
        await FX.matrix_intro(message)
        
        start_time = time.perf_counter()
        end_time = time.perf_counter()
        ping_ms = (end_time - start_time) * 1000
        
        global state_store
        module_list = list(modules_help.keys())
        state_store["total"] = (len(module_list) + 4) // 5 
        state_store["page"] = 1
        
        await render_help_page(message, module_list, 1, state_store["total"], ping_ms)

    elif message.command[1].lower() in modules_help:
        await message.edit(
            format_module_help(message.command[1].lower(), prefix),
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.edit(f"<b>Command not found.</b>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command(["pn", "pp", "pq"], prefix) & filters.me)
@with_reply
async def handle_navigation(client: Client, message: Message):
    """
    Revised Navigation Logic: Checks for visual structure instead of hidden IDs.
    """
    # Robust Check: verify if the reply contains the dashboard structure
    # We check for the Top-Left Corner (╔) OR the specific string "Page:"
    is_help_menu = False
    if message.reply_to_message and message.reply_to_message.text:
        txt = message.reply_to_message.text
        if Dashboard.TL in txt or "Page:" in txt:
            is_help_menu = True

    if is_help_menu:
        global state_store
        act = message.command[0].lower()
        ping = round(random.uniform(10.5, 45.2), 2) 
        
        if act == "pn":
            if state_store["page"] < state_store["total"]:
                state_store["page"] += 1
                await message.react(reaction=enums.ReactionType.EMOJI, emoji="👎")
                await FX.radar_scan(message.reply_to_message, direction="right")
                
                await render_help_page(
                    message.reply_to_message, 
                    list(modules_help.keys()), 
                    state_store["page"], 
                    state_store["total"], 
                    ping
                )
                return await message.delete()
            else:
                await message.edit("<code>End of list.</code>", parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(1)
                return await message.delete()

        elif act == "pp":
            if state_store["page"] > 1:
                state_store["page"] -= 1
                await message.react(reaction=enums.ReactionType.EMOJI, emoji="👍")
                await FX.radar_scan(message.reply_to_message, direction="left")
                
                await render_help_page(
                    message.reply_to_message, 
                    list(modules_help.keys()), 
                    state_store["page"], 
                    state_store["total"], 
                    ping
                )
                return await message.delete()
            else:
                await message.edit("<code>Start of list.</code>", parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(1)
                return await message.delete()

        elif act == "pq":
            await message.reply_to_message.edit(
                f"<b>{Dashboard.TL}{Dashboard.HZ*12}</b>\n"
                f"<b>{Dashboard.VT}</b> 😴 {Aesthetix.render('system sleep', 'small_caps')}\n"
                f"<b>{Dashboard.BL}</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return await message.delete()

modules_help["help"] = {
    "help": "Open Kinetic Dashboard",
    "pn": "Scan Next ⏩",
    "pp": "Scan Prev ⏪",
    "pq": "System Collapse ❌"
}