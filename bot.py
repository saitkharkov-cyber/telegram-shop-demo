import asyncio, json, os
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and paste your token.")

PRODUCTS = json.loads(Path("products.json").read_text(encoding="utf-8"))
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
CARTS = {}

class Checkout(StatesGroup):
    waiting_phone = State()
    waiting_city = State()
    waiting_branch = State()


def money(v):
    return f"{v:,.0f} грн".replace(",", " ")


def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🧺 Кошик", callback_data="cart")],
        [InlineKeyboardButton(text="ℹ️ Про демо", callback_data="about")],
    ])


def catalog_kb():
    rows = [[InlineKeyboardButton(text=f'{p["emoji"]} {p["name"]} — {money(p["price"])}', callback_data=f'product:{p["id"]}')]
            for p in PRODUCTS]
    rows.append([InlineKeyboardButton(text="🧺 Кошик", callback_data="cart"), InlineKeyboardButton(text="⬅️ Головне", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_kb(pid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати в кошик", callback_data=f"add:{pid}")],
        [InlineKeyboardButton(text="⬅️ Каталог", callback_data="catalog"), InlineKeyboardButton(text="🧺 Кошик", callback_data="cart")],
    ])


def cart_text(uid):
    cart = CARTS.get(uid, {})
    if not cart:
        return "🧺 <b>Кошик порожній</b>"
    lines, total = ["🧺 <b>Ваш кошик:</b>\n"], 0
    for pid, qty in cart.items():
        p = PRODUCT_BY_ID[pid]
        subtotal = p["price"] * qty
        total += subtotal
        lines.append(f'{p["emoji"]} {p["name"]} × {qty} — <b>{money(subtotal)}</b>')
    lines.append(f"\nРазом: <b>{money(total)}</b>")
    return "\n".join(lines)


def cart_kb(uid):
    cart = CARTS.get(uid, {})
    rows = []
    for pid, qty in cart.items():
        p = PRODUCT_BY_ID[pid]
        rows.append([
            InlineKeyboardButton(text="➖", callback_data=f"dec:{pid}"),
            InlineKeyboardButton(text=f'{p["name"][:18]} × {qty}', callback_data=f"product:{pid}"),
            InlineKeyboardButton(text="➕", callback_data=f"add:{pid}"),
        ])
    if cart:
        rows.append([InlineKeyboardButton(text="✅ Оформити замовлення", callback_data="checkout")])
        rows.append([InlineKeyboardButton(text="🗑 Очистити", callback_data="clear")])
    rows.append([InlineKeyboardButton(text="⬅️ Каталог", callback_data="catalog"), InlineKeyboardButton(text="🏠 Головне", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 <b>Demo Shop</b>\n\nДемонстраційний Telegram-магазин: каталог, кошик та оформлення доставки Новою Поштою.",
        reply_markup=main_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "home")
async def home(c: CallbackQuery):
    await c.message.edit_text("🏠 <b>Demo Shop</b>\nОберіть дію:", reply_markup=main_kb(), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "catalog")
async def catalog(c: CallbackQuery):
    await c.message.edit_text("🛍 <b>Каталог товарів</b>\nОберіть товар:", reply_markup=catalog_kb(), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("product:"))
async def product(c: CallbackQuery):
    pid = int(c.data.split(":")[1]); p = PRODUCT_BY_ID[pid]
    text = f'{p["emoji"]} <b>{p["name"]}</b>\n\n{p["description"]}\n\nЦіна: <b>{money(p["price"])}</b>'
    await c.message.edit_text(text, reply_markup=product_kb(pid), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("add:"))
async def add(c: CallbackQuery):
    pid = int(c.data.split(":")[1]); uid = c.from_user.id
    CARTS.setdefault(uid, {})[pid] = CARTS.setdefault(uid, {}).get(pid, 0) + 1
    await c.answer("Додано до кошика ✅")

@dp.callback_query(F.data.startswith("dec:"))
async def dec(c: CallbackQuery):
    pid = int(c.data.split(":")[1]); uid = c.from_user.id
    cart = CARTS.setdefault(uid, {})
    if pid in cart:
        cart[pid] -= 1
        if cart[pid] <= 0: del cart[pid]
    await c.message.edit_text(cart_text(uid), reply_markup=cart_kb(uid), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "cart")
async def cart(c: CallbackQuery):
    uid = c.from_user.id
    await c.message.edit_text(cart_text(uid), reply_markup=cart_kb(uid), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "clear")
async def clear(c: CallbackQuery):
    CARTS[c.from_user.id] = {}
    await c.message.edit_text(cart_text(c.from_user.id), reply_markup=cart_kb(c.from_user.id), parse_mode="HTML")
    await c.answer("Кошик очищено")

@dp.callback_query(F.data == "about")
async def about(c: CallbackQuery):
    await c.message.edit_text(
        "ℹ️ <b>Portfolio demo</b>\n\nНавчально-демонстраційний Telegram-магазин. Реалізовано каталог, картки товарів, кошик та checkout. Інтеграцію API Нової Пошти можна підключити окремим модулем.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="home")]]), parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "checkout")
async def checkout(c: CallbackQuery, state: FSMContext):
    if not CARTS.get(c.from_user.id):
        await c.answer("Кошик порожній", show_alert=True); return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Надіслати номер", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await c.message.answer("Для оформлення замовлення надішліть номер телефону:", reply_markup=kb)
    await state.set_state(Checkout.waiting_phone)
    await c.answer()

@dp.message(Checkout.waiting_phone)
async def phone(m: Message, state: FSMContext):
    phone_value = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=phone_value)
    await m.answer("Вкажіть місто доставки:", reply_markup=None)
    await state.set_state(Checkout.waiting_city)

@dp.message(Checkout.waiting_city)
async def city(m: Message, state: FSMContext):
    await state.update_data(city=m.text)
    await m.answer("Вкажіть номер або назву відділення Нової Пошти:")
    await state.set_state(Checkout.waiting_branch)

@dp.message(Checkout.waiting_branch)
async def branch(m: Message, state: FSMContext):
    await state.update_data(branch=m.text)
    data = await state.get_data(); uid = m.from_user.id
    summary = cart_text(uid)
    text = (f"✅ <b>Замовлення сформовано</b>\n\n{summary}\n\n"
            f"📱 {data.get('phone')}\n🏙 {data.get('city')}\n📦 Нова Пошта: {data.get('branch')}\n\n"
            "Це демо-режим: замовлення не передається в реальну CRM.")
    CARTS[uid] = {}
    await state.clear()
    await m.answer(text, reply_markup=main_kb(), parse_mode="HTML")

async def main():
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
