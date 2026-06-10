# 04_CODE_ARCHITECTURE.md

# Архитектура кода проекта servo_diagnostic_model

## 1. Назначение документа

Этот документ описывает архитектуру Python-проекта `servo_diagnostic_model`.

Coding agent должен реализовать проект в соответствии с данной структурой.

Главная цель архитектуры — сделать код:

- модульным;
- расширяемым;
- тестируемым;
- понятным;
- пригодным для будущей интеграции с backend/PWA;
- независимым от готовых ML-фреймворков.

---

## 2. Основной принцип архитектуры

Проект должен быть построен как pipeline.

Общая цепочка:

```text
input file
    ↓
loader
    ↓
validator
    ↓
preprocessor
    ↓
windowing
    ↓
feature extraction
    ↓
physical risk model
    ↓
statistical anomaly model
    ↓
health score
    ↓
classifier
    ↓
explanation
    ↓
recommendations
    ↓
diagnostic result
```

Каждый этап должен быть отдельным модулем.

Нельзя смешивать:

- загрузку CSV и расчёт Health Score;
- расчёт признаков и генерацию рекомендаций;
- классификацию и чтение конфигураций;
- работу API и математику модели.

---

## 3. Рекомендуемая структура проекта

```text
servo_diagnostic_model/
│
├── README.md
├── pyproject.toml
├── requirements.txt
│
├── config/
│   ├── limits.json
│   ├── weights.json
│   └── thresholds.json
│
├── data/
│   ├── __init__.py
│   ├── loader.py
│   ├── validator.py
│   ├── preprocessing.py
│   ├── windowing.py
│   └── schemas.py
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
│   └── test_recommendations.py
│
└── main.py
```

---

## 4. Назначение верхнего уровня

### 4.1. `README.md`

Краткое описание проекта:

- что делает модель;
- как установить зависимости;
- как запустить диагностику CSV;
- как запустить тесты;
- какие файлы конфигурации используются.

---

### 4.2. `pyproject.toml`

Файл конфигурации проекта.

В первой версии можно сделать минимальным.

---

### 4.3. `requirements.txt`

Минимальные зависимости:

```text
numpy
pandas
pytest
```

Опционально:

```text
matplotlib
```

Если графики не реализуются в первой версии, `matplotlib` можно не добавлять.

---

### 4.4. `main.py`

CLI-точка входа для ручного запуска.

Пример:

```bash
python main.py --csv data/telemetry.csv
```

`main.py` не должен содержать бизнес-логику. Он должен только вызывать `api.diagnostic_service`.

---

## 5. Папка `config/`

Папка содержит конфигурации модели.

### 5.1. `limits.json`

Паспортные и инженерные пределы.

Пример:

```json
{
  "rated_current_A": 4.27,
  "max_current_A": 12.8,
  "rated_torque_Nm": 2.39,
  "max_torque_Nm": 8.36,
  "max_velocity_rpm": 6000,
  "dc_bus_min_safe": 280,
  "dc_bus_max_safe": 340,
  "dc_bus_min_critical": 240,
  "dc_bus_max_critical": 380,
  "temp_safe": 55,
  "temp_warning": 70,
  "temp_critical": 85,
  "voltage_std_limit": 5.0,
  "temp_slope_limit": 0.2
}
```

---

### 5.2. `weights.json`

Веса рисков для Health Score.

Пример:

```json
{
  "error": 0.25,
  "statusword": 0.15,
  "temperature": 0.18,
  "current": 0.16,
  "torque": 0.14,
  "voltage": 0.14,
  "statistical_anomaly": 0.08,
  "velocity": 0.03,
  "data_quality": 0.02
}
```

---

### 5.3. `thresholds.json`

Пороги классификации.

Пример:

```json
{
  "health_normal": 85,
  "health_observation": 70,
  "health_warning": 50,
  "anomaly_observation": 0.3,
  "anomaly_warning": 0.5,
  "anomaly_critical": 0.75,
  "window_seconds": 5,
  "window_step_seconds": 1,
  "min_samples_per_window": 10
}
```

---

## 6. Папка `data/`

Папка отвечает за загрузку и подготовку телеметрии.

---

### 6.1. `data/schemas.py`

Здесь должны быть dataclass-структуры данных.

Рекомендуемые классы:

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

### 6.2. `data/loader.py`

Отвечает за загрузку данных.

Обязательные функции:

```python
def load_csv(path: str) -> pandas.DataFrame:
    ...
```

```python
def load_telemetry(path: str) -> pandas.DataFrame:
    ...
```

`load_telemetry` должен выбирать loader по расширению файла.

В версии 0.1 достаточно поддержать `.csv`.

---

### 6.3. `data/validator.py`

Отвечает за проверку данных.

Обязательные функции:

```python
def validate_dataframe(df: pandas.DataFrame) -> tuple[list[str], list[str]]:
    ...
```

```python
def check_required_columns(df: pandas.DataFrame) -> list[str]:
    ...
```

```python
def check_numeric_columns(df: pandas.DataFrame) -> list[str]:
    ...
```

```python
def check_time_column(df: pandas.DataFrame) -> list[str]:
    ...
```

Функции должны возвращать ошибки и предупреждения, а не сразу завершать программу.

---

### 6.4. `data/preprocessing.py`

Отвечает за приведение данных к каноническому виду.

Обязательные функции:

```python
def normalize_column_names(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

```python
def parse_time_columns(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

```python
def coerce_numeric_columns(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

```python
def dataframe_to_samples(df: pandas.DataFrame) -> list[TelemetrySample]:
    ...
```

```python
def preprocess_dataframe(df: pandas.DataFrame) -> TelemetryDataset:
    ...
```

---

### 6.5. `data/windowing.py`

Отвечает за разбиение сэмплов на окна.

Обязательные функции:

```python
def estimate_sampling_rate(samples: list[TelemetrySample]) -> float | None:
    ...
```

```python
def make_windows(
    samples: list[TelemetrySample],
    window_seconds: float,
    step_seconds: float,
    min_samples: int = 10
) -> list[TelemetryWindow]:
    ...
```

Окна должны идти с перекрытием.

Пример:

```text
0–5
1–6
2–7
3–8
```

---

## 7. Папка `features/`

Папка отвечает за расчёт признаков.

---

### 7.1. `features/basic_features.py`

Базовые математические функции.

Обязательные функции:

```python
def safe_mean(values: list[float]) -> float | None:
    ...
```

```python
def safe_min(values: list[float]) -> float | None:
    ...
```

```python
def safe_max(values: list[float]) -> float | None:
    ...
```

```python
def safe_std(values: list[float]) -> float | None:
    ...
```

```python
def rms(values: list[float]) -> float | None:
    ...
```

```python
def slope(times: list[float], values: list[float]) -> float | None:
    ...
```

Все функции должны корректно обрабатывать:

- пустые списки;
- `None`;
- `NaN`.

---

### 7.2. `features/motion_features.py`

Признаки движения.

Обязательные функции:

```python
def calculate_velocity_features(window: TelemetryWindow) -> dict:
    ...
```

```python
def calculate_position_features(window: TelemetryWindow) -> dict:
    ...
```

```python
def detect_motion_phase(features: dict) -> str:
    ...
```

Примеры признаков:

```text
velocity_mean
velocity_max
velocity_min
velocity_std
velocity_rms
abs_velocity_max
accel_mean
accel_max
motion_ratio
hold_ratio
position_delta
motion_phase
```

---

### 7.3. `features/electrical_features.py`

Признаки тока, момента и DC-шины.

Обязательные функции:

```python
def calculate_current_features(window: TelemetryWindow) -> dict:
    ...
```

```python
def calculate_torque_features(window: TelemetryWindow) -> dict:
    ...
```

```python
def calculate_voltage_features(window: TelemetryWindow) -> dict:
    ...
```

Примеры признаков:

```text
current_mean
current_max
current_rms
current_std
torque_mean
torque_max
torque_rms
torque_std
voltage_mean
voltage_min
voltage_max
voltage_std
```

---

### 7.4. `features/thermal_features.py`

Тепловые признаки.

Обязательные функции:

```python
def calculate_temperature_features(window: TelemetryWindow) -> dict:
    ...
```

Примеры признаков:

```text
temp_mean
temp_min
temp_max
temp_std
temp_slope
```

---

### 7.5. `features/status_features.py`

Признаки состояния и ошибок.

Обязательные функции:

```python
def decode_statusword(statusword: int | None) -> dict:
    ...
```

```python
def calculate_status_features(window: TelemetryWindow) -> dict:
    ...
```

Примеры признаков:

```text
error_flag
error_count
unique_error_codes
fault_flag
warning_flag
operation_enabled_ratio
```

---

### 7.6. `features/feature_extractor.py`

Главный модуль расчёта признаков.

Обязательная функция:

```python
def extract_features(window: TelemetryWindow) -> dict:
    ...
```

Эта функция должна вызвать все частные feature-модули и объединить результат в один словарь.

---

## 8. Папка `model/`

Папка содержит математическое ядро модели.

---

### 8.1. `model/physical_risks.py`

Расчёт физических рисков.

Обязательная функция:

```python
def calculate_physical_risks(features: dict, limits: dict) -> dict:
    ...
```

Должна вернуть:

```python
{
    "current": ...,
    "torque": ...,
    "velocity": ...,
    "voltage": ...,
    "temperature": ...,
    "statusword": ...,
    "error": ...,
    "data_quality": ...
}
```

Все значения должны быть от 0 до 1.

---

### 8.2. `model/statistical_profile.py`

Работа с нормальным статистическим профилем.

В версии 0.1 можно реализовать базовые заготовки.

Обязательные функции:

```python
def fit_normal_profile(feature_rows: list[dict]) -> dict:
    ...
```

```python
def save_profile(profile: dict, path: str) -> None:
    ...
```

```python
def load_profile(path: str) -> dict:
    ...
```

---

### 8.3. `model/anomaly_score.py`

Расчёт Anomaly Score.

В версии 0.1 можно вернуть 0, если profile отсутствует.

Обязательная функция:

```python
def calculate_anomaly_score(features: dict, profile: dict | None = None) -> dict:
    ...
```

Ожидаемый выход:

```python
{
    "anomaly_score": 0.0,
    "feature_scores": {}
}
```

---

### 8.4. `model/health_score.py`

Расчёт Health Score.

Обязательная функция:

```python
def calculate_health_score(risks: dict, weights: dict, features: dict | None = None) -> float:
    ...
```

Также желательно сделать:

```python
def apply_hard_limits(health_score: float, risks: dict, features: dict) -> float:
    ...
```

---

### 8.5. `model/classifier.py`

Классификация состояния.

Обязательная функция:

```python
def classify_state(
    health_score: float,
    anomaly_score: float,
    risks: dict,
    thresholds: dict,
    features: dict
) -> str:
    ...
```

Также:

```python
def risk_level_from_state(state: str) -> str:
    ...
```

---

### 8.6. `model/explanation.py`

Генерация объяснений и главных причин.

Обязательные функции:

```python
def get_main_causes(risks: dict, features: dict, top_n: int = 3) -> list[dict]:
    ...
```

```python
def generate_explanation(state: str, risks: dict, features: dict, main_causes: list[dict]) -> list[str]:
    ...
```

---

## 9. Папка `recommendations/`

### 9.1. `recommendations/rule_based.py`

Rule-based рекомендации без LLM.

Обязательная функция:

```python
def generate_recommendations(
    state: str,
    risks: dict,
    features: dict,
    main_causes: list[dict]
) -> list[dict]:
    ...
```

Рекомендации должны зависеть от главных рисков.

---

## 10. Папка `api/`

Папка содержит слой, который будет использовать backend или CLI.

---

### 10.1. `api/schemas.py`

JSON-совместимые структуры результата.

Можно использовать dataclass:

```python
@dataclass
class DiagnosticResult:
    window_start: float
    window_end: float
    device_id: str | None
    health_score: float
    anomaly_score: float
    state: str
    risk_level: str
    motion_phase: str
    features: dict
    risks: dict
    main_causes: list[dict]
    explanation: list[str]
    recommendations: list[dict]
    data_quality: dict
    debug: dict
```

---

### 10.2. `api/diagnostic_service.py`

Главный сервис диагностики.

Обязательные функции:

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

```python
def diagnose_csv(
    csv_path: str,
    limits_path: str,
    weights_path: str,
    thresholds_path: str,
    normal_profile_path: str | None = None
) -> list[dict]:
    ...
```

---

## 11. Папка `evaluation/`

Папка для будущей оценки качества.

В версии 0.1 можно создать заготовки.

### 11.1. `synthetic_anomalies.py`

Генерация искусственных аномалий.

Примеры функций:

```python
def inject_current_overload(df, start_t, end_t, multiplier):
    ...
```

```python
def inject_voltage_drop(df, start_t, end_t, drop_value):
    ...
```

```python
def inject_temperature_ramp(df, start_t, end_t, final_temp):
    ...
```

---

### 11.2. `metrics.py`

Метрики:

- accuracy;
- precision;
- recall;
- F1;
- false alarm rate;
- detection delay.

Можно оставить заготовки до появления размеченных данных.

---

### 11.3. `plots.py`

Графики:

- Health Score во времени;
- Anomaly Score во времени;
- риски во времени;
- телеметрия + пороги.

---

## 12. Папка `tests/`

Тесты должны использовать `pytest`.

Минимальные тесты:

```text
test_loader.py
test_validator.py
test_windowing.py
test_features.py
test_physical_risks.py
test_health_score.py
test_classifier.py
test_recommendations.py
```

---

## 13. Общие правила кодирования

### 13.1. Типизация

Использовать type hints.

Пример:

```python
def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    ...
```

---

### 13.2. Безопасная математика

Нужно реализовать utility-функции:

```python
def clamp(value, low=0.0, high=1.0):
    ...
```

```python
def safe_divide(numerator, denominator, default=0.0):
    ...
```

```python
def is_valid_number(value):
    ...
```

И использовать их в расчётах.

---

### 13.3. Нет падений на плохих данных

Модель не должна падать из-за:

- `None`;
- `NaN`;
- пустого окна;
- отсутствия необязательного поля;
- отсутствия статистического профиля.

---

### 13.4. Нет готовых ML-моделей

Запрещено использовать:

```text
sklearn
tensorflow
pytorch
keras
xgboost
lightgbm
catboost
```

---

## 14. Главная функция проекта

В итоге должна быть функция:

```python
diagnose_csv(...)
```

Пример использования:

```python
results = diagnose_csv(
    csv_path="data/telemetry.csv",
    limits_path="config/limits.json",
    weights_path="config/weights.json",
    thresholds_path="config/thresholds.json"
)
```

Она должна вернуть список результатов по окнам.

---

## 15. Acceptance criteria по архитектуре

Архитектура считается реализованной корректно, если:

1. Проект имеет описанную структуру папок.
2. Все ключевые модули разделены.
3. `main.py` не содержит бизнес-логики.
4. `diagnostic_service.py` является главным orchestrator.
5. Математика рисков находится в `model/`.
6. Признаки находятся в `features/`.
7. Загрузка и подготовка данных находятся в `data/`.
8. Рекомендации находятся в `recommendations/`.
9. Конфиги вынесены в JSON.
10. Тесты могут проверять модули отдельно.
