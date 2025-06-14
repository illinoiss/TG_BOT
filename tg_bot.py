import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

API_TOKEN = '7510934024:AAGCo_-J9NoeXegrirP7E7-Ga63HoUkwIr0'
ADMIN_IDS = [7290616621]
ADMIN_CARD = '2200701944367520'
ADMIN_CONTACT = '@r1ck_grimess'

CATEGORIES = ['Обувь', 'Штаны', 'Джинсы', 'Футболки', 'Куртки', 'Другое']
TYPES = ['Оригинал', 'Реплика']
DELIVERY = ['СДЭК', 'Яндекс', 'Личная встреча (Москва)']

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

class AddProduct(StatesGroup):
    choose_type = State()
    choose_category = State()
    enter_name = State()
    enter_desc = State()
    enter_price = State()
    enter_photo = State()

class MakeOrder(StatesGroup):
    choose_type = State()
    choose_category = State()
    choose_product = State()
    choose_delivery = State()
    enter_contacts = State()
    wait_payment = State()
    wait_screen = State()

def menu_kb(is_admin: bool = False):
    kb = [
        [KeyboardButton(text='📦 Сделать заказ'), KeyboardButton(text='➕ Добавить заказ')],
        [KeyboardButton(text='🛒 Каталог')],
        [KeyboardButton(text='👤 Профиль'), KeyboardButton(text='❓Помощь')]
    ]
    if is_admin:
        kb.append([KeyboardButton(text='🔧 Админ-меню')])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='➕ Добавить товар')],
        [KeyboardButton(text='📦 Заказы')],
        [KeyboardButton(text='🔙 Назад'), KeyboardButton(text='🏠 В меню')]
    ], resize_keyboard=True)

def category_kb():
    kb = [[KeyboardButton(text=cat)] for cat in CATEGORIES]
    kb.append([KeyboardButton(text='🏠 В меню')])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def types_kb():
    kb = [[KeyboardButton(text=t)] for t in TYPES]
    kb.append([KeyboardButton(text='🏠 В меню')])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def delivery_kb():
    kb = [[KeyboardButton(text=d)] for d in DELIVERY]
    kb.append([KeyboardButton(text='🏠 В меню')])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='❌ Отмена')],
            [KeyboardButton(text='🏠 В меню')]
        ],
        resize_keyboard=True
    )

def back_to_menu_kb(is_admin=False):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='🏠 В меню')]],
        resize_keyboard=True
    )

async def db_init():
    async with aiosqlite.connect('shop.db') as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, category TEXT, name TEXT, desc TEXT, price INTEGER, photo_id TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, username TEXT, product_id INTEGER, delivery TEXT,
            contacts TEXT, payment_screen TEXT, status TEXT DEFAULT 'pending'
        )""")
        await db.commit()

def is_menu_command(msg: Message):
    return msg.text and msg.text.lower() in ['🏠 в меню', '/menu', 'меню', 'главное меню']

async def back_to_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Главное меню:", reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))

@router.message(lambda m: is_menu_command(m))
async def catch_menu_cmd(msg: Message, state: FSMContext):
    await back_to_menu(msg, state)

@router.message(Command('menu'))
async def menu_cmd(msg: Message, state: FSMContext):
    await back_to_menu(msg, state)

@router.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    is_admin = msg.from_user.id in ADMIN_IDS
    await msg.answer("Добро пожаловать в магазин 👋\nВыберите действие:", reply_markup=menu_kb(is_admin))

@router.message(F.text == '❓Помощь')
async def help_handler(msg: Message):
    await msg.answer(f"По вопросам заказа: {ADMIN_CONTACT}", reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))

@router.message(F.text == '👤 Профиль')
async def profile(msg: Message):
    await msg.answer(f"Ваш ID: {msg.from_user.id}\nUsername: @{msg.from_user.username or 'нет'}",
                     reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))

@router.message(F.text == '🛒 Каталог')
async def catalog(msg: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{t}", callback_data=f"cat_type_{t.lower()}")] for t in TYPES
        ]
    )
    await msg.answer("Выберите тип товара:", reply_markup=kb)

@router.callback_query(F.data.startswith('cat_type_'))
async def catalog_type(call: CallbackQuery):
    t = call.data.split('_')[-1].capitalize()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=cat, callback_data=f"cat_{t.lower()}_{cat.lower()}")] for cat in CATEGORIES
        ]
    )
    await call.message.edit_text(f"Товары: {t}\nВыберите категорию:", reply_markup=kb)

@router.callback_query(F.data.startswith('cat_'))
async def catalog_category(call: CallbackQuery):
    _, t, cat = call.data.split('_')
    items = []
    async with aiosqlite.connect('shop.db') as db:
        res = await db.execute("SELECT id, name, price FROM products WHERE type=? AND category=?",
                               (t.capitalize(), cat.capitalize()))
        items = await res.fetchall()
    if not items:
        await call.message.edit_text("В данной категории пока нет товаров.", reply_markup=None)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{name} ({price}₽)", callback_data=f"show_{pid}")]
            for pid, name, price in items
        ]
    )
    await call.message.edit_text("Выберите товар:", reply_markup=kb)

@router.callback_query(F.data.startswith('show_'))
async def show_catalog_product(call: CallbackQuery):
    pid = int(call.data.split('_')[1])
    async with aiosqlite.connect('shop.db') as db:
        res = await db.execute("SELECT name, desc, price, photo_id FROM products WHERE id=?", (pid,))
        row = await res.fetchone()
    if row:
        name, desc, price, photo_id = row
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("Заказать", callback_data=f"order_{pid}")]
            ]
        )
        await call.message.answer_photo(photo_id, caption=f"<b>{name}</b>\n{desc}\nЦена: {price}₽",
                                        parse_mode='HTML', reply_markup=kb)
    else:
        await call.message.answer("Ошибка! Товар не найден.", reply_markup=back_to_menu_kb())

@router.callback_query(F.data.startswith('order_'))
async def start_order_callback(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split('_')[1])
    await state.clear()
    await state.set_state(MakeOrder.choose_delivery)
    await state.update_data(product_id=pid)
    await call.message.answer("Выберите способ доставки:", reply_markup=delivery_kb())

@router.message(F.text == '📦 Сделать заказ')
async def order_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Выберите тип товара:", reply_markup=types_kb())
    await state.set_state(MakeOrder.choose_type)

@router.message(StateFilter(MakeOrder.choose_type))
async def order_choose_type(msg: Message, state: FSMContext):
    if is_menu_command(msg):
        await back_to_menu(msg, state)
        return
    if msg.text not in TYPES:
        return await msg.answer("Выберите тип из списка.", reply_markup=types_kb())
    await state.update_data(type=msg.text)
    await state.set_state(MakeOrder.choose_category)
    await msg.answer("Выберите категорию:", reply_markup=category_kb())

@router.message(StateFilter(MakeOrder.choose_category))
async def order_choose_cat(msg: Message, state: FSMContext):
    if is_menu_command(msg):
        await back_to_menu(msg, state)
        return
    if msg.text not in CATEGORIES:
        return await msg.answer("Выберите категорию из списка.", reply_markup=category_kb())
    await state.update_data(category=msg.text)
    async with aiosqlite.connect('shop.db') as db:
        data = await state.get_data()
        res = await db.execute("SELECT id, name, price FROM products WHERE type=? AND category=?",
                               (data['type'], msg.text))
        products = await res.fetchall()
    if not products:
        await msg.answer("В этой категории пока нет товаров.", reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))
        await state.clear()
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{name} ({price}₽)", callback_data=f"makeorder_{pid}")]
            for pid, name, price in products
        ]
    )
    await msg.answer("Выберите товар:", reply_markup=kb)

# ========== ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ ==========
# 1. Показываем фото и описание товара перед покупкой
@router.callback_query(StateFilter(MakeOrder.choose_category), F.data.startswith('makeorder_'))
async def show_product_to_buyer(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split('_')[1])
    async with aiosqlite.connect('shop.db') as db:
        res = await db.execute("SELECT name, desc, price, photo_id FROM products WHERE id=?", (pid,))
        row = await res.fetchone()
    if not row:
        await call.message.answer("Ошибка: товар не найден.")
        return
    name, desc, price, photo_id = row

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Купить", callback_data=f"buy_{pid}")]
        ]
    )

    await call.message.answer_photo(
        photo_id,
        caption=f"<b>{name}</b>\n{desc}\nЦена: {price}₽",
        parse_mode="HTML",
        reply_markup=kb
    )

# 2. Обработка нажатия «Купить» — старт оформления заказа
@router.callback_query(StateFilter(MakeOrder.choose_category), F.data.startswith('buy_'))
async def start_order_after_photo(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split('_')[1])
    await state.update_data(product_id=pid)
    await state.set_state(MakeOrder.choose_delivery)
    await call.message.answer("Выберите способ доставки:", reply_markup=delivery_kb())

# 3. Подтверждение заказа админом: удаляем "Оригинал", оставляем "Реплика", отправляем фото пользователю
@router.callback_query(F.data.startswith('admin_confirm_'))
async def admin_confirm_order(call: CallbackQuery):
    order_id = int(call.data.split('_')[-1])
    async with aiosqlite.connect('shop.db') as db:
        res = await db.execute("SELECT product_id FROM orders WHERE id=?", (order_id,))
        product_res = await res.fetchone()
        product_id = product_res[0] if product_res else None

        product_type, photo_id, product_name = None, None, None
        if product_id:
            res = await db.execute("SELECT type, photo_id, name FROM products WHERE id=?", (product_id,))
            prod_info = await res.fetchone()
            if prod_info:
                product_type, photo_id, product_name = prod_info

        await db.execute("UPDATE orders SET status='confirmed' WHERE id=?", (order_id,))
        await db.commit()
        res = await db.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
        user = await res.fetchone()

        # Если оригинал — удалить из базы
        if product_type == "Оригинал":
            await db.execute("DELETE FROM products WHERE id=?", (product_id,))
            await db.commit()

    await call.message.delete()
    await call.message.answer("Заказ подтверждён ✅")
    if user and user[0]:
        try:
            if photo_id:
                await call.bot.send_photo(
                    user[0],
                    photo_id,
                    caption=f"Ваш заказ подтверждён!\nТовар: {product_name}\nС вами свяжется менеджер для уточнения доставки."
                )
            else:
                await call.bot.send_message(
                    user[0],
                    "Ваш заказ подтверждён!\nС вами свяжется менеджер для уточнения доставки."
                )
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю: {e}")
# ========== /КОНЕЦ БЛОКА ==========

@router.message(StateFilter(MakeOrder.choose_delivery))
async def order_delivery(msg: Message, state: FSMContext):
    if is_menu_command(msg):
        await back_to_menu(msg, state)
        return
    if msg.text not in DELIVERY:
        return await msg.answer("Пожалуйста, выберите способ доставки.", reply_markup=delivery_kb())
    await state.update_data(delivery=msg.text)
    await state.set_state(MakeOrder.enter_contacts)
    await msg.answer("Укажите ваши контакты (username, телефон и т.п.):", reply_markup=cancel_kb())

@router.message(StateFilter(MakeOrder.enter_contacts))
async def order_contacts(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    await state.update_data(contacts=msg.text)
    await state.set_state(MakeOrder.wait_payment)
    await msg.answer(
        f"Оплатите заказ по карте <code>{ADMIN_CARD}</code> и отправьте скриншот перевода.",
        parse_mode='HTML', reply_markup=cancel_kb()
    )

@router.message(StateFilter(MakeOrder.wait_payment), F.photo)
async def order_payment_screen(msg: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get('product_id') or not data.get('delivery') or not data.get('contacts'):
        await msg.answer("Ошибка: недостающие данные заказа. Попробуйте начать сначала.", reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))
        await state.clear()
        return
    async with aiosqlite.connect('shop.db') as db:
        await db.execute(
            "INSERT INTO orders (user_id, username, product_id, delivery, contacts, payment_screen, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (msg.from_user.id, msg.from_user.username, data['product_id'], data['delivery'], data['contacts'], msg.photo[-1].file_id)
        )
        await db.commit()
    await msg.answer(
        f"Ваш заказ оформлен и ожидает подтверждения. Если не подтвердится в течение 24 часов, напишите {ADMIN_CONTACT}.",
        reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS)
    )
    await bot.send_message(
        ADMIN_IDS[0],
        f"Новый заказ.\nПользователь: @{msg.from_user.username}\nКонтакты: {data['contacts']}\n"
        f"Доставка: {data['delivery']}\nДля подтверждения используйте 📦 Заказы в админ-меню.",
    )
    await bot.send_photo(ADMIN_IDS[0], msg.photo[-1].file_id)
    await state.clear()

@router.message(StateFilter(MakeOrder.wait_payment))
async def order_payment_text(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    await msg.answer("Пожалуйста, отправьте скриншот перевода.", reply_markup=cancel_kb())

@router.message(F.text == '➕ Добавить заказ')
async def user_add_order(msg: Message):
    await msg.answer("Чтобы добавить заказ, воспользуйтесь кнопкой 📦 Сделать заказ или выберите товар в каталоге.",
                     reply_markup=menu_kb(msg.from_user.id in ADMIN_IDS))

@router.message(F.text == '🔧 Админ-меню', F.from_user.id.in_(ADMIN_IDS))
async def admin_menu(msg: Message):
    await msg.answer("Админ-меню:", reply_markup=admin_kb())

@router.message(F.text == '➕ Добавить товар', F.from_user.id.in_(ADMIN_IDS))
async def admin_add_product(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddProduct.choose_type)
    await msg.answer("Тип товара?", reply_markup=types_kb())

@router.message(StateFilter(AddProduct.choose_type))
async def prod_type(msg: Message, state: FSMContext):
    if is_menu_command(msg):
        await back_to_menu(msg, state)
        return
    if msg.text not in TYPES:
        return await msg.answer("Выберите из списка.", reply_markup=types_kb())
    await state.update_data(type=msg.text)
    await state.set_state(AddProduct.choose_category)
    await msg.answer("Категория товара?", reply_markup=category_kb())

@router.message(StateFilter(AddProduct.choose_category))
async def prod_cat(msg: Message, state: FSMContext):
    if is_menu_command(msg):
        await back_to_menu(msg, state)
        return
    if msg.text not in CATEGORIES:
        return await msg.answer("Выберите из списка.", reply_markup=category_kb())
    await state.update_data(category=msg.text)
    await state.set_state(AddProduct.enter_name)
    await msg.answer("Название товара:", reply_markup=cancel_kb())

@router.message(StateFilter(AddProduct.enter_name))
async def prod_name(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    await state.update_data(name=msg.text)
    await state.set_state(AddProduct.enter_desc)
    await msg.answer("Описание товара:", reply_markup=cancel_kb())

@router.message(StateFilter(AddProduct.enter_desc))
async def prod_desc(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    await state.update_data(desc=msg.text)
    await state.set_state(AddProduct.enter_price)
    await msg.answer("Цена товара (только число):", reply_markup=cancel_kb())

@router.message(StateFilter(AddProduct.enter_price))
async def prod_price(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    try:
        price = int(msg.text)
    except Exception:
        return await msg.answer("Только число!", reply_markup=cancel_kb())
    await state.update_data(price=price)
    await state.set_state(AddProduct.enter_photo)
    await msg.answer("Отправьте фото товара:", reply_markup=cancel_kb())

@router.message(StateFilter(AddProduct.enter_photo), F.photo)
async def prod_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect('shop.db') as db:
        await db.execute(
            "INSERT INTO products (type, category, name, desc, price, photo_id) VALUES (?, ?, ?, ?, ?, ?)",
            (data['type'], data['category'], data['name'], data['desc'], data['price'], msg.photo[-1].file_id)
        )
        await db.commit()
    await msg.answer("Товар добавлен!", reply_markup=admin_kb())
    await state.clear()

@router.message(StateFilter(AddProduct.enter_photo))
async def prod_photo_wrong(msg: Message, state: FSMContext):
    if is_menu_command(msg) or msg.text == '❌ Отмена':
        await back_to_menu(msg, state)
        return
    await msg.answer("Пожалуйста, отправьте фото товара.", reply_markup=cancel_kb())

@router.message(F.text == '📦 Заказы', F.from_user.id.in_(ADMIN_IDS))
async def admin_orders(msg: Message):
    async with aiosqlite.connect('shop.db') as db:
        res = await db.execute(
            "SELECT o.id, o.user_id, o.username, p.name, o.delivery, o.contacts, o.status, o.payment_screen "
            "FROM orders o LEFT JOIN products p ON o.product_id = p.id ORDER BY o.status DESC, o.id DESC"
        )
        orders = await res.fetchall()
    if not orders:
        await msg.answer("Нет заказов.", reply_markup=admin_kb())
        return
    for o in orders:
        kb = None
        if o[6] == 'pending':
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{o[0]}")]
                ]
            )
        txt = (
            f"Заказ #{o[0]}\nПользователь: {o[2]}\nТовар: {o[3]}\n"
            f"Доставка: {o[4]}\nКонтакты: {o[5]}\nСтатус: {o[6]}"
        )
        await msg.answer_photo(o[7], txt, reply_markup=kb)

@router.message(F.text == '🔙 Назад')
async def back(msg: Message, state: FSMContext):
    await back_to_menu(msg, state)

async def main():
    await db_init()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())