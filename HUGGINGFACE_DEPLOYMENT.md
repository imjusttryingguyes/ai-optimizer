# 🚀 Развертывание на HuggingFace Spaces

## 📝 Статус
- ✅ Phase 4 система полностью готова
- ✅ Все файлы в `/opt/phase4/deployment/`
- ✅ База данных на 43.245.224.117:5432 (интернет-доступна)
- ⏳ Требуется: Загрузить файлы на HF + добавить Secrets

---

## 📂 Файлы для загрузки

Из `/opt/phase4/deployment/` загрузить на HF Space:

| Файл | Размер | Назначение |
|------|--------|-----------|
| `app.py` | 136 B | Entry point для Streamlit |
| `dashboard.py` | 16 KB | Основной dashboard + API |
| `requirements.txt` | 121 B | Python зависимости |
| `.streamlit/config.toml` | 304 B | Streamlit конфиг |
| `README.md` | 2.2 KB | Документация |
| `.env.example` | 400 B | Шаблон переменных окружения |

**Итого**: 44 KB

---

## 🔐 Необходимые Secrets

В HuggingFace Space Settings → Repository secrets добавить:

```
DB_HOST = 43.245.224.117
DB_PORT = 5432
DB_USER = aiopt
DB_PASSWORD = strongpassword123
DB_NAME = aiopt
YANDEX_TOKEN = y0__xD5uoWyARi5xhEgyr6szxbuAp_PjJt-QLtZRpJakzhYYXRIPw
YANDEX_LOGIN = mmg-sz
```

---

## 📖 Пошаговая инструкция

### Вариант 1: Через Web UI (Самый простой)

1. **Перейти на Space**
   ```
   https://huggingface.co/spaces/SamShal1/phase4-analytics
   ```

2. **Открыть Files вкладку**
   - Кликни "Files" вверху

3. **Загрузить файлы**
   - Кликни "Upload files"
   - Выбери все 6 файлов из `/opt/phase4/deployment/`
   - Убедись что .streamlit/config.toml загружается как `config.toml`
   - Кликни Upload

4. **Добавить Secrets**
   - Перейди Settings → Repository secrets
   - Кликни "Add new secret"
   - Добавь все 7 secrets из таблицы выше

5. **Проверить результат**
   - Space должен перезагрузиться (~30 сек)
   - Перейди на https://huggingface.co/spaces/SamShal1/phase4-analytics
   - Дождись загрузки (синий экран с логотипом)
   - Должен открыться Streamlit dashboard

---

### Вариант 2: Через Git (Требует терминала)

```bash
# 1. Новый токен на HF (с правом repo write)
# Перейти: https://huggingface.co/settings/tokens
# Создать новый токен → скопировать

# 2. Клонировать Space репо
export HF_TOKEN="<вставь_новый_токен>"
git clone https://oauth2:${HF_TOKEN}@huggingface.co/spaces/SamShal1/phase4-analytics
cd phase4-analytics

# 3. Скопировать файлы
cp /opt/phase4/deployment/* .
mkdir -p .streamlit
cp /opt/phase4/deployment/.streamlit/config.toml .streamlit/

# 4. Коммит и пуш
git add .
git commit -m "Add Phase 4 analytics system"
git push

# 5. Добавить Secrets в Web UI
# Settings → Repository secrets → Add 7 secrets
```

---

### Вариант 3: Через GitHub Actions (Автоматизировано)

```bash
# Если хочешь - могу создать GH Action для автоматического деплоя
# (требует GH + HF токены в Settings → Secrets)
```

---

## 🧪 Проверка после загрузки

### 1️⃣ Проверить загрузку файлов
```bash
# В Files вкладке должны быть:
✅ app.py
✅ dashboard.py
✅ requirements.txt
✅ config.toml (в .streamlit/)
✅ .env.example
✅ README.md
```

### 2️⃣ Проверить Secrets
```bash
# Settings → Repository secrets должны быть:
✅ DB_HOST
✅ DB_PORT
✅ DB_USER
✅ DB_PASSWORD
✅ DB_NAME
✅ YANDEX_TOKEN
✅ YANDEX_LOGIN
```

### 3️⃣ Проверить результат
- Перейди на Space URL
- Дождись загрузки Streamlit (~30 сек)
- Должен увидеть 3 вкладки: Overview, Insights, Campaigns
- Клик на вкладку → должны загруститься данные из БД

---

## 🐛 Troubleshooting

| Проблема | Решение |
|----------|---------|
| **Streamlit не загружается** | Проверить Logs вкладку в Settings. Может быть ошибка БД подключения |
| **"Connection refused" на 43.245.224.117** | Firewall блокирует. Проверить что 5432 открыт с интернета |
| **Blank page / No data** | Проверить что все 7 Secrets добавлены правильно |
| **"ModuleNotFoundError"** | Проверить requirements.txt загружен. Может пересоздать Space |
| **Ошибка авторизации при push** | Создать новый HF токен с правом "repo write" |

---

## 📊 После успешного деплоя

### Доступно на HF:
- **Dashboard**: https://huggingface.co/spaces/SamShal1/phase4-analytics
- **API** (если включить): http://space-url:8501/api/account/kpi
- **Docs**: README внутри Space

### Что работает:
- ✅ Загрузка данных за 30 дней
- ✅ Расчет KPI по аккаунту
- ✅ Выявление 33 проблемных/перспективных сегментов
- ✅ Интерактивные графики и таблицы
- ✅ Фильтры по типам сегментов

### Что планируется:
- 🔄 Level 3: Drill-down по кампаниям (архитектура готова)
- 🔄 Динамика 7 дней (основа реализована)
- 🔄 Рекомендации по оптимизации (шаблоны готовы)

---

## 📞 Если что-то не работает

1. Проверь **Logs** в Settings (все ошибки Python там)
2. Проверь **Secrets** - все ли добавлены правильно
3. Проверь **Files** - все ли загружено
4. Проверь **Database** доступна с интернета:
   ```bash
   psql -h 43.245.224.117 -U aiopt -d aiopt -c "SELECT 1;"
   ```
5. Напиши об ошибке - помогу дебагировать

---

**Автор**: AI Optimizer Phase 4  
**Дата**: 2024-04-11  
**Статус**: ✅ Готово к развертыванию
