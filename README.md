# 🛒 KazanExpress Exporter

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

Скрипт для автоматической выгрузки товаров с **KazanExpress / Магнит Маркет** в Excel с загрузкой всех фотографий.

## ✨ Возможности

- 📥 **Полная выгрузка данных**: название, описание, цена, характеристики, рейтинг, остатки
- ️ **Автоскачивание фото**: все фотографии товара сохраняются в отдельные папки
- 📊 **Экспорт в Excel**: удобный формат .xlsx с готовыми колонками
- 🔑 **Однократный ввод ключа**: ключ авторизации сохраняется в `.env`
- 🔄 **Пакетная обработка**: загрузка множества товаров по списку
- 💾 **Умное кэширование**: не скачивает фото повторно
-  **Логирование**: все действия записываются в файл

## 📋 Требования

- Python 3.8 или выше
- Доступ в интернет
- Ключ авторизации (как получить — см. ниже)

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/MingazovArtur/kazanexpress-exporter.git
cd kazanexpress-exporter

# Установите зависимости
pip install -r requirements.txt
