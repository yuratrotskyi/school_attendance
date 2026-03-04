# School Attendance on Windows

Коротка інструкція для запуску на Windows 10/11.

## 1) Передумови

- Встановлений `Git`
- Встановлений `Python 3.10+` (з опцією "Add Python to PATH")

Перевірка:

```powershell
git --version
python --version
```

## 2) Клонування і перехід в проєкт

```powershell
git clone https://github.com/yuratrotskyi/school_attendance.git
cd school_attendance
```

## 3) Віртуальне середовище

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Якщо PowerShell блокує активацію:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 4) Встановлення залежностей

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## 5) Налаштування конфігів

```powershell
Copy-Item .env.example .env
Copy-Item config\nz_selectors.example.json config\nz_selectors.json
```

Відкрий `.env` і заповни потрібні змінні (`NZ_LOGIN`, `NZ_PASSWORD` тощо).

## 6) Перший вхід (збереження сесії)

```powershell
$env:PYTHONPATH = "src"
python -m school_attendance.cli bootstrap-session --timeout-seconds 300
```

Що робити:

- у відкритому браузері увійти в `nz.ua`
- пройти Cloudflare, якщо з’явиться
- після успішного входу повернутись в термінал і натиснути `Enter`

## 7) Щоденний запуск

```powershell
$env:PYTHONPATH = "src"
python -m school_attendance.cli run-daily
```

## 8) Де дивитись результати

- `out\YYYY-MM-DD\report.md`
- `out\YYYY-MM-DD\student-absence-summary.csv`
- `out\YYYY-MM-DD\summary.json`
- `data\normalized\YYYY-MM-DD\attendance.csv`

## 9) Якщо сесія протухла

Повтори крок 6 (`bootstrap-session`), потім знову крок 7.

## 10) Варіант для CMD

```cmd
py -3 -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python -m playwright install chromium
set PYTHONPATH=src
python -m school_attendance.cli bootstrap-session --timeout-seconds 300
python -m school_attendance.cli run-daily
```

