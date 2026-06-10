# 13_IMPLEMENTATION_ROADMAP.md

# Roadmap реализации проекта servo_diagnostic_model

## 1. Назначение документа

Этот документ задаёт пошаговый план реализации проекта `servo_diagnostic_model`.

Coding agent должен выполнять работу по этапам, не перескакивая сразу к сложной статистике, графикам или API.

Главная идея roadmap:

```text
Сначала сделать простую, работающую и тестируемую физическую модель.
Потом добавить статистическую модель.
Потом добавить рекомендации, синтетические аномалии и интеграционный слой.
```

---

## 2. Общая стратегия

Разработка делится на версии:

```text
Version 0.1 — физическая диагностическая модель
Version 0.2 — статистический Anomaly Score
Version 0.3 — рекомендации и объяснения
Version 0.4 — synthetic anomalies и evaluation
Version 1.0 — API/service layer и подготовка к интеграции
```

---

## 3. Что запрещено делать на старте

На старте не нужно:

- делать нейросеть;
- подключать sklearn;
- делать FastAPI;
- подключать базу данных;
- писать PWA;
- реализовывать WebSocket;
- писать LLM-рекомендации;
- оптимизировать производительность раньше времени;
- складывать весь код в один файл.

---

## 4. Version 0.1 — физическая диагностическая модель

### 4.1. Цель

Получить первую рабочую модель, которая:

- загружает CSV;
- валидирует данные;
- разбивает телеметрию на окна;
- считает признаки;
- считает физические риски;
- считает Health Score;
- классифицирует состояние;
- возвращает JSON-результат.

---

### 4.2. Файлы, которые нужно создать

```text
servo_diagnostic_model/
├── data/
│   ├── schemas.py
│   ├── loader.py
│   ├── preprocessing.py
│   ├── validator.py
│   └── windowing.py
│
├── features/
│   ├── basic_features.py
│   ├── motion_features.py
│   ├── electrical_features.py
│   ├── thermal_features.py
│   ├── status_features.py
│   └── feature_extractor.py
│
├── model/
│   ├── physical_risks.py
│   ├── health_score.py
│   └── classifier.py
│
├── api/
│   └── diagnostic_service.py
│
├── config/
│   ├── limits.json
│   ├── weights.json
│   └── thresholds.json
│
└── main.py
```

---

### 4.3. Шаг 1 — создать структуры данных

Файл:

```text
data/schemas.py
```

Создать:

```python
TelemetrySample
TelemetryDataset
TelemetryWindow
```

Критерий готовности:

```text
dataclass-структуры импортируются и используются в тестах.
```

---

### 4.4. Шаг 2 — реализовать загрузку CSV

Файл:

```text
data/loader.py
```

Функции:

```python
load_csv(path)
load_telemetry(path)
```

Критерий готовности:

```text
CSV загружается в pandas.DataFrame.
```

---

### 4.5. Шаг 3 — реализовать preprocessing

Файл:

```text
data/preprocessing.py
```

Функции:

```python
normalize_column_names(df)
parse_time_columns(df)
coerce_numeric_columns(df)
sort_by_time(df)
dataframe_to_samples(df)
preprocess_dataframe(df)
```

Критерий готовности:

```text
сырой DataFrame превращается в TelemetryDataset.
```

---

### 4.6. Шаг 4 — реализовать validator

Файл:

```text
data/validator.py
```

Функции:

```python
validate_dataframe(df)
check_time_column(df)
check_required_columns(df)
check_numeric_quality(df)
check_duration(df)
```

Критерий готовности:

```text
validator возвращает errors и warnings.
```

---

### 4.7. Шаг 5 — реализовать windowing

Файл:

```text
data/windowing.py
```

Функции:

```python
estimate_sampling_rate(samples)
calculate_duration(samples)
make_windows(samples, window_seconds, step_seconds, min_samples)
```

Критерий готовности:

```text
телеметрия разбивается на окна по 5 секунд с шагом 1 секунда.
```

---

### 4.8. Шаг 6 — реализовать basic features

Файл:

```text
features/basic_features.py
```

Функции:

```python
is_valid_number(value)
clean_values(values)
safe_mean(values)
safe_min(values)
safe_max(values)
safe_std(values)
rms(values)
slope(times, values)
safe_abs_max(values)
```

Критерий готовности:

```text
RMS, slope, mean, max/min корректно работают с None/NaN.
```

---

### 4.9. Шаг 7 — реализовать feature modules

Файлы:

```text
features/motion_features.py
features/electrical_features.py
features/thermal_features.py
features/status_features.py
```

Критерий готовности:

```text
для окна телеметрии рассчитываются speed/current/torque/voltage/temp/status признаки.
```

---

### 4.10. Шаг 8 — реализовать feature_extractor

Файл:

```text
features/feature_extractor.py
```

Функция:

```python
extract_features(window, thresholds=None)
```

Критерий готовности:

```text
возвращает единый dict признаков.
```

---

### 4.11. Шаг 9 — реализовать physical risks

Файл:

```text
model/physical_risks.py
```

Функция:

```python
calculate_physical_risks(features, limits)
```

Критерий готовности:

```text
возвращает risks с ключами current, torque, velocity, voltage, temperature, statusword, error, data_quality.
```

---

### 4.12. Шаг 10 — реализовать Health Score

Файл:

```text
model/health_score.py
```

Функции:

```python
calculate_health_score(risks, weights, features=None)
apply_hard_limits(health_score, risks, features)
```

Критерий готовности:

```text
Health Score всегда в диапазоне 0..100.
```

---

### 4.13. Шаг 11 — реализовать classifier

Файл:

```text
model/classifier.py
```

Функции:

```python
classify_state(health_score, anomaly_score, risks, thresholds, features)
risk_level_from_state(state)
```

Критерий готовности:

```text
модель возвращает normal/observation/warning/critical/unknown.
```

---

### 4.14. Шаг 12 — реализовать diagnostic_service

Файл:

```text
api/diagnostic_service.py
```

Функции:

```python
diagnose_window(...)
diagnose_dataset(...)
diagnose_csv(...)
```

Критерий готовности:

```text
можно вызвать diagnose_csv и получить список результатов по окнам.
```

---

## 5. Version 0.1 — Definition of Done

Версия 0.1 готова, если:

1. CSV загружается.
2. Данные валидируются.
3. Данные разбиваются на окна.
4. Признаки считаются.
5. Физические риски считаются.
6. Health Score считается.
7. State классифицируется.
8. `error_code != 0` даёт critical.
9. Результат возвращается как JSON-compatible dict.
10. Есть базовые unit-тесты.

---

## 6. Version 0.2 — статистический Anomaly Score

### 6.1. Цель

Добавить статистический слой, который сравнивает текущее окно с профилем нормальной работы.

---

### 6.2. Файлы

```text
model/statistical_profile.py
model/anomaly_score.py
config/feature_weights.json
```

---

### 6.3. Шаг 1 — fit normal profile

Функция:

```python
fit_normal_profile(feature_rows)
```

Критерий готовности:

```text
создаётся профиль с median, MAD, mean, std.
```

---

### 6.4. Шаг 2 — save/load profile

Функции:

```python
save_profile(profile, path)
load_profile(path)
```

Критерий готовности:

```text
normal_profile сохраняется в JSON и загружается обратно.
```

---

### 6.5. Шаг 3 — robust z-score

Функция:

```python
robust_feature_score(value, stats, z_limit)
```

Критерий готовности:

```text
возвращает score 0..1.
```

---

### 6.6. Шаг 4 — calculate anomaly score

Функция:

```python
calculate_anomaly_score(features, profile, thresholds)
```

Критерий готовности:

```text
возвращает anomaly_score 0..1 и feature_scores.
```

---

### 6.7. Шаг 5 — интеграция с Health Score

Обновить:

```python
risks["statistical_anomaly"] = anomaly_score
```

Критерий готовности:

```text
Anomaly Score влияет на классификацию.
```

---

## 7. Version 0.2 — Definition of Done

Версия 0.2 готова, если:

1. Есть normal profile.
2. Профиль строится по feature rows.
3. Профиль сохраняется и загружается.
4. MAD=0 не ломает расчёт.
5. Anomaly Score считается.
6. Если профиля нет, модель не падает.
7. Anomaly Score влияет на state.
8. Есть unit-тесты.

---

## 8. Version 0.3 — объяснения и рекомендации

### 8.1. Цель

Добавить человекочитаемые объяснения и rule-based рекомендации.

---

### 8.2. Файлы

```text
model/explanation.py
recommendations/rule_based.py
```

---

### 8.3. Шаг 1 — main causes

Функция:

```python
get_main_causes(risks, features, top_n=3)
```

Критерий готовности:

```text
модель показывает главные причины снижения оценки.
```

---

### 8.4. Шаг 2 — explanation

Функция:

```python
generate_explanation(state, health_score, anomaly_score, risks, features, main_causes)
```

Критерий готовности:

```text
возвращается список понятных строк.
```

---

### 8.5. Шаг 3 — recommendations

Функция:

```python
generate_recommendations(state, risks, features, main_causes, thresholds)
```

Критерий готовности:

```text
возвращается список рекомендаций с priority, action, reason.
```

---

## 9. Version 0.3 — Definition of Done

Версия 0.3 готова, если:

1. Есть `main_causes`.
2. Есть explanation.
3. Есть recommendations.
4. Для normal есть рекомендация продолжить мониторинг.
5. Для error есть critical-рекомендация.
6. Для voltage есть рекомендация по питанию.
7. Для temperature есть рекомендация по охлаждению.
8. Для current/torque есть рекомендация по механике.
9. Количество рекомендаций ограничено.
10. Есть unit-тесты.

---

## 10. Version 0.4 — synthetic anomalies и evaluation

### 10.1. Цель

Добавить проверку модели на искусственно созданных аномалиях.

---

### 10.2. Файлы

```text
evaluation/synthetic_anomalies.py
evaluation/metrics.py
evaluation/plots.py
```

---

### 10.3. Шаг 1 — synthetic anomalies

Реализовать:

```python
inject_current_overload(...)
inject_temperature_ramp(...)
inject_voltage_drop(...)
inject_voltage_spike(...)
inject_error_code(...)
inject_data_gap(...)
inject_velocity_oscillation(...)
```

---

### 10.4. Шаг 2 — metrics

Реализовать:

```python
accuracy_score(...)
precision_recall_f1(...)
false_alarm_rate(...)
detection_delay(...)
```

---

### 10.5. Шаг 3 — plots

Реализовать графики:

```text
Health Score over time
Anomaly Score over time
Risks over time
Telemetry with anomalies
```

---

## 11. Version 0.4 — Definition of Done

Версия 0.4 готова, если:

1. Можно создать синтетическую перегрузку по току.
2. Можно создать перегрев.
3. Можно создать просадку DC-шины.
4. Можно создать ошибку.
5. Модель реагирует на аномалии.
6. Считаются precision/recall/F1.
7. Считается detection delay.
8. Генерируются графики.

---

## 12. Version 1.0 — подготовка к интеграции

### 12.1. Цель

Сделать модель удобной для подключения к backend/PWA.

---

### 12.2. Требования

1. Стабильный JSON-контракт.
2. Главная функция `diagnose_window`.
3. Главная функция `diagnose_csv`.
4. Возможность отключить debug.
5. Возможность округлять результат.
6. Отдельные config files.
7. Отсутствие тяжёлых зависимостей.
8. Предсказуемое время выполнения.

---

## 13. Version 1.0 — JSON contract

Пример результата:

```json
{
  "window_start": 0.0,
  "window_end": 5.0,
  "device_id": "servo_1",
  "health_score": 92.5,
  "anomaly_score": 0.12,
  "state": "normal",
  "risk_level": "low",
  "motion_phase": "holding",
  "risks": {},
  "main_causes": [],
  "explanation": [],
  "recommendations": [],
  "data_quality": {},
  "debug": {}
}
```

---

## 14. Порядок реализации для coding agent

Строгий порядок:

```text
1. schemas.py
2. loader.py
3. preprocessing.py
4. validator.py
5. windowing.py
6. basic_features.py
7. feature modules
8. feature_extractor.py
9. physical_risks.py
10. health_score.py
11. classifier.py
12. diagnostic_service.py
13. tests for v0.1
14. statistical_profile.py
15. anomaly_score.py
16. explanation.py
17. recommendations.py
18. synthetic_anomalies.py
19. metrics.py
20. plots.py
```

---

## 15. Рекомендуемый план по дням

### День 1

- создать структуру проекта;
- создать dataclass-схемы;
- реализовать loader;
- добавить первые тесты.

---

### День 2

- preprocessing;
- validator;
- estimate sampling rate;
- make windows.

---

### День 3

- basic features;
- motion features;
- electrical features;
- thermal features;
- status features.

---

### День 4

- physical risks;
- Health Score;
- classifier.

---

### День 5

- diagnostic_service;
- diagnose_csv;
- JSON output;
- интеграционный тест.

---

### День 6

- statistical profile;
- MAD;
- robust z-score;
- anomaly score.

---

### День 7

- explanation;
- main causes;
- recommendations.

---

### День 8

- synthetic anomalies;
- metrics;
- plots.

---

### День 9

- refactoring;
- type hints;
- docstrings;
- README.

---

### День 10

- финальное тестирование;
- проверка acceptance criteria;
- подготовка примеров вывода.

---

## 16. Что считать успешным MVP

MVP считается успешным, если можно выполнить:

```python
results = diagnose_csv(
    csv_path="data/telemetry.csv",
    limits_path="config/limits.json",
    weights_path="config/weights.json",
    thresholds_path="config/thresholds.json"
)
```

и получить:

```text
список окон диагностики,
Health Score,
state,
risks,
explanation,
recommendations.
```

---

## 17. Главный критерий качества

Модель должна быть не самой сложной, а:

```text
понятной,
объяснимой,
устойчивой,
тестируемой,
расширяемой.
```

Если coding agent выбирает между сложной реализацией и простой надёжной реализацией, выбирать простую надёжную.
