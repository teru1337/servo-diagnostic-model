# 14_CODING_AGENT_PROMPT.md

# Инструкция для coding agent

## 1. Роль

Ты — coding agent, который должен реализовать Python-проект:

```text
servo_diagnostic_model
```

Проект представляет собой физико-статистическую диагностическую модель для анализа телеметрии сервопривода.

Твоя задача — написать рабочий, модульный, тестируемый Python-код на основе Markdown-документации.

---

## 2. Главная цель проекта

Нужно реализовать диагностическую модель, которая принимает телеметрию сервопривода, разбивает её на временные окна, рассчитывает признаки, физические риски, Health Score, Anomaly Score, состояние привода, объяснения и рекомендации.

Итоговый результат должен быть JSON-совместимым.

Пример итогового результата:

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
  "risks": {
    "current": 0.03,
    "torque": 0.02,
    "velocity": 0.3,
    "voltage": 0.01,
    "temperature": 0.0,
    "statusword": 0.0,
    "error": 0.0,
    "data_quality": 0.0,
    "statistical_anomaly": 0.12
  },
  "main_causes": [],
  "explanation": ["Состояние привода оценивается как нормальное."],
  "recommendations": [
    {
      "priority": "low",
      "category": "normal_operation",
      "action": "Продолжить мониторинг.",
      "reason": "Параметры привода находятся в нормальном диапазоне.",
      "source_risks": [],
      "target_role": "operator"
    }
  ]
}
```

---

## 3. Документы, которые нужно изучить

Перед написанием кода изучи документы в таком порядке:

```text
00_PROJECT_OVERVIEW.md
01_DOMAIN_CONTEXT.md
02_TELEMETRY_SCHEMA.md
03_MODEL_REQUIREMENTS.md
04_CODE_ARCHITECTURE.md
05_DATA_PIPELINE.md
06_FEATURE_ENGINEERING.md
07_PHYSICAL_RISK_MODEL.md
08_STATISTICAL_ANOMALY_MODEL.md
09_HEALTH_SCORE_AND_CLASSIFIER.md
10_RECOMMENDATION_MODULE.md
11_CONFIGS_AND_CONSTANTS.md
12_TESTING_AND_EVALUATION.md
13_IMPLEMENTATION_ROADMAP.md
```

Не начинай писать код, пока не поймёшь общую архитектуру.

---

## 4. Что нужно реализовать в первую очередь

Сначала реализуй Version 0.1.

Version 0.1 включает:

1. Загрузку CSV.
2. Нормализацию колонок.
3. Валидацию данных.
4. Предобработку времени.
5. Преобразование в `TelemetrySample`.
6. Оценку частоты дискретизации.
7. Разбиение на окна.
8. Расчёт признаков.
9. Расчёт физических рисков.
10. Расчёт Health Score.
11. Классификацию состояния.
12. JSON-результат.

Не начинай с Anomaly Score, графиков или синтетических аномалий, пока Version 0.1 не работает.

---

## 5. Ограничения

Запрещено использовать готовые ML-библиотеки:

```text
sklearn
tensorflow
pytorch
keras
xgboost
lightgbm
catboost
```

Разрешено использовать:

```text
Python standard library
numpy
pandas
pytest
matplotlib
```

`matplotlib` использовать только для evaluation/plots, не для ядра модели.

---

## 6. Главный принцип реализации

Код должен быть модульным.

Нельзя писать всю модель в одном файле.

Правильная структура:

```text
servo_diagnostic_model/
├── data/
├── features/
├── model/
├── recommendations/
├── evaluation/
├── api/
├── config/
├── tests/
└── main.py
```

---

## 7. Структура проекта, которую нужно создать

Создай:

```text
servo_diagnostic_model/
│
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── config/
│   ├── limits.json
│   ├── weights.json
│   └── thresholds.json
│
├── data/
│   ├── __init__.py
│   ├── schemas.py
│   ├── loader.py
│   ├── validator.py
│   ├── preprocessing.py
│   └── windowing.py
│
├── features/
│   ├── __init__.py
│   ├── basic_features.py
│   ├── motion_features.py
│   ├── electrical_features.py
│   ├── thermal_features.py
│   ├── status_features.py
│   └── feature_extractor.py
│
├── model/
│   ├── __init__.py
│   ├── physical_risks.py
│   ├── statistical_profile.py
│   ├── anomaly_score.py
│   ├── health_score.py
│   ├── classifier.py
│   └── explanation.py
│
├── recommendations/
│   ├── __init__.py
│   └── rule_based.py
│
├── evaluation/
│   ├── __init__.py
│   ├── synthetic_anomalies.py
│   ├── metrics.py
│   └── plots.py
│
├── api/
│   ├── __init__.py
│   ├── schemas.py
│   └── diagnostic_service.py
│
├── tests/
│   ├── test_loader.py
│   ├── test_validator.py
│   ├── test_windowing.py
│   ├── test_features.py
│   ├── test_physical_risks.py
│   ├── test_health_score.py
│   ├── test_classifier.py
│   ├── test_recommendations.py
│   └── test_diagnostic_service.py
│
└── main.py
```

---

## 8. Coding style

Требования к стилю:

1. Используй type hints.
2. Используй dataclasses.
3. Пиши маленькие функции.
4. Каждая функция должна иметь одну ответственность.
5. Не дублируй формулы.
6. Не делай глобальные mutable-состояния.
7. Не скрывай ошибки данных.
8. Не делай silent failure без warnings.
9. Не зашивай пределы и веса прямо в формулы.
10. Используй конфиги.

---

## 9. Обработка плохих данных

Код не должен падать при:

- `None`;
- `NaN`;
- пустом окне;
- отсутствующем `position`;
- отсутствующем `mode_display`;
- отдельных пропусках в `current_A`;
- отдельных пропусках в `torque_Nm`;
- отсутствии normal profile;
- неизвестном `statusword`.

Код должен возвращать:

- warnings;
- `data_quality` risk;
- `state = unknown`, если диагностика невозможна.

---

## 10. Обязательные dataclass-структуры

В `data/schemas.py` реализуй:

```python
@dataclass
class TelemetrySample:
    t: float
    ts: datetime | None
    device_id: str | None
    statusword: int | None
    mode_display: str | None
    position: float | None
    velocity: float | None
    torque: float | None
    torque_Nm: float | None
    current: float | None
    current_A: float | None
    dc_bus_voltage: float | None
    drive_temp: float | None
    error_code: int | None
```

```python
@dataclass
class TelemetryDataset:
    samples: list[TelemetrySample]
    columns_available: dict[str, bool]
    validation_errors: list[str]
    validation_warnings: list[str]
    sampling_rate_hz: float | None
    duration_s: float | None
    device_id: str | None
```

```python
@dataclass
class TelemetryWindow:
    samples: list[TelemetrySample]
    start_t: float
    end_t: float
    device_id: str | None
    sampling_rate_hz: float | None
```

---

## 11. Главные функции

В итоге должны работать функции:

```python
diagnose_window(...)
diagnose_dataset(...)
diagnose_csv(...)
```

---

### 11.1. `diagnose_window`

```python
def diagnose_window(
    window: TelemetryWindow,
    limits: dict,
    weights: dict,
    thresholds: dict,
    normal_profile: dict | None = None
) -> dict:
    ...
```

Должна выполнить:

```text
extract_features
calculate_physical_risks
calculate_anomaly_score
calculate_health_score
classify_state
get_main_causes
generate_explanation
generate_recommendations
return result
```

---

### 11.2. `diagnose_dataset`

```python
def diagnose_dataset(
    dataset: TelemetryDataset,
    limits: dict,
    weights: dict,
    thresholds: dict,
    normal_profile: dict | None = None
) -> list[dict]:
    ...
```

Должна:

```text
создать окна;
выполнить diagnose_window для каждого окна;
вернуть список результатов.
```

---

### 11.3. `diagnose_csv`

```python
def diagnose_csv(
    csv_path: str,
    limits_path: str = "config/limits.json",
    weights_path: str = "config/weights.json",
    thresholds_path: str = "config/thresholds.json",
    normal_profile_path: str | None = None
) -> list[dict]:
    ...
```

Должна:

```text
загрузить конфиги;
загрузить CSV;
подготовить dataset;
выполнить диагностику;
вернуть результаты.
```

---

## 12. Минимальный результат Version 0.1

После Version 0.1 должен работать пример:

```python
from servo_diagnostic_model.api.diagnostic_service import diagnose_csv

results = diagnose_csv(
    csv_path="data/telemetry.csv",
    limits_path="config/limits.json",
    weights_path="config/weights.json",
    thresholds_path="config/thresholds.json"
)

print(results[0])
```

---

## 13. Тесты

После каждого реализованного модуля добавляй тесты.

Минимально должны пройти:

```bash
pytest
```

Тесты должны покрывать:

- loader;
- preprocessing;
- validator;
- windowing;
- feature extraction;
- physical risks;
- Health Score;
- classifier;
- recommendations;
- diagnostic_service.

---

## 14. Правила для Health Score

Health Score:

```text
0..100
```

Формула:

```text
total_risk = weighted_sum(risks)
health_score = 100 * (1 - total_risk)
```

Обязательные hard rules:

```text
если error_flag=True:
    health_score <= 40

если fault_flag=True:
    health_score <= 40

если risks["temperature"] >= 1:
    health_score <= 50

если risks["voltage"] >= 1:
    health_score <= 50
```

---

## 15. Правила классификации

Допустимые состояния:

```text
normal
observation
warning
critical
unknown
```

Обязательные правила:

```text
error_flag=True => critical
fault_flag=True => critical
health_score < 50 => critical
50 <= health_score < 70 => warning
70 <= health_score < 85 => observation
health_score >= 85 and anomaly_score < 0.3 => normal
```

Anomaly Score должен влиять:

```text
anomaly_score >= 0.75 => critical
0.50 <= anomaly_score < 0.75 => warning
0.30 <= anomaly_score < 0.50 => observation
```

---

## 16. Правила рекомендаций

Рекомендации должны быть rule-based.

Обязательные сценарии:

```text
normal => Продолжить мониторинг
error => Проверить код ошибки
fault => Проверить statusword/CiA 402
voltage risk => Проверить питание/DC-шину/тормозной резистор
temperature risk => Проверить охлаждение
current/torque risk => Проверить механику/нагрузку/муфту
data quality risk => Проверить телеметрию
statistical anomaly => Проверить признаки, давшие вклад в Anomaly Score
```

---

## 17. Порядок работы

Работай строго по этому порядку:

```text
1. Создай структуру проекта.
2. Реализуй dataclasses.
3. Реализуй loader.
4. Реализуй preprocessing.
5. Реализуй validator.
6. Реализуй windowing.
7. Реализуй basic_features.
8. Реализуй feature modules.
9. Реализуй feature_extractor.
10. Реализуй physical_risks.
11. Реализуй health_score.
12. Реализуй classifier.
13. Реализуй diagnostic_service.
14. Добавь tests для Version 0.1.
15. Только после этого добавляй statistical_profile и anomaly_score.
16. Потом explanation.
17. Потом recommendations.
18. Потом synthetic anomalies.
19. Потом metrics и plots.
```

---

## 18. Что делать, если данных или требований не хватает

Если точное значение неизвестно:

- используй default config;
- добавь warning;
- не выдумывай специфические паспортные значения;
- оставь возможность заменить значение через JSON.

Если поле отсутствует:

- не ломай программу;
- пометь в data quality;
- рассчитай доступные признаки.

Если normal profile отсутствует:

```python
anomaly_score = 0.0
available = False
```

---

## 19. Финальный критерий готовности

Проект считается готовым, если:

1. `pytest` проходит.
2. `diagnose_csv` работает.
3. Результат JSON-совместим.
4. Health Score рассчитывается.
5. State рассчитывается.
6. Recommendations формируются.
7. Ненулевой `error_code` даёт critical.
8. Нормальная телеметрия не даёт critical.
9. Нет готовых ML-моделей.
10. Код разбит по модулям.
11. Конфиги вынесены в JSON.
12. Есть README с примером запуска.

---

## 20. Главная установка

Не пытайся сделать сложную интеллектуальную систему сразу.

Сделай сначала:

```text
простую,
надёжную,
объяснимую,
проверяемую
```

диагностическую модель.

Главная ценность проекта — не в сложности алгоритма, а в том, что сырая телеметрия превращается в понятную инженерную оценку состояния привода.
