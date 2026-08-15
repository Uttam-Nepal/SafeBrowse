# SafeBrowse

A hybrid machine learning web application for phishing and malicious URL detection. Paste a URL, get an instant Safe/Unsafe classification with a confidence score and a plain-language explanation of why.

**Live demo:** https://safebrowse-rmgh.onrender.com
**Backend API docs:** https://safebrowse-backend.onrender.com/docs
**Repository:** https://github.com/Uttam-Nepal/SafeBrowse

> Note: the deployed backend runs the six lightweight statistical models. The full hybrid (Default) model requires a fine-tuned BERT model too large for free hosting — see [Limitations](#limitations) below for why, and how it's demonstrated instead.

---

## Project overview

SafeBrowse started as a MIT207 project proposal and has been developed through MIT208 into a working full-stack application: a React frontend, a FastAPI backend, a real authentication/history database, and seven independently trained classification models — six statistical models (Random Forest, XGBoost, Logistic Regression, Decision Tree, SVM, Naive Bayes) plus a hybrid model ("DeepTrace") combining a fine-tuned BERT encoder, handcrafted URL features, and a tree ensemble.

## Problem addressed

Phishing links spread through email, SMS, and social media faster than browser blacklists can catch them — a domain has to be reported and confirmed malicious before it's blocked, leaving a real window where new phishing sites go undetected. SafeBrowse gives a fast, independent, explainable second opinion before someone clicks, without needing a security background to interpret the result.

## Features

- Paste a URL, get a Safe/Unsafe verdict with a confidence score and plain-language reasons
- "Default" hybrid model, or pick from six "Experiment" statistical models to directly compare how different approaches score the same link
- Fast reputation allowlist for well-known and institution-specific domains, checked before any model runs
- Optional accounts (sign up / sign in) — guest use is always fully supported, no account required
- Per-user Dashboard showing check history and summary statistics
- Minimal admin endpoint for viewing registered users and their check counts

## Screenshots

See the MIT208 Assessment 2 report (`/docs/SafeBrowse_MIT208_Assessment2.docx` in this repo) and the presentation deck for labelled screenshots of the checker, sign-in/sign-up, and Dashboard screens.

## Architecture

Three-tier design, with the machine learning layer deliberately decoupled from the web layer so models can be retrained or swapped without touching the API or frontend:

```
React (Vite + Tailwind)  ->  FastAPI backend  ->  SQLite/MySQL database
  checker / auth / dashboard    REST API,          users, check_history
                                 auth, model
                                 orchestration
                                     |
                    +----------------+----------------+
                    |     ML layer (own modules)       |
                    |  feature extraction * statistical |
                    |  models * hybrid model * reputation|
                    |  allowlist * explanation generator |
                    +-----------------------------------+
```

Full labelled architecture diagram, the DeepTrace hybrid model pipeline diagram, and the database ERD are in the MIT208 Assessment 2 report.

## Technology stack

| Layer              | Technology                                                                   |
| ------------------ | ---------------------------------------------------------------------------- |
| Frontend           | React, Vite, Tailwind CSS                                                    |
| Backend            | Python, FastAPI, Uvicorn                                                     |
| Database / ORM     | SQLite (dev), SQLAlchemy (MySQL-ready for production with one config change) |
| Auth               | bcrypt password hashing, JWT bearer tokens                                   |
| Statistical models | scikit-learn, XGBoost                                                        |
| Hybrid model       | PyTorch, Hugging Face Transformers, XGBoost, scikit-learn                    |
| Deployment         | Render (Static Site + Web Service)                                           |

## Installation

### Prerequisites

- Python 3.10
- Node.js (LTS)
- Git

### Clone

```bash
git clone https://github.com/Uttam-Nepal/SafeBrowse.git
cd SafeBrowse
```

### Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### Frontend setup

```bash
cd frontend
npm install
```

## Configuration

The backend reads configuration from OS environment variables (see `.env.example` for the full list and safe local defaults). On Render, these are set directly in the service's Environment tab. Locally, the defaults below work out of the box for development — no `.env` file is required unless you want to override them.

| Variable         | Purpose                                  | Default (dev only)                             |
| ---------------- | ---------------------------------------- | ---------------------------------------------- |
| `JWT_SECRET_KEY` | Signs authentication tokens              | `dev-only-secret-change-this-before-deploying` |
| `ADMIN_KEY`      | Protects the `/api/admin/users` endpoint | `dev-admin-key`                                |
| `DATABASE_URL`   | Database connection string               | `sqlite:///./safebrowse.db`                    |

## How to run

**Terminal 1 — backend:**

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. The database (`safebrowse.db`) is created automatically on first run — no manual setup needed.

## Test accounts

No test account is needed. Checking a URL never requires an account — this is a deliberate design decision (NFR2 in the project report), not a missing feature: the core workflow (paste a URL, get a verdict) is fully usable as a guest, with every check still logged to the database regardless of login state.

To test the optional account features (sign-up, sign-in, Dashboard/history), simply use **Sign Up** on the live site with any email address — no pre-seeded credentials are required or provided.

## Testing

- Automated evaluation metrics (accuracy, precision, recall, F1) were captured for all seven models during training
- Manual scenario-based testing used URLs outside the training dataset, including typosquats, compound-TLD domains, and IP-hosted links
- Full test case table, results, and two documented bugs (with root cause and fix) are in the MIT208 Assessment 2 report, Appendix B and Section 6

## Limitations

- **The hybrid (Default) model is not hosted on the live deployment.** Its BERT component (~440MB) exceeds what free hosting tiers reliably support; the deployed backend automatically and transparently falls back to the Decision Tree model when Default is selected, with a visible note explaining why. The real hybrid model is demonstrated running locally instead.
- Statistical model accuracy (~84% for Random Forest) reflects a lexical-features-only approach; it is not a guarantee, and confidence scores reflect performance on a class-balanced test set rather than real-world URL prevalence.
- Combining phishing, malware, and defacement into one "Unsafe" label was found to dilute phishing-specific signal in feature importance analysis — documented in the report as a known limitation, not fixed in this version.
- Deep Learning (CNN, LSTM, BiLSTM, GRU) and additional Transformer (DistilBERT, RoBERTa, ALBERT) models are reserved in the interface ("coming soon") but not yet trained.
- The free-tier deployment sleeps after 15 minutes of inactivity; the first request after idle time takes 30-60 seconds.

## AI-use note

Claude (Anthropic) was used to help derive and refine the Default hybrid classification method (DeepTrace) and to assist with testing and implementing parts of the codebase. All AI-assisted output was reviewed, tested, and adapted before inclusion; genuine defects (documented in the project report) were found and understood through hands-on investigation, including inspecting model outputs, checking database records, and diagnosing deployment errors directly. No content, code, or evidence in this repository represents work the author cannot explain.

## Author

Uttam Nepal (MLB0001298)
MIT208 Project 2 (Implementation) — MIHE
Submitted to Dr. Saugata Bose
