# 🚀 Как запустить дашборд

## Быстрый старт (рекомендуется)

### Вариант 1: Simple HTTP Dashboard (Легко, быстро) ⭐ РЕКОМЕНДУЕТСЯ

```bash
cd /opt/ai-optimizer
./start-simple-dashboard.sh
```

**Что откроется:**
- 🌐 http://localhost:8501
- 📊 Две вкладки:
  1. **KPI Статус** - дневные метрики аккаунта
  2. **Инсайты** - проблемы и точки роста по сегментам

**Особенности:**
- ✅ Работает с Phase 3 архитектурой
- ✅ Показывает problems и opportunities
- ✅ Клик на сегмент → Drill-down modal с top-3 РК
- ✅ Легкий, без зависимостей

**Порт:** 8501

---

### Вариант 2: Streamlit Dashboard

```bash
cd /opt/ai-optimizer
./start-streamlit-dashboard.sh
```

**Что откроется:**
- 🌐 http://localhost:8501
- 📊 Streamlit UI (красивый, интерактивный)

**Особенности:**
- ✅ Встроенный UI builder
- ✅ Горячая перезагрузка при изменении кода
- ⚠️ Медленнее чем Simple Dashboard

**Порт:** 8501

---

### Вариант 3: API Server (для интеграций)

```bash
cd /opt/ai-optimizer
python3 dashboard_optimized.py
```

**Что откроется:**
- 🔌 API endpoints на http://localhost:8502

**API Routes:**

```
GET /api/kpi?account=mmg-sz
  ↓ Returns: Daily metrics (cost, conversions, CPA per date)

GET /api/insights?account=mmg-sz
  ↓ Returns: All problems and opportunities with details

GET /api/insights/segment/{type}/{value}?is_problem=true/false
  ↓ Returns: Top-3 campaigns for this segment
```

**Пример запроса:**
```bash
curl http://localhost:8502/api/insights?account=mmg-sz | jq
```

**Порт:** 8502

---

### Вариант 4: Legacy Flask Dashboard

```bash
cd /opt/ai-optimizer
./start-dashboard.sh
```

**Что откроется:**
- 🌐 http://localhost:5000
- 📊 Старый Flask интерфейс

**⚠️ Примечание:** Это более старая версия, рекомендуется использовать Вариант 1 или 2

**Порт:** 5000

---

## Как проверить что дашборд запустился

```bash
# Проверка Simple Dashboard (8501)
curl -s http://127.0.0.1:8501 | head -20

# Проверка API (8502)
curl -s http://127.0.0.1:8502/api/insights?account=mmg-sz | jq

# Проверка процессов
ps aux | grep "python.*dashboard"

# Проверка портов
lsof -i :8501
lsof -i :8502
```

---

## Полный workflow

### 1. Выгрузить данные

```bash
# Один раз (все слои)
cd /opt/ai-optimizer
python3 ingestion/extract_optimized.py

# Или ежедневно в cron:
*/1 * * * * cd /opt/ai-optimizer && python3 ingestion/extract_optimized.py
```

### 2. Запустить дашборд

```bash
./start-simple-dashboard.sh
```

### 3. Открыть в браузере

```
http://localhost:8501
```

### 4. Пользование

**Вкладка "KPI Статус":**
- Выбрать аккаунт из dropdown
- Видеть дневные метрики (расход, конверсии, СРА)
- Видеть прогнозы и целевые показатели

**Вкладка "Инсайты":**
- Видеть список проблемных сегментов (красные карточки)
- Видеть список перспективных сегментов (зелёные карточки)
- Кликнуть на карточку → открыть modal с top-3 РК

---

## Остановка дашборда

### Если запущен в foreground:
```bash
Ctrl+C
```

### Если запущен в background:
```bash
# Simple Dashboard (port 8501)
kill $(lsof -i :8501 | tail -1 | awk '{print $2}')

# API Server (port 8502)
kill $(lsof -i :8502 | tail -1 | awk '{print $2}')

# Flask (port 5000)
kill $(lsof -i :5000 | tail -1 | awk '{print $2}')
```

---

## Логи

### Simple Dashboard:
```bash
tail -f dashboard.log
```

### Streamlit:
```bash
tail -f streamlit.log
```

### Flask:
```bash
tail -f /tmp/flask.log
```

---

## Часто задаваемые вопросы

### Q: Какой дашборд использовать?
**A:** Вариант 1 (Simple HTTP Dashboard) - самый легкий и подходит для Phase 3.

### Q: Данные не загружаются?
**A:** 
1. Убедись что выгружены данные: `SELECT COUNT(*) FROM segment_insights;`
2. Убедись что PostgreSQL запущена: `psql -h localhost -U aiopt -d aiopt -c "SELECT 1;"`
3. Проверь логи: `tail -20 dashboard.log`

### Q: Порт занят?
**A:** 
```bash
# Убить процесс на порту
kill $(lsof -i :8501 | tail -1 | awk '{print $2}')

# Или использовать другой порт (отредактировать скрипт)
```

### Q: Как добавить новый аккаунт?
**A:** 
1. Выгрузить данные для этого аккаунта (update CONFIG в extract_optimized.py)
2. В дашборде выбрать новый аккаунт из dropdown

### Q: Как интегрировать API с другим приложением?
**A:**
1. Запустить `python3 dashboard_optimized.py` (порт 8502)
2. Использовать endpoints:
   - `/api/kpi?account=...`
   - `/api/insights?account=...`
   - `/api/insights/segment/{type}/{value}?is_problem=...`

---

## Архитектура дашборда

```
┌─ dashboard_simple.py (HTTP, 8501)
│  ├─ HTML/CSS/JS frontend
│  ├─ Fetch: /api/kpi, /api/insights
│  └─ Modal для drill-down

├─ dashboard_optimized.py (API, 8502)
│  ├─ /api/kpi → account_daily_metrics
│  ├─ /api/insights → segment_insights
│  └─ /api/insights/segment/... → segment_campaign_analysis

├─ dashboard_streamlit.py (UI, 8501)
│  └─ Streamlit interface

└─ web/app.py (Legacy Flask, 5000)
   └─ Old interface (deprecated)
```

---

## Phase 3 Features

✅ **Трёхслойная архитектура:**
- Layer 1: account_daily_metrics (дневные метрики)
- Layer 2: segment_insights (проблемы/возможности)
- Layer 3: segment_campaign_analysis (drill-down по РК)

✅ **Классификация на 2 типа:**
- Problem: CPA ≥ 2.0x account_cpa
- Opportunity: CPA ≤ 0.5x account_cpa AND conversions ≥ 2

✅ **Campaign Drill-Down:**
- Клик на сегмент → Top-3 РК, которые его прогонали

✅ **Все 11 сегментов:**
- AdFormat, AdNetworkType, Age, CriterionType, Device
- Gender, IncomeGrade, Placement, Slot, TargetingCategory, TargetingLocationId

---

*Last Updated: 2026-04-10*
*Phase 3 Implementation Complete*
