# 🔧 Troubleshooting

## Дашборд не открывается

### Проблема 1: "Port 8501 is not available"

**Решение 1** (рекомендуется): Используй другой порт
```bash
bash /opt/phase4/start-dashboard-alt.sh
# Откроется на: http://localhost:8502
```

**Решение 2**: Убей процесс на порту 8501 и повтори
```bash
fuser -k 8501/tcp
bash /opt/phase4/start-dashboard.sh
```

**Решение 3**: Запусти на произвольном свободном порту
```bash
streamlit run /opt/phase4/ui/dashboard.py --server.port 8503
```

### Проблема 2: "ModuleNotFoundError: No module named 'plotly'"

**Решение**: Установи зависимости
```bash
pip install --break-system-packages plotly pandas streamlit
```

### Проблема 3: "connection refused" к БД

**Проверь**:
1. `.env` файл существует: `/opt/ai-optimizer/.env`
2. Правильные credentials для БД
3. PostgreSQL запущен

**Команда для проверки**:
```bash
python3 << 'PYTHON'
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('/opt/ai-optimizer/.env')
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print("✅ БД подключена")
    conn.close()
except Exception as e:
    print(f"❌ Ошибка: {e}")
PYTHON
```

### Проблема 4: Дашборд открывается, но пустые графики

**Решение**: Запусти extraction скрипты
```bash
# Уровень 1 (3 мин)
python3 /opt/phase4/extraction/level1_kpi.py

# Уровень 2 (2 мин)
python3 /opt/phase4/extraction/level2_trends.py

# Уровень 3 (10 мин, опционально)
python3 /opt/phase4/extraction/level3_campaign_30d.py
```

После этого нажми кнопку "🔄 Обновить" на дашборде.

### Проблема 5: "StreamlitAPIException"

Обычно связана с Streamlit кешем. Решение:
```bash
# Очистить кеш
rm -rf ~/.streamlit/cache

# Перезапустить
bash /opt/phase4/start-dashboard-alt.sh
```

### Проблема 6: Медленно/зависает

**Это нормально при первом запуске** - Streamlit инициализирует кеш.

Ускорь:
1. Нажми кнопку "🔄 Обновить" (очистит кеш)
2. Переключайся между страницами (используют кеш 5 мин)

## Быстрые команды

```bash
# Проверить всё
cd /opt/phase4
python3 << 'CHECK'
# Зависимости
import streamlit, plotly, psycopg2
print("✅ Зависимости OK")

# БД
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('/opt/ai-optimizer/.env')
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM account_kpi")
    print(f"✅ БД OK ({cur.fetchone()[0]} rows)")
conn.close()
CHECK

# Запустить дашборд
bash start-dashboard-alt.sh  # На порту 8502
# или
streamlit run ui/dashboard.py --server.port 8503  # На любом порту
```

## Где смотреть логи?

Streamlit показывает логи прямо в консоли. Если что-то не так, смотри:
1. Сообщения об ошибках в консоли
2. `/opt/phase4` логи (если они есть)
3. Streamlit config: `~/.streamlit/config.toml`

## Рекомендуемый запуск

**Самый надёжный способ**:
```bash
cd /opt/phase4
streamlit run ui/dashboard.py --server.port 8502 --logger.level=error
```

Откроется на `http://localhost:8502` 📊

---

**Если всё ещё не работает**, запусти:
```bash
cd /opt/phase4
python3 storage/init_db.py  # Пересоздаст БД
python3 extraction/level1_kpi.py  # Загрузит данные
bash start-dashboard-alt.sh  # Запустит дашборд
```

Этого должно быть достаточно! 🚀
