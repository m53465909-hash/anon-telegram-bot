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

# --- ФУНКЦИЯ АНОНИМИЗАЦИИ (ХЭШИРОВАНИЕ ID) ---
def get_anonymous_id(user_id: int) -> str:
    """Превращает реальный Telegram ID в короткий анонимный хэш-код"""
    raw_str = f"{user_id}:{SECRET_SALT}"
    hash_obj = hashlib.sha256(raw_str.encode())
    return hash_obj.hexdigest()[:8]  # Берём первые 8 символов для удобства

# Словарь для обратного поиска (нужен для Long Polling, пока бот запущен в памяти)
# Хранит связь: "анонимный_код" -> реальный_id
id_map = {}

# --- КОД ДЛЯ ОБМАНА RENDER (чтобы сервис не засыпал с ошибкой Port) ---
async def handle_hc(request):
    return web.Response(text="Бот активен и анонимен!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЛОГИКА БОТА ---

# Команда /start
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

# Обработка ответов от админов (через функцию Reply)
@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.reply_to_message)
async def handle_admin_reply(message: types.Message):
    try:
        # Ищем текст во всем сообщении (текст или подпись к фото)
        reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not reply_text or "Anon ID:" not in reply_text:
            await message.answer("❌ Ошибка: Отвечайте только на сообщения бота, содержащие 'Anon ID:'.")
            return
        
        # Вытаскиваем анонимный хэш из строки вида "👤 Аноним (Anon ID: a8f3b2)"
        try:
            anon_id = reply_text.split("Anon ID:").strip().split(")")[0]
        except Exception:
            await message.answer("❌ Не удалось считать Anon ID из сообщения.")
            return

        # Ищем реальный Telegram ID в нашей базе в памяти
        real_user_id = id_map.get(anon_id)
        
        if not real_user_id:
            await message.answer("❌ Срок действия сессии истек или пользователь не найден (бот перезапускался).")
            return

        # Отправляем ответ пользователю от имени бота (Анонимно для админа)
        if message.text:
            await bot.send_message(chat_id=real_user_id, text=f"💬 **Ответ от администрации:**\n\n{message.text}", parse_mode="Markdown")
        elif message.photo:
            await bot.send_photo(chat_id=real_user_id, photo=message.photo[-1].file_id, caption=f"💬 **Ответ от администрации:**\n\n{message.caption or ''}", parse_mode="Markdown")
        elif message.video:
            await bot.send_video(chat_id=real_user_id, video=message.video.file_id, caption=f"💬 **Ответ от администрации:**\n\n{message.caption or ''}", parse_mode="Markdown")
        
        await message.answer(f"✅ Ответ успешно отправлен пользователю `{anon_id}`!")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

# Пересылка сообщений от пользователей всем админам
@dp.message()
async def handle_user_message(message: types.Message):
    # Если админ пишет просто так (не в Reply), ничего не делаем
    if message.from_user.id in ADMIN_IDS:
        return

    # Генерируем анонимный код для пользователя
    anon_id = get_anonymous_id(message.from_user.id)
    # Запоминаем связь кода и реального ID
    id_map[anon_id] = message.from_user.id

    # Формируем красивую плашку БЕЗ личных данных пользователя
    info_header = f"👤 **Анонимное сообщение** (Anon ID: `{anon_id}`)\n\n"
    
    # Рассылаем всем админам из списка
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

# Запуск
async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
