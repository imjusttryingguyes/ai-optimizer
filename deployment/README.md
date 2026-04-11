# 🚀 Phase 4 Analytics Dashboard - Ready for Deployment

## 📦 Что здесь?

Готовый пакет для разворачивания на облаке в одну команду.

## 🎯 Быстрый старт

### Для Hugging Face Spaces (РЕКОМЕНДУЕТСЯ)

1. **Создайте Space:**
   - Перейти: https://huggingface.co/new-space
   - Выбрать: Streamlit SDK
   - Создать

2. **Загрузите файлы:**
   ```bash
   git clone https://huggingface.co/spaces/[ваш-ник]/phase4-analytics
   cd phase4-analytics
   cp -r . /opt/phase4/deployment/
   git add .
   git commit -m "Add dashboard"
   git push
   ```

3. **Добавьте Secrets:**
   - Settings → Repository secrets
   - Добавьте переменные из .env.example

4. **Готово!**
   - Space автоматически запустится
   - Ссылка: https://huggingface.co/spaces/[ваш-ник]/phase4-analytics

### Файлы в папке:

```
app.py                      ← Главный файл для запуска
dashboard.py               ← Streamlit интерфейс
requirements.txt           ← Зависимости Python
.streamlit/config.toml     ← Конфигурация
.env.example               ← Пример переменных
.gitignore                 ← Что не выкладывать
```

### Переменные окружения (Secrets):

```
DB_HOST           = ваш-хост
DB_PORT           = 5432
DB_USER           = postgres
DB_PASSWORD       = пароль
DB_NAME           = ai_optimizer
YANDEX_TOKEN      = токен
YANDEX_LOGIN      = mmg-sz
```

---

## 📖 Полная документация

Смотри: `../HOSTING_GUIDE.md`

Там описаны все варианты:
- Hugging Face (бесплатно) ⭐
- Railway (дешево)
- Docker (универсально)
- Heroku (старый стандарт)

---

## 🔐 Безопасность

- ❌ НЕ выкладывайте .env
- ✅ Используйте Secrets хостинга
- ✅ .env в .gitignore

---

**Готово к разворачиванию!** 🎉
