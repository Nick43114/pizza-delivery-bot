import os
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    CallbackQuery, Message
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import database as db

# ⚠️ Вставь свой токен от нового бота из @BotFather
BOT_TOKEN = "8727274117:AAE6SeWRXAlaAotAia47F35Ln7UmGFsxj-w"

# ⚠️ Твой цифровой ID Telegram из @userinfobot
ADMIN_ID = 7595032420 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- Фоновый веб-сервер для проверки Render ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Pizza bot is alive!")

    def log_message(self, format, *args):
        pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# ---------- Состояния оформления заказа (FSM) ----------
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()

# ---------- Клавиатуры ----------

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍕 Відкрити Меню", callback_data="open_menu")],
        [InlineKeyboardButton(text="🛒 Моя Корзина", callback_data="open_cart")],
        [InlineKeyboardButton(text="ℹ️ Про нас / Доставка", callback_data="about_us")]
    ])

def get_categories_keyboard():
    categories = db.get_categories()
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"cat_{cat_id}")]
        for cat_id, name in categories
    ]
    buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="open_cart")])
    buttons.append([InlineKeyboardButton(text="◀️ На головну", callback_data="to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(category_id):
    products = db.get_products_by_category(category_id)
    buttons = [
        [InlineKeyboardButton(text=f"{name} — {price} грн", callback_data=f"prod_{prod_id}")]
        for prod_id, name, price in products
    ]
    buttons.append([InlineKeyboardButton(text="◀️ До категорій", callback_data="open_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_detail_keyboard(product_id, category_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати в корзину", callback_data=f"add_{product_id}")],
        [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="open_cart")],
        [InlineKeyboardButton(text="◀️ Назад до страв", callback_data=f"cat_{category_id}")]
    ])

def get_cart_keyboard(cart_items):
    buttons = []
    for item in cart_items:
        prod_id, name, price, qty, total = item
        buttons.append([
            InlineKeyboardButton(text=f"{name}", callback_data="ignore"),
            InlineKeyboardButton(text="➖", callback_data=f"dec_{prod_id}"),
            InlineKeyboardButton(text=f"{qty} шт", callback_data="ignore"),
            InlineKeyboardButton(text="➕", callback_data=f"inc_{prod_id}")
        ])
    
    if cart_items:
        buttons.append([InlineKeyboardButton(text="🚀 Оформити замовлення", callback_data="start_order")])
        buttons.append([InlineKeyboardButton(text="🗑 Очистити корзину", callback_data="clear_cart")])
    
    buttons.append([InlineKeyboardButton(text="🍕 До меню", callback_data="open_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- Обработчики событий ----------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        f"👋 <b>Вітаємо у піцерії «Mario Pizza»!</b>\n\n"
        f"Гаряча крафтова піца на дровах з доставкою до 40 хвилин.\n"
        f"Оберіть дію в меню нижче:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "to_main")
async def cb_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 <b>Головне меню «Mario Pizza»:</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "open_menu")
async def cb_open_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍕 <b>Оберіть категорію страв:</b>",
        reply_markup=get_categories_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def cb_category(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    await callback.message.edit_text(
        "😋 <b>Оберіть страву зі списку:</b>",
        reply_markup=get_products_keyboard(cat_id),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("prod_"))
async def cb_product(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    prod = db.get_product(prod_id)
    
    if not prod:
        await callback.answer("Страву не знайдено.")
        return

    name, desc, price, photo_url = prod[1], prod[2], prod[3], prod[4]
    caption = (
        f"🍕 <b>{name}</b>\n\n"
        f"{desc}\n\n"
        f"💰 <b>Ціна:</b> {price} грн"
    )
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=get_product_detail_keyboard(prod_id, category_id=1),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("add_"))
async def cb_add_cart(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    db.add_to_cart(callback.from_user.id, prod_id)
    await callback.answer("✅ Додано в корзину!", show_alert=False)

@dp.callback_query(F.data == "open_cart")
async def cb_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    items = db.get_user_cart(user_id)
    
    if not items:
        text = "🛒 <b>Ваша корзина порожня.</b>\nДодайте щось смачненьке з меню!"
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=get_categories_keyboard(), parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=get_categories_keyboard(), parse_mode="HTML")
        await callback.answer()
        return

    total_sum = sum(item[4] for item in items)
    lines = ["🛒 <b>Ваше замовлення:</b>\n"]
    for idx, item in enumerate(items, 1):
        _, name, price, qty, total = item
        lines.append(f"{idx}. <b>{name}</b> — {qty} шт. × {price} = <b>{total} грн</b>")
    
    lines.append(f"\n━━━━━━━━━━━━━━\nРазом до сплати: <b>{total_sum} грн</b>")
    text = "\n".join(lines)

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_cart_keyboard(items), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=get_cart_keyboard(items), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("inc_"))
async def cb_inc_cart(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    db.change_cart_quantity(callback.from_user.id, prod_id, 1)
    await cb_cart(callback)

@dp.callback_query(F.data.startswith("dec_"))
async def cb_dec_cart(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    db.change_cart_quantity(callback.from_user.id, prod_id, -1)
    await cb_cart(callback)

@dp.callback_query(F.data == "clear_cart")
async def cb_clear_cart(callback: CallbackQuery):
    db.clear_cart(callback.from_user.id)
    await callback.answer("Корзину очищено!")
    await cb_cart(callback)

@dp.callback_query(F.data == "about_us")
async def cb_about(callback: CallbackQuery):
    text = (
        "ℹ️ <b>Про піцерію «Mario Pizza»:</b>\n\n"
        "📍 вул. Хрещатик, 1 (Київ)\n"
        "🕒 Працюємо щодня: 10:00 — 22:00\n"
        "🚀 Безкоштовна доставка від 300 грн.\n\n"
        "📞 Контактний телефон: +380 99 123 45 67"
    )
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# ---------- Оформление заказа (FSM) ----------

@dp.callback_query(F.data == "start_order")
async def process_start_order(callback: CallbackQuery, state: FSMContext):
    items = db.get_user_cart(callback.from_user.id)
    if not items:
        await callback.answer("Корзина порожня!")
        return

    await state.set_state(OrderState.waiting_for_name)
    await callback.message.delete()
    await callback.message.answer("📝 <b>Крок 1/3:</b> Як до вас звертатися? Введіть ваше ім'я:", parse_mode="HTML")
    await callback.answer()

@dp.message(OrderState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(customer_name=message.text)
    await state.set_state(OrderState.waiting_for_phone)
    
    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("📱 <b>Крок 2/3:</b> Вкажіть номер телефону (натисніть кнопку нижче або введіть вручну):", 
                         reply_markup=phone_keyboard, parse_mode="HTML")

@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_address)
    
    await message.answer(
        "📍 <b>Крок 3/3:</b> Вкажіть адресу доставки (вулиця, будинок, під'їзд, квартира):",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

@dp.message(OrderState.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    address = message.text
    user_data = await state.get_data()
    customer_name = user_data["customer_name"]
    phone = user_data["phone"]
    user_id = message.from_user.id

    items = db.get_user_cart(user_id)
    total_sum = sum(item[4] for item in items)
    items_summary = ", ".join([f"{item[1]} (x{item[3]})" for item in items])

    order_id = db.create_order(user_id, customer_name, phone, address, total_sum, items_summary)
    await state.clear()

    client_text = (
        f"🎉 <b>Дякуємо, {customer_name}! Замовлення #{order_id} прийнято!</b>\n\n"
        f"📦 <b>Склад:</b> {items_summary}\n"
        f"💰 <b>Сума:</b> {total_sum} грн (оплата при отриманні)\n"
        f"📍 <b>Адреса:</b> {address}\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        f"Кур'єр уже готує доставку! Очікуйте замовлення протягом 40 хвилин."
    )
    await message.answer(client_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

    try:
        admin_text = (
            f"🚨 <b>НОВЕ ЗАМОВЛЕННЯ #{order_id}!</b>\n\n"
            f"👤 Клієнт: {customer_name} (@{message.from_user.username or 'немає'})\n"
            f"📞 Телефон: <code>{phone}</code>\n"
            f"📍 Адреса: {address}\n"
            f"💰 Сума: <b>{total_sum} грн</b>\n"
            f"🍕 Замовлення:\n{items_summary}"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Не вдалося надіслати сповіщення адміну: {e}")

# ---------- Запуск ----------

async def main():
    # Запускаем скрытый сервер проверки Render в фоновом потоке
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    db.init_db()
    print("🚀 Бот-піцерія запущений! Натисніть /start у Telegram.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())