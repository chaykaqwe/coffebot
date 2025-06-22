import asyncio
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot import bot
import keyboard as kb
from google_sheets import get_products_by_category, get_product
from crm import create_lead, debug_create_lead, test_bitrix_connection

router = Router(name=__name__)
tasks = {}
reply_events: dict[int, asyncio.Event] = {}

# Сохраняем последнее отправленное сообщение для удаления
active_messages: dict[int, list[int]] = {}


class OrderStates(StatesGroup):
    choosing_category = State()
    choosing_item = State()
    choosing_quantity = State()
    adding_more = State()
    confirming_order = State()
    entering_name = State()  # Добавлено состояние для имени
    entering_contact = State()
    entering_address = State()
    editing_quantity = State()


async def delete_active_messages(tg_id: int):
    """Удаляет все сохранённые сообщения пользователя."""
    if tg_id in active_messages:
        for msg_id in active_messages[tg_id]:
            try:
                await bot.delete_message(tg_id, msg_id)
            except Exception as e:
                print(f"[{tg_id}] Не удалось удалить сообщение {msg_id}: {e}")
        active_messages[tg_id] = []


@router.message(CommandStart())
async def cmd(mes: Message):
    await mes.answer("🌟 Добро пожаловать в нашу кофейню!\n"
                     "☕️ Здесь вы можете сделать заказ онлайн\n"
                     "📋 Посмотреть историю заказов\n"
                     "Выберите действие:", reply_markup=kb.main)


@router.message(F.text == "Сделать заказ☕")
async def show_categories(mes: Message, state: FSMContext):
    await mes.answer("Выберете категорию", reply_markup=kb.create_categories())
    await state.set_state(OrderStates.choosing_category)


@router.callback_query(F.data.startswith("category_"))
async def show_product(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("category_", "")
    products = get_products_by_category(category)
    await callback.message.answer("Выберете товар", reply_markup=kb.create_products(products))
    await callback.answer()
    await state.set_state(OrderStates.choosing_item)


@router.callback_query(F.data == 'return_categories')
async def return_to_categories(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберете категорию", reply_markup=kb.create_categories())
    await callback.answer()
    await state.set_state(OrderStates.choosing_category)


@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery, state: FSMContext):
    name_product = callback.data.replace("product_", "")
    product = get_product(name_product)[0]

    # Просто сохраняем продукт как текущий, но не добавляем в корзину
    await state.update_data(current_product={
        "id": product[0],
        "name": product[1],
        "description": product[2],
        'priece': int(product[3]),
        "calories": product[4],
        "proteins": product[5],
        "fats": product[6],
        "sugar": product[7],
        "image_url": product[8],
        "category": product[9]
    })

    await callback.message.answer_photo(
        photo=product[8],
        caption=(
            f"{product[9][0]}{product[1]}\n\n📝{product[2]}\n"
            f"💰Цена {product[3]}\n"
            f"📊КБЖУ: K : {product[4]}, Б : {product[5]}, Ж : {product[6]}, У : {product[7]}"
        ),
        reply_markup=kb.create_quantity()
    )

    await callback.answer()
    await state.set_state(OrderStates.choosing_quantity)


@router.callback_query(F.data.startswith("quantity_"))
async def set_quantity(callback: CallbackQuery, state: FSMContext):
    quantity = int(callback.data.replace("quantity_", ""))
    data = await state.get_data()

    product = data.get("current_product")
    if not product:
        await callback.message.answer("❌ Ошибка: товар не выбран.")
        return

    product["quantity"] = quantity

    products = data.get("products", [])
    products.append(product)

    await state.update_data(products=products)
    await state.update_data(current_product=None)

    await show_cart_summary_message(callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(F.data == "add_more")
async def show_categories(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберете категорию", reply_markup=kb.create_categories())
    await state.set_state(OrderStates.choosing_category)
    await callback.answer()


@router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get("products", [])

    if not products:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        await callback.answer()
        return

    message = "🛒 Ваша корзина:\n\n"
    total = 0
    for i, p in enumerate(products):
        subtotal = int(p["priece"]) * p["quantity"]
        total += subtotal
        message += f"{i + 1}. {p['name']} x{p['quantity']} = {subtotal}₽\n"

    message += f"\n💰 Сумма: {total}₽"
    await callback.message.answer(message, reply_markup=kb.create_cart_buttons(products))
    await callback.answer()


@router.callback_query(F.data.startswith("remove_"))
async def remove_item(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.replace("remove_", ""))
    data = await state.get_data()
    products = data.get("products", [])

    if 0 <= index < len(products):
        removed = products.pop(index)
        await state.update_data(products=products)
        await callback.message.answer(f"❌ {removed['name']} удалён из корзины.")
    else:
        await callback.message.answer("⚠️ Не удалось удалить товар.")

    await show_cart(callback, state)  # показать обновлённую корзину


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(products=[])
    await callback.message.answer("🗑 Корзина очищена.")
    await callback.answer()


@router.callback_query(F.data.startswith("editqty_"))
async def start_quantity_edit(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.replace("editqty_", ""))
    await state.update_data(edit_index=index)
    await callback.message.answer("✏ Введите новое количество:")
    await state.set_state(OrderStates.editing_quantity)
    await callback.answer()


@router.message(OrderStates.editing_quantity)
async def update_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите положительное целое число.")
        return

    data = await state.get_data()
    products = data.get("products", [])
    index = data.get("edit_index")

    if index is not None and 0 <= index < len(products):
        products[index]["quantity"] = qty
        await state.update_data(products=products)
        await message.answer(f"✅ Обновлено: {products[index]['name']} теперь x{qty}", reply_markup=kb.back_to_cart())
    else:
        await message.answer("⚠️ Не удалось найти товар для изменения.")

    await state.set_state(OrderStates.confirming_order)


@router.callback_query(F.data == "purchase")
async def purchase_cart(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("👤 Как к вам обращаться? Введите ваше имя:", reply_markup=kb.return_to_cart_summary())
    await state.set_state(OrderStates.entering_name)
    await callback.answer()


@router.message(OrderStates.entering_name)
async def receive_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя (не менее 2 символов).")
        return

    await state.update_data(name=name)
    await message.answer(f"✅ Приятно познакомиться, {name}! Теперь введите номер телефона в формате +7xxxxxxxxxx")
    await state.set_state(OrderStates.entering_contact)


@router.message(OrderStates.entering_contact)
async def receive_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    # Более гибкая проверка телефона
    if not (phone.startswith('+7') or phone.startswith('8') or phone.startswith('7')):
        await message.answer(
            "❌ Пожалуйста, введите корректный номер телефона (например, +79991234567, 89991234567 или 79991234567).")
        return

    # Нормализация номера
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    elif phone.startswith('7') and not phone.startswith('+7'):
        phone = '+' + phone

    await state.update_data(phone=phone)
    await message.answer("✅ Номер сохранён. Теперь укажите адрес доставки:")
    await state.set_state(OrderStates.entering_address)


@router.message(OrderStates.entering_address)
async def receive_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if len(address) < 5:
        await message.answer("❌ Пожалуйста, введите корректный адрес (не менее 5 символов).")
        return

    await state.update_data(address=address)

    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")
    products = data.get("products", [])

    # Подсчитываем итоговую сумму
    total = sum(int(p["priece"]) * int(p.get("quantity", 1)) for p in products)

    await message.answer(
        f"📋 Проверьте данные заказа:\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n"
        f"💰 Сумма заказа: {total}₽\n\n"
        f"✅ Всё верно? Подтверждаем заказ?",
        reply_markup=kb.confirm_order_menu()
    )
    await state.set_state(OrderStates.confirming_order)


@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Получаем данные пользователя из Telegram
    user = callback.from_user
    telegram_name = user.first_name
    if user.last_name:
        telegram_name += f" {user.last_name}"

    lead_data = {
        "name": data.get("name", telegram_name),  # Используем введённое имя или данные из Telegram
        "phone": data.get("phone"),
        "address": data.get("address"),
        "telegram_id": user.id,
        "telegram_username": user.username,  # Убираем проверку на None
        "products": data.get("products", [])
    }

    print(f"🔄 Создаём заказ для пользователя: {lead_data['name']}")
    print(f"📦 Товаров в заказе: {len(lead_data['products'])}")

    # Выводим детали заказа для отладки
    total_amount = 0
    for product in lead_data['products']:
        price = int(product.get("priece", 0))
        quantity = int(product.get("quantity", 1))
        subtotal = price * quantity
        total_amount += subtotal
        print(f"   - {product.get('name')}: {price}₽ x {quantity} = {subtotal}₽")

    print(f"💰 Общая сумма заказа: {total_amount}₽")

    # Используем debug версию для отладки
    if debug_create_lead(lead_data):
        await callback.message.answer(
            f"✅ Заказ успешно подтверждён и отправлен в систему!\n"
            f"💰 Сумма заказа: {total_amount}₽\n"
            f"📞 Наш менеджер свяжется с вами в ближайшее время.\n"
            f"☕️ Спасибо за заказ!",
            reply_markup=kb.main
        )
    else:
        await callback.message.answer(
            "❌ Произошла ошибка при создании заказа.\n"
            "📞 Пожалуйста, свяжитесь с нами напрямую или попробуйте позже.\n"
            "Ваш заказ сохранён и будет обработан.",
            reply_markup=kb.main
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "show_cart_summary")
async def show_cart_summary(callback: CallbackQuery, state: FSMContext):
    await show_cart_summary_message(callback.message.chat.id, state)
    await callback.answer()


async def show_cart_summary_message(chat_id: int, state: FSMContext):
    data = await state.get_data()
    products = data.get("products", [])

    total_cost = sum(int(p["priece"]) * int(p.get("quantity", 1)) for p in products)
    total_quantity = sum(int(p.get("quantity", 1)) for p in products)

    return await bot.send_message(
        chat_id,
        f'✅ Добавлено в корзину!\n\n'
        f'🛒 В корзине: {total_quantity} товаров\n'
        f'💰 Сумма заказа: {total_cost}₽\n'
        'Что дальше?',
        reply_markup=kb.cart_menu()
    )


# Команда для тестирования CRM
@router.message(F.text == "/test_crm")
async def test_crm(message: Message):
    """Тестирование подключения к CRM"""
    if test_bitrix_connection():
        await message.answer("✅ Подключение к Bitrix24 работает!")
    else:
        await message.answer("❌ Проблема с подключением к Bitrix24. Проверьте настройки.")