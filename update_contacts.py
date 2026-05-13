import json
import re
import requests
from bs4 import BeautifulSoup
import urllib3

# Отключаем предупреждения о несекьюрных соединениях (полезно для внутренних сетей)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Пути и ссылки
JSON_PATH = r"c:\Users\Incognitus\YandexDisk\Документы\Мапинг\contact\contact.json"
URL = "https://intranet.pirogov-center.ru/upravlenie.php?org_id=13"

def update_contacts():
    # 1. Читаем текущий JSON
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения JSON: {e}")
        return

    existing_items = data.get("items", [])
    
    # Собираем список уже существующих контактов в нижнем регистре для проверки дублей
    existing_names = [item.get("name", "").strip().lower() for item in existing_items]
    
    def is_duplicate(last_name):
        """
        Проверяет, есть ли переданная фамилия в уже существующих контактах.
        Если есть, возвращает True.
        """
        last_name_lower = last_name.lower()
        for name in existing_names:
            if last_name_lower in name:
                return True
        return False

    # 2. Получаем страницу
    try:
        # verify=False нужен, если во внутренней сети нет доверенного SSL сертификата
        response = requests.get(URL, verify=False)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Ошибка загрузки страницы интранета: {e}")
        return

    soup = BeautifulSoup(html, 'html.parser')

    # 3. Парсим данные
    # Находим все блоки с классом userpage
    user_nodes = soup.find_all(class_="userpage")
    
    new_contacts_count = 0

    for node in user_nodes:
        # Согласно описанию: берем имя из класса phoneusr внутри userpage 
        # (или из самого userpage, если структура немного другая)
        name_node = node.find(class_="phoneusr")
        full_name_raw = name_node.get_text(strip=True) if name_node else node.get_text(strip=True)
        
        if not full_name_raw:
            continue
        
        # Очищаем, оставляем только "Фамилия Имя"
        # Убираем лишние пробелы и разбиваем на слова
        name_parts = full_name_raw.split()
        if len(name_parts) >= 2:
            last_name = name_parts[0]
            formatted_name = f"{name_parts[0]} {name_parts[1]}"
        else:
            last_name = name_parts[0]
            formatted_name = last_name

        # Если контакт с такой фамилией есть в JSON, пропускаем (приоритет у JSON)
        if is_duplicate(last_name):
            continue

        # Ищем блок с номером (внутр.: 2078).
        # Берем весь текстовый контент узла и ищем в нем совпадение по регулярному выражению
        block_text = node.get_text(" ", strip=True)
        match = re.search(r'внутр[\.\s]*:\s*(\d+)', block_text, re.IGNORECASE)
        
        if not match:
            # Если не нашли в самом узле, можем поискать в родительском элементе
            parent_block = node.find_parent()
            if parent_block:
                parent_text = parent_block.get_text(" ", strip=True)
                match = re.search(r'внутр[\.\s]*:\s*(\d+)', parent_text, re.IGNORECASE)

        if not match:
            continue # Если номер не найден, пропускаем контакт
            
        phone_number = match.group(1)

        # Формируем новый контакт по шаблону из contact.json
        new_contact = {"number": phone_number, "name": formatted_name, "firstname": "", "lastname": "", "phone": "", "mobile": "", "email": "", "address": "", "city": "", "state": "", "zip": "", "comment": "", "presence": 0, "starred": 0, "info": ""}

        existing_items.append(new_contact)
        # Сразу добавляем в список существующих, чтобы не добавить дубль с той же страницы
        existing_names.append(formatted_name.lower())
        new_contacts_count += 1

    # 4. Сохраняем обновленный JSON
    if new_contacts_count > 0:
        data["items"] = existing_items
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        print(f"Успешно! Добавлено новых контактов: {new_contacts_count}")
    else:
        print("Новых уникальных контактов для добавления не найдено.")

if __name__ == "__main__":
    update_contacts()
