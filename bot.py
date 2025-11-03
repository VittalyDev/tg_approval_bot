import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "8256448041:AAH9DIa05TtZ2pEgItsn_xIgp6W1aTwnHxg"
CHANNEL_USERNAME = "https://t.me/+PEgw_oLxbVgzYmFi"  # вставь ссылку на канал
ADMIN_ID = 5801614479  # твой Telegram ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


# Словарь для хранения заявок
pending_requests = {}


# /start
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Подать заявку", callback_data="apply_request")
    kb.adjust(1)

    await message.answer(
        "Привет! Чтобы подать заявку на вступление в закрытый канал, нажми кнопку ниже.",
        reply_markup=kb.as_markup()
    )


# Обработка кнопки заявки
@dp.callback_query(lambda c: c.data == "apply_request")
async def handle_request(call: types.CallbackQuery):
    user_id = call.from_user.id
    pending_requests[user_id] = call.from_user

    # Сообщение пользователю
    await call.message.answer("Заявка принята! Ожидайте одобрения админа.")

    # Отправка админу кнопок Approve / Reject
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"approve_{user_id}")
    kb.button(text="❌ Отклонить", callback_data=f"reject_{user_id}")
    kb.adjust(2)

    await bot.send_message(
        ADMIN_ID,
        f"Новая заявка от @{call.from_user.username} ({user_id})",
        reply_markup=kb.as_markup()
    )

    await call.answer()


# Обработка инлайн-кнопок админа
@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_callback(call: types.CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != ADMIN_ID:
        await call.answer("Ты не админ!", show_alert=True)
        return

    if user_id in pending_requests:
        try:
            await bot.send_message(
                user_id,
                f"Ваша заявка одобрена! Вот ссылка на канал: {CHANNEL_USERNAME}"
            )
        except Exception as e:
            await call.message.answer(f"Ошибка при отправке ЛС: {e}")

        del pending_requests[user_id]
        await call.message.edit_text("Пользователь одобрен ✅")
    else:
        await call.message.edit_text("Заявка уже обработана.")


@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_callback(call: types.CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != ADMIN_ID:
        await call.answer("Ты не админ!", show_alert=True)
        return

    if user_id in pending_requests:
        try:
            await bot.send_message(user_id, "Ваша заявка отклонена ❌")
        except Exception:
            pass

        del pending_requests[user_id]
        await call.message.edit_text("Пользователь отклонён ❌")
    else:
        await call.message.edit_text("Заявка уже обработана.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
