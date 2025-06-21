import gspread
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = 'C:\\Users\\User\\PycharmProjects\coffeshop2\\app\\coffemenu-462712-5af8851dacc6.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)


def get_categories():
    spreadsheet = client.open("МенюКофейни")
    sheet = spreadsheet.worksheet("Меню")
    column_j = sheet.col_values(10)[1:]
    result = set()
    for value in column_j:
        result.add(value)
    return result


def get_products_by_category(keyword):
    spreadsheet = client.open("МенюКофейни")
    sheet = spreadsheet.worksheet("Меню")
    rows = sheet.get_all_values()

    # Ищем строки, где в колонке J (индекс 9) содержится нужное слово
    matching_rows = []

    for row in rows[1:]:  # Пропускаем заголовок
        if len(row) >= 10 and keyword.lower() in row[9].lower():  # Ищем в 10-й колонке (индекс 9)
            matching_rows.append(row[1])

    return matching_rows


def get_product(name):
    spreadsheet = client.open("МенюКофейни")
    sheet = spreadsheet.worksheet("Меню")
    rows = sheet.get_all_values()

    # Ищем строки, где в колонке J (индекс 9) содержится нужное слово
    matching_rows = []

    for row in rows[1:]:  # Пропускаем заголовок
        if len(row) >= 10 and name.lower() in row[1].lower():  # Ищем в 10-й колонке (индекс 9)
            matching_rows.append(row)
    return matching_rows
