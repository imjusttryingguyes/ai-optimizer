# Phase 3: Campaign Drill-Down Analytics Implementation

## Цель
Создать аналитический слой с возможностью drill-down по кампаниям для каждого сегмента, чтобы пользователи могли видеть, в каких РК происходит проблема или точка роста.

## Архитектура

### Три слоя данных:

**Слой 1: Дневные метрики аккаунта** (`account_daily_metrics`)
- Обновляются ежедневно
- Показатели: расход, конверсии, СРА по дням
- Используются на первой вкладке "KPI Статус"

**Слой 2: Отфильтрованные сегменты** (`segment_insights`)
- Выгружаются раз в месяц (1-го числа) или вручную
- Только 2 классификации: `problem` (СРА ≥ 2x) и `opportunity` (СРА ≤ 0.5x с conv ≥ 2)
- Сегменты, не прошедшие фильтр, исключаются
- Фильтр: пропуск если (conversions ≤ 1 И cost < account_cpa)
- Используются на вкладке "Инсайты" (сводка)

**Слой 3: Drill-down по кампаниям** (`segment_campaign_analysis`)
- Выгружаются для каждого проблемного/opportunity сегмента
- Top-3 кампании, которые потратили больше всего в этом сегменте
- Показатели: campaign_id, campaign_name, cost, conversions, cpa
- Используются при клике на карточку сегмента в "Инсайтах"

## Процесс выгрузки

### extract_optimized.py

**Функция `extract_daily_metrics()`**
```
1. Получить последние 30 дней (без текущего дня)
2. Запросить счет с суммированием по дням
3. Вычислить account_cpa = total_cost / total_conversions
4. Вставить в account_daily_metrics
```

**Функция `extract_segment_insights()`**
```
1. Для каждого из 11 сегментов (AdFormat, Device, Placement, etc):
   - Запросить детальный отчет с этим сегментом
   - Для каждого значения сегмента вычислить:
     * cost, conversions, cpa
     * ratio_to_account = segment_cpa / account_cpa
   
   - ФИЛЬТР: пропустить если (conversions ≤ 1 И cost < account_cpa)
   
   - КЛАССИФИКАЦИЯ:
     * problem:      ratio ≥ 2.0
     * opportunity:  ratio ≤ 0.5 И conversions ≥ 2
     * (все остальные пропускаются)
   
   - Вставить в segment_insights

2. Вставить summary в account_stats:
   - total_cost, total_conversions, account_cpa
   - total_segments_before_filter, total_segments_after_filter
```

**Функция `extract_campaign_drill_down()`** ⭐ НОВАЯ
```
1. Для каждого сегмента из segment_insights (только problem/opportunity):
   - Запросить детальный отчет с этим сегментом И срезом CAMPAIGN_ID
   - Сгруппировать по campaign_id:
     * campaign_name, cost, conversions
     * cpa = cost / conversions (или cost если conversions=0)
   - Отсортировать по cost DESC, взять TOP 3
   - Вставить в segment_campaign_analysis
```

## Новые таблицы БД

### segment_campaign_analysis
```sql
CREATE TABLE segment_campaign_analysis (
    id BIGSERIAL PRIMARY KEY,
    segment_type VARCHAR(50),           -- "Device", "Placement", etc
    segment_value VARCHAR(255),         -- "MOBILE", "dzen.ru", etc
    campaign_id BIGINT,                 -- ID РК
    campaign_name VARCHAR(255),         -- Название РК
    cost FLOAT,                         -- Расход
    conversions INT,                    -- Конверсии
    cpa FLOAT,                          -- Стоимость конверсии
    period_start DATE,                  -- Начало периода (30 дней)
    period_end DATE,                    -- Конец периода
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(segment_type, segment_value, campaign_id, period_start, period_end)
);

CREATE INDEX idx_segment_campaign ON segment_campaign_analysis(segment_type, segment_value);
CREATE INDEX idx_campaign_drill ON segment_campaign_analysis(campaign_id);
```

## API endpoints

### /api/insights [GET]
```
GET /api/insights?account=mmg-sz

Response:
{
  "status": "ok",
  "account_cpa": 7500,
  "account_cost": 2500000,
  "account_conversions": 333,
  "problems": [
    {
      "segment_name": "Device",
      "segment_value": "SMART_TV",
      "spend": 150000,
      "conversions": 15,
      "cpa": 10000,
      "cpa_ratio": 1.33
    },
    ...
  ],
  "opportunities": [
    {
      "segment_name": "Device",
      "segment_value": "MOBILE",
      "spend": 1200000,
      "conversions": 600,
      "cpa": 2000,
      "cpa_ratio": 0.27
    },
    ...
  ]
}
```

### /api/insights/segment/{segment_type}/{segment_value} [GET]
```
GET /api/insights/segment/Device/SMART_TV?is_problem=true

Response:
{
  "status": "ok",
  "segment_type": "Device",
  "segment_value": "SMART_TV",
  "is_problem": true,
  "campaigns": [
    {
      "campaign_id": 12345,
      "campaign_name": "Смартфоны Q2",
      "cost": 75000,
      "conversions": 7,
      "cpa": 10714
    },
    {
      "campaign_id": 12346,
      "campaign_name": "Смартфоны Q3",
      "cost": 50000,
      "conversions": 5,
      "cpa": 10000
    },
    {
      "campaign_id": 12347,
      "campaign_name": "Планшеты",
      "cost": 25000,
      "conversions": 3,
      "cpa": 8333
    }
  ]
}
```

## Пример использования

1. **Пользователь нажимает на вкладку "Инсайты"**
   - Загружается `/api/insights?account=mmg-sz`
   - Показываются все problems и opportunities

2. **Видит**: "Device: SMART_TV | CPA: 10000₽ (1.33x выше среднего)"

3. **Нажимает на карточку**
   - Загружается `/api/insights/segment/Device/SMART_TV?is_problem=true`
   - Показывается модальное окно с TOP-3 РК

4. **Видит**: 
   - РК "Смартфоны Q2": 75K ₽ потрачено, 7 конверсий, СРА 10714₽
   - РК "Смартфоны Q3": 50K ₽ потрачено, 5 конверсий, СРА 10000₽
   - РК "Планшеты": 25K ₽ потрачено, 3 конверсии, СРА 8333₽

5. **Вывод**: В этих РК нужно оптимизировать работу с SMART_TV (может быть, высокий CPC, низкая CTR, или плохой таргет)

## Обработка особых случаев

### Нулевые конверсии
- Для problems: сегмент с 0 конверсиями может быть проблемой (потратили деньги без результата)
- Для opportunities: требуется min 2 конверсии (иначе скорее всего шум)
- В drill-down при 0 конверсиях показываем CPA = cost (всю потраченную сумму)

### Пустые данные
- Если для проблемного сегмента нет данных о кампаниях → показываем "Нет данных"
- Если в целом нет problems/opportunities → показываем "Проблемных сегментов не найдено"

### Фильтрация по целям
- Используем Goals из конфига для выгрузки конверсий
- Суммируем Conversions_{goal_id}_AUTO для всех целей
- Это гарантирует, что считаем только достижения нужных целей, а не все событие

## Процесс обновления

### Ежедневно (скрипт `extract-daily.sh` в cron):
```bash
python3 /opt/ai-optimizer/ingestion/extract_optimized.py
# Обновляет: account_daily_metrics
```

### Раз в месяц (1-го числа):
```bash
python3 /opt/ai-optimizer/ingestion/extract_optimized.py
# Выполняет ВСЕ 3 функции:
# - extract_daily_metrics()
# - extract_segment_insights()
# - extract_campaign_drill_down()
```

## Улучшения по сравнению с Phase 2

| Аспект | Phase 2 | Phase 3 |
|--------|---------|---------|
| **Сегменты** | 11 типов | 11 типов (улучшено: TargetingLocationId теперь работает) |
| **Классификация** | 6 типов (нормально/проблема/возможность/etc) | 2 типа (problem/opportunity только) |
| **Drill-down** | ❌ Нет | ✅ Top-3 РК для каждого сегмента |
| **Фильтрация** | Простая | Умная (пропуск низкомерных шумных сегментов) |
| **Отчеты** | По типам сегментов | По значениям сегментов (с детализацией) |

## Файлы, измененные в Phase 3

- `ingestion/extract_optimized.py`: +функция `extract_campaign_drill_down()`
- `dashboard_optimized.py`: +endpoint `/api/insights/segment/{type}/{value}`
- `dashboard_simple.py`: обновлена функция `showCampaigns()`, обновлен API вызов
- БД: +таблица `segment_campaign_analysis`

## TODO для готовности к Production

- [ ] Протестировать с реальными данными API (currently using dummy)
- [ ] Убедиться что все 11 сегментов выгружаются корректно
- [ ] Оптимизировать запросы при большом объёме кампаний (INDEX)
- [ ] Добавить error handling для timeout API
- [ ] Документация для пользователей
