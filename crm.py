# crm.py
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
import json

load_dotenv()
BITRIX_URL = os.getenv("BITRIX_WEBHOOK")


def create_lead(data: Dict) -> bool:
    """Создание лида в Bitrix24"""
    if not BITRIX_URL:
        print("❌ BITRIX_WEBHOOK не указан в .env")
        return False

    # Проверяем корректность URL и формируем правильный endpoint
    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'
    webhook_url = base_url + 'crm.lead.add'

    # Подготавливаем данные
    phone_value = data.get("phone", "")
    if phone_value and not phone_value.startswith("+"):
        phone_value = f"+{phone_value}"

    # Рассчитываем общую сумму заказа
    products = data.get("products", [])
    total_amount = 0
    for item in products:
        price = int(item.get("priece", 0))
        quantity = int(item.get("quantity", 1))
        total_amount += price * quantity

    payload = {
        "fields": {
            "TITLE": f"Заказ из Telegram от {data.get('name', 'клиента')} на {total_amount}₽",
            "NAME": data.get("name", "Telegram клиент"),
            "LAST_NAME": "",
            "PHONE": [{"VALUE": phone_value, "VALUE_TYPE": "WORK"}] if phone_value else [],
            "COMMENTS": format_comment(data),
            "SOURCE_ID": "OTHER",
            "CURRENCY_ID": "RUB",
            "ASSIGNED_BY_ID": 1,
            "OPENED": "Y",
            "OPPORTUNITY": total_amount,  # Сумма сделки
            "STAGE_ID": "NEW"  # Стадия "Новый"
        }
    }

    print(f"🔄 Отправляем запрос в Bitrix24...")
    print(f"URL: {webhook_url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30,
            headers=headers
        )

        print(f"📊 Статус ответа: {response.status_code}")
        print(f"📝 Ответ: {response.text}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"📋 Результат JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")

                if result.get("result"):
                    lead_id = result["result"]
                    print(f"✅ Лид успешно создан в Bitrix24. ID: {lead_id}")

                    # Добавляем товары к лиду - используем улучшенную версию
                    if data.get("products"):
                        products_added = add_products_to_lead_improved(lead_id, data["products"])
                        if products_added:
                            print(f"✅ Товары успешно добавлены к лиду {lead_id}")
                        else:
                            print(f"⚠️ Основной способ не сработал, обновляем комментарий с товарами...")
                            # Если не получилось добавить товары, хотя бы обновим комментарий
                            update_lead_with_products(lead_id, data["products"])

                    return True
                elif result.get("error"):
                    error_msg = result["error"]
                    print(f"❌ Ошибка Bitrix24 API: {error_msg}")
                    return False
                else:
                    print(f"⚠️ Неожиданный ответ от Bitrix24: {result}")
                    return False

            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга JSON ответа: {e}")
                print(f"Сырой ответ: {response.text}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"Текст ошибки: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Таймаут при запросе к Bitrix24")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения с Bitrix24")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка при отправке в Bitrix24: {e}")
        return False


def add_products_to_lead_improved(lead_id: int, products: List[Dict]) -> bool:
    """Улучшенная версия добавления товаров к лиду"""
    if not BITRIX_URL:
        print("❌ BITRIX_WEBHOOK не настроен для добавления товаров")
        return False

    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'

    # Сначала попробуем добавить товары через crm.lead.productrows.set
    webhook_url = base_url + 'crm.lead.productrows.set'

    print(f"🛒 Добавляем {len(products)} товаров к лиду {lead_id}")
    print(f"URL для товаров: {webhook_url}")

    # Формируем массив товарных позиций с минимальными обязательными полями
    product_rows = []
    for i, product in enumerate(products):
        price = float(product.get("priece", 0))
        quantity = float(product.get("quantity", 1))

        # Минимальный набор полей для товарной позиции
        product_row = {
            "PRODUCT_NAME": product.get("name", f"Товар {i + 1}"),
            "PRICE": price,
            "QUANTITY": quantity,
            "CUSTOMIZED": "Y",  # Кастомный товар (не из каталога)
            "MEASURE_CODE": 796,  # Код единицы измерения (шт)
            "MEASURE_NAME": "шт"
        }

        product_rows.append(product_row)
        print(f"   Товар {i + 1}: {product.get('name')} - {price}₽ x {quantity} шт.")

    # Первый способ - через productrows.set
    payload = {
        "id": lead_id,
        "rows": product_rows
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        print(f"📊 Статус ответа товаров (способ 1): {response.status_code}")
        print(f"📝 Ответ товаров (способ 1): {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get("result") is not None:
                print(f"✅ Товары добавлены способом 1 к лиду {lead_id}")
                return True

    except Exception as e:
        print(f"❌ Ошибка способа 1: {e}")

    # Второй способ - через batch запрос
    print("🔄 Пробуем способ 2 - batch запрос...")
    return add_products_batch(lead_id, products)


def add_products_batch(lead_id: int, products: List[Dict]) -> bool:
    """Добавление товаров через batch запрос"""
    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'

    batch_url = base_url + 'batch'

    # Формируем batch команды
    commands = {}
    for i, product in enumerate(products):
        price = float(product.get("priece", 0))
        quantity = float(product.get("quantity", 1))

        commands[
            f"product_{i}"] = f"crm.lead.productrows.set?id={lead_id}&rows[0][PRODUCT_NAME]={product.get('name', f'Товар {i + 1}')}&rows[0][PRICE]={price}&rows[0][QUANTITY]={quantity}&rows[0][CUSTOMIZED]=Y&rows[0][MEASURE_CODE]=796&rows[0][MEASURE_NAME]=шт"

    payload = {
        "cmd": commands
    }

    try:
        response = requests.post(batch_url, json=payload, timeout=30)
        print(f"📊 Статус ответа товаров (способ 2): {response.status_code}")
        print(f"📝 Ответ товаров (способ 2): {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get("result"):
                print(f"✅ Товары добавлены способом 2 к лиду {lead_id}")
                return True

    except Exception as e:
        print(f"❌ Ошибка способа 2: {e}")

    return False


def update_lead_with_products(lead_id: int, products: List[Dict]) -> bool:
    """Обновляем лид с подробной информацией о товарах в комментарии"""
    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'

    update_url = base_url + 'crm.lead.update'

    # Получаем текущий комментарий
    get_url = base_url + 'crm.lead.get'
    try:
        get_response = requests.post(get_url, json={"id": lead_id}, timeout=10)
        current_comments = ""
        if get_response.status_code == 200:
            lead_data = get_response.json()
            if lead_data.get("result") and lead_data["result"].get("COMMENTS"):
                current_comments = lead_data["result"]["COMMENTS"] + "\n\n"
    except:
        current_comments = ""

    # Добавляем детальную информацию о товарах
    products_detail = "🛒 ТОВАРНЫЕ ПОЗИЦИИ:\n"
    products_detail += "=" * 50 + "\n"

    total = 0
    for i, product in enumerate(products, 1):
        name = product.get("name", f"Товар {i}")
        price = int(product.get("priece", 0))
        quantity = int(product.get("quantity", 1))
        subtotal = price * quantity
        total += subtotal

        products_detail += f"📦 Позиция {i}:\n"
        products_detail += f"   Название: {name}\n"
        products_detail += f"   Цена за единицу: {price}₽\n"
        products_detail += f"   Количество: {quantity} шт.\n"
        products_detail += f"   Сумма: {subtotal}₽\n"

        if product.get("description"):
            products_detail += f"   Описание: {product['description']}\n"

        if any([product.get("calories"), product.get("proteins"), product.get("fats"), product.get("sugar")]):
            products_detail += f"   КБЖУ: Калории:{product.get('calories', 0)}, Белки:{product.get('proteins', 0)}, Жиры:{product.get('fats', 0)}, Углеводы:{product.get('sugar', 0)}\n"

        products_detail += "\n"

    products_detail += "=" * 50 + "\n"
    products_detail += f"💰 ИТОГОВАЯ СУММА: {total}₽\n"
    products_detail += f"📊 Количество позиций: {len(products)}\n"

    # Обновляем лид
    payload = {
        "id": lead_id,
        "fields": {
            "COMMENTS": current_comments + products_detail
        }
    }

    try:
        response = requests.post(update_url, json=payload, timeout=30)
        print(f"📊 Статус обновления комментария: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get("result"):
                print(f"✅ Комментарий лида {lead_id} обновлен с товарами")
                return True

    except Exception as e:
        print(f"❌ Ошибка обновления комментария: {e}")

    return False


def format_comment(data: Dict) -> str:
    """Форматирование комментария для лида"""
    comment = f"🗓 Время заказа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
    comment += f"🆔 Telegram ID: {data.get('telegram_id', 'не указан')}\n"

    # Добавляем username если есть
    if data.get('telegram_username'):
        comment += f"👤 Telegram: @{data['telegram_username']}\n"

    comment += f"📱 Телефон: {data.get('phone', 'не указан')}\n"
    comment += f"📍 Адрес доставки: {data.get('address', 'не указан')}\n"
    comment += "=" * 40 + "\n"

    products = data.get("products", [])
    if products:
        comment += "🛒 КРАТКИЙ СПИСОК ЗАКАЗА:\n\n"
        total = 0
        for i, item in enumerate(products, 1):
            name = item.get("name", f"товар #{i}")
            quantity = int(item.get("quantity", 1))
            price = int(item.get("priece", 0))
            item_total = price * quantity
            total += item_total

            comment += f"{i}. {name} - {price}₽ x {quantity} шт. = {item_total}₽\n"

        comment += "\n" + "=" * 40 + "\n"
        comment += f"💰 ИТОГО К ОПЛАТЕ: {total}₽\n"
        comment += f"📦 Позиций в заказе: {len(products)}\n"
        comment += f"🚚 Способ получения: Доставка"
    else:
        comment += "🛒 Корзина пуста (возможная ошибка)"

    return comment


def test_bitrix_connection() -> bool:
    """Тестирование соединения с Bitrix24"""
    if not BITRIX_URL:
        print("❌ BITRIX_WEBHOOK не настроен")
        return False

    # Формируем корректный URL для тестирования
    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'
    test_url = base_url + 'crm.lead.list'

    try:
        response = requests.get(test_url, timeout=10, params={"select": ["ID"], "start": 0})
        print(f"🔍 Тестовый запрос: {test_url}")
        print(f"📊 Статус тестирования: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Соединение с Bitrix24 работает. Найдено лидов: {len(result.get('result', []))}")
            return True
        else:
            print(f"❌ Ошибка тестирования Bitrix24: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка соединения с Bitrix24: {e}")
        return False


def debug_create_lead(data: Dict) -> bool:
    """Версия create_lead с расширенной отладкой"""
    print("🔍 === ОТЛАДКА CRM ===")
    print(f"BITRIX_URL: {BITRIX_URL}")
    print(f"Данные для отправки: {json.dumps(data, ensure_ascii=False, indent=2)}")

    result = create_lead(data)
    print(f"Результат создания лида: {result}")
    print("🔍 === КОНЕЦ ОТЛАДКИ ===")

    return result


# Функция для проверки товарных позиций лида
def check_lead_products(lead_id: int) -> bool:
    """Проверяем, добавились ли товары к лиду"""
    if not BITRIX_URL:
        return False

    base_url = BITRIX_URL.replace('/crm.lead.add.json', '').replace('/crm.lead.add', '')
    if not base_url.endswith('/'):
        base_url += '/'

    check_url = base_url + 'crm.lead.productrows.get'

    try:
        response = requests.post(check_url, json={"id": lead_id}, timeout=10)
        print(f"🔍 Проверяем товары лида {lead_id}: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            products = result.get("result", [])
            print(f"📦 Найдено товарных позиций: {len(products)}")

            for i, product in enumerate(products):
                print(
                    f"   {i + 1}. {product.get('PRODUCT_NAME')} - {product.get('PRICE')}₽ x {product.get('QUANTITY')}")

            return len(products) > 0

    except Exception as e:
        print(f"❌ Ошибка проверки товаров: {e}")

    return False