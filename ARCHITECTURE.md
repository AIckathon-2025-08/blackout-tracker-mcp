# Архітектура MCP Server для відключень електроенергії

## Огляд системи

MCP-сервер для моніторингу графіків відключень електроенергії від ДТЕК Дніпровські електромережі.

## Структура даних

### Два типи графіків

Система працює з двома типами графіків з сайту ДТЭК:

#### 1. Точний графік (ACTUAL Schedule)
**Джерело:** Таблиця "Графік відключень:"

**Характеристики:**
- Точні відключення на сьогодні та завтра
- Дані на завтра з'являються ближче до кінця дня
- Використовується для сповіщень
- Приоритетний при запитах "на сьогодні"

**Структура таблиці:**
```
Дата: "на сьогодні 14.11.25" / "на завтра 15.11.25"
Часові проміжки: 00-01, 01-02, ..., 23-24
Символи:
  ✗ (чорний) - точне відключення
  ⚡ (жовтий) - відключення перші 30 хв
  ⚡ (зі зірочкою) - можливе відключення другі 30 хв
```

#### 2. Прогноз на тиждень (POSSIBLE_WEEK Schedule)
**Джерело:** Таблиця "Графік можливих відключень на тиждень:"

**Характеристики:**
- Прогноз на всі дні тижня
- Менш точний
- Використовується для загального планування
- Показується тільки при запиті конкретного дня тижня

**Структура таблиці:**
```
Дні тижня: Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
Часові проміжки: 00-01, 01-02, ..., 23-24
Символи:
  ✗ - можливе відключення
  ⚡ - можливе відключення (різні типи)
  Сірий фон - ймовірне відключення
```

## Моделі даних

### Address
```python
class Address:
    city: str              # "м. Дніпро"
    street: str            # "Вʼячеслава Липинського" (з префіксом з автокомпліту)
    house_number: str      # "4"
```

### OutageSchedule
```python
class OutageSchedule:
    schedule_type: str     # "actual" або "possible_week"
    day_of_week: str       # "Понеділок", "Вівторок", ...
    date: Optional[str]    # "14.11.25" (тільки для actual)
    start_hour: int        # 0-23
    end_hour: int          # 1-24
    outage_type: str       # "definite", "first_30min", "second_30min", "possible"
    fetched_at: datetime
```

### ScheduleCache
```python
class ScheduleCache:
    actual_schedules: list[OutageSchedule]    # Точний графік
    possible_schedules: list[OutageSchedule]  # Прогноз на тиждень
    last_updated: datetime
```

## Компоненти системи

### 1. Parser (parser.py)
Відповідає за парсинг сайту ДТЭК.

**Основні функції:**
- `fill_form(city, street, house_number)` - заповнення форми адреси
- `parse_actual_schedule()` - парсинг таблиці "Графік відключень:"
- `parse_possible_schedule()` - парсинг таблиці "Графік можливих відключень на тиждень:"
- `detect_outage_type(cell)` - визначення типу відключення по іконці/кольору

**Технології:**
- Playwright для рендерингу JS-сторінки
- BeautifulSoup для парсингу HTML

### 2. Config (config.py)
Управління конфігурацією та збереженням даних.

**Відповідальності:**
- Збереження адреси користувача
- Налаштування моніторингу
- Кешування графіків (обидва типи окремо)
- Завантаження/збереження в JSON

**Файли:**
- `~/.config/electricity_shutdowns_mcp/config.json` - конфігурація
- `~/.config/electricity_shutdowns_mcp/schedule_cache.json` - кеш графіків

### 3. Scheduler (scheduler.py)
Логіка моніторингу та сповіщень.

**Відповідальності:**
- Періодична перевірка точного графіка
- Порівняння з попередньою версією (детект змін)
- Розрахунок часу до наступного відключення
- Генерація сповіщень за N хвилин

**ВАЖЛИВО:** Сповіщення працюють тільки з точним графіком (ACTUAL), не з прогнозом!

### 4. Server (server.py)
Основний MCP-сервер.

**MCP Tools:**

#### `check_outage_schedule`
```python
Parameters:
  city: str
  street: str
  house_number: str
  include_possible: bool = False

Returns:
  - actual_schedules: list[OutageSchedule]
  - possible_schedules: list[OutageSchedule] (якщо include_possible=True)
```

#### `get_next_outage`
```python
Returns:
  - next_outage: OutageSchedule (з точного графіка)
  - time_until: str (скільки часу до відключення)
```

#### `get_outages_for_day`
```python
Parameters:
  day_of_week: str (Понеділок, Вівторок, ...)
  use_actual: bool = True

Returns:
  - outages: list[OutageSchedule]
```

#### `configure_monitoring`
```python
Parameters:
  check_interval_minutes: int
  notification_before_minutes: int
  enabled: bool

Returns:
  - success: bool
  - config: MonitoringConfig
```

## Потік даних

### 1. Перевірка графіка
```
User Request → MCP Tool → Parser → DTEK Website
                ↓
         Parse HTML Tables
                ↓
    actual_schedules + possible_schedules
                ↓
         Save to Cache
                ↓
         Return to User
```

### 2. Моніторинг та сповіщення
```
Scheduler (кожні N хвилин)
    ↓
Fetch ACTUAL schedule from Parser
    ↓
Compare with cached version
    ↓
If changed → Notify user
    ↓
Check time until next outage
    ↓
If < notification_time → Alert user
```

## Приклад використання

### Налаштування адреси
```
Claude: Встанови адресу: м. Дніпро, вул. Вʼячеслава Липинського, буд. 4
→ Викликає configure_address() → зберігає в config
```

### Перевірка на сьогодні
```
User: Коли сьогодні відключать світло?
Claude: Викликає get_next_outage()
→ Повертає найближче відключення з ACTUAL графіка
```

### Прогноз на тиждень
```
User: Які можливі відключення у середу?
Claude: Викликає get_outages_for_day(day_of_week="Середа", use_actual=False)
→ Повертає дані з POSSIBLE_WEEK графіка
```

## Безпека та обробка помилок

### Можливі помилки:
1. Сайт ДТЭК недоступний
2. Змінилась структура HTML
3. Адреса не знайдена в базі ДТЭК
4. Playwright не може запуститись

### Обробка:
- Fallback на кешовані дані
- Повідомлення користувача про проблему
- Логування помилок
- Graceful degradation

## Майбутні покращення

1. **Розрахунок часу зарядки**
   - Визначення часу до відключення
   - Розрахунок коли почати заряджати (щоб досягти 100%)

2. **Підтримка інших енергокомпаній**
   - ДТЕК Київські електромережі
   - ДТЕК Одеські електромережі
   - Інші оператори

3. **Історія змін графіка**
   - Збереження всіх версій графіка
   - Аналіз частоти змін
   - Прогнозування змін

4. **Інтеграція з календарем**
   - Експорт у Google Calendar
   - iCal формат
