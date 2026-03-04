# Attendance Reporting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Запустити щоденну звітність по відвідуваності для адміністрації з правилами інцидентів "втік з уроків" (1+) і доставкою до 06:30.

**Architecture:** Дані експортуються з nz.ua, зводяться в єдиній таблиці (Sheets/Excel), автоматично формуються KPI і списки ризику, після чого готується 1-сторінковий PDF + деталізація. Процес працює за щоденним регламентом з контролем якості і статусами інцидентів.

**Tech Stack:** nz.ua (джерело), Google Sheets або Excel (обробка), PDF (доставка), email/внутрішній канал (розсилка).

---

### Task 1: Зафіксувати нормативні правила звітності

**Files:**
- Create: `docs/ops/attendance/attendance-policy.md`
- Test: `docs/ops/attendance/attendance-policy-checklist.md`

**Step 1: Підготувати перелік правил (чернетка)**

```markdown
- Періоди: 7 днів, 30 днів, семестр
- Інцидент "втік": 1+ пропуск після факту появи в школі цього дня
- Винятки: офіційна причина на урок/день
```

**Step 2: Перевірити чернетку на повноту**

Run: `rg -n "Періоди|Інцидент|Винятки" docs/ops/attendance/attendance-policy.md`
Expected: знайдено 3 ключові блоки правил.

**Step 3: Дописати фінальну версію політики**

```markdown
Додати єдині коди причин відсутності і SLA по статусах інцидентів.
```

**Step 4: Верифікація покриття правил**

Run: `rg -n "SLA|коди причин|06:30|10:00|12:00" docs/ops/attendance/attendance-policy.md`
Expected: усі ключові терміни присутні.

**Step 5: Commit**

```bash
git add docs/ops/attendance/attendance-policy.md docs/ops/attendance/attendance-policy-checklist.md
git commit -m "docs: add attendance reporting policy"
```

### Task 2: Створити шаблон щоденного звіту

**Files:**
- Create: `docs/templates/attendance/daily-report-template.md`
- Create: `docs/templates/attendance/daily-report-columns.csv`
- Test: `docs/templates/attendance/daily-report-template-checklist.md`

**Step 1: Створити структуру 1-сторінкового PDF**

```markdown
1) Заголовок
2) KPI
3) Класи
4) TOP-20 ризику
5) Інциденти "втік"
6) Рішення/дії
```

**Step 2: Задати колонки деталізації (CSV)**

```csv
student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident
```

**Step 3: Перевірити відповідність структури вимогам**

Run: `rg -n "KPI|TOP-20|Інциденти|Рішення" docs/templates/attendance/daily-report-template.md`
Expected: знайдені всі 4 ключові секції.

**Step 4: Додати приклад одного заповненого рядка**

```csv
12345,"Іваненко Іван",7-А,2026-03-05,5,"ABSENT","UNEXCUSED",true
```

**Step 5: Commit**

```bash
git add docs/templates/attendance/daily-report-template.md docs/templates/attendance/daily-report-columns.csv docs/templates/attendance/daily-report-template-checklist.md
git commit -m "docs: add daily attendance report template"
```

### Task 3: Налаштувати правило "втік з уроків" (1+)

**Files:**
- Create: `docs/ops/attendance/escape-incident-rule.md`
- Test: `docs/ops/attendance/escape-incident-test-cases.md`

**Step 1: Записати формальне правило і винятки**

```markdown
Інцидент = 1+ пропущений урок після першої фіксації присутності за день.
```

**Step 2: Додати тест-кейси (мінімум 6)**

```markdown
- Присутній на 1-2, відсутній на 3 => інцидент
- Відсутній з 1-го уроку => не інцидент
- Офіційна причина на 5-й => не інцидент
```

**Step 3: Перевірити, що всі кейси мають очікуваний результат**

Run: `rg -n "=>" docs/ops/attendance/escape-incident-test-cases.md`
Expected: кожен кейс має явний expected outcome.

**Step 4: Додати інструкцію валідації класним керівником до 10:00**

```markdown
Статуси: new -> in_review -> confirmed/closed
```

**Step 5: Commit**

```bash
git add docs/ops/attendance/escape-incident-rule.md docs/ops/attendance/escape-incident-test-cases.md
git commit -m "docs: define escape-from-lesson incident rule"
```

### Task 4: Описати щоденний SOP і ескалації

**Files:**
- Create: `docs/ops/attendance/daily-sop.md`
- Create: `docs/ops/attendance/escalation-matrix.md`
- Test: `docs/ops/attendance/sop-runbook-checklist.md`

**Step 1: Зафіксувати щоденний таймінг**

```markdown
06:00-06:20 збір/зведення
до 06:30 доставка
до 10:00 первинна перевірка інцидентів
до 12:00 фінальні статуси
```

**Step 2: Описати ролі і відповідальність**

```markdown
- Відповідальний за звіт
- Класний керівник
- Заступник директора
```

**Step 3: Перевірити наявність SLA і маршрутів ескалації**

Run: `rg -n "06:30|10:00|12:00|ескалац" docs/ops/attendance/daily-sop.md docs/ops/attendance/escalation-matrix.md`
Expected: SLA та ескалації явно прописані.

**Step 4: Додати fallback-сценарій (якщо дані в nz.ua неповні)**

```markdown
Позначити звіт як "попередній", відправити уточнений до 09:00.
```

**Step 5: Commit**

```bash
git add docs/ops/attendance/daily-sop.md docs/ops/attendance/escalation-matrix.md docs/ops/attendance/sop-runbook-checklist.md
git commit -m "docs: add attendance SOP and escalation matrix"
```

### Task 5: Пілот і приймальні критерії (30 днів)

**Files:**
- Create: `docs/ops/attendance/30-day-pilot-metrics.md`
- Test: `docs/ops/attendance/acceptance-checklist.md`

**Step 1: Зафіксувати KPI пілоту**

```markdown
- >=95% звітів до 06:30
- Розбіжність <=2%
- 100% інцидентів зі статусом до 12:00
- Неопрацьовані <=5%
```

**Step 2: Описати метод перевірки кожного KPI**

```markdown
Джерело, формула, період виміру, відповідальний.
```

**Step 3: Провести dry-run на тестових даних за 2 дні**

Run: `echo "Dry-run complete"`
Expected: сценарій пройдено, виявлені прогалини зафіксовано.

**Step 4: Оновити документи за результатами dry-run**

```markdown
Внести виправлення у SOP і правила інцидентів.
```

**Step 5: Commit**

```bash
git add docs/ops/attendance/30-day-pilot-metrics.md docs/ops/attendance/acceptance-checklist.md
git commit -m "docs: add 30-day pilot metrics and acceptance criteria"
```
