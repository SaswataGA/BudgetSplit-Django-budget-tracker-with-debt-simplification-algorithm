# 💰 BudgetSplit — Personal Budget & Group Bill-Splitting

A full-stack Django web app combining personal budget tracking with group expense splitting — including a real **debt-simplification algorithm** (like Splitwise's "simplify debts") that computes the minimum number of payments needed to settle a group, not just raw ledger math.

![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django)
![Tests](https://img.shields.io/badge/Tests-51%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

**Personal budgeting**
- Custom spending categories with color tags
- Monthly budget limits per category, with live progress bars
- Expense logging with search, category filtering, date-range filtering, and pagination
- Dashboard showing this month's budget-vs-spend and recent activity

**Group bill-splitting**
- Create groups, add members by username
- Log a shared expense paid by one member — split equally, or with custom per-person amounts
- **Automatic debt simplification**: instead of everyone settling every individual expense, the app computes the minimum set of payments to settle the whole group
- Real-time balance view: who owes what, and who's owed

**Platform**
- Full authentication (register, login, logout, password change/reset)
- User profiles extending Django's built-in `User` model (avatar, currency preference)
- Django admin panel for all models
- Responsive Bootstrap 5 UI
- Environment-based settings (dev uses SQLite; production uses PostgreSQL) with all secrets in environment variables, never hardcoded
- Custom 404/500 error pages
- 51 automated tests, including authorization tests that verify users can never access each other's data

## 🧮 The Debt Simplification Algorithm

This is the most interesting part of the codebase — see `groups/services.py`.

**The problem:** in a group with many shared expenses, a naive approach ("everyone pays back everyone they individually owe") can require far more transactions than necessary.

**The approach:** compute each member's *net balance* (total they paid, minus total they owe) across all group expenses. Then greedily match the biggest creditor with the biggest debtor, settle the smaller of the two amounts, and repeat. This always resolves a group in at most *(number of members − 1)* transactions.

**Example** (see `groups/test_services.py` for the automated version of this exact scenario):
- Alice pays $90 for dinner, split 3 ways ($30 each) → Alice is owed $60 net
- Bob pays $30 for a cab, split 3 ways ($10 each) → Bob is owed $10 net after his own share
- Carol never pays for anything → Carol owes $40 net

Naive settling could take several transactions. This algorithm produces exactly **two**: Carol pays Alice $40, and Bob pays Alice $10 — fully resolving all balances to zero.

## 📂 Project Structure

```
budgetsplit/
├── manage.py
├── requirements.txt
├── Procfile                          # web/release commands for Render/Railway
├── .env.example                      # copy to .env for local dev
├── .gitignore
├── LICENSE
├── budgetsplit/                      # project config
│   ├── settings/
│   │   ├── base.py                   # shared settings
│   │   ├── development.py            # SQLite, DEBUG=True
│   │   └── production.py             # PostgreSQL, security hardening
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                         # auth, Profile model, dashboard
│   ├── models.py                     # Profile (extends User via OneToOne)
│   ├── signals.py                    # auto-creates Profile on User creation
│   ├── forms.py
│   ├── views.py                      # register, dashboard (aggregates budgets+groups), profile
│   ├── tests.py                      # 12 tests
│   └── templates/accounts/
├── budgets/                          # personal budgeting
│   ├── models.py                     # Category, Budget, Expense
│   ├── forms.py
│   ├── views.py                      # CBVs for Category/Budget, FBVs for Expense (search/filter/pagination)
│   ├── tests.py                      # 17 tests, including IDOR authorization tests
│   └── templates/budgets/
├── groups/                           # group bill-splitting
│   ├── models.py                     # Group, GroupMembership, GroupExpense, GroupExpenseSplit
│   ├── services.py                   # ⭐ debt simplification algorithm
│   ├── forms.py
│   ├── views.py
│   ├── tests.py                      # view/model tests
│   ├── test_services.py              # 15 tests for the algorithm itself
│   └── templates/groups/
├── templates/
│   ├── base.html
│   ├── 404.html / 500.html
│   └── registration/                 # login, register, password change/reset
├── static/css/custom.css
└── media/avatars/                    # user-uploaded avatars
```

## ⚙️ Installation (Local Development)

**Requirements:** Python 3.10, 3.11, 3.12, or 3.13 (Django 5.2 LTS supports all of these — check yours with `python --version`).

```bash
git clone https://github.com/<your-username>/budgetsplit.git
cd budgetsplit

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Generate a real secret key and paste it into .env:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` — you'll be redirected to log in, or register a new account. Visit `/admin/` to manage data directly.

## ✅ Running Tests

```bash
python manage.py test
```
All 51 tests should pass, covering: registration and the Profile auto-creation signal, dashboard authentication requirements, category/budget/expense CRUD, **authorization tests confirming one user can never view or edit another user's data** (an "Insecure Direct Object Reference" check), group creation/membership, equal and custom expense splitting, and — most thoroughly — the debt simplification algorithm itself (correctness properties like "settlements always resolve every balance to exactly zero" are checked across multiple scenarios, not just one hand-picked example).

## 🔒 Security Practices Implemented

- **Secrets never hardcoded**: `SECRET_KEY`, `DATABASE_URL`, etc. all come from environment variables via `python-decouple` (see `.env.example`)
- **User-scoped querysets everywhere**: every view that fetches a Category/Budget/Expense/Group filters by `request.user` (or group membership) — verified with explicit IDOR tests, not just assumed
- **CSRF protection**: on by default via Django's `CsrfViewMiddleware`; every form includes `{% csrf_token %}`
- **Password validation**: Django's built-in validators (minimum length, common-password check, similarity-to-username check) are active
- **Production hardening** (in `production.py`, OFF in development so local HTTP still works): forced HTTPS redirect, secure cookies, HSTS headers, `X-Frame-Options: DENY`, content-type sniffing protection
- **File upload limits**: avatar uploads capped at 2MB, validated both in the form and via `DATA_UPLOAD_MAX_MEMORY_SIZE`
- **404, not 403, for unauthorized access**: viewing a group you're not a member of returns 404 rather than confirming the group exists at all

## 🚀 Deployment

### Step 1: SQLite → PostgreSQL

Locally, `development.py` uses SQLite — zero setup needed. In production, `production.py` expects a `DATABASE_URL` environment variable (standard on every platform below) and connects via `dj-database-url` + `psycopg2`.

**Migrating existing local data to PostgreSQL**, if you have data you want to keep:
```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json
# ... set DATABASE_URL to your new Postgres instance, then:
DJANGO_SETTINGS_MODULE=budgetsplit.settings.production python manage.py migrate
DJANGO_SETTINGS_MODULE=budgetsplit.settings.production python manage.py loaddata data.json
```

### Step 2: Required environment variables in production

| Variable | Example | Notes |
|---|---|---|
| `SECRET_KEY` | (random string) | Generate fresh — never reuse the dev one |
| `DEBUG` | not set | `production.py` hardcodes `DEBUG = False` |
| `ALLOWED_HOSTS` | `myapp.onrender.com` | Comma-separated |
| `DATABASE_URL` | `postgres://...` | Usually auto-provided when you attach a DB addon |
| `DJANGO_SETTINGS_MODULE` | `budgetsplit.settings.production` | **Must be set explicitly** — `manage.py`/`wsgi.py` default to `development` otherwise |

### Step 3: Static & media files

`collectstatic` runs during each platform's build step (all four below do this automatically if you tell them to, or via the `release` line in the `Procfile`). WhiteNoise then serves the hashed, compressed static files directly from the app process — no separate Nginx/CDN needed to get started. `MEDIA` files (user avatars) are served from local disk in this project; for real production use at scale, swap `STORAGES["default"]` for something like `django-storages` + S3, since disk storage on most of these platforms doesn't persist across redeploys.

### Step 4: Choose a host

| Platform | Pros | Cons |
|---|---|---|
| **Render** | Generous free tier, auto-deploys from GitHub, free managed PostgreSQL, simple `render.yaml` or dashboard config | Free tier services sleep after inactivity (cold start delay) |
| **Railway** | Very fast deploys, clean UI, usage-based pricing, easy PostgreSQL attach | No permanently-free tier (small usage-based cost); can surprise you if traffic spikes |
| **PythonAnywhere** | Simplest for absolute beginners, Python-focused dashboard, free tier available | Free tier has no custom domain/HTTPS on some plans, less flexible for background workers, manual-ish deploy flow (not git-push-to-deploy by default) |
| **Fly.io** | Deploys as a real Docker container, runs close to users globally (edge regions), generous free allowance | Steeper learning curve (Dockerfile/`fly.toml`), overkill if you just want the simplest possible deploy |

**Recommended path for a first deploy:** Render or Railway — both are git-push-to-deploy with minimal config. Use the `Procfile` in this repo as-is; both platforms read it automatically.

**Render-specific quick start:**
1. Push this repo to GitHub.
2. New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. Start command: `gunicorn budgetsplit.wsgi`
5. Add a PostgreSQL instance (Render provides `DATABASE_URL` automatically).
6. Set `SECRET_KEY`, `ALLOWED_HOSTS`, and `DJANGO_SETTINGS_MODULE=budgetsplit.settings.production` in the Environment tab.
7. After first deploy, run migrations from the Render shell: `python manage.py migrate`.

### Docker (optional)

Not included by default in this project (kept dependency-light per the "simplest first deploy" philosophy above), but since `gunicorn` + `whitenoise` + environment-variable settings are already in place, a minimal `Dockerfile` would just need: a Python base image, `pip install -r requirements.txt`, `collectstatic`, and `CMD ["gunicorn", "budgetsplit.wsgi", "--bind", "0.0.0.0:8000"]` — useful if you later choose Fly.io or any container-based host.

## 🩹 Troubleshooting

**`ERROR: Could not find a version that satisfies the requirement Django<6.1,>=6.0`**
This means your Python is older than 3.12. Run `python --version` to check. This project deliberately requires only Python 3.10+ (via Django 5.2 LTS in `requirements.txt`) precisely to avoid this — if you're seeing this error, you likely have an old copy of `requirements.txt` from before that fix. Re-download the project, or manually check that `requirements.txt` says `Django>=5.2,<5.3`, not `Django>=6.0,<6.1`, then re-run `pip install -r requirements.txt`.

**`pip install` succeeds but `python manage.py runserver` fails with a `SECRET_KEY` / decouple error**
You're missing `.env`. Copy `.env.example` to `.env` and fill in a real secret key (see Installation step above).

**Windows: `venv\Scripts\activate` says scripts are disabled**
Run PowerShell as administrator once and execute: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, then retry.

## 🔭 Future Improvements

- [ ] REST API via Django REST Framework for a mobile companion app
- [ ] Real payment settlement via Stripe Connect (currently only *suggests* who should pay whom)
- [ ] Email notifications when added to a group or when a new group expense is logged
- [ ] Recurring budgets (auto-create next month's budget from this month's)
- [ ] django-storages + S3 for avatar uploads in production

## 📄 License

MIT License — see [LICENSE](LICENSE).

## 👤 Author

**Your Name** — [GitHub](https://github.com/<your-username>) · [LinkedIn](https://linkedin.com/in/<your-username>)

## 🙏 Acknowledgements

Debt-simplification concept inspired by Splitwise's well-known "simplify debts" feature. Project #8 of a self-directed software engineering portfolio roadmap covering Python, SQL, Java, and Django.
