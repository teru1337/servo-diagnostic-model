# 06_FEATURE_ENGINEERING.md

# Расчёт диагностических признаков

## 1. Назначение документа

Этот документ описывает feature engineering для проекта `servo_diagnostic_model`.

Coding agent должен реализовать расчёт признаков из временного окна телеметрии.

Признаки — это промежуточный слой между сырыми данными и диагностической моделью.

Модель не должна напрямую принимать сырые ряды скорости, тока, момента и температуры. Сначала нужно преобразовать окно телеметрии в компактный словарь признаков.

Общая схема:

```text
TelemetryWindow
    ↓
extract_features(window)
    ↓
features: dict
    ↓
physical risk model
    ↓
statistical anomaly model
```

---

## 2. Почему нужны признаки

Один сэмпл телеметрии показывает состояние только в один момент времени.

Но диагностика требует анализа поведения во времени:

- RMS-ток нельзя оценить по одной точке;
- тренд температуры виден только на окне;
- стабильность DC-шины оценивается по разбросу;
- микровибрации видны по изменению скорости и положения;
- фаза движения определяется по динамике;
- выбросы определяются по минимумам, максимумам и стандартным отклонениям.

Поэтому каждое окно телеметрии нужно преобразовать в признаки.

---

## 3. Вход и выход feature extraction

### 3.1. Вход

Вход:

```python
TelemetryWindow
```

Структура:

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

### 3.2. Выход

Выход:

```python
dict
```

Пример:

```python
{
    "window_start": 0.0,
    "window_end": 5.0,
    "sample_count": 50,

    "velocity_mean": 120.5,
    "velocity_max": 1789.0,
    "velocity_min": 0.0,
    "velocity_std": 35.2,
    "velocity_rms": 310.4,
    "abs_velocity_max": 1789.0,

    "current_mean": 0.055,
    "current_max": 0.128,
    "current_rms": 0.071,
    "current_std": 0.015,

    "torque_mean": 0.021,
    "torque_max": 0.074,
    "torque_rms": 0.033,
    "torque_std": 0.008,

    "voltage_mean": 305.1,
    "voltage_min": 304.8,
    "voltage_max": 305.5,
    "voltage_std": 0.26,

    "temp_mean": 37.0,
    "temp_min": 37.0,
    "temp_max": 37.0,
    "temp_std": 0.0,
    "temp_slope": 0.0,

    "error_flag": False,
    "error_count": 0,
    "fault_flag": False,
    "warning_flag": False,

    "motion_phase": "holding",
    "motion_ratio": 0.08,
    "hold_ratio": 0.92,

    "missing_ratio": 0.0,
    "invalid_ratio": 0.0,
    "data_quality_notes": []
}
```

---

## 4. Модули feature engineering

Файлы:

```text
features/
├── basic_features.py
├── motion_features.py
├── electrical_features.py
├── thermal_features.py
├── status_features.py
└── feature_extractor.py
```

---

## 5. Общие правила расчёта признаков

### 5.1. Все функции должны быть safe

Функции не должны падать при:

- пустом списке;
- `None`;
- `NaN`;
- бесконечности;
- отсутствии поля в сэмпле.

Если признак нельзя посчитать, вернуть:

```python
None
```

или разумное значение по умолчанию, если это явно описано.

---

### 5.2. Не скрывать проблемы данных

Если данные плохие, нельзя просто молча вернуть 0.

Пример:

```text
Нет current_A.
```

Плохо:

```python
current_rms = 0
```

Хорошо:

```python
current_rms = None
feature_warnings.append("current_A is missing")
```

---

### 5.3. Все признаки должны иметь стабильные имена

Нельзя в одном месте использовать `temp_max`, а в другом `temperature_max`.

Использовать имена из этого документа.

---

### 5.4. Единицы измерения

Feature extraction не должен менять физический смысл единиц.

Ожидаемые единицы:

| Признак           | Единица |
| ----------------- | ------- |
| velocity\_\*      | RPM     |
| current\_\*       | A       |
| torque\_\*        | Н·м     |
| voltage\_\*       | V       |
| temp\_\*          | °C      |
| slope temperature | °C/s    |
| acceleration      | RPM/s   |

---

## 6. Модуль `basic_features.py`

### 6.1. Назначение

Содержит базовые математические функции, используемые остальными модулями.

---

### 6.2. Функция `is_valid_number`

```python
def is_valid_number(value: object) -> bool:
    ...
```

Должна вернуть `True`, если значение:

- int или float;
- не `NaN`;
- не бесконечность;
- не `None`.

---

### 6.3. Функция `clean_values`

```python
def clean_values(values: list[object]) -> list[float]:
    ...
```

Должна удалить:

- `None`;
- `NaN`;
- бесконечности;
- строки, которые нельзя привести к числу.

---

### 6.4. Функция `safe_mean`

```python
def safe_mean(values: list[object]) -> float | None:
    ...
```

Если после очистки нет значений:

```python
return None
```

---

### 6.5. Функция `safe_min`

```python
def safe_min(values: list[object]) -> float | None:
    ...
```

---

### 6.6. Функция `safe_max`

```python
def safe_max(values: list[object]) -> float | None:
    ...
```

---

### 6.7. Функция `safe_std`

```python
def safe_std(values: list[object]) -> float | None:
    ...
```

Требование:

- если значений меньше 2, вернуть `0.0` или `None`.

Рекомендация:

```python
если len(values) == 1:
    return 0.0
если len(values) == 0:
    return None
```

---

### 6.8. Функция `rms`

```python
def rms(values: list[object]) -> float | None:
    ...
```

Формула:

```text
RMS = sqrt(mean(x_i^2))
```

Для тока и момента обычно использовать абсолютные значения не обязательно, потому что квадрат уже убирает знак.

---

### 6.9. Функция `slope`

```python
def slope(times: list[float], values: list[float]) -> float | None:
    ...
```

Назначение — оценить линейный тренд.

Можно реализовать простую линейную регрессию через `numpy.polyfit` или вручную.

Формула вручную:

```text
slope = sum((t_i - mean_t) * (x_i - mean_x)) / sum((t_i - mean_t)^2)
```

Если точек меньше 2:

```python
return None
```

Если все `t` одинаковые:

```python
return None
```

---

### 6.10. Функция `safe_abs_max`

```python
def safe_abs_max(values: list[object]) -> float | None:
    ...
```

Возвращает максимальное абсолютное значение.

Используется для:

- скорости;
- момента;
- тока.

---

## 7. Модуль `motion_features.py`

### 7.1. Назначение

Считает признаки движения:

- скорость;
- ускорение;
- положение;
- фаза движения;
- доля движения;
- доля удержания.

---

### 7.2. Функция `calculate_velocity_features`

```python
def calculate_velocity_features(window: TelemetryWindow) -> dict:
    ...
```

Должна вернуть:

```python
{
    "velocity_mean": ...,
    "velocity_min": ...,
    "velocity_max": ...,
    "velocity_std": ...,
    "velocity_rms": ...,
    "abs_velocity_max": ...
}
```

---

### 7.3. Ускорение

Ускорение считать как производную скорости:

```text
accel_i = (velocity_i - velocity_{i-1}) / (t_i - t_{i-1})
```

Единица:

```text
RPM/s
```

Функция:

```python
def calculate_acceleration_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "accel_mean": ...,
    "accel_min": ...,
    "accel_max": ...,
    "accel_std": ...,
    "abs_accel_max": ...
}
```

Если временной шаг некорректный, пропускать пару точек.

---

### 7.4. Признаки положения

Функция:

```python
def calculate_position_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "position_min": ...,
    "position_max": ...,
    "position_delta": ...,
    "position_std": ...
}
```

Если `position` отсутствует:

```python
{
    "position_min": None,
    "position_max": None,
    "position_delta": None,
    "position_std": None
}
```

---

### 7.5. Motion ratio

`motion_ratio` — доля точек окна, где привод считается движущимся.

Порог скорости:

```text
velocity_motion_threshold_rpm
```

Рекомендуемое значение по умолчанию:

```text
10 RPM
```

Формула:

```text
motion_ratio = count(abs(velocity) > threshold) / sample_count
```

---

### 7.6. Hold ratio

```text
hold_ratio = 1 - motion_ratio
```

Если данных скорости нет:

```python
hold_ratio = None
```

---

### 7.7. Определение фазы движения

Функция:

```python
def detect_motion_phase(features: dict, thresholds: dict | None = None) -> str:
    ...
```

Допустимые фазы:

```text
holding
acceleration
moving
braking
stopped
mixed
unknown
```

---

### 7.8. Простая логика фаз

Рекомендуемая логика для версии 0.1:

```text
если sample_count слишком мал:
    unknown

если abs_velocity_max < velocity_stop_threshold:
    stopped

если motion_ratio < 0.2:
    holding

если accel_mean > accel_threshold и velocity_mean > velocity_motion_threshold:
    acceleration

если accel_mean < -accel_threshold и velocity_mean > velocity_motion_threshold:
    braking

если velocity_std < velocity_stability_threshold и motion_ratio >= 0.5:
    moving

иначе:
    mixed
```

---

### 7.9. Особенность знака скорости

Скорость может быть отрицательной. Поэтому для определения движения использовать:

```text
abs(velocity)
```

---

## 8. Модуль `electrical_features.py`

### 8.1. Назначение

Считает признаки:

- тока;
- момента;
- DC-шины;
- связей между током, моментом и скоростью.

---

### 8.2. Признаки тока

Функция:

```python
def calculate_current_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "current_mean": ...,
    "current_min": ...,
    "current_max": ...,
    "current_abs_max": ...,
    "current_rms": ...,
    "current_std": ...
}
```

Использовать приоритет:

1. `current_A`;
2. если `current_A` нет, использовать `current`;
3. если нет обоих — вернуть `None`.

Если используется `current`, а не `current_A`, нужно добавить признак:

```python
"current_unit": "relative"
```

Если используется `current_A`:

```python
"current_unit": "A"
```

---

### 8.3. Признаки момента

Функция:

```python
def calculate_torque_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "torque_mean": ...,
    "torque_min": ...,
    "torque_max": ...,
    "torque_abs_max": ...,
    "torque_rms": ...,
    "torque_std": ...
}
```

Приоритет:

1. `torque_Nm`;
2. если нет, использовать `torque`;
3. если нет обоих — вернуть `None`.

Добавить:

```python
"torque_unit": "Nm"
```

или

```python
"torque_unit": "relative"
```

---

### 8.4. Признаки DC-шины

Функция:

```python
def calculate_voltage_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "voltage_mean": ...,
    "voltage_min": ...,
    "voltage_max": ...,
    "voltage_std": ...,
    "voltage_range": ...
}
```

Формула:

```text
voltage_range = voltage_max - voltage_min
```

---

### 8.5. Связь тока и момента

Функция:

```python
def calculate_load_relation_features(window: TelemetryWindow, base_features: dict) -> dict:
    ...
```

Признаки:

```text
current_to_torque_ratio
current_at_low_speed
torque_at_low_speed
```

---

### 8.6. `current_to_torque_ratio`

Если есть `current_rms` и `torque_rms`:

```text
current_to_torque_ratio = current_rms / max(torque_rms, eps)
```

Если `torque_rms` около нуля, не допускать деления на ноль.

---

### 8.7. `current_at_low_speed`

Смысл:

> Средний или RMS-ток на точках, где скорость близка к нулю.

Алгоритм:

```text
1. Найти точки, где abs(velocity) < low_speed_threshold.
2. Взять current_A на этих точках.
3. Посчитать RMS.
```

Это полезно для поиска возможной нагрузки или заклинивания при удержании.

---

### 8.8. `torque_at_low_speed`

Аналогично:

```text
1. Найти точки, где abs(velocity) < low_speed_threshold.
2. Взять torque_Nm.
3. Посчитать RMS.
```

---

## 9. Модуль `thermal_features.py`

### 9.1. Назначение

Считает тепловые признаки.

Функция:

```python
def calculate_temperature_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "temp_mean": ...,
    "temp_min": ...,
    "temp_max": ...,
    "temp_std": ...,
    "temp_slope": ...
}
```

---

### 9.2. Temperature slope

Формула:

```text
temp_slope = dT / dt
```

Единица:

```text
°C/s
```

Лучше считать через функцию `slope(times, temperatures)`.

---

### 9.3. Обработка стабильной температуры

Если температура во всём окне одинаковая:

```python
temp_slope = 0.0
temp_std = 0.0
```

Это нормальная ситуация.

---

## 10. Модуль `status_features.py`

### 10.1. Назначение

Считает признаки:

- ошибок;
- аварийных флагов;
- предупреждений;
- состояния CiA 402.

---

### 10.2. Декодирование statusword

Функция:

```python
def decode_statusword(statusword: int | None) -> dict:
    ...
```

Рекомендуемый базовый вариант:

```python
def decode_statusword(statusword):
    if statusword is None:
        return {
            "statusword_available": False,
            "ready_to_switch_on": False,
            "switched_on": False,
            "operation_enabled": False,
            "fault": False,
            "voltage_enabled": False,
            "warning": False
        }

    return {
        "statusword_available": True,
        "ready_to_switch_on": bool(statusword & 0x0001),
        "switched_on": bool(statusword & 0x0002),
        "operation_enabled": bool(statusword & 0x0004),
        "fault": bool(statusword & 0x0008),
        "voltage_enabled": bool(statusword & 0x0010),
        "warning": bool(statusword & 0x0080)
    }
```

Если позже будут уточнены битовые маски, нужно заменить только эту функцию.

---

### 10.3. Признаки statusword по окну

Функция:

```python
def calculate_status_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "statusword_available": True,
    "fault_flag": False,
    "warning_flag": False,
    "operation_enabled_ratio": 1.0,
    "fault_count": 0,
    "warning_count": 0
}
```

Логика:

```text
fault_flag = True, если хотя бы в одной точке fault=True
warning_flag = True, если хотя бы в одной точке warning=True
operation_enabled_ratio = доля точек с operation_enabled=True
```

---

### 10.4. Признаки error_code

Поля:

```python
{
    "error_flag": False,
    "error_count": 0,
    "unique_error_codes": []
}
```

Логика:

```text
error_flag = True, если есть error_code != 0
error_count = количество точек с error_code != 0
unique_error_codes = уникальные ненулевые error_code
```

---

## 11. Data quality features

Data quality можно считать в отдельной функции:

```python
def calculate_data_quality_features(window: TelemetryWindow) -> dict:
    ...
```

Выход:

```python
{
    "sample_count": 50,
    "missing_ratio": 0.0,
    "invalid_ratio": 0.0,
    "time_gap_count": 0,
    "is_too_short": False,
    "flatline_velocity": False,
    "flatline_current": False,
    "flatline_voltage": False,
    "flatline_temp": True,
    "data_quality_notes": []
}
```

---

### 11.1. Missing ratio

```text
missing_ratio = missing_values / total_expected_values
```

Считать по ключевым полям:

```text
velocity
current_A
torque_Nm
dc_bus_voltage
drive_temp
statusword
error_code
```

---

### 11.2. Invalid ratio

Invalid values:

- NaN;
- бесконечность;
- невозможные значения;
- строки после preprocessing.

---

### 11.3. Flatline

Flatline — параметр почти не меняется.

Функция:

```python
def is_flatline(values: list[float], tolerance: float = 1e-9) -> bool:
    ...
```

Логика:

```text
если max(values) - min(values) <= tolerance:
    True
```

Но flatline не всегда является проблемой.

Например:

- температура может быть стабильной;
- скорость может быть нулевой в режиме остановки;
- напряжение может быть почти стабильным.

Flatline лучше использовать как информационный признак, а не как прямую аварию.

---

## 12. Главный модуль `feature_extractor.py`

### 12.1. Назначение

Объединяет все признаки в один словарь.

Функция:

```python
def extract_features(window: TelemetryWindow, thresholds: dict | None = None) -> dict:
    ...
```

---

### 12.2. Псевдокод

```python
def extract_features(window, thresholds=None):
    features = {}

    features.update({
        "window_start": window.start_t,
        "window_end": window.end_t,
        "sample_count": len(window.samples),
        "device_id": window.device_id,
        "sampling_rate_hz": window.sampling_rate_hz
    })

    features.update(calculate_velocity_features(window))
    features.update(calculate_acceleration_features(window))
    features.update(calculate_position_features(window))

    features.update(calculate_current_features(window))
    features.update(calculate_torque_features(window))
    features.update(calculate_voltage_features(window))
    features.update(calculate_load_relation_features(window, features))

    features.update(calculate_temperature_features(window))
    features.update(calculate_status_features(window))
    features.update(calculate_data_quality_features(window))

    motion_phase = detect_motion_phase(features, thresholds)
    features["motion_phase"] = motion_phase

    return features
```

---

## 13. Минимальный набор признаков для Version 0.1

Обязательно реализовать:

```text
window_start
window_end
sample_count

velocity_mean
velocity_max
velocity_min
velocity_std
velocity_rms
abs_velocity_max

current_mean
current_max
current_abs_max
current_rms
current_std

torque_mean
torque_max
torque_abs_max
torque_rms
torque_std

voltage_mean
voltage_min
voltage_max
voltage_std
voltage_range

temp_mean
temp_min
temp_max
temp_std
temp_slope

error_flag
error_count
unique_error_codes

fault_flag
warning_flag
operation_enabled_ratio

motion_ratio
hold_ratio
motion_phase

missing_ratio
invalid_ratio
time_gap_count
is_too_short
```

---

## 14. Признаки для Version 0.2+

Добавить позже:

```text
current_to_torque_ratio
current_at_low_speed
torque_at_low_speed

velocity_outlier_count
current_outlier_count
torque_outlier_count

micro_vibration_score
position_jitter
voltage_instability_score

mode_display_encoded
phase_transition_count
statusword_transition_count
```

---

## 15. Тесты feature engineering

Минимальные тесты:

### 15.1. RMS

```text
values = [1, 1, 1]
rms = 1
```

---

### 15.2. RMS with negative values

```text
values = [-1, 1]
rms = 1
```

---

### 15.3. Empty values

```text
values = []
rms = None
```

---

### 15.4. Velocity features

Проверить:

```text
velocity_max
velocity_min
abs_velocity_max
velocity_rms
```

---

### 15.5. Temperature slope

Для линейного роста температуры проверить положительный slope.

---

### 15.6. Error flag

Если в окне есть `error_code != 0`, `error_flag=True`.

---

### 15.7. Fault flag

Если `statusword` содержит fault-bit, `fault_flag=True`.

---

### 15.8. Motion phase

Проверить:

- stopped;
- holding;
- moving;
- acceleration;
- braking;
- mixed.

---

## 16. Acceptance criteria

Feature engineering считается готовым, если:

1. Есть функция `extract_features(window)`.
2. Она возвращает единый словарь признаков.
3. Все обязательные признаки Version 0.1 рассчитываются.
4. Пустые и плохие данные не ломают код.
5. RMS считается корректно.
6. Slope считается корректно.
7. Error/status признаки считаются корректно.
8. Фаза движения определяется хотя бы эвристически.
9. Data quality признаки возвращаются.
10. Все функции покрыты базовыми unit-тестами.
