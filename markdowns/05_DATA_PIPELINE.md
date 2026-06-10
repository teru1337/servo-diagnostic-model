# 05_DATA_PIPELINE.md

# Pipeline обработки данных телеметрии

## 1. Назначение документа

Этот документ описывает полный путь данных в проекте `servo_diagnostic_model`.

Coding agent должен реализовать data pipeline так, чтобы сырая телеметрия из CSV превращалась в набор временных окон, готовых для расчёта признаков и диагностики.

Pipeline должен быть устойчивым к:

- пропущенным значениям;
- различным названиям колонок;
- неидеальной частоте дискретизации;
- коротким сессиям;
- отдельным ошибкам в данных;
- отсутствию необязательных колонок.

Главная задача pipeline:

```text
raw CSV
    ↓
load
    ↓
normalize columns
    ↓
validate
    ↓
preprocess
    ↓
convert to internal schema
    ↓
estimate sampling rate
    ↓
make time windows
    ↓
send windows to feature extraction
```

---

## 2. Роль data pipeline в проекте

Data pipeline не должен выполнять диагностику.

Он не должен считать:

- Health Score;
- Anomaly Score;
- физические риски;
- рекомендации;
- классификацию состояния.

Его задача — подготовить данные для следующих этапов.

Pipeline должен отвечать на вопросы:

1. Можно ли использовать файл?
2. Какие колонки доступны?
3. Есть ли критические ошибки?
4. Какая частота дискретизации?
5. Какова длительность записи?
6. Можно ли разбить данные на окна?
7. Есть ли предупреждения по качеству данных?

---

## 3. Общая схема

```text
Input file
    ↓
load_telemetry()
    ↓
normalize_column_names()
    ↓
parse_time_columns()
    ↓
coerce_numeric_columns()
    ↓
validate_dataframe()
    ↓
dataframe_to_samples()
    ↓
estimate_sampling_rate()
    ↓
make_windows()
    ↓
TelemetryWindow[]
```

---

## 4. Основные модули

Data pipeline должен быть распределён по модулям:

```text
data/
├── loader.py
├── validator.py
├── preprocessing.py
├── windowing.py
└── schemas.py
```

---

## 5. Входные форматы

### 5.1. Обязательный формат первой версии

В версии 0.1 обязательно реализовать загрузку CSV.

Поддержка:

```text
.csv
```

Пример вызова:

```python
df = load_csv("data/telemetry.csv")
```

---

### 5.2. Форматы будущих версий

Архитектура должна позволять позже добавить:

```text
.sqlite
.json
.parquet
API response
```

Но в первой версии не нужно реализовывать всё сразу.

---

## 6. Модуль `loader.py`

### 6.1. Назначение

`loader.py` отвечает только за чтение файла и возврат сырых данных в виде `pandas.DataFrame`.

Он не должен:

- валидировать физические значения;
- считать признаки;
- разбивать данные на окна;
- считать риски.

---

### 6.2. Обязательные функции

```python
def load_csv(path: str) -> pandas.DataFrame:
    """
    Load telemetry data from CSV file.

    Parameters:
        path: path to CSV file.

    Returns:
        pandas.DataFrame with raw telemetry rows.

    Raises:
        FileNotFoundError: if file does not exist.
        ValueError: if file is empty or cannot be parsed.
    """
```

```python
def load_telemetry(path: str) -> pandas.DataFrame:
    """
    Load telemetry data by file extension.

    Supported in v0.1:
        .csv

    Future:
        .sqlite
        .json
    """
```

---

### 6.3. Поведение `load_csv`

Функция должна:

1. Проверить, что файл существует.
2. Проверить, что файл не пустой.
3. Загрузить CSV через `pandas.read_csv`.
4. Вернуть `DataFrame`.
5. Не менять названия колонок.
6. Не приводить типы.
7. Не удалять строки.

---

### 6.4. Ошибки загрузки

| Ситуация                 | Действие                                |
| ------------------------ | --------------------------------------- |
| Файл не найден           | `FileNotFoundError`                     |
| Файл пустой              | `ValueError("Telemetry file is empty")` |
| Формат не CSV            | `ValueError("Unsupported file format")` |
| CSV невозможно прочитать | `ValueError` с пояснением               |

---

## 7. Модуль `preprocessing.py`

### 7.1. Назначение

`preprocessing.py` приводит данные к каноническому формату.

Задачи:

- нормализовать названия колонок;
- распарсить время;
- создать колонку `t`, если её нет;
- привести числовые поля к числам;
- отсортировать строки;
- подготовить данные для создания `TelemetrySample`.

---

### 7.2. Нормализация названий колонок

Функция:

```python
def normalize_column_names(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

Она должна:

1. Привести названия колонок к нижнему регистру.
2. Убрать лишние пробелы.
3. Заменить пробелы и дефисы на `_`.
4. Применить mapping алиасов.
5. Вернуть новый `DataFrame`.

---

### 7.3. Пример alias mapping

```python
COLUMN_ALIASES = {
    "timestamp": "ts",
    "datetime": "ts",
    "time_abs": "ts",

    "time": "t",
    "time_s": "t",
    "elapsed": "t",
    "elapsed_s": "t",

    "speed": "velocity",
    "rpm": "velocity",
    "velocity_rpm": "velocity",
    "actual_velocity": "velocity",

    "current_a": "current_A",
    "current_amp": "current_A",
    "current_ampere": "current_A",

    "torque_nm": "torque_Nm",
    "moment_nm": "torque_Nm",

    "dc_voltage": "dc_bus_voltage",
    "bus_voltage": "dc_bus_voltage",
    "vdc": "dc_bus_voltage",
    "voltage": "dc_bus_voltage",

    "temperature": "drive_temp",
    "temp": "drive_temp",
    "drive_temperature": "drive_temp",

    "status_word": "statusword",
    "cia402_statusword": "statusword",

    "fault_code": "error_code",
    "alarm_code": "error_code",
    "err_code": "error_code",

    "mode": "mode_display",
    "operation_mode": "mode_display"
}
```

Важно: если после mapping появляются дубликаты колонок, нужно обработать это явно.

Пример:

```text
Исходные колонки:
current_A, current_amp

Обе мапятся в current_A.
```

В такой ситуации:

- если значения одинаковые — оставить одну;
- если значения разные — добавить warning;
- приоритет отдать каноническому имени.

---

### 7.4. Парсинг времени

Функция:

```python
def parse_time_columns(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

Логика:

1. Если есть `t`, привести его к `float`.
2. Если `t` нет, но есть `ts`, распарсить `ts` как datetime.
3. Если есть `ts`, но нет `t`, создать `t`:

```text
t = ts - min(ts)
```

в секундах.

4. Если нет ни `t`, ни `ts`, это critical validation error.

---

### 7.5. Сортировка по времени

Функция:

```python
def sort_by_time(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

Приоритет сортировки:

1. `t`;
2. `ts`.

Если значения `t` не монотонны, нужно отсортировать.

Если есть одинаковые временные метки, не удалять их сразу, но добавить warning.

---

### 7.6. Приведение числовых колонок

Функция:

```python
def coerce_numeric_columns(df: pandas.DataFrame) -> pandas.DataFrame:
    ...
```

Числовые поля:

```text
t
position
velocity
torque
torque_Nm
current
current_A
dc_bus_voltage
drive_temp
rated_current_A
max_current_A
rated_torque_Nm
max_torque_Nm
max_velocity_rpm
```

Целочисленные поля:

```text
statusword
error_code
```

Если значение не приводится к числу:

- заменить на `NaN`;
- добавить warning;
- не завершать pipeline.

---

## 8. Модуль `validator.py`

### 8.1. Назначение

`validator.py` проверяет пригодность данных.

Он должен возвращать:

```python
validation_errors: list[str]
validation_warnings: list[str]
```

Ошибки делятся на:

- critical errors;
- warnings.

---

### 8.2. Critical errors

Critical error означает, что диагностику выполнять нельзя.

Примеры:

| Ошибка                                   | Причина                           |
| ---------------------------------------- | --------------------------------- |
| Нет времени                              | Невозможно построить окна         |
| Файл пустой                              | Нет данных                        |
| Нет ни одного диагностического параметра | Нечего анализировать              |
| Все строки некорректны                   | Невозможно создать dataset        |
| Длительность записи равна 0              | Невозможно анализировать динамику |

---

### 8.3. Warnings

Warning означает, что диагностику можно выполнять, но качество данных хуже.

Примеры:

| Warning                | Последствие                                  |
| ---------------------- | -------------------------------------------- |
| Нет `position`         | Нельзя анализировать микровибрации положения |
| Нет `mode_display`     | Режим нужно определять эвристически          |
| Нет `torque_Nm`        | Ограниченная диагностика момента             |
| Есть пропуски          | Повысить data quality risk                   |
| Есть временные разрывы | Повысить data quality risk                   |
| Очень короткая запись  | Меньше уверенность в выводе                  |

---

### 8.4. Обязательные функции

```python
def validate_dataframe(df: pandas.DataFrame) -> tuple[list[str], list[str]]:
    ...
```

```python
def check_time_column(df: pandas.DataFrame) -> list[str]:
    ...
```

```python
def check_required_columns(df: pandas.DataFrame) -> list[str]:
    ...
```

```python
def check_numeric_quality(df: pandas.DataFrame) -> list[str]:
    ...
```

```python
def check_duration(df: pandas.DataFrame) -> list[str]:
    ...
```

---

### 8.5. Минимальный набор колонок

Для первой версии желательно наличие:

```text
t или ts
velocity
current_A
torque_Nm
dc_bus_voltage
drive_temp
statusword
error_code
```

Но модель может работать частично.

Обязательными для запуска являются:

```text
t или ts
```

и хотя бы 3 диагностических параметра из списка:

```text
velocity
current_A
torque_Nm
dc_bus_voltage
drive_temp
statusword
error_code
```

Если диагностических параметров меньше 3, вернуть critical error.

---

## 9. Преобразование в `TelemetrySample`

Функция:

```python
def dataframe_to_samples(df: pandas.DataFrame) -> list[TelemetrySample]:
    ...
```

Она должна:

1. Пройти по строкам DataFrame.
2. Для каждой строки создать `TelemetrySample`.
3. Привести отсутствующие поля к `None`.
4. Не падать при `NaN`.
5. Сохранить порядок по времени.

---

## 10. Структура `TelemetryDataset`

После preprocessing должен быть создан объект:

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

---

## 11. Расчёт частоты дискретизации

Функция:

```python
def estimate_sampling_rate(samples: list[TelemetrySample]) -> float | None:
    ...
```

Алгоритм:

```text
1. Извлечь t из samples.
2. Отсортировать t.
3. Посчитать dt между соседними точками.
4. Удалить dt <= 0.
5. Взять median_dt.
6. sampling_rate = 1 / median_dt.
```

Если данных меньше 2 точек:

```python
return None
```

---

### 11.1. Почему использовать медиану

Среднее значение чувствительно к большим разрывам.

Пример:

```text
0.1, 0.1, 0.1, 5.0, 0.1
```

Среднее сильно исказится из-за разрыва 5 секунд. Медиана останется близкой к реальному шагу.

---

## 12. Расчёт длительности записи

Функция:

```python
def calculate_duration(samples: list[TelemetrySample]) -> float | None:
    ...
```

Формула:

```text
duration = max(t) - min(t)
```

Если точек меньше 2:

```python
return None
```

---

## 13. Разбиение на окна

Модуль:

```text
windowing.py
```

Функция:

```python
def make_windows(
    samples: list[TelemetrySample],
    window_seconds: float,
    step_seconds: float,
    min_samples: int = 10
) -> list[TelemetryWindow]:
    ...
```

---

### 13.1. Рекомендуемые параметры

Для первой версии:

```json
{
  "window_seconds": 5,
  "window_step_seconds": 1,
  "min_samples_per_window": 10
}
```

Если запись около 10 Гц, окно 5 секунд содержит около 50 точек.

---

### 13.2. Алгоритм windowing

```text
1. Найти start = min(t).
2. Найти end = max(t).
3. current_start = start.
4. Пока current_start + window_seconds <= end:
    window_start = current_start
    window_end = current_start + window_seconds
    выбрать samples, где window_start <= t < window_end
    если len(samples) >= min_samples:
        создать TelemetryWindow
    иначе:
        создать окно с warning или пропустить, в зависимости от режима
    current_start += step_seconds
```

---

### 13.3. Перекрывающиеся окна

Окна должны перекрываться.

Пример:

```text
window_seconds = 5
step_seconds = 1
```

Окна:

```text
0–5
1–6
2–7
3–8
4–9
...
```

Это даёт более плавный Health Score во времени.

---

### 13.4. Короткие окна

Если в окне меньше `min_samples`, есть два варианта:

1. Пропустить окно.
2. Создать окно, но пометить его как низкокачественное.

Рекомендация для первой версии:

```text
Если точек меньше min_samples — пропустить окно.
Если точек достаточно, но меньше ожидаемого количества — оставить окно и повысить data_quality_risk на этапе feature extraction.
```

---

## 14. Проверка временных разрывов

Функция:

```python
def detect_time_gaps(samples: list[TelemetrySample], expected_dt: float | None = None) -> list[dict]:
    ...
```

Алгоритм:

```text
1. Если expected_dt не передан, оценить его через median dt.
2. Для каждого dt между соседними точками:
    если dt > expected_dt * gap_multiplier:
        добавить gap.
```

Рекомендуемый параметр:

```text
gap_multiplier = 3
```

Пример результата:

```json
[
  {
    "start_t": 12.1,
    "end_t": 13.0,
    "gap_s": 0.9
  }
]
```

---

## 15. Data quality metadata

Для каждого окна нужно подготовить базовую информацию качества данных.

Поля:

```python
{
    "sample_count": 48,
    "expected_sample_count": 50,
    "missing_ratio": 0.02,
    "invalid_ratio": 0.00,
    "time_gap_count": 0,
    "sampling_rate_hz": 9.9,
    "is_too_short": False
}
```

Эту информацию можно считать в `features` или в `windowing`.

Рекомендуется:

- базовые данные окна считать в `windowing`;
- более детальную оценку качества считать в `feature_extractor`.

---

## 16. Главная функция подготовки dataset

Функция:

```python
def prepare_dataset(path: str) -> TelemetryDataset:
    ...
```

Псевдокод:

```python
def prepare_dataset(path: str) -> TelemetryDataset:
    raw_df = load_telemetry(path)

    df = normalize_column_names(raw_df)
    df = parse_time_columns(df)
    df = coerce_numeric_columns(df)
    df = sort_by_time(df)

    errors, warnings = validate_dataframe(df)

    if errors:
        return TelemetryDataset(
            samples=[],
            columns_available={},
            validation_errors=errors,
            validation_warnings=warnings,
            sampling_rate_hz=None,
            duration_s=None,
            device_id=None
        )

    samples = dataframe_to_samples(df)
    sampling_rate = estimate_sampling_rate(samples)
    duration = calculate_duration(samples)

    return TelemetryDataset(
        samples=samples,
        columns_available=detect_available_columns(df),
        validation_errors=errors,
        validation_warnings=warnings,
        sampling_rate_hz=sampling_rate,
        duration_s=duration,
        device_id=detect_device_id(samples)
    )
```

---

## 17. Главная функция подготовки окон

Функция:

```python
def prepare_windows(
    dataset: TelemetryDataset,
    thresholds: dict
) -> list[TelemetryWindow]:
    ...
```

Псевдокод:

```python
def prepare_windows(dataset, thresholds):
    if dataset.validation_errors:
        return []

    window_seconds = thresholds.get("window_seconds", 5)
    step_seconds = thresholds.get("window_step_seconds", 1)
    min_samples = thresholds.get("min_samples_per_window", 10)

    return make_windows(
        samples=dataset.samples,
        window_seconds=window_seconds,
        step_seconds=step_seconds,
        min_samples=min_samples
    )
```

---

## 18. Требования к устойчивости

Pipeline не должен падать при:

- лишних колонках;
- другом порядке колонок;
- отдельных пустых значениях;
- строковых числах;
- отрицательной скорости;
- отрицательном моменте;
- отсутствующем `device_id`;
- отсутствующем `mode_display`;
- отсутствующем `position`.

Pipeline должен падать или возвращать critical validation error при:

- отсутствии времени;
- пустом файле;
- невозможности создать хотя бы одно окно;
- полном отсутствии диагностических параметров.

---

## 19. Пример результата data pipeline

После выполнения pipeline должен быть результат:

```python
dataset = prepare_dataset("telemetry.csv")

windows = prepare_windows(dataset, thresholds)
```

Пример:

```python
print(dataset.sampling_rate_hz)
# 9.9

print(dataset.duration_s)
# 61.1

print(len(windows))
# примерно 56 окон при window=5s и step=1s
```

---

## 20. Тесты data pipeline

Минимальные тесты:

### 20.1. `test_load_csv_success`

Проверить, что CSV загружается.

---

### 20.2. `test_load_csv_file_not_found`

Проверить, что отсутствующий файл вызывает `FileNotFoundError`.

---

### 20.3. `test_normalize_column_names`

Проверить, что алиасы приводятся к каноническим именам.

---

### 20.4. `test_parse_time_from_t`

Проверить, что поле `t` корректно приводится к float.

---

### 20.5. `test_parse_time_from_ts`

Проверить, что при наличии `ts` создаётся `t`.

---

### 20.6. `test_validate_missing_time`

Проверить, что отсутствие `t` и `ts` даёт critical error.

---

### 20.7. `test_estimate_sampling_rate`

Проверить расчёт частоты по регулярному временному ряду.

---

### 20.8. `test_make_windows`

Проверить, что данные корректно делятся на окна.

---

### 20.9. `test_make_windows_short_data`

Проверить поведение при слишком короткой записи.

---

## 21. Acceptance criteria

Data pipeline считается готовым, если:

1. CSV-файл загружается.
2. Алиасы колонок приводятся к каноническим именам.
3. Время приводится к `t` в секундах.
4. Данные сортируются по времени.
5. Числовые поля приводятся к числовым типам.
6. Валидация возвращает errors и warnings.
7. Critical errors останавливают дальнейшую диагностику.
8. Warnings не останавливают диагностику.
9. Рассчитывается частота дискретизации.
10. Рассчитывается длительность записи.
11. DataFrame преобразуется в `TelemetrySample`.
12. Сэмплы разбиваются на перекрывающиеся окна.
13. Короткие окна обрабатываются корректно.
14. Pipeline не содержит логики Health Score.
15. Pipeline покрыт базовыми unit-тестами.
