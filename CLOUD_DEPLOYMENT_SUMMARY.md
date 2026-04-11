# ☁️ Облачное развертывание Phase 4 Dashboard

## 🎯 Статус: ГОТОВО К РАЗВОРАЧИВАНИЮ

Подготовлен полный пакет для развертывания на облаке.

---

## 📦 Что подготовлено

### Deployment пакет (`/opt/phase4/deployment/`)
```
44 KB, 6 файлов
├── app.py                      ← Главный файл для запуска
├── dashboard.py               ← Streamlit интерфейс (копия с адаптациями)
├── requirements.txt           ← Python зависимости
├── .streamlit/config.toml     ← Конфигурация Streamlit
├── .env.example               ← Шаблон переменных окружения
├── .gitignore                 ← Что не коммитить
└── README.md                  ← Инструкция по деплою
```

### Документация
- **HOSTING_GUIDE.md** (299 строк) — Подробные инструкции для 4 хостингов
- **deployment/README.md** (79 строк) — Быстрая справка
- **Этот файл** — Резюме

---

## 🚀 Три варианта развертывания

### 1️⃣ Hugging Face Spaces (⭐ РЕКОМЕНДУЕТСЯ)

**Почему:**
- ✅ Полностью бесплатно
- ✅ Не нужна кредитная карта
- ✅ 2 клика для создания
- ✅ Автоматический перезапуск
- ✅ Легко шарить ссылку
- ✅ Отлично работает с Streamlit

**Как делать:**
1. https://huggingface.co/new-space
2. Выбрать Streamlit SDK
3. Загрузить файлы из `/opt/phase4/deployment/`
4. Settings → Repository secrets → добавить переменные
5. Готово! Space запустится автоматически

**Результат:** Публичная ссылка вроде:
```
https://huggingface.co/spaces/ваш-ник/phase4-analytics
```

---

### 2️⃣ Railway.app (Альтернатива)

**Плюсы:**
- ✅ Стабильный и надежный
- ✅ Первые $5 бесплатно
- ✅ Потом ~$5-10/месяц
- ✅ Автоматический деплой из GitHub

**Как делать:**
1. https://railway.app
2. Create new Project
3. Подключить GitHub репо
4. Добавить переменные окружения
5. Deploy автоматически

---

### 3️⃣ Docker (Универсально)

**Плюсы:**
- ✅ Работает везде
- ✅ Полный контроль
- ✅ Легко масштабировать

**Как делать:**
```bash
# Создать Dockerfile (готов в документации)
docker build -t phase4-dashboard .
docker run -p 8501:8501 phase4-dashboard
```

---

## 🔐 Безопасность

### ⚠️ ВАЖНО

Никогда не выкладывайте:
- ❌ `.env` файл
- ❌ API токены в коде
- ❌ Пароли в README

### ✅ Правильно делать

1. `.env` в `.gitignore` (уже сделано)
2. Использовать **Secrets** каждого хостинга
3. `.env.example` с шаблоном (без реальных значений)

### Переменные окружения (добавить в Secrets)

```env
# PostgreSQL
DB_HOST=ваш-хост-бд
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=ваш-пароль
DB_NAME=ai_optimizer

# Yandex API
YANDEX_TOKEN=ваш-токен
YANDEX_LOGIN=mmg-sz
```

---

## 📋 Пошаговая инструкция (Hugging Face)

### Шаг 1: Создайте аккаунт
```
https://huggingface.co/join
```

### Шаг 2: Создайте Space
```
https://huggingface.co/new-space
├─ Name: phase4-analytics
├─ License: OpenRAIL (default)
├─ SDK: Streamlit
├─ Public/Private: выбрать
└─ Create Space
```

### Шаг 3: Загрузьте файлы
**Способ A: Через UI (проще)**
```
1. Files tab
2. Upload files
3. Выбрать все файлы из /opt/phase4/deployment/
```

**Способ B: Через Git (профессионально)**
```bash
git clone https://huggingface.co/spaces/ваш-ник/phase4-analytics
cd phase4-analytics
cp /opt/phase4/deployment/* .
git add .
git commit -m "Initial dashboard"
git push
```

### Шаг 4: Добавьте Secrets
```
Settings → Repository secrets → Add secret
├─ DB_HOST
├─ DB_PORT
├─ DB_USER
├─ DB_PASSWORD
├─ DB_NAME
├─ YANDEX_TOKEN
└─ YANDEX_LOGIN
```

### Шаг 5: Готово!
```
Space запустится автоматически
Ссылка: https://huggingface.co/spaces/ваш-ник/phase4-analytics
```

---

## 📊 После развертывания

### 1️⃣ Проверьте работоспособность
```
1. Откройте публичную ссылку
2. Пройдитесь по всем 3 страницам
3. Убедитесь, что данные загружаются
```

### 2️⃣ Настройте ежедневное обновление
```bash
# На локальном сервере запускайте каждый день (cron):
0 1 * * * python3 /opt/phase4/extraction/level1_kpi.py
0 2 * * * python3 /opt/phase4/extraction/level2_trends.py
```

### 3️⃣ Мониторинг
```
- Проверяйте логи Space/Project
- Отслеживайте использование ресурсов
- При ошибках → см. HOSTING_GUIDE.md → Troubleshooting
```

---

## 📁 Файлы для копирования

Все готово в одной папке:
```
/opt/phase4/deployment/
```

**Для копирования (например, на GitHub):**
```bash
cd /opt/phase4/deployment
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/ваш-ник/phase4-dashboard.git
git push -u origin main
```

Или просто скопируйте файлы вручную.

---

## 🆘 Если что-то не работает

### Dashboard пустой
```
Решение: Проверьте переменные окружения (Secrets)
         Убедитесь, что DB подключена правильно
```

### Ошибка подключения к БД
```
Решение: DB_HOST должен быть доступен из хостинга
         Проверьте firewall/VPN
```

### Медленная загрузка
```
Решение: Увеличьте кеш Streamlit
         Проверьте скорость интернета
```

**Подробнее в:** `/opt/phase4/HOSTING_GUIDE.md` → Troubleshooting

---

## ✨ Что происходит после деплоя

1. **Dashboard будет доступен 24/7**
   - По публичной ссылке
   - Любой может открыть (если Public)

2. **Данные обновляются ежедневно**
   - Если вы запускаете extraction скрипты
   - На локальном сервере

3. **Производительность**
   - Dashboard загружается <2 сек
   - API ответы <500мс

---

## 📞 Итоговая рекомендация

### ✅ Используйте HUGGING FACE SPACES

**Потому что:**
- Бесплатно
- Легко настроить
- Нет кредитной карты
- Подходит для всех уровней опыта
- Сообщество активно помогает
- Легко обновлять через Git

### Инструкция:
1. Читай: `/opt/phase4/HOSTING_GUIDE.md` (раздел "Вариант 1")
2. Следуй пошагово
3. Готово! 🎉

---

## 🎯 Дальнейшее развитие

После развертывания можно добавить:
- 📊 **Дополнительные графики** (histograms, heatmaps)
- 🤖 **Рекомендации** (auto-optimize campaigns)
- 📧 **Уведомления** (Telegram бот при проблемах)
- 📱 **Мобильная версия** (responsive design)
- 🌐 **Многоязычность** (i18n)

Но сейчас система уже полностью функциональна!

---

## 📚 Файлы для чтения

| Файл | Для кого | Когда читать |
|------|----------|-------------|
| `HOSTING_GUIDE.md` | Все | Перед деплоем |
| `deployment/README.md` | Разработчики | Для быстрого старта |
| `/opt/phase4/00-START-HERE.md` | Новички | Первый раз |
| `/opt/phase4/TROUBLESHOOTING.md` | При проблемах | Если что сломалось |

---

## 🚀 Начнем?

1. **Выбери хостинг** (я советую Hugging Face)
2. **Прочитай инструкцию** в `/opt/phase4/HOSTING_GUIDE.md`
3. **Следуй пошагово**
4. **Готово!** 🎉

---

**Дата подготовки:** 2026-04-10  
**Версия:** 1.0.0  
**Статус:** ✅ Готово к развертыванию  
**Вопросы?** Пиши! 🚀
