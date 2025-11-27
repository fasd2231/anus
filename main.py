# main.py
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# --- FSM для админки (состояния) ---
class AdminState(StatesGroup):
    waiting_for_broadcast_text = State()

# --- ФУНКЦИИ ПОИСКА ---
async def search_kp_id(film_name):
    """Ищет фильм через Kinopoisk Unofficial API"""
    headers = {
        'X-API-KEY': config.KP_API_KEY,
        'Content-Type': 'application/json',
    }
    async with aiohttp.ClientSession() as session:
        url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={film_name}"
        try:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if data.get("films") and len(data["films"]) > 0:
                    first = data["films"][0]
                    return {
                        "id": first["filmId"],
                        "name": first.get("nameRu") or first.get("nameEn") or "Название неизвестно",
                        "year": first.get("year") or "..."
                    }
        except Exception as e:
            logging.error(f"Ошибка API: {e}")
    return None

# --- ХЕНДЛЕРЫ ПОЛЬЗОВАТЕЛЕЙ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Сохраняем юзера в БД
    database.add_user(message.from_user.id)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для просмотра фильмов и сериалов. Без рекламы и смс.\n"
        "Просто напиши мне **название** фильма, и я его найду.",
        parse_mode="Markdown"
    )

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: types.Message):
    """Обрабатывает любой текст как запрос на поиск"""
    wait_msg = await message.answer("🔎 Ищу на просторах сети...")
    
    result = await search_kp_id(message.text)
    
    if not result:
        await wait_msg.edit_text("😔 Ничего не нашел. Попробуй написать точнее (например, с годом).")
        return

    # Формируем ссылку
    play_url = f"{config.WEB_APP_URL}?id={result['id']}&name={result['name']}"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🎬 Смотреть онлайн",
        web_app=WebAppInfo(url=play_url)
    ))

    await wait_msg.edit_text(
        f"🎥 Нашел: *{result['name']}* ({result['year']})\n\nПриятного просмотра!",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# --- АДМИНКА ---

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return # Игнорим не админов

    count = database.get_users_count()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])
    
    await message.answer(
        f"👑 **Админ-панель**\n\n📊 Пользователей в базе: `{count}`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введи текст (или фото с подписью) для рассылки всем пользователям.\nДля отмены напиши /cancel")
    await state.set_state(AdminState.waiting_for_broadcast_text)
    await callback.answer()

@dp.message(AdminState.waiting_for_broadcast_text)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Рассылка отменена.")
        return

    users = database.get_all_users()
    await message.answer(f"🚀 Начинаю рассылку на {len(users)} пользователей...")

    blocked = 0
    good = 0
    
    for user_id in users:
        try:
            # Копируем сообщение админа пользователю
            await message.copy_to(chat_id=user_id)
            good += 1
            await asyncio.sleep(0.05) # Небольшая задержка, чтобы телега не банила за спам
        except Exception:
            blocked += 1
    
    await message.answer(f"✅ Рассылка завершена!\nДоставлено: {good}\nЗаблокировали бота: {blocked}")
    await state.clear()

@dp.callback_query(F.data == "admin_close")
async def close_admin(callback: types.CallbackQuery):
    await callback.message.delete()

# --- ЗАПУСК ---
async def main():
    database.init_db() # Создаем БД при старте
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())