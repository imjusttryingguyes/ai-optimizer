# 🚀 Разворачивание Phase 4 Dashboard на облаке

## 📊 Готовые варианты хостинга

| Хостинг | Цена | Сложность | Рекомендация |
|---------|------|-----------|--------------|
| **Hugging Face Spaces** | ⭐ Бесплатно | Очень просто | ✅ **ЛУЧШИЙ ВЫБОР** |
| **Render.com** | ⭐ Бесплатно (14 дней) | Просто | Хорош для testing |
| **Railway** | 💵 ~$5/мес | Просто | Стабильный |
| **Heroku** | 💵 ~$7/мес | Просто | Старый стандарт |

---

## 🏆 Вариант 1: Hugging Face Spaces (РЕКОМЕНДУЕТСЯ)

### ✅ Преимущества
- Полностью бесплатно
- Легко настроить (2 клика)
- Автоматический перезапуск
- Просто шарить ссылку

### 📝 Инструкция

**Шаг 1: Создайте аккаунт**
```
Перейти: https://huggingface.co/join
Войти с GitHub/Google/Email
```

**Шаг 2: Создайте Space**
```
1. Нажать "Create new Space" (huggingface.co/new-space)
2. Название: "phase4-analytics" (или своё)
3. License: OpenRAIL (default)
4. Space SDK: Streamlit
5. Public/Private: (на ваш выбор)
6. Нажать "Create Space"
```

**Шаг 3: Загрузьте файлы**
```
Способ A (через UI):
1. Нажать "Files" в Space
2. Drag-drop файлы из /opt/phase4/deployment/

Способ B (через Git):
git clone https://huggingface.co/spaces/[ваш-ник]/phase4-analytics
cd phase4-analytics
cp -r /opt/phase4/deployment/* .
git add .
git commit -m "Add Phase 4 Dashboard"
git push
```

**Шаг 4: Готово!**
```
Space автоматически запустится
Ссылка: https://huggingface.co/spaces/[ваш-ник]/phase4-analytics
```

### ⚠️ Важно для Spaces

Измените `dashboard.py` для подключения к БД:

```python
# В начале dashboard.py добавьте:
import os
from dotenv import load_dotenv

# Для Hugging Face Spaces
if os.getenv('SPACE_ID'):
    load_dotenv('/tmp/.env')  # Загружаем переменные из secrets
```

**Добавьте Secrets в Space:**
1. Settings → Repository secrets
2. Добавьте:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `YANDEX_TOKEN`
   - `YANDEX_LOGIN`

---

## 🚀 Вариант 2: Railway.app (СТАБИЛЬНЫЙ)

### 💰 Цена
- Первые 5$ бесплатно в месяц
- Потом ~$5-10/месяц

### 📝 Инструкция

**Шаг 1: Зарегистрируйтесь**
```
https://railway.app
(Войти через GitHub)
```

**Шаг 2: Создайте новый проект**
```
1. "Create a new Project"
2. "Deploy from GitHub repo" (или загрузить ZIP)
```

**Шаг 3: Выберите runtime**
```
- Python 3.11
- Установить из requirements.txt
```

**Шаг 4: Переменные окружения**
```
Settings → Variables
Добавить все из .env файла
```

**Шаг 5: Deploy**
```
Railway автоматически запустит
Ссылка будет в "Deployments"
```

---

## 📦 Вариант 3: Docker (для любого хостинга)

Создайте `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
```

Затем загрузьте на:
- **Docker Hub** (публичный реестр)
- **Heroku** (платный)
- **AWS** (сложный)
- **DigitalOcean** (~$5/мес)

---

## 🔧 Что нужно подготовить

### Файлы в `/opt/phase4/deployment/`:

```
✅ app.py                      # Главный файл
✅ dashboard.py               # Streamlit UI
✅ requirements.txt           # Зависимости
✅ .streamlit/config.toml     # Конфиг
✅ .gitignore                 # Git ignore
```

### Переменные окружения для хостинга

```
# PostgreSQL
DB_HOST=your-db-host
DB_PORT=5432
DB_USER=your-user
DB_PASSWORD=your-pass
DB_NAME=your-db

# Yandex API
YANDEX_TOKEN=your-token
YANDEX_LOGIN=your-login
```

---

## 🔐 Безопасность

### ⚠️ НИКОГДА не выкладывайте:
- ❌ `.env` файл
- ❌ API токены в коде
- ❌ Пароли в README

### ✅ ДЕЛАЙТЕ так:
- ✅ Используйте Secrets (на каждом хостинге)
- ✅ `.env` в `.gitignore`
- ✅ `.env.example` с шаблоном

---

## 📝 .env.example (выложите вместо .env)

```env
# Database Connection
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=change_me
DB_NAME=ai_optimizer

# Yandex Direct API
YANDEX_TOKEN=change_me
YANDEX_LOGIN=mmg-sz

# App Settings
DEBUG=false
LOG_LEVEL=INFO
```

---

## 🎯 Быстрый старт

### Для Hugging Face (проще всего):

```bash
# 1. Подготовьте папку
cd /opt/phase4/deployment

# 2. Создайте Git репо (если нужно)
git init
git add .
git commit -m "Initial commit"

# 3. Загрузитесь на GitHub
git push origin main

# 4. На HuggingFace подключите репо
# Settings → Connect a repository → выберите ваш репо

# 5. Готово! Space запустится автоматически
```

---

## ✨ После разворачивания

1. **Проверьте работоспособность:**
   - Откройте ссылку пространства
   - Пройдитесь по всем 3 страницам
   - Проверьте, что данные загружаются

2. **Настройте обновление данных:**
   ```bash
   # На вашем сервере запустите каждый день:
   python3 /opt/phase4/extraction/level1_kpi.py
   python3 /opt/phase4/extraction/level2_trends.py
   ```

3. **Мониторинг:**
   - Проверяйте логи хостинга
   - Отслеживайте использование ресурсов

---

## 🆘 Проблемы

### Dashboard открывается пусто
```
Решение: Проверьте переменные окружения (Secrets)
```

### Ошибка подключения к БД
```
Решение: Убедитесь, что DB_HOST доступен с хостинга
```

### Медленная загрузка данных
```
Решение: Увеличьте кеш Streamlit (see .streamlit/config.toml)
```

---

## 📞 Рекомендация

**Я советую Hugging Face Spaces, потому что:**
- ✅ Полностью бесплатно
- ✅ Не нужно платить карточкой
- ✅ Легко обновлять через Git
- ✅ Сообщество поддерживает
- ✅ Отлично работает с Streamlit

**Инструкция:**
1. Создать Space на HF
2. Загрузить файлы из `/opt/phase4/deployment/`
3. Добавить Secrets
4. Готово!

---

**Вопросы?** Пиши — помогу развернуть! 🚀
