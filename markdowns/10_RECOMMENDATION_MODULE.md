# 10_RECOMMENDATION_MODULE.md

# Модуль объяснимых рекомендаций

## 1. Назначение документа

Этот документ описывает модуль рекомендаций для проекта `servo_diagnostic_model`.

Coding agent должен реализовать модуль:

```text
recommendations/rule_based.py
```

Модуль рекомендаций должен принимать результат диагностики и формировать понятные инженерные рекомендации для оператора или инженера ТОиР.

В первой версии проекта рекомендации должны быть rule-based, то есть основанными на правилах.

Запрещено использовать:

```text
LLM
OpenAI API
локальные языковые модели
готовые генеративные модели
```

Причина: текущая цель — реализовать с нуля физико-статистическую диагностическую модель. Текст рекомендаций должен быть детерминированным, объяснимым и зависящим от найденных рисков.

---

## 2. Место модуля рекомендаций в pipeline

Общая цепочка:

```text
TelemetryWindow
    ↓
Feature Extraction
    ↓
Physical Risks
    ↓
Statistical Anomaly Score
    ↓
Health Score
    ↓
State Classification
    ↓
Main Causes
    ↓
Recommendation Module
    ↓
Recommendations[]
```

Модуль рекомендаций вызывается после того, как уже известны:

- `state`;
- `risk_level`;
- `health_score`;
- `anomaly_score`;
- `risks`;
- `features`;
- `main_causes`.

---

## 3. Главная задача модуля

Модуль должен ответить на вопрос:

> Что оператору или инженеру нужно сделать с учётом найденного состояния привода?

Рекомендация должна быть не просто текстом, а структурированным объектом.

Пример:

```json
{
  "priority": "high",
  "category": "mechanical_load",
  "action": "Проверить механическую нагрузку, муфту и возможное заклинивание.",
  "reason": "Обнаружен повышенный ток при малой скорости.",
  "source_risks": ["current", "torque"],
  "target_role": "engineer"
}
```

---

## 4. Входные данные

Основная функция должна принимать:

```python
def generate_recommendations(
    state: str,
    risks: dict,
    features: dict,
    main_causes: list[dict],
    thresholds: dict | None = None
) -> list[dict]:
    ...
```

---

### 4.1. `state`

Допустимые значения:

```text
normal
observation
warning
critical
unknown
```

---

### 4.2. `risks`

Пример:

```python
risks = {
    "current": 0.72,
    "torque": 0.45,
    "velocity": 0.20,
    "voltage": 0.10,
    "temperature": 0.35,
    "statusword": 0.00,
    "error": 0.00,
    "data_quality": 0.00,
    "statistical_anomaly": 0.58
}
```

---

### 4.3. `features`

Пример:

```python
features = {
    "motion_phase": "holding",
    "current_rms": 0.8,
    "current_at_low_speed": 0.7,
    "torque_rms": 0.3,
    "voltage_min": 305.0,
    "voltage_max": 306.0,
    "voltage_std": 0.26,
    "temp_max": 45.0,
    "temp_slope": 0.02,
    "error_flag": False,
    "fault_flag": False,
    "warning_flag": False,
    "unique_error_codes": []
}
```

---

### 4.4. `main_causes`

Пример:

```python
main_causes = [
    {
        "risk_key": "current",
        "parameter": "current_A",
        "risk_value": 0.72,
        "severity": "warning",
        "message": "Токовая нагрузка повышена."
    }
]
```

---

## 5. Выходные данные

Модуль должен вернуть список рекомендаций.

Тип:

```python
list[dict]
```

Пример:

```json
[
  {
    "priority": "medium",
    "category": "mechanical_load",
    "action": "Проверить механическую нагрузку, муфту и возможное заклинивание.",
    "reason": "Токовая нагрузка повышена в режиме удержания.",
    "source_risks": ["current"],
    "target_role": "engineer"
  }
]
```

---

## 6. Структура рекомендации

Каждая рекомендация должна иметь поля:

| Поле           | Тип         | Обязательное | Назначение                       |
| -------------- | ----------- | -----------: | -------------------------------- |
| `priority`     | `str`       |           да | приоритет действия               |
| `category`     | `str`       |           да | категория проблемы               |
| `action`       | `str`       |           да | что нужно сделать                |
| `reason`       | `str`       |           да | почему это нужно сделать         |
| `source_risks` | `list[str]` |           да | какие риски вызвали рекомендацию |
| `target_role`  | `str`       |           да | кому адресована рекомендация     |
| `confidence`   | `float`     |   желательно | уверенность 0..1                 |
| `is_blocking`  | `bool`      |   желательно | блокирует ли дальнейшую работу   |
| `next_step`    | `str`       |   желательно | следующий шаг после действия     |

---

## 7. Допустимые значения `priority`

```text
low
medium
high
critical
```

Интерпретация:

| Priority   | Смысл                                                 |
| ---------- | ----------------------------------------------------- |
| `low`      | Информационное действие, срочность низкая             |
| `medium`   | Нужно наблюдение или плановая проверка                |
| `high`     | Желательно выполнить проверку до продолжения нагрузки |
| `critical` | Нужно немедленное вмешательство                       |

---

## 8. Допустимые значения `category`

```text
normal_operation
mechanical_load
thermal
power_supply
drive_error
statusword_fault
data_quality
statistical_anomaly
motion_instability
maintenance
unknown
```

---

## 9. Допустимые значения `target_role`

```text
operator
engineer
admin
maintenance
```

Правила:

| Роль          | Когда использовать                                                            |
| ------------- | ----------------------------------------------------------------------------- |
| `operator`    | простые действия: продолжить мониторинг, снизить нагрузку, остановить процесс |
| `engineer`    | диагностика параметров, проверка механики, питания, приводной части           |
| `maintenance` | действия ТОиР: осмотр, заявка, регламентная проверка                          |
| `admin`       | проблемы конфигурации, данных, прав, интеграции                               |

---

## 10. Общая логика выбора рекомендаций

Порядок приоритета:

```text
1. Unknown/data quality
2. Critical error/fault
3. Voltage/DC-bus risk
4. Temperature risk
5. Current/torque/mechanical risk
6. Statistical anomaly
7. Motion instability
8. Observation-level issues
9. Normal operation
```

Почему именно так:

- если данные плохие, выводы модели ненадёжны;
- если есть авария, она важнее обычных отклонений;
- питание и перегрев могут привести к отключению или повреждению;
- ток и момент указывают на нагрузку и механику;
- статистическая аномалия требует внимания, но без физической причины её нельзя считать единственной причиной аварии.

---

## 11. Правило для `normal`

Если состояние:

```text
state = normal
```

и нет существенных рисков, вернуть одну рекомендацию:

```json
{
  "priority": "low",
  "category": "normal_operation",
  "action": "Продолжить мониторинг.",
  "reason": "Параметры привода находятся в нормальном диапазоне.",
  "source_risks": [],
  "target_role": "operator",
  "confidence": 1.0,
  "is_blocking": false,
  "next_step": "Продолжать наблюдение за Health Score и графиками телеметрии."
}
```

---

## 12. Правило для `unknown`

Если состояние:

```text
state = unknown
```

или риск качества данных высокий:

```python
risks["data_quality"] >= 0.75
```

вернуть рекомендацию:

```json
{
  "priority": "high",
  "category": "data_quality",
  "action": "Проверить источник телеметрии, частоту поступления данных и наличие пропусков.",
  "reason": "Состояние привода не может быть надёжно определено из-за недостаточного качества данных.",
  "source_risks": ["data_quality"],
  "target_role": "engineer",
  "confidence": 0.9,
  "is_blocking": true,
  "next_step": "Повторить диагностику после восстановления корректного потока данных."
}
```

---

## 13. Правило для ошибки привода

Условие:

```python
features["error_flag"] is True
```

или:

```python
risks["error"] >= 1.0
```

Рекомендация:

```json
{
  "priority": "critical",
  "category": "drive_error",
  "action": "Проверить код ошибки привода по руководству и выполнить регламентную диагностику.",
  "reason": "Обнаружен ненулевой код ошибки привода.",
  "source_risks": ["error"],
  "target_role": "engineer",
  "confidence": 1.0,
  "is_blocking": true,
  "next_step": "Сопоставить error_code с таблицей ошибок и определить допустимость сброса ошибки."
}
```

Если доступны `unique_error_codes`, добавить их в текст:

```text
Обнаружены коды ошибок: ...
```

---

## 14. Правило для Fault в statusword

Условие:

```python
features["fault_flag"] is True
```

или:

```python
risks["statusword"] >= 1.0
```

Рекомендация:

```json
{
  "priority": "critical",
  "category": "statusword_fault",
  "action": "Проверить состояние CiA 402, причину Fault и условия перехода привода в аварийное состояние.",
  "reason": "Statusword содержит аварийный флаг Fault.",
  "source_risks": ["statusword"],
  "target_role": "engineer",
  "confidence": 1.0,
  "is_blocking": true,
  "next_step": "Не выполнять повторный запуск до проверки причины аварийного состояния."
}
```

---

## 15. Правило для Warning в statusword

Условие:

```python
features["warning_flag"] is True
```

и при этом нет Fault.

Рекомендация:

```json
{
  "priority": "high",
  "category": "statusword_fault",
  "action": "Проверить предупреждение в statusword и сопоставить его с текущими параметрами телеметрии.",
  "reason": "Привод сообщает предупреждение, но критическая авария не зафиксирована.",
  "source_risks": ["statusword"],
  "target_role": "engineer",
  "confidence": 0.85,
  "is_blocking": false,
  "next_step": "Проверить температуру, DC-шину, ток и момент в момент появления предупреждения."
}
```

---

## 16. Правило для высокого риска DC-шины

Условие:

```python
risks["voltage"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "power_supply",
  "action": "Проверить питание, DC-шину, тормозной резистор и режимы торможения.",
  "reason": "Обнаружен высокий риск по напряжению DC-шины: возможна просадка, перенапряжение или нестабильность.",
  "source_risks": ["voltage"],
  "target_role": "engineer",
  "confidence": 0.9,
  "is_blocking": false,
  "next_step": "Сравнить voltage_min, voltage_max и voltage_std с допустимыми пределами."
}
```

---

## 17. Детализация рекомендации по DC-шине

Если доступны признаки:

```python
voltage_min
voltage_max
voltage_std
```

можно уточнить причину.

### 17.1. Просадка

Если `voltage_min` ниже безопасного предела:

```text
"Обнаружена просадка DC-шины. Проверить входное питание, нагрузку и соединения."
```

### 17.2. Перенапряжение

Если `voltage_max` выше безопасного предела:

```text
"Обнаружен риск перенапряжения DC-шины. Проверить тормозной резистор и режим торможения."
```

### 17.3. Нестабильность

Если `voltage_std` высокий:

```text
"Напряжение DC-шины нестабильно. Проверить питание и качество соединений."
```

---

## 18. Правило для перегрева

Условие:

```python
risks["temperature"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "thermal",
  "action": "Проверить охлаждение привода, вентиляцию шкафа, длительность цикла и нагрузку.",
  "reason": "Температура или скорость её роста приближаются к опасной зоне.",
  "source_risks": ["temperature"],
  "target_role": "engineer",
  "confidence": 0.9,
  "is_blocking": false,
  "next_step": "Сравнить temp_max и temp_slope с тепловыми пределами."
}
```

---

## 19. Правило для умеренного теплового риска

Условие:

```python
0.5 <= risks["temperature"] < 0.75
```

Рекомендация:

```json
{
  "priority": "medium",
  "category": "thermal",
  "action": "Продолжить наблюдение за температурой и проверить условия охлаждения при повторении роста.",
  "reason": "Температура пока не критична, но тепловой риск повышен.",
  "source_risks": ["temperature"],
  "target_role": "operator",
  "confidence": 0.8,
  "is_blocking": false,
  "next_step": "Проверить динамику температуры на следующих окнах."
}
```

---

## 20. Правило для высокого тока

Условие:

```python
risks["current"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "mechanical_load",
  "action": "Проверить механическую нагрузку, муфту, трение, заклинивание и профиль движения.",
  "reason": "Токовая нагрузка повышена относительно допустимого диапазона.",
  "source_risks": ["current"],
  "target_role": "engineer",
  "confidence": 0.85,
  "is_blocking": false,
  "next_step": "Сравнить current_rms, current_abs_max и current_at_low_speed с пределами."
}
```

---

## 21. Ток при низкой скорости

Особое условие:

```python
features["motion_phase"] in ["holding", "stopped"]
```

и:

```python
features["current_at_low_speed"] is high
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "mechanical_load",
  "action": "Проверить механическую часть на повышенное сопротивление или заклинивание.",
  "reason": "Обнаружен повышенный ток при малой скорости или удержании позиции.",
  "source_risks": ["current"],
  "target_role": "engineer",
  "confidence": 0.9,
  "is_blocking": false,
  "next_step": "Проверить муфту, нагрузку на вал и отсутствие механического заедания."
}
```

---

## 22. Правило для высокого момента

Условие:

```python
risks["torque"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "mechanical_load",
  "action": "Проверить нагрузку на валу и корректность профиля ускорения/торможения.",
  "reason": "Момент нагрузки повышен относительно допустимого диапазона.",
  "source_risks": ["torque"],
  "target_role": "engineer",
  "confidence": 0.85,
  "is_blocking": false,
  "next_step": "Сравнить torque_rms и torque_abs_max с номинальным и максимальным моментом."
}
```

---

## 23. Правило для скорости

Условие:

```python
risks["velocity"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "medium",
  "category": "motion_instability",
  "action": "Проверить профиль задания скорости и ограничение максимальной скорости.",
  "reason": "Скорость близка к заданному пределу.",
  "source_risks": ["velocity"],
  "target_role": "engineer",
  "confidence": 0.75,
  "is_blocking": false,
  "next_step": "Сравнить abs_velocity_max с max_velocity_rpm."
}
```

---

## 24. Правило для статистической аномалии

Условие:

```python
risks["statistical_anomaly"] >= 0.75
```

Рекомендация:

```json
{
  "priority": "high",
  "category": "statistical_anomaly",
  "action": "Сравнить текущий режим с нормальным профилем и проверить параметры, давшие наибольший вклад в Anomaly Score.",
  "reason": "Текущее поведение существенно отличается от нормального статистического профиля.",
  "source_risks": ["statistical_anomaly"],
  "target_role": "engineer",
  "confidence": 0.8,
  "is_blocking": false,
  "next_step": "Открыть feature_scores и определить признаки с максимальным отклонением."
}
```

---

## 25. Умеренная статистическая аномалия

Условие:

```python
0.5 <= risks["statistical_anomaly"] < 0.75
```

Рекомендация:

```json
{
  "priority": "medium",
  "category": "statistical_anomaly",
  "action": "Продолжить наблюдение и проверить повторяемость отклонения на следующих окнах.",
  "reason": "Обнаружено подозрительное отклонение от нормального профиля.",
  "source_risks": ["statistical_anomaly"],
  "target_role": "engineer",
  "confidence": 0.7,
  "is_blocking": false,
  "next_step": "Если отклонение сохраняется, провести дополнительную диагностику механики, питания и температурного режима."
}
```

---

## 26. Правило для сниженного качества данных

Условие:

```python
risks["data_quality"] >= 0.5
```

Рекомендация:

```json
{
  "priority": "medium",
  "category": "data_quality",
  "action": "Проверить полноту телеметрии, временные разрывы и корректность значений.",
  "reason": "Качество данных снижено, что может уменьшать достоверность диагностики.",
  "source_risks": ["data_quality"],
  "target_role": "admin",
  "confidence": 0.85,
  "is_blocking": false,
  "next_step": "Проверить edge-сбор, буфер, timestamp и частоту поступления сэмплов."
}
```

---

## 27. Ограничение количества рекомендаций

Модуль не должен возвращать слишком много рекомендаций.

Рекомендуемое ограничение:

```text
max_recommendations = 3
```

Приоритет выбора:

```text
critical > high > medium > low
```

Если рекомендаций много, оставить самые важные.

---

## 28. Удаление дубликатов

Если ток и момент одновременно дают рекомендацию про механику, не нужно возвращать две почти одинаковые рекомендации.

Нужно объединить их:

```json
{
  "priority": "high",
  "category": "mechanical_load",
  "action": "Проверить механическую нагрузку, муфту, трение, заклинивание и профиль движения.",
  "reason": "Повышены токовая и моментная нагрузки.",
  "source_risks": ["current", "torque"],
  "target_role": "engineer"
}
```

---

## 29. Функции модуля

### 29.1. Основная функция

```python
def generate_recommendations(
    state: str,
    risks: dict,
    features: dict,
    main_causes: list[dict],
    thresholds: dict | None = None
) -> list[dict]:
    ...
```

---

### 29.2. Вспомогательные функции

```python
def make_recommendation(
    priority: str,
    category: str,
    action: str,
    reason: str,
    source_risks: list[str],
    target_role: str,
    confidence: float = 0.8,
    is_blocking: bool = False,
    next_step: str | None = None
) -> dict:
    ...
```

```python
def deduplicate_recommendations(recommendations: list[dict]) -> list[dict]:
    ...
```

```python
def sort_recommendations(recommendations: list[dict]) -> list[dict]:
    ...
```

```python
def limit_recommendations(recommendations: list[dict], max_count: int = 3) -> list[dict]:
    ...
```

---

## 30. Псевдокод основной функции

```python
def generate_recommendations(state, risks, features, main_causes, thresholds=None):
    recommendations = []

    if state == "unknown" or risks.get("data_quality", 0) >= 0.75:
        recommendations.append(recommend_data_quality_critical())
        return recommendations

    if features.get("error_flag") or risks.get("error", 0) >= 1:
        recommendations.append(recommend_drive_error(features))

    if features.get("fault_flag") or risks.get("statusword", 0) >= 1:
        recommendations.append(recommend_statusword_fault())

    if features.get("warning_flag") and not features.get("fault_flag"):
        recommendations.append(recommend_statusword_warning())

    if risks.get("voltage", 0) >= 0.75:
        recommendations.append(recommend_voltage_check(features))

    if risks.get("temperature", 0) >= 0.75:
        recommendations.append(recommend_thermal_check(features))
    elif risks.get("temperature", 0) >= 0.5:
        recommendations.append(recommend_thermal_observation(features))

    if risks.get("current", 0) >= 0.75 or risks.get("torque", 0) >= 0.75:
        recommendations.append(recommend_mechanical_load(features, risks))

    if risks.get("velocity", 0) >= 0.75:
        recommendations.append(recommend_velocity_check(features))

    if risks.get("statistical_anomaly", 0) >= 0.75:
        recommendations.append(recommend_statistical_anomaly())
    elif risks.get("statistical_anomaly", 0) >= 0.5:
        recommendations.append(recommend_statistical_observation())

    if risks.get("data_quality", 0) >= 0.5:
        recommendations.append(recommend_data_quality_warning())

    if not recommendations:
        recommendations.append(recommend_normal_operation())

    recommendations = deduplicate_recommendations(recommendations)
    recommendations = sort_recommendations(recommendations)
    recommendations = limit_recommendations(recommendations, max_count=3)

    return recommendations
```

---

## 31. Тесты

### 31.1. Normal recommendation

Если `state=normal`, вернуть `Продолжить мониторинг`.

---

### 31.2. Error recommendation

Если `error_flag=True`, вернуть critical-рекомендацию по error_code.

---

### 31.3. Fault recommendation

Если `fault_flag=True`, вернуть critical-рекомендацию по statusword.

---

### 31.4. Voltage recommendation

Если `risks["voltage"] >= 0.75`, вернуть рекомендацию по питанию/DC-шине.

---

### 31.5. Temperature recommendation

Если `risks["temperature"] >= 0.75`, вернуть рекомендацию по охлаждению.

---

### 31.6. Mechanical recommendation

Если `risks["current"] >= 0.75`, вернуть рекомендацию по механической нагрузке.

---

### 31.7. Data quality recommendation

Если `state=unknown`, вернуть рекомендацию по проверке телеметрии.

---

### 31.8. Limit recommendations

Если сработало много правил, итоговый список не должен превышать `max_recommendations`.

---

## 32. Acceptance criteria

Модуль рекомендаций считается готовым, если:

1. Есть функция `generate_recommendations`.
2. Функция возвращает список словарей.
3. Каждая рекомендация имеет `priority`, `category`, `action`, `reason`, `source_risks`, `target_role`.
4. Для `normal` возвращается рекомендация продолжить мониторинг.
5. Для `error_flag=True` возвращается critical-рекомендация.
6. Для `fault_flag=True` возвращается critical-рекомендация.
7. Для высокого voltage risk есть рекомендация по питанию/DC-шине.
8. Для высокого temperature risk есть рекомендация по охлаждению.
9. Для высокого current/torque risk есть рекомендация по механической нагрузке.
10. Для плохих данных есть рекомендация по телеметрии.
11. Рекомендации сортируются по приоритету.
12. Дубликаты удаляются или объединяются.
13. Количество рекомендаций ограничивается.
14. Модуль не использует LLM.
15. Есть unit-тесты на основные сценарии.
