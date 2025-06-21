# crm.py
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List

load_dotenv()
BITRIX_URL = os.getenv("BITRIX_WEBHOOK")


def create_lead(data: Dict) -> bool:
    """Создание лида в Bitrix24"""
    if not BITRIX_URL:
        print("❌ BITRIX_WEBHOOK не указан в .env")
        return False

    payload = {
        "fields": {
            "TITLE": f"Заказ от {data.get('name', 'Без имени')}",
            "NAME": data.get("name", "Telegram клиент"),
            "PHONE": [{"VALUE": data.get("phone", "Не указан"), "VALUE_TYPE": "WORK"}],
            "COMMENTS": format_comment(data),
            "SOURCE_ID": "TELEGRAM",
            "CURRENCY_ID": "RUB"
        }
    }

    try:
        response = requests.post(BITRIX_URL, json=payload, timeout=15)

        if response.status_code == 200:
            result = response.json()
            if result.get("result"):
                print(f"✅ Лид создан в Bitrix24. ID: {result['result']}")
                return True
            else:
                print(f"⚠️ Ошибка создания лида: {result}")
                return False
        else:
            print(f"❌ HTTP ошибка Bitrix: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Ошибка при отправке в Bitrix24: {e}")
        return False


def format_comment(data: Dict) -> str:
    """Форматирование комментария для лида"""
    comment = f"🗓 Время заказа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    comment += f"🆔 Telegram ID: {data.get('telegram_id')}\n"
    comment += f"📱 Телефон: {data.get('phone', 'не указан')}\n"
    comment += f"📍 Адрес: {data.get('address', 'не указан')}\n\n"

    comment += "🛒 Заказ:\n"
    total = 0
    for item in data.get("products", []):
        name = item.get("name", "товар")
        quantity = int(item.get("quantity", 1))
        price = int(item.get("priece", 0))
        item_total = price * quantity
        total += item_total
        comment += f"• {name} x{quantity} = {item_total}₽\n"

    comment += f"\n💰 Общая сумма: {total}₽"
    return comment
