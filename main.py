import requests
import pandas as pd
import re
import os
import time
from pathlib import Path
from bs4 import BeautifulSoup

# ============================================================
# БЛОК 1: Работа с ключом авторизации
# ============================================================

ENV_FILE = ".env"
AUTH_KEY_NAME = "KAZAN_AUTH_HEADER"

def load_auth_key():
    """Загружает ключ из .env файла или запрашивает у пользователя"""
    # 1. Проверяем файл .env
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{AUTH_KEY_NAME}="):
                    key = line.split("=", 1)[1].strip()
                    if key:
                        print(f"✅ Ключ авторизации загружен из {ENV_FILE}")
                        return key
    
    # 2. Если файла нет или ключ пустой — запрашиваем у пользователя
    print("\n" + "="*60)
    print("🔑 Требуется ключ авторизации KazanExpress")
    print("="*60)
    print("Вставьте ваш ключ (начинается с 'Basic ...')")
    print("Он будет сохранён в файл .env и не потребуется в следующий раз\n")
    
    key = input("Ваш ключ: ").strip()
    
    if not key:
        print("❌ Ключ не введён. Завершение работы.")
        return None
    
    # 3. Сохраняем ключ в .env
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(f"{AUTH_KEY_NAME}={key}\n")
    
    print(f"✅ Ключ сохранён в {ENV_FILE}")
    return key


# ============================================================
# БЛОК 2: Скачивание фотографий
# ============================================================

PHOTOS_DIR = "photos"

def download_photos(product_id: int, photos_urls: list) -> dict:
    """
    Скачивает все фото товара в папку photos/{product_id}/
    Возвращает словарь с информацией о скачивании
    """
    product_dir = Path(PHOTOS_DIR) / str(product_id)
    product_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    skipped = 0
    errors = 0
    saved_files = []
    
    for i, url in enumerate(photos_urls, 1):
        file_path = product_dir / f"photo_{i}.jpg"
        
        # Если файл уже существует и не пустой — пропускаем
        if file_path.exists() and file_path.stat().st_size > 0:
            skipped += 1
            saved_files.append(str(file_path))
            continue
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Проверяем, что это действительно изображение
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type and len(response.content) < 1000:
                print(f"  ⚠️ Фото {i} не является изображением, пропускаем")
                errors += 1
                continue
            
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            downloaded += 1
            saved_files.append(str(file_path))
            
        except requests.exceptions.RequestException as e:
            print(f"   Ошибка скачивания фото {i}: {e}")
            errors += 1
        
        # Небольшая задержка, чтобы не перегружать сервер
        time.sleep(0.2)
    
    return {
        "папка": str(product_dir),
        "скачано": downloaded,
        "пропущено": skipped,
        "ошибок": errors,
        "всего": len(photos_urls),
        "файлы": saved_files
    }


# ============================================================
# БЛОК 3: GraphQL и обработка товара
# ============================================================

GRAPHQL_URL = "https://graphql.kazanexpress.ru/"

QUERY = """
query GetProduct($id: Int!) {
  product(id: $id) {
    id
    title
    shortDescription
    description
    minSellPrice
    rating
    category {
      title
    }
    photos {
      key
      original {
        high
      }
    }
    characteristics {
      title
      values {
        title
      }
    }
    skuList {
      id
      skuTitle
      sellPrice
      availableAmount
    }
  }
}
"""

def extract_product_id(url):
    """Извлекает ID товара из URL"""
    clean_url = url.split('?')[0]
    match = re.search(r'-(\d+)$', clean_url)
    if match:
        return int(match.group(1))
    return None

def clean_html(html_text):
    """Удаляет HTML-теги"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" | ", strip=True)

def get_product_data(product_id: str, auth_header: str):
    """Получает данные о товаре и скачивает фото"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {"query": QUERY, "variables": {"id": int(product_id)}}
    
    try:
        response = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 400:
            print(f"\n  ⚠️ Ошибка в запросе (400). Ответ сервера: {response.text[:200]}")
            return None
            
        if response.status_code == 401:
            print(f"  ⚠️ Ошибка авторизации (401). Проверьте ключ.")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data or not data.get("data", {}).get("product"):
            return None
            
        product = data["data"]["product"]
        
        # === Собираем ссылки на все фото ===
        photos = product.get("photos", [])
        photo_urls = []
        for photo in photos:
            if photo.get("original"):
                url = photo["original"].get("high", "")
                if url:
                    photo_urls.append(url)
        
        # === Скачиваем фото ===
        print(f"\n  📥 Скачивание фото ({len(photo_urls)} шт.)...", end=" ")
        photo_info = download_photos(product_id, photo_urls)
        print(f"✅ скачано: {photo_info['скачано']}, пропущено: {photo_info['пропущено']}")
        
        # === Характеристики ===
        characteristics = {}
        for char in product.get("characteristics", []):
            title = char.get("title")
            values = [v.get("title") for v in char.get("values", []) if v.get("title")]
            if title and values:
                characteristics[title] = ", ".join(values)
        
        # === SKU и цена ===
        sku_list = product.get("skuList", [])
        first_sku = sku_list[0] if sku_list else {}
        price = first_sku.get("sellPrice", product.get("minSellPrice", 0)) / 100
        
        return {
            "ID товара": product.get("id"),
            "SKU ID": first_sku.get("id", ""),
            "Название": product.get("title"),
            "Краткое описание": product.get("shortDescription"),
            "Полное описание": clean_html(product.get("description")),
            "Категория": product.get("category", {}).get("title") if product.get("category") else "",
            "Рейтинг": product.get("rating"),
            "Цена (₽)": round(price, 2),
            "Остаток (шт)": first_sku.get("availableAmount", 0),
            "Артикул": first_sku.get("skuTitle", ""),
            "Характеристики": ", ".join([f"{k}: {v}" for k, v in characteristics.items()]),
            "Папка с фото": photo_info["папка"],
            "Кол-во фото": photo_info["всего"],
            "Скачано фото": photo_info["скачано"],
        }
    except Exception as e:
        print(f"  ❌ Ошибка при запросе товара {product_id}: {e}")
        return None


# ============================================================
# БЛОК 4: Главная функция
# ============================================================

def main():
    print("="*60)
    print("🛒 Экспорт товаров KazanExpress / Магнит Маркет")
    print("="*60 + "\n")
    
    # 1. Получаем ключ авторизации
    auth_header = load_auth_key()
    if not auth_header:
        return
    
    # 2. Получаем список ссылок
    input_file = "links.txt"
    urls = []

    if os.path.exists(input_file):
        print(f"\n📂 Найден файл '{input_file}'. Читаем ссылки из него...")
        with open(input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and line.startswith('http')]
    else:
        print("\n💡 Файл 'links.txt' не найден.")
        print("Введите ссылку на товар (или несколько через пробел/запятую):")
        user_input = input("> ").strip()
        urls = re.split(r'[\s,]+', user_input)
        urls = [url for url in urls if url.startswith('http')]

    if not urls:
        print("❌ Корректные ссылки не найдены. Завершение работы.")
        return

    # 3. Обрабатываем товары
    print(f"\n⏳ Начинаем обработку {len(urls)} ссылок...")
    all_products = []
    
    for url in urls:
        product_id = extract_product_id(url)
        if not product_id:
            print(f"\n⚠️ Не удалось извлечь ID из ссылки: {url}")
            continue
            
        print(f"\n{'='*60}")
        print(f"🔍 Товар ID: {product_id}")
        print(f"{'='*60}")
        
        product_data = get_product_data(product_id, auth_header)
        
        if product_data:
            product_data["Исходная ссылка"] = url
            all_products.append(product_data)
            print(f"  ✅ Товар {product_id} обработан")
        else:
            print(f"  ❌ Товар {product_id} не найден или нет данных")
        
        # Пауза между товарами
        time.sleep(0.5)
    
    # 4. Сохраняем результат
    if all_products:
        excel_filename = r"C:\Users\usr\Downloads\Выгрузка_товаров.xlsx"
        df = pd.DataFrame(all_products)
        df.to_excel(excel_filename, index=False, engine="openpyxl")
        
        print(f"\n{'='*60}")
        print(f"🎉 ГОТОВО!")
        print(f"{'='*60}")
        print(f" Excel-файл: {excel_filename}")
        print(f"📁 Фото сохранены в папку: {Path.cwd() / PHOTOS_DIR}")
        print(f"📦 Обработано товаров: {len(all_products)}")
        
        # Статистика по фото
        total_photos = sum(p["Кол-во фото"] for p in all_products)
        total_downloaded = sum(p["Скачано фото"] for p in all_products)
        print(f"🖼️  Всего фото: {total_photos}, скачано: {total_downloaded}")
    else:
        print("\n❌ Не удалось получить данные ни по одному товару.")

if __name__ == "__main__":
    main()