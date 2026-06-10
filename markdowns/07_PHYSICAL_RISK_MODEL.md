# 07_PHYSICAL_RISK_MODEL.md

# Физическая модель рисков

## 1. Назначение документа

Этот документ описывает физическую часть диагностической модели.

Coding agent должен реализовать модуль `model/physical_risks.py`, который принимает признаки окна телеметрии и паспортные ограничения, а возвращает набор рисков по шкале от 0 до 1.

Физическая модель рисков отвечает на вопрос:

> Насколько текущие параметры сервопривода близки к опасным или паспортным ограничениям?

---

## 2. Место физической модели в pipeline

```text
TelemetryWindow
    ↓
extract_features()
    ↓
features
    ↓
calculate_physical_risks(features, limits)
    ↓
risks
    ↓
calculate_health_score()
```

---

## 3. Главный принцип

Каждый риск должен быть числом:

```text
0 <= risk <= 1
```

Интерпретация:

| Значение | Смысл                    |
| -------: | ------------------------ |
|      0.0 | Риска нет                |
|  0.1–0.3 | Низкий риск              |
|  0.3–0.5 | Наблюдение               |
| 0.5–0.75 | Предупреждение           |
| 0.75–1.0 | Высокий/критический риск |
|      1.0 | Максимальный риск        |

---

## 4. Обязательные риски

Функция должна возвращать:

```python
{
    "current": 0.0,
    "torque": 0.0,
    "velocity": 0.0,
    "voltage": 0.0,
    "temperature": 0.0,
    "statusword": 0.0,
    "error": 0.0,
    "data_quality": 0.0,
    "statistical_anomaly": 0.0
}
```

В `physical_risks.py` можно вернуть `statistical_anomaly = 0.0`, если статистическая модель подключается позже. Но в итоговом объединении нужно учитывать этот ключ.

---

## 5. Конфигурация `limits.json`

Физическая модель использует `limits`.

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
  "voltage_std_limit": 5.0,

  "temp_safe": 55,
  "temp_warning": 70,
  "temp_critical": 85,
  "temp_slope_limit": 0.2,

  "missing_ratio_limit": 0.3,
  "invalid_ratio_limit": 0.2,
  "time_gap_count_limit": 3
}
```

Если какого-то предела нет, соответствующий риск нужно считать осторожно.

---

## 6. Utility-функции

### 6.1. `clamp`

```python
def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    ...
```

Должна ограничивать значение диапазоном.

---

### 6.2. `safe_divide`

```python
def safe_divide(numerator: float | None, denominator: float | None, default: float = 0.0) -> float:
    ...
```

Если denominator:

- `None`;
- `0`;
- NaN;
- бесконечность,

вернуть `default`.

---

### 6.3. `linear_risk`

```python
def linear_risk(value: float, safe: float, critical: float) -> float:
    ...
```

Смысл:

```text
value <= safe      → 0
value >= critical  → 1
между ними        → линейный рост
```

Формула:

```text
risk = (value - safe) / (critical - safe)
```

с `clamp`.

---

### 6.4. `inverse_linear_risk`

Для случаев, когда опасны низкие значения.

```python
def inverse_linear_risk(value: float, safe: float, critical: float) -> float:
    ...
```

Смысл:

```text
value >= safe      → 0
value <= critical  → 1
между ними        → линейный рост риска
```

Формула:

```text
risk = (safe - value) / (safe - critical)
```

---

## 7. Риск по току

### 7.1. Назначение

Ток показывает электрическую и тепловую нагрузку.

Риск по току должен учитывать:

- RMS-ток;
- пиковый ток;
- номинальный ток;
- максимальный ток.

---

### 7.2. Входные признаки

Из `features`:

```text
current_rms
current_abs_max
current_unit
motion_phase
current_at_low_speed
```

Из `limits`:

```text
rated_current_A
max_current_A
```

---

### 7.3. Формула

```text
risk_current_rms = current_rms / rated_current_A
risk_current_peak = current_abs_max / max_current_A
risk_current = max(risk_current_rms, risk_current_peak)
risk_current = clamp(risk_current)
```

---

### 7.4. Если есть только относительный ток

Если `current_unit == "relative"`, а ампер нет:

- использовать относительное значение;
- риск считать осторожно;
- добавить warning в debug/explanation.

Пример:

```text
если current_rms <= 1000 промилле:
    risk_current = current_rms / 1000
```

Но это зависит от формата данных. В первой версии лучше:

```text
Если current_A отсутствует и нет понятного rated_current:
    risk_current = 0.0
    current_risk_available = False
```

---

### 7.5. Дополнительный риск: высокий ток при малой скорости

Если:

```text
motion_phase in ["holding", "stopped"]
```

и ток высокий, это подозрительнее, чем высокий ток при разгоне.

Можно добавить усиление:

```text
если motion_phase == "holding" и current_at_low_speed / rated_current_A > 0.5:
    risk_current = max(risk_current, current_at_low_speed / rated_current_A)
```

---

### 7.6. Функция

```python
def calculate_current_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 8. Риск по моменту

### 8.1. Назначение

Момент показывает механическую нагрузку.

Риск по моменту должен учитывать:

- RMS-момент;
- пиковый момент;
- номинальный момент;
- максимальный момент.

---

### 8.2. Входные признаки

```text
torque_rms
torque_abs_max
torque_unit
torque_at_low_speed
motion_phase
```

Пределы:

```text
rated_torque_Nm
max_torque_Nm
```

---

### 8.3. Формула

```text
risk_torque_rms = torque_rms / rated_torque_Nm
risk_torque_peak = torque_abs_max / max_torque_Nm
risk_torque = max(risk_torque_rms, risk_torque_peak)
risk_torque = clamp(risk_torque)
```

---

### 8.4. Высокий момент при удержании

Если `motion_phase == "holding"` и момент заметно высокий:

```text
risk_torque = max(risk_torque, torque_at_low_speed / rated_torque_Nm)
```

---

### 8.5. Функция

```python
def calculate_torque_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 9. Риск по скорости

### 9.1. Назначение

Скорость показывает близость к скоростному пределу.

---

### 9.2. Входные признаки

```text
abs_velocity_max
```

Предел:

```text
max_velocity_rpm
```

---

### 9.3. Формула

```text
risk_velocity = abs_velocity_max / max_velocity_rpm
risk_velocity = clamp(risk_velocity)
```

---

### 9.4. Особенность

Скорость может быть отрицательной, поэтому использовать:

```text
abs_velocity_max
```

---

### 9.5. Функция

```python
def calculate_velocity_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 10. Риск по DC-шине

### 10.1. Назначение

DC-шина нужна для контроля питания.

Риск по напряжению должен учитывать:

- просадку;
- перенапряжение;
- нестабильность.

---

### 10.2. Входные признаки

```text
voltage_min
voltage_max
voltage_std
voltage_range
```

Пределы:

```text
dc_bus_min_safe
dc_bus_max_safe
dc_bus_min_critical
dc_bus_max_critical
voltage_std_limit
```

---

### 10.3. Риск просадки

```text
risk_voltage_low = inverse_linear_risk(
    value=voltage_min,
    safe=dc_bus_min_safe,
    critical=dc_bus_min_critical
)
```

---

### 10.4. Риск перенапряжения

```text
risk_voltage_high = linear_risk(
    value=voltage_max,
    safe=dc_bus_max_safe,
    critical=dc_bus_max_critical
)
```

---

### 10.5. Риск нестабильности

```text
risk_voltage_unstable = voltage_std / voltage_std_limit
risk_voltage_unstable = clamp(risk_voltage_unstable)
```

---

### 10.6. Итоговый риск

```text
risk_voltage = max(
    risk_voltage_low,
    risk_voltage_high,
    risk_voltage_unstable
)
```

---

### 10.7. Функция

```python
def calculate_voltage_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 11. Риск по температуре

### 11.1. Назначение

Температура показывает тепловое состояние силовой части.

Риск должен учитывать:

- максимальную температуру;
- среднюю температуру;
- тренд температуры.

---

### 11.2. Входные признаки

```text
temp_mean
temp_max
temp_slope
```

Пределы:

```text
temp_safe
temp_warning
temp_critical
temp_slope_limit
```

---

### 11.3. Риск уровня температуры

```text
risk_temp_level = linear_risk(
    value=temp_max,
    safe=temp_safe,
    critical=temp_critical
)
```

---

### 11.4. Риск быстрого роста температуры

```text
risk_temp_slope = temp_slope / temp_slope_limit
risk_temp_slope = clamp(risk_temp_slope)
```

Если `temp_slope < 0`, риск по росту должен быть 0.

```text
risk_temp_slope = clamp(max(temp_slope, 0) / temp_slope_limit)
```

---

### 11.5. Итоговый риск

```text
risk_temperature = max(
    risk_temp_level,
    risk_temp_slope
)
```

---

### 11.6. Функция

```python
def calculate_temperature_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 12. Риск по `error_code`

### 12.1. Назначение

Код ошибки является жёстким диагностическим признаком.

---

### 12.2. Входные признаки

```text
error_flag
error_count
unique_error_codes
```

---

### 12.3. Формула

```text
если error_flag == True:
    risk_error = 1.0
иначе:
    risk_error = 0.0
```

---

### 12.4. Функция

```python
def calculate_error_risk(features: dict) -> float:
    ...
```

---

## 13. Риск по `statusword`

### 13.1. Назначение

`statusword` содержит флаги состояния привода.

---

### 13.2. Входные признаки

```text
statusword_available
fault_flag
warning_flag
operation_enabled_ratio
```

---

### 13.3. Формула

```text
если statusword_available == False:
    risk_statusword = 0.3

если fault_flag == True:
    risk_statusword = 1.0

иначе если warning_flag == True:
    risk_statusword = 0.6

иначе:
    risk_statusword = 0.0
```

---

### 13.4. Operation enabled

Если привод должен быть активен, но `operation_enabled_ratio` низкий, это может быть проблемой.

Но в первой версии не делать это критическим, потому что привод может быть остановлен штатно.

Можно добавить мягкий риск:

```text
если operation_enabled_ratio == 0 и motion_phase != "stopped":
    risk_statusword = max(risk_statusword, 0.4)
```

---

### 13.5. Функция

```python
def calculate_statusword_risk(features: dict) -> float:
    ...
```

---

## 14. Риск качества данных

### 14.1. Назначение

Если данные плохие, модель должна быть менее уверенной.

Качество данных не всегда означает аварию оборудования, но влияет на достоверность диагностики.

---

### 14.2. Входные признаки

```text
missing_ratio
invalid_ratio
time_gap_count
is_too_short
sample_count
```

Пределы:

```text
missing_ratio_limit
invalid_ratio_limit
time_gap_count_limit
```

---

### 14.3. Риск пропусков

```text
risk_missing = missing_ratio / missing_ratio_limit
risk_missing = clamp(risk_missing)
```

---

### 14.4. Риск некорректных значений

```text
risk_invalid = invalid_ratio / invalid_ratio_limit
risk_invalid = clamp(risk_invalid)
```

---

### 14.5. Риск временных разрывов

```text
risk_gaps = time_gap_count / time_gap_count_limit
risk_gaps = clamp(risk_gaps)
```

---

### 14.6. Слишком короткое окно

```text
если is_too_short:
    risk_short = 1.0
иначе:
    risk_short = 0.0
```

---

### 14.7. Итог

```text
risk_data_quality = max(
    risk_missing,
    risk_invalid,
    risk_gaps,
    risk_short
)
```

---

### 14.8. Функция

```python
def calculate_data_quality_risk(features: dict, limits: dict) -> float:
    ...
```

---

## 15. Общая функция `calculate_physical_risks`

```python
def calculate_physical_risks(features: dict, limits: dict) -> dict:
    ...
```

Псевдокод:

```python
def calculate_physical_risks(features, limits):
    risks = {}

    risks["current"] = calculate_current_risk(features, limits)
    risks["torque"] = calculate_torque_risk(features, limits)
    risks["velocity"] = calculate_velocity_risk(features, limits)
    risks["voltage"] = calculate_voltage_risk(features, limits)
    risks["temperature"] = calculate_temperature_risk(features, limits)
    risks["error"] = calculate_error_risk(features)
    risks["statusword"] = calculate_statusword_risk(features)
    risks["data_quality"] = calculate_data_quality_risk(features, limits)

    # Placeholder. Will be overwritten by statistical model later.
    risks["statistical_anomaly"] = 0.0

    return {key: clamp(value) for key, value in risks.items()}
```

---

## 16. Что делать при отсутствии признака

Если признак отсутствует, нельзя аварийно завершать программу.

Примеры:

| Отсутствует   | Действие                                            |
| ------------- | --------------------------------------------------- |
| `current_rms` | `current` risk = 0, но отметить недоступность       |
| `torque_rms`  | `torque` risk = 0, но отметить недоступность        |
| `voltage_min` | `voltage` risk = 0.3 или недоступность              |
| `temp_max`    | `temperature` risk = 0.3 или недоступность          |
| `statusword`  | `statusword` risk = 0.3                             |
| `error_code`  | `error` risk = 0.3 или 0, в зависимости от политики |

Рекомендация:

```text
Для отсутствия критически важных параметров повышать data_quality_risk.
Не завышать физический риск параметра без данных.
```

---

## 17. Output metadata

В будущем желательно возвращать не только значения рисков, но и metadata.

Например:

```python
{
    "risks": {
        "current": 0.03,
        "torque": 0.02
    },
    "risk_details": {
        "current": {
            "available": True,
            "reason": "current_rms and current_abs_max are within limits"
        }
    }
}
```

В Version 0.1 можно возвращать только `risks`.

---

## 18. Unit-тесты

Минимальные тесты:

### 18.1. Current risk normal

```text
current_rms = 1
rated_current_A = 4
risk_current = 0.25
```

---

### 18.2. Current risk clamp

```text
current_rms = 10
rated_current_A = 4
risk_current <= 1
```

---

### 18.3. Voltage risk low

Если `voltage_min` ниже `dc_bus_min_safe`, риск должен быть > 0.

---

### 18.4. Voltage risk critical low

Если `voltage_min <= dc_bus_min_critical`, риск должен быть 1.

---

### 18.5. Temperature risk

Если `temp_max == temp_safe`, риск 0.

Если `temp_max == temp_critical`, риск 1.

---

### 18.6. Error risk

Если `error_flag=True`, risk_error=1.

---

### 18.7. Statusword fault

Если `fault_flag=True`, risk_statusword=1.

---

### 18.8. Missing feature

Отсутствие необязательного признака не должно ломать функцию.

---

## 19. Acceptance criteria

Физическая модель рисков считается готовой, если:

1. Есть функция `calculate_physical_risks(features, limits)`.
2. Она возвращает все обязательные ключи рисков.
3. Все риски находятся в диапазоне 0..1.
4. Риск тока учитывает RMS и пик.
5. Риск момента учитывает RMS и пик.
6. Риск скорости учитывает максимальную абсолютную скорость.
7. Риск DC-шины учитывает просадку, перенапряжение и нестабильность.
8. Риск температуры учитывает уровень и тренд.
9. Ненулевой `error_code` даёт риск ошибки 1.
10. Fault в `statusword` даёт высокий риск.
11. Плохое качество данных повышает `data_quality` risk.
12. Отсутствующие признаки не ломают код.
13. Есть unit-тесты для каждого риска.
