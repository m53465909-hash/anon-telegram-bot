import os
import asyncio
import hashlib
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8751774975:AAHd6rI1cWvYHqEW280OJIx8SQzx_Iw6dco"
ADMIN_IDS = [1662629295, 5208268640, 8966941202, 8614257780, 6489442860, 8854400653, 8508113717]  
CHANNEL_ID = "@podslushka1547"
SECRET_SALT = "super_secret_salt_123"  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_anonymous_id(user_id: int) -> str:
    raw_str = f"{user_id}:{SECRET_SALT}"
    hash_obj = hashlib.sha256(raw_str.encode())
    return hash_obj.hexdigest()[:8]

id_map = {}

# Функция создания инлайн-кнопки с callback_data, чтобы бот сам обрабатывал нажатие
def get_post_keyboard(anon_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Опубликовать в канал", callback_data=f"post_{anon_id}")
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👋 Привет, админ!\n\n"
            "Сюда приходят анонимные сообщения.\n"
            "Чтобы ответить пользователю, сделайте **REPLY (Ответить)**.\n"
            "Нажмите на кнопку под сообщением, чтобы бот сам автоматически выложил текст в канал."
        )
    else:
        await message.answer(
            "👋 Привет! Напиши сюда любое сообщение, вопрос или отзыв.\n\n"
            "Администраторы получат его **абсолютно анонимно**."
        )

# Обработчик нажатия кнопки "Опубликовать в канал" для админов
@dp.callback_query(lambda c: c.data.startswith("post_") and c.from_user.id in ADMIN_IDS)
async def process_post_to_channel(callback_query: types.CallbackQuery):
    try:
        anon_id = callback_query.data.split("_")
        
        # Получаем текст исходного сообщения админа, убирая "шапку" анонима
        reply_text = callback_query.message.text or callback_query.message.caption
        if not reply_text:
            await callback_query.answer("❌ Ошибка: Нет текста для публикации.", show_alert=True)
            return

        # Отсекаем служебную шапку "👤 Анонимное сообщение (Anon ID: ...)"
        actual_text = reply_text.split(f"(Anon ID: {anon_id})")[-1].strip()

        # Бот сам отправляет чистый текст в канал
        if callback_query.message.text:
            await bot.send_message(chat_id=CHANNEL_ID, text=actual_text)
        elif callback_query.message.photo:
            await bot.send_photo(chat_id=CHANNEL_ID, photo=callback_query.message.photo[-1].file_id, caption=actual_text)
        elif callback_query.message.video:
            await bot.send_video(chat_id=CHANNEL_ID, video=callback_query.message.video.file_id, caption=actual_text)

        # Меняем кнопку на текст, чтобы никто не нажал её повторно
        await bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=None
        )
        
        await callback_query.message.reply(f"✅ Сообщение пользователя `{anon_id}` успешно опубликовано в канал!")
        await callback_query.answer("Опубликовано!")

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка публикации: {e}", show_alert=True)

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.reply_to_message)
async def handle_admin_reply(message: types.Message):
    try:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not reply_text or "Anon ID:" not in reply_text:
            return

        admin_name = message.from_user.first_name
        if message.from_user.username:
            admin_name = f"@{message.from_user.username} ({admin_name})"

        try:
            anon_id = reply_text.split("Anon ID:").split(")").strip()
        except Exception:
            return

        real_user_id = id_map.get(anon_id)
        if not real_user_id:
            await message.answer("❌ Срок действия сессии истек или пользователь не найден.")
            return

        if message.text:
            await bot.send_message(chat_id=real_user_id, text=f"💬 **Ответ от администрации:**\n\n{message.text}", parse_mode="Markdown")
        
        await message.answer(f"✅ Ответ успешно отправлен пользователю `{anon_id}`!")

    except Exception as e:
        await message.answer(f"❌ Ошибка в админ-панели: {e}")

@dp.message()
async def handle_user_message(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        return

    anon_id = get_anonymous_id(message.from_user.id)
    id_map[anon_id] = message.from_user.id
    
    info_header = f"👤 **Анонимное сообщение** (Anon ID: `{anon_id}`)\n\n"
    kb = get_post_keyboard(anon_id)

    for admin_id in ADMIN_IDS:
        try:
            if message.text:
                await bot.send_message(chat_id=admin_id, text=info_header + message.text, reply_markup=kb)
            elif message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=info_header + (message.caption or ""), reply_markup=kb)
            elif message.video:
                await bot.send_video(chat_id=admin_id, video=message.video.file_id, caption=info_header + (message.caption or ""), reply_markup=kb)
        except Exception as e:
            print(f"Не удалось доставить админу {admin_id}: {e}")
            
    await message.answer("🚀 Твое сообщение отправлено администрации! Это абсолютно анонимно.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
