from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from google_sheets import get_categories

main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Сделать заказ☕")],
                                     [KeyboardButton(text="Мои заказы📃")],
                                     [KeyboardButton(text='О кофейнеℹ️')]])


def create_categories():
    categories = get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.add(InlineKeyboardButton(text=category, callback_data=f"category_{category}"))
    builder.adjust(1)
    keyboard = builder.as_markup()
    return keyboard


def create_products(products):
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.add(InlineKeyboardButton(text=product, callback_data=f"product_{product}"))
    builder.add(InlineKeyboardButton(text="Назад к категорям⬅", callback_data="return_categories"))
    builder.adjust(1)
    keyboard = builder.as_markup()
    return keyboard


def create_quantity():
    builder = InlineKeyboardBuilder()
    for i in range(10):
        if i != 0:
            builder.add(InlineKeyboardButton(text=str(i), callback_data=f"quantity_{i}"))
    builder.add(InlineKeyboardButton(text="✏Ввести свое значение", callback_data="personality_quantity"))
    builder.adjust(3)
    keyboard = builder.as_markup()
    return keyboard


def cart_menu():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕Добавить еще", callback_data="add_more"))
    builder.add(InlineKeyboardButton(text='🛒Моя корзина', callback_data="show_cart"))
    builder.add(InlineKeyboardButton(text='✅Оформить заказ', callback_data="purchase"))
    builder.adjust(1)
    keyboard = builder.as_markup()
    return keyboard


def create_cart_buttons(products):
    buttons = []
    for i, p in enumerate(products):
        buttons.append([
            InlineKeyboardButton(text=f"❌ Удалить {p['name']}", callback_data=f"remove_{i}"),
            InlineKeyboardButton(text="✏ Кол-во", callback_data=f"editqty_{i}")
        ])
    buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="show_cart_summary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_cart():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🛒Вернуться в корзину", callback_data="show_cart"))
    builder.adjust(1)
    keyboard = builder.as_markup()
    return keyboard


def return_to_cart_summary():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅Назад", callback_data="show_cart_summary"))
    keyboard = builder.as_markup()
    return keyboard


def confirm_order_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="show_cart_summary")]
        ]
    )
