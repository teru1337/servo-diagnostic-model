---
name: servo-implementation-planner
description: Use before implementing or refactoring any substantial module in servo_diagnostic_model. Creates a concise file-level plan, required functions, tests, and acceptance criteria before coding.
---

# Servo Implementation Planner Skill

Use this skill before coding a non-trivial task.

## Workflow

1. Identify which part of the project the user asked about.
2. Select the smallest relevant subset of documentation from `markdowns/`.
3. List files that need to be created or modified.
4. List functions/classes to implement.
5. List tests to add or update.
6. State acceptance criteria.
7. Only then start coding.

## Do not

- Do not read all documentation by default.
- Do not modify unrelated modules.
- Do not implement future roadmap stages unless explicitly requested.
- Do not mix data pipeline, feature extraction, model logic, recommendations, and evaluation in one change.

## Default implementation order

Follow this order unless the user asks otherwise:

1. `data/schemas.py`
2. `data/loader.py`
3. `data/preprocessing.py`
4. `data/validator.py`
5. `data/windowing.py`
6. `features/basic_features.py`
7. feature modules
8. `features/feature_extractor.py`
9. `model/physical_risks.py`
10. `model/health_score.py`
11. `model/classifier.py`
12. `api/diagnostic_service.py`
13. tests
14. statistical anomaly model
15. explanations and recommendations
16. evaluation tools
