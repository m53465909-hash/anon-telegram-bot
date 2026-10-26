import os
import asyncio
import hashlib
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8751774975:AAHd6rI1cWvYHqEW280OJIx8SQzx_Iw6dco"  # Токен от @BotFather
ADMIN_IDS = [1662629295, 5208268640, 8966941202, 8614257780, 6489442860, 8854400653, 8508113717]  # ID админов через запятую (пример)
SECRET_SALT = "PodslushkaAdmins"  # Любое секретное слово для шифрования ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_anonymous_id(user_id: int) -> str:
    raw_str = f"{user_id}:{SECRET_SALT}"
    hash_obj = hashlib.sha256(raw_str.encode())
    return hash_obj.hexdigest()[:8]

id_map = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👋 Привет, админ!\n\n"
            "Сюда будут приходить сообщения от пользователей. Их личности полностью скрыты.\n"
            "Чтобы ответить пользователю, просто сделайте **REPLY (Ответить)** на сообщение бота."
        )
    else:
        await message.answer(
            "👋 Привет! Напиши сюда любое сообщение, вопрос или отзыв.\n\n"
            "Администраторы получат его **абсолютно анонимно** — они не узнают твое имя, ник или ID. "
            "Когда они ответят, ты получишь сообщение прямо здесь."
        )

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.reply_to_message)
async def handle_admin_reply(message: types.Message):
    try:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not reply_text:
            return

        admin_name = message.from_user.first_name
        if message.from_user.username:
            admin_name = f"@{message.from_user.username} ({admin_name})"

        if "Anon ID:" in reply_text:
            try:
                anon_id = reply_text.split("Anon ID:")[1].split(")")[0].strip()
            except Exception:
                await message.answer("❌ Не удалось считать Anon ID из сообщения.")
                return

            real_user_id = id_map.get(anon_id)
            if not real_user_id:
                await message.answer("❌ Срок действия сессии истек или пользователь не найден.")
                return

            if message.text:
                await bot.send_message(chat_id=real_user_id, text=f"💬 **Ответ от администрации:**\n\n{message.text}", parse_mode="Markdown")
            elif message.photo:
                await bot.send_photo(chat_id=real_user_id, photo=message.photo[-1].file_id, caption=f"💬 **Ответ от администрации:**\n\n{message.caption or ''}", parse_mode="Markdown")
            elif message.video:
                await bot.send_video(chat_id=real_user_id, video=message.video.file_id, caption=f"💬 **Ответ от администрации:**\n\n{message.caption or ''}", parse_mode="Markdown")
            
            await message.answer(f"✅ Ответ успешно отправлен пользователю `{anon_id}`!")

            log_text = f"📢 **Админ {admin_name} ответил пользователю** `{anon_id}`:\n\n"
            for admin_id in ADMIN_IDS:
                if admin_id != message.from_user.id:
                    try:
                        if message.text:
                            await bot.send_message(chat_id=admin_id, text=log_text + message.text, parse_mode="Markdown")
                        elif message.photo:
                            await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=log_text + (message.caption or ""), parse_mode="Markdown")
                        elif message.video:
                            await bot.send_video(chat_id=admin_id, video=message.video.file_id, caption=log_text + (message.caption or ""), parse_mode="Markdown")
                    except Exception as e:
                        print(f"Не удалось отправить лог админу {admin_id}: {e}")

        elif "📢 Админ" in reply_text or "💬 Внутреннее обсуждение" in reply_text:
            chat_text = f"💬 **Внутреннее обсуждение**\n✍️ от {admin_name}:\n\n"
            for admin_id in ADMIN_IDS:
                if admin_id != message.from_user.id:
                    try:
                        if message.text:
                            await bot.send_message(chat_id=admin_id, text=chat_text + message.text, parse_mode="Markdown")
                        elif message.photo:
                            await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=chat_text + (message.caption or ""), parse_mode="Markdown")
                        elif message.video:
                            await bot.send_video(chat_id=admin_id, video=message.video.file_id, caption=chat_text + (message.caption or ""), parse_mode="Markdown")
                    except Exception as e:
                        print(f"Не удалось переслать сообщение админу {admin_id}: {e}")

    except Exception as e:
        await message.answer(f"❌ Ошибка в админ-панели: {e}")

@dp.message()
async def handle_user_message(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        return

    anon_id = get_anonymous_id(message.from_user.id)
    id_map[anon_id] = message.from_user.id

    info_header = f"👤 **Анонимное сообщение** (Anon ID: `{anon_id}`)\n\n"
    for admin_id in ADMIN_IDS:
        try:
            if message.text:
                await bot.send_message(chat_id=admin_id, text=info_header + message.text, parse_mode="Markdown")
            elif message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=info_header + (message.caption or ""), parse_mode="Markdown")
            elif message.video:
                await bot.send_video(chat_id=admin_id, video=message.video.file_id, caption=info_header + (message.caption or ""), parse_mode="Markdown")
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=info_header + (message.caption or ""), parse_mode="Markdown")
        except Exception as e:
            print(f"Не удалось доставить админу {admin_id}: {e}")
            
    await message.answer("🚀 Твое сообщение отправлено администрации! Это абсолютно анонимно.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
