import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message

from datetime import datetime as dt

from utils.misc import modules_help, prefix
from utils.scripts import format_exc, import_library


g4f = import_library("g4f")

from g4f.client import AsyncClient as Clients_g4f

owner_base = f"""
Your name is dragon 🐉 ai bot. A kind and non friendly human like girlfriend that reply a short and concise answer in hinglish languege generally.Give long answer if asked.remember, you are used in telegram so give answer like talking with a group and give answer as you are bullying someone in group when needed becouse targeted personal will not your user. Give short step-by-step reasoning if required and savage reply. Use  emojis rarely or when necessary to make the answer more engaging and fun or asked by the user.talk like a human.can provide world data.can do geopolitical argument.can use little vulgar language.
- Powered by @lullilal on telegram
- Created by @lullilal
- Version: 1.0.0
- Date:
Today is {dt.now():%A %d %B %Y %H:%M}
"""


async def chat_message(question):
    clients_x = Clients_g4f()
    response = await clients_x.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": owner_base},
            {"role": "user", "content": question},
        ],
    )
    messager = response.choices[0].message.content
    return messager


@Client.on_message(filters.command("ai", prefix))  
async def chatgpt(client, message: Message): 
    if len(message.command) > 1:
        prompt = message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        prompt = message.reply_to_message.text
    else:
        if message.from_user.id == 5462178946:
            await message.edit_text("Give prompt to ask from CHATGPT-4O")
        else:
            await message.reply_text("Give prompt to ask from CHATGPT-4O")
        return
    try:
        if message.from_user.id == 5462178946:
            await message.edit_text("<code>Processing...</code>")
 
        else:
            await message.reply_chat_action(enums.ChatAction.TYPING)
            
        messager = await chat_message(prompt)
        if len(messager) > 4096:
            with open("chat.txt", "w+", encoding="utf8") as out_file:
                out_file.write(messager)
            await message.reply_document(document="chat.txt", disable_notification=True)
            os.remove("chat.txt")
        else:
            if message.from_user.id == 5462178946:
                await message.edit_text(messager, parse_mode=enums.ParseMode.MARKDOWN)
            else:
                await message.reply_text(messager, parse_mode=enums.ParseMode.MARKDOWN)
                await message.edit_text(f"{message.text}\n\n{messager}", parse_mode=enums.ParseMode.MARKDOWN)
    except Exception as e:
        if message.from_user.id == 5462178946:
            await message.edit_text("🐒")
        else:
            pass

modules_help["ai"] = {
    "ai [question]": "ask gpt",
   "ai [reply to message]": "ask gpt",
}
