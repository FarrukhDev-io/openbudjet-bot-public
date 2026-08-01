# 🚀 DevOps & Git Workflow Guide (Production Hardening)

Ushbu loyihani haqiqiy Enterprise darajasiga olib chiqish uchun quyidagi DevOps qoidalari va avtomatlashtirilgan CI (Continuous Integration) quvurlari joriy qilinishi shart. Bu production tarmog'ini tasodifiy buzulishlardan va asossiz `force-push` amallaridan to'liq himoya qiladi.

---

## 1. 🛡️ Branch Protection Rules (GitHub)

GitHub repositoriyasida `main` (va `master`) tarmog'ini himoyalash uchun quyidagi sozlamalarni yoqish shart:

1. **Require a pull request before merging:**
   - Hech kim `main` tarmog'iga to'g'ridan-to'g'ri `git push` qila olmaydi.
   - O'zgarishlar faqat Pull Request (PR) orqali kiritiladi.
   - Kamida 1 ta Senior Developer yoki Tech Lead kodni tasdiqlashi (Approve) shart.
2. **Require status checks to pass before merging:**
   - Pull Request tasdiqlanishidan oldin barcha avtomatlashtirilgan CI testlari muvaffaqiyatli o'tgan bo'lishi shart.
3. **Restrict who can push to matching branches:**
   - `force-push` (majburiy yangilash) va `delete branch` amallari barcha foydalanuvchilar (jumladan adminlar) uchun **taqiqlanadi**.

---

## 2. 🤖 GitHub Actions CI Pipeline (`.github/workflows/ci.yml`)

Loyiha ildizida `.github/workflows/ci.yml` faylini yaratib, quyidagi avtomatlashtirilgan tekshiruvlarni joriy qiling:

```yaml
name: OpenBudjet Bot CI

on:
  push:
    branches: [ main, farrukh ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: bot_data
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-python: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install flake8 pytest

    - name: Lint with flake8
      run: |
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings.
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

    - name: Verify Python Syntax
      run: |
        python -m py_compile $(find . -name "*.py" -not -path "./venv/*")

    - name: Run Schema Migrations Check
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/bot_data
      run: |
        python -m database.migrate
```

---

## 3. 🔄 Sog'lom Git Flow va PR tartibi

1. **Feature Branch:** Har bir yangi vazifa uchun `main` dan alohida tarmoq ochiladi:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/secure-auth
   ```
2. **Local Test:** Dasturchi o'z kodini local muhitda tekshiradi (xususan xavfsizlik va migratsiya scriptlarini sinab ko'radi).
3. **Push & PR:** Tarmoq masofaviy repoga yuklanadi va `main` tarmog'iga nisbatan **Pull Request** ochiladi.
4. **CI & Code Review:** GitHub Actions CI tizimi kod sintaksisi va xavfsizligini tekshiradi. Kamida bitta hamkasbingiz kodni o'qib chiqib tasdiqlaydi.
5. **Merge:** PR muvaffaqiyatli o'tgandan so'ng `Squash and merge` orqali asosiy tarmoqqa birlashtiriladi.
