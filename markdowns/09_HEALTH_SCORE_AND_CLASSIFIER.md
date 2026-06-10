# 09_HEALTH_SCORE_AND_CLASSIFIER.md

# Health Score и классификация состояния

## 1. Назначение документа

Этот документ описывает итоговую сборку диагностического решения:

- расчёт Health Score;
- объединение физических и статистических рисков;
- применение жёстких правил;
- классификацию состояния;
- определение уровня риска;
- выбор главных причин снижения оценки.

Coding agent должен реализовать модули:

```text
model/health_score.py
model/classifier.py
model/explanation.py
```

---

## 2. Место в pipeline

```text
features
    ↓
physical risks
    ↓
anomaly score
    ↓
combined risks
    ↓
Health Score
    ↓
hard rules
    ↓
state classifier
    ↓
risk level
    ↓
main causes
```

---

## 3. Входные данные

### 3.1. `features`

Словарь признаков:

```python
features = {
    "current_rms": 0.071,
    "torque_rms": 0.033,
    "voltage_std": 0.26,
    "temp_max": 37.0,
    "error_flag": False,
    "fault_flag": False,
    "motion_phase": "holding"
}
```

---

### 3.2. `risks`

Словарь рисков:

```python
risks = {
    "current": 0.03,
    "torque": 0.02,
    "velocity": 0.30,
    "voltage": 0.01,
    "temperature": 0.00,
    "statusword": 0.00,
    "error": 0.00,
    "data_quality": 0.00,
    "statistical_anomaly": 0.14
}
```

---

### 3.3. `weights`

Словарь весов:

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

### 3.4. `thresholds`

Пороги классификации:

```json
{
  "health_normal": 85,
  "health_observation": 70,
  "health_warning": 50,

  "anomaly_observation": 0.3,
  "anomaly_warning": 0.5,
  "anomaly_critical": 0.75
}
```

---

## 4. Health Score

Health Score — интегральная оценка состояния сервопривода.

Диапазон:

```text
0..100
```

Интерпретация:

| Health Score | Смысл                 |
| -----------: | --------------------- |
|       85–100 | Норма                 |
|        70–84 | Наблюдение            |
|        50–69 | Предупреждение        |
|         0–49 | Критическое состояние |

---

## 5. Общая формула Health Score

```text
total_risk = Σ(w_i * risk_i) / Σ(w_i)

health_score = 100 * (1 - total_risk)
```

Где:

- `risk_i` — риск от 0 до 1;
- `w_i` — вес риска;
- `total_risk` — итоговый риск от 0 до 1.

---

## 6. Пример расчёта

Допустим:

```python
risks = {
    "current": 0.03,
    "torque": 0.02,
    "velocity": 0.30,
    "voltage": 0.01,
    "temperature": 0.00,
    "error": 0.00,
    "statusword": 0.00,
    "statistical_anomaly": 0.14,
    "data_quality": 0.00
}
```

Если веса нормальные, итоговый риск будет низким, а Health Score высоким.

Пример:

```text
total_risk = 0.083
health_score = 91.7
```

---

## 7. Модуль `health_score.py`

### 7.1. Основная функция

```python
def calculate_health_score(
    risks: dict,
    weights: dict,
    features: dict | None = None
) -> float:
    ...
```

---

### 7.2. Алгоритм

```text
1. Пройти по всем рискам.
2. Для каждого риска найти вес.
3. Если веса нет, использовать 0 или default.
4. Пропустить риски, которые не являются числом.
5. Посчитать weighted_sum.
6. Посчитать sum_weights.
7. Если sum_weights == 0, вернуть 0 или unknown.
8. total_risk = weighted_sum / sum_weights.
9. health_score = 100 * (1 - total_risk).
10. Ограничить health_score в диапазоне 0..100.
11. Применить hard limits.
12. Вернуть health_score.
```

---

### 7.3. Псевдокод

```python
def calculate_health_score(risks, weights, features=None):
    weighted_sum = 0.0
    weight_sum = 0.0

    for risk_key, risk_value in risks.items():
        if not is_valid_number(risk_value):
            continue

        risk_value = clamp(risk_value, 0.0, 1.0)
        weight = weights.get(risk_key, 0.0)

        if weight <= 0:
            continue

        weighted_sum += risk_value * weight
        weight_sum += weight

    if weight_sum == 0:
        base_score = 0.0
    else:
        total_risk = weighted_sum / weight_sum
        base_score = 100.0 * (1.0 - total_risk)

    base_score = clamp(base_score, 0.0, 100.0)

    if features is not None:
        base_score = apply_hard_limits(base_score, risks, features)

    return round(base_score, 2)
```

---

## 8. Жёсткие ограничения Health Score

Некоторые события не должны "усредняться" с остальными параметрами.

Пример:

```text
error_code != 0
```

Даже если ток, момент и температура нормальные, наличие ошибки должно резко снизить Health Score.

---

### 8.1. Функция `apply_hard_limits`

```python
def apply_hard_limits(
    health_score: float,
    risks: dict,
    features: dict
) -> float:
    ...
```

---

### 8.2. Правила

```text
если error_flag == True:
    health_score = min(health_score, 40)

если fault_flag == True:
    health_score = min(health_score, 40)

если risks["error"] >= 1:
    health_score = min(health_score, 40)

если risks["statusword"] >= 1:
    health_score = min(health_score, 40)

если risks["temperature"] >= 1:
    health_score = min(health_score, 50)

если risks["voltage"] >= 1:
    health_score = min(health_score, 50)

если risks["data_quality"] >= 1:
    health_score = min(health_score, 60)
```

---

### 8.3. Почему нужны hard limits

Без hard limits может возникнуть ситуация:

```text
error risk = 1.0
но остальные риски очень маленькие
итоговый Health Score = 78
```

Это инженерно неверно.

Если есть аварийная ошибка, состояние не может считаться хорошим.

---

## 9. Объединение Anomaly Score с рисками

Статистическая модель возвращает:

```python
{
    "anomaly_score": 0.57,
    "feature_scores": {...}
}
```

Перед расчётом Health Score нужно обновить риски:

```python
risks["statistical_anomaly"] = anomaly_result["anomaly_score"]
```

---

## 10. Классификация состояния

Классификатор должен определить одно состояние:

```text
normal
observation
warning
critical
unknown
```

---

## 11. Модуль `classifier.py`

### 11.1. Основная функция

```python
def classify_state(
    health_score: float | None,
    anomaly_score: float | None,
    risks: dict,
    thresholds: dict,
    features: dict
) -> str:
    ...
```

---

## 12. Логика классификации

### 12.1. Unknown

Если данных недостаточно:

```text
state = unknown
```

Условия:

```text
health_score is None
features["sample_count"] == 0
features["is_too_short"] == True and risks["data_quality"] >= 1
```

---

### 12.2. Critical

Условия:

```text
error_flag == True
fault_flag == True
risks["error"] >= 1
risks["statusword"] >= 1
health_score < health_warning
anomaly_score >= anomaly_critical
```

Важно:

```text
error/fault должны проверяться до обычных порогов Health Score.
```

---

### 12.3. Warning

Условия:

```text
health_warning <= health_score < health_observation
anomaly_warning <= anomaly_score < anomaly_critical
любой физический риск >= 0.75
```

---

### 12.4. Observation

Условия:

```text
health_observation <= health_score < health_normal
anomaly_observation <= anomaly_score < anomaly_warning
любой физический риск >= 0.5
```

---

### 12.5. Normal

Условия:

```text
health_score >= health_normal
anomaly_score < anomaly_observation
нет error_flag
нет fault_flag
нет высоких физических рисков
```

---

## 13. Псевдокод классификатора

```python
def classify_state(health_score, anomaly_score, risks, thresholds, features):
    if health_score is None:
        return "unknown"

    if features.get("is_too_short") and risks.get("data_quality", 0) >= 1:
        return "unknown"

    if features.get("error_flag") is True:
        return "critical"

    if features.get("fault_flag") is True:
        return "critical"

    if risks.get("error", 0) >= 1:
        return "critical"

    if risks.get("statusword", 0) >= 1:
        return "critical"

    health_warning = thresholds.get("health_warning", 50)
    health_observation = thresholds.get("health_observation", 70)
    health_normal = thresholds.get("health_normal", 85)

    anomaly_observation = thresholds.get("anomaly_observation", 0.30)
    anomaly_warning = thresholds.get("anomaly_warning", 0.50)
    anomaly_critical = thresholds.get("anomaly_critical", 0.75)

    anomaly_score = anomaly_score if anomaly_score is not None else 0.0

    if health_score < health_warning:
        return "critical"

    if anomaly_score >= anomaly_critical:
        return "critical"

    if has_risk_above(risks, 0.9):
        return "critical"

    if health_score < health_observation:
        return "warning"

    if anomaly_score >= anomaly_warning:
        return "warning"

    if has_risk_above(risks, 0.75):
        return "warning"

    if health_score < health_normal:
        return "observation"

    if anomaly_score >= anomaly_observation:
        return "observation"

    if has_risk_above(risks, 0.5):
        return "observation"

    return "normal"
```

---

## 14. Функция `has_risk_above`

```python
def has_risk_above(risks: dict, threshold: float, exclude: list[str] | None = None) -> bool:
    ...
```

Исключения:

```text
statistical_anomaly
data_quality
```

можно обрабатывать отдельно.

---

## 15. Risk level

Функция:

```python
def risk_level_from_state(state: str) -> str:
    ...
```

Соответствие:

| State         | Risk level |
| ------------- | ---------- |
| `normal`      | `low`      |
| `observation` | `medium`   |
| `warning`     | `high`     |
| `critical`    | `critical` |
| `unknown`     | `unknown`  |

---

## 16. Главные причины

Модель должна объяснять, почему состояние получилось именно таким.

Модуль:

```text
model/explanation.py
```

Функция:

```python
def get_main_causes(
    risks: dict,
    features: dict,
    top_n: int = 3,
    min_risk: float = 0.3
) -> list[dict]:
    ...
```

---

### 16.1. Алгоритм выбора причин

```text
1. Взять все риски.
2. Убрать риски ниже min_risk.
3. Отсортировать по убыванию.
4. Взять top_n.
5. Для каждого риска сформировать человекочитаемое сообщение.
```

---

### 16.2. Пример результата

```json
[
  {
    "risk_key": "current",
    "parameter": "current_A",
    "risk_value": 0.72,
    "severity": "warning",
    "message": "RMS-ток повышен относительно допустимого уровня."
  },
  {
    "risk_key": "temperature",
    "parameter": "drive_temp",
    "risk_value": 0.55,
    "severity": "warning",
    "message": "Температура или её рост требуют наблюдения."
  }
]
```

---

## 17. Severity по значению риска

Функция:

```python
def severity_from_risk(risk: float) -> str:
    ...
```

Соответствие:

|     Risk | Severity      |
| -------: | ------------- |
|  0.0–0.3 | `low`         |
|  0.3–0.5 | `observation` |
| 0.5–0.75 | `warning`     |
| 0.75–1.0 | `critical`    |

---

## 18. Сообщения для причин

### 18.1. Current

```text
risk_key = current
parameter = current_A
message = "Токовая нагрузка повышена. Возможна перегрузка или повышенное механическое сопротивление."
```

---

### 18.2. Torque

```text
risk_key = torque
parameter = torque_Nm
message = "Момент нагрузки повышен относительно допустимого диапазона."
```

---

### 18.3. Velocity

```text
risk_key = velocity
parameter = velocity
message = "Скорость близка к заданному скоростному пределу."
```

---

### 18.4. Voltage

```text
risk_key = voltage
parameter = dc_bus_voltage
message = "Обнаружен риск по напряжению DC-шины: просадка, перенапряжение или нестабильность."
```

---

### 18.5. Temperature

```text
risk_key = temperature
parameter = drive_temp
message = "Температура или её рост приближаются к опасной зоне."
```

---

### 18.6. Error

```text
risk_key = error
parameter = error_code
message = "Обнаружен ненулевой код ошибки привода."
```

---

### 18.7. Statusword

```text
risk_key = statusword
parameter = statusword
message = "Statusword содержит аварийный флаг или предупреждение."
```

---

### 18.8. Statistical anomaly

```text
risk_key = statistical_anomaly
parameter = anomaly_score
message = "Текущее поведение отличается от нормального статистического профиля."
```

---

### 18.9. Data quality

```text
risk_key = data_quality
parameter = telemetry
message = "Качество телеметрии снижено: есть пропуски, некорректные значения или временные разрывы."
```

---

## 19. Генерация общего объяснения

Функция:

```python
def generate_explanation(
    state: str,
    health_score: float,
    anomaly_score: float,
    risks: dict,
    features: dict,
    main_causes: list[dict]
) -> list[str]:
    ...
```

---

### 19.1. Для normal

Пример:

```python
[
    "Состояние привода оценивается как нормальное.",
    "Ошибки и аварийные флаги отсутствуют.",
    "Ток, момент, температура и напряжение DC-шины находятся в безопасном диапазоне.",
    "Статистических отклонений от нормального профиля не обнаружено."
]
```

---

### 19.2. Для observation

```python
[
    "Состояние требует наблюдения.",
    "Критических ошибок нет, но один или несколько параметров начали отклоняться от нормы.",
    "Рекомендуется контролировать динамику параметров в следующих окнах."
]
```

---

### 19.3. Для warning

```python
[
    "Обнаружено предупреждающее состояние.",
    "Параметры приближаются к опасной зоне или поведение отличается от нормального профиля.",
    "Рекомендуется выполнить проверку оборудования или снизить нагрузку."
]
```

---

### 19.4. Для critical

```python
[
    "Обнаружено критическое состояние.",
    "Есть аварийный признак, ошибка или высокий риск по одному из параметров.",
    "Необходимо проверить привод и связанные узлы перед продолжением эксплуатации."
]
```

---

### 19.5. Для unknown

```python
[
    "Состояние не может быть надёжно определено.",
    "Недостаточно данных или качество телеметрии слишком низкое.",
    "Рекомендуется проверить источник данных и повторить диагностику."
]
```

---

## 20. Главная функция итоговой оценки

Можно создать функцию:

```python
def evaluate_state(
    features: dict,
    physical_risks: dict,
    anomaly_result: dict,
    weights: dict,
    thresholds: dict
) -> dict:
    ...
```

Псевдокод:

```python
def evaluate_state(features, physical_risks, anomaly_result, weights, thresholds):
    risks = dict(physical_risks)
    risks["statistical_anomaly"] = anomaly_result.get("anomaly_score", 0.0)

    health_score = calculate_health_score(
        risks=risks,
        weights=weights,
        features=features
    )

    anomaly_score = anomaly_result.get("anomaly_score", 0.0)

    state = classify_state(
        health_score=health_score,
        anomaly_score=anomaly_score,
        risks=risks,
        thresholds=thresholds,
        features=features
    )

    risk_level = risk_level_from_state(state)

    main_causes = get_main_causes(
        risks=risks,
        features=features,
        top_n=3
    )

    explanation = generate_explanation(
        state=state,
        health_score=health_score,
        anomaly_score=anomaly_score,
        risks=risks,
        features=features,
        main_causes=main_causes
    )

    return {
        "health_score": health_score,
        "anomaly_score": anomaly_score,
        "state": state,
        "risk_level": risk_level,
        "risks": risks,
        "main_causes": main_causes,
        "explanation": explanation
    }
```

---

## 21. Unit-тесты

### 21.1. Health Score normal

Если все риски 0:

```text
health_score = 100
```

---

### 21.2. Health Score critical risk

Если один риск 1 и вес большой, Health Score должен снизиться.

---

### 21.3. Clamp Health Score

Health Score не должен быть меньше 0 или больше 100.

---

### 21.4. Hard limit error

Если `error_flag=True`, Health Score должен быть не выше 40.

---

### 21.5. Classifier normal

При:

```text
health_score >= 85
anomaly_score < 0.3
нет error/fault
```

state должен быть:

```text
normal
```

---

### 21.6. Classifier critical by error

Если `error_flag=True`:

```text
state = critical
```

---

### 21.7. Classifier warning by anomaly

Если `anomaly_score >= 0.5`, но ниже critical:

```text
state = warning
```

---

### 21.8. Classifier observation by health

Если Health Score между 70 и 85:

```text
state = observation
```

---

### 21.9. Main causes

Если risks:

```python
{
    "current": 0.8,
    "temperature": 0.6,
    "voltage": 0.2
}
```

top causes должны включать current и temperature.

---

## 22. Acceptance criteria

Health Score и классификатор считаются готовыми, если:

1. Есть `calculate_health_score`.
2. Health Score всегда находится в диапазоне 0..100.
3. Риски корректно взвешиваются.
4. Отсутствующие веса не ломают расчёт.
5. Есть hard limits для error/fault.
6. Anomaly Score добавляется в risks.
7. Есть `classify_state`.
8. Классификатор возвращает только допустимые состояния.
9. Error/fault всегда дают critical.
10. Низкий Health Score даёт warning или critical.
11. Высокий Anomaly Score влияет на состояние.
12. Есть `risk_level_from_state`.
13. Есть `get_main_causes`.
14. Есть человекочитаемые explanation.
15. Все основные сценарии покрыты unit-тестами.
