# README and Start Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Додати україномовний README та базову інструкцію запуску звітності, щоб новий користувач міг почати роботу за 10-15 хвилин.

**Architecture:** README працює як головна точка входу: короткий опис, швидкий старт і карта документації. Окремий start-guide містить покроковий операційний сценарій щоденного запуску з fallback та перевірками перед відправкою.

**Tech Stack:** Markdown-документація, GitHub repository.

---

### Task 1: Створити README українською

**Files:**
- Create: `README.md`
- Test: `docs/ops/attendance/acceptance-checklist.md`

**Step 1: Додати вступ і призначення репозиторію**

```markdown
# Звітність відвідуваності школи
Короткий опис призначення і цільової аудиторії.
```

**Step 2: Додати розділ "Швидкий старт" на 5 кроків**

```markdown
1) Перевірити доступ до nz.ua
2) Оновити таблицю
3) Перевірити інциденти
4) Згенерувати PDF
5) Надіслати до 06:30
```

**Step 3: Додати блоки циклу, правила "втік" і KPI**

```markdown
06:00-12:00, правило 1+, KPI 30-денного пілоту.
```

**Step 4: Додати посилання на повну документацію**

```markdown
Лінки на policy, SOP, escalation, templates, plans.
```

**Step 5: Перевірка структури README**

Run: `rg -n "Швидкий старт|Щоденний цикл|втік|KPI|Повна документація" README.md`
Expected: усі секції присутні.

### Task 2: Додати базову інструкцію запуску

**Files:**
- Create: `docs/ops/attendance/start-guide.md`
- Test: `docs/ops/attendance/sop-runbook-checklist.md`

**Step 1: Додати підготовку перед першим запуском**

```markdown
Доступи, відповідальний, шаблони, графік.
```

**Step 2: Додати щоденний покроковий сценарій**

```markdown
06:00-06:20 збір і зведення, 06:30 відправка.
```

**Step 3: Додати fallback при неповних даних**

```markdown
Маркування "попередній", оновлення до 09:00.
```

**Step 4: Додати чек перед відправкою**

```markdown
Перевірка KPI, інцидентів, підпису і часу відправки.
```

**Step 5: Перевірка змісту інструкції**

Run: `rg -n "06:30|09:00|fallback|інцидент|чек" docs/ops/attendance/start-guide.md`
Expected: ключові керуючі точки присутні.

### Task 3: Верифікація і публікація

**Files:**
- Modify: `README.md`
- Modify: `docs/ops/attendance/start-guide.md`

**Step 1: Перевірити Markdown-файли на наявність**

Run: `test -f README.md && test -f docs/ops/attendance/start-guide.md && echo "docs-ready"`
Expected: `docs-ready`.

**Step 2: Перевірити статус git**

Run: `git status -sb`
Expected: змінені/нові лише очікувані файли.

**Step 3: Зробити commit**

```bash
git add README.md docs/ops/attendance/start-guide.md docs/plans/2026-03-04-readme-start-guide-design.md docs/plans/2026-03-04-readme-start-guide-implementation-plan.md
git commit -m "docs: add ukrainian README and attendance start guide"
```

**Step 4: Відправити зміни на origin/main**

Run: `git push`
Expected: remote updated.
