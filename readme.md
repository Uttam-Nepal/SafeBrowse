# SafeBrowse

A machine learning web application for phishing and malicious URL detection. Paste a URL and get an instant **Safe / Unsafe** verdict with a confidence score and a plain-language explanation of why, judged from the text of the address alone, so it can warn you before the page ever loads.

**Live demo:** https://safe-browse-sigma.vercel.app/
**Backend API docs:** https://safebrowse-api-764112628669.us-central1.run.app/docs
**Repository:** https://github.com/Uttam-Nepal/SafeBrowse

> **Note:** the demo runs on free-tier hosting. The backend scales to zero when idle, so the first check after a quiet period can take 30 to 60 seconds while the model loads. Accounts and history reset when the backend restarts.
>
> The version submitted for MIT208 assessment (the DeepTrace hybrid model plus six statistical models) is preserved at the Git tag `v1.0-final`. The assessment report and presentation describe that earlier version. This `main` branch runs the newer model described below.

## Project overview

SafeBrowse started as a MIT207 project proposal and was developed through MIT208 into a working full-stack application: a React frontend, a FastAPI backend, and a real authentication and history database. It now runs **TURL-MV-LeafFuse**, a research model developed by the author with Dr. Saugata Bose, in place of the earlier models.

### Problem addressed

Phishing links spread through email, SMS and social media faster than browser blacklists can catch them. A domain has to be reported and confirmed malicious before it is blocked, leaving a real window where new phishing sites go undetected. SafeBrowse gives a fast, independent, explainable second opinion before someone clicks, without needing a security background to interpret the result.

## Features

- Paste a URL, get a Safe/Unsafe verdict with a confidence score and plain-language reasons
- Fast reputation allowlist (2,064 well-known and institution-specific domains) checked before the model runs
- A model-details page in the app explaining how the model works, its results and its limitations
- Optional accounts (sign up / sign in). Guest use is always fully supported, no account required
- Per-user Dashboard showing check history and summary statistics
- Minimal admin endpoint for viewing registered users and their check counts

## The model: TURL-MV-LeafFuse

TURL-MV-LeafFuse stands for **Transformer URL, Multi-View, with tree-leaf fusion**.

- It reads each URL three ways: structure (length, symbols, suspicious words), character patterns, and meaning, using a BERT model adapted to URLs.
- Eight base classifiers each give an opinion: XGBoost on 36 handcrafted features, two TF-IDF logistic models, a fine-tuned BERT classifier, and XGBoost and random-forest models on BERT embeddings and on a hybrid of embeddings and features.
- A final logistic model combines the eight probabilities, the BERT embedding, the 36 features and one-hot "leaf fingerprints" taken from the hybrid XGBoost model's decision trees (2,294 inputs in total).
- The decision threshold (0.513) was chosen on out-of-fold predictions, and the test set was scored once.

### Results

Test set of 16,690 URLs from websites never seen in training (split by registrable domain):

| Model                    | Precision | Recall | F1         | PR-AUC | ROC-AUC |
| ------------------------ | --------- | ------ | ---------- | ------ | ------- |
| **TURL-MV-LeafFuse**     | 0.9236    | 0.9115 | **0.9175** | 0.9687 | 0.9837  |
| BERT-Standalone          | 0.9095    | 0.9160 | 0.9127     | 0.9702 | 0.9828  |
| Hybrid + Random Forest   | 0.8922    | 0.9238 | 0.9077     | 0.9696 | 0.9836  |
| BERT-Emb + XGBoost       | 0.8818    | 0.9294 | 0.9050     | 0.9713 | 0.9842  |
| Hybrid + XGBoost         | 0.8840    | 0.9268 | 0.9049     | 0.9714 | 0.9843  |
| BERT-Emb + Random Forest | 0.8792    | 0.9303 | 0.9040     | 0.9692 | 0.9827  |
| TF-IDF Character         | 0.8803    | 0.8927 | 0.8865     | 0.9455 | 0.9699  |
| XGBoost Lexical          | 0.7218    | 0.8432 | 0.7778     | 0.8889 | 0.9404  |
| TF-IDF Token             | 0.7035    | 0.8555 | 0.7721     | 0.8899 | 0.9395  |

LeafFuse has the best F1, a statistically significant gain over all eight baselines (paired bootstrap, 10,000 resamples). It does not have the best ranking scores (PR-AUC, ROC-AUC); its advantage is better final decisions at the chosen threshold. On a second dataset (Kaggle Phishing Site URLs) it reached F1 0.9232. The deployed model scores slightly differently: precision 0.9232, recall 0.9117, F1 0.9174, accuracy 0.9545.

Data: the Kaggle Malicious URLs Dataset (651,191 URLs). After cleaning, a fixed 80,000-URL sample was drawn. Benign is Safe; phishing, malware and defacement are Unsafe.

### Reference

Nepal, U. and Bose, S. (2026) "TURL-MV-LeafFuse: Multi-View Fusion with Tree-Leaf Features for Malicious URL Detection". Submitted; under review.

## Architecture

Three-tier design, with the machine learning layer decoupled from the web layer so the model can be retrained or swapped without touching the API or frontend:

```
React (Vite + Tailwind)  ->  FastAPI backend  ->  SQLite database
 Vercel                       Google Cloud Run     users, check_history
 checker / auth / dashboard   REST API, auth,
 / model page                 model orchestration
                                    |
                      +-------------+--------------+
                      |    ML layer (own modules)  |
                      |  reputation allowlist ->   |
                      |  TURL-MV-LeafFuse model    |
                      |  explanation generator     |
                      +----------------------------+
```

How a check works:

1. The URL is validated.
2. The reputation allowlist is checked first (exact or subdomain match on the parsed hostname, never a substring match). Hosts where strangers can publish pages, such as `sites.google.com`, are excluded from it.
3. Otherwise the URL is canonicalised and scored by TURL-MV-LeafFuse.
4. The verdict is returned and saved to the check history.

## Technology stack

| Layer          | Technology                                                      |
| -------------- | --------------------------------------------------------------- |
| Frontend       | React, Vite, Tailwind CSS (hosted on Vercel)                    |
| Backend        | Python 3.13, FastAPI, Uvicorn (hosted on Google Cloud Run)      |
| Database / ORM | SQLite, SQLAlchemy (MySQL-ready with one config change)         |
| Auth           | bcrypt password hashing, JWT bearer tokens                      |
| Model          | PyTorch (CPU), Hugging Face Transformers, XGBoost, scikit-learn |

## Installation

The model weights are **not** in this repository, because the paper is under review. Without them the app still starts, but `/health` reports `model_loaded: false` and checks return a 503 error. To run the model locally you need the model folder placed at `backend/models/turl_mv/`.

### Prerequisites

- **Python 3.13** (the version the model was trained with). The package versions in `requirements.txt` are pinned exactly, because part of the model is a pickle.
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
py -3.13 -m venv venv-turl          # Windows; use python3.13 on macOS/Linux
venv-turl\Scripts\activate          # source venv-turl/bin/activate on macOS/Linux
pip install -r requirements.txt
```

### Frontend setup

```bash
cd frontend
npm install
```

## Configuration

The backend reads configuration from OS environment variables (see `.env.example` for the list and safe local defaults). The defaults below work out of the box for local development.

| Variable          | Purpose                                                               | Default (dev only)                           |
| ----------------- | --------------------------------------------------------------------- | -------------------------------------------- |
| `JWT_SECRET_KEY`  | Signs authentication tokens. **Set this in production.**              | dev-only-secret-change-this-before-deploying |
| `ADMIN_KEY`       | Protects the `/api/admin/users` endpoint. **Set this in production.** | dev-admin-key                                |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins                      | `*`                                          |
| `DATABASE_URL`    | Database connection string                                            | sqlite:///./safebrowse.db                    |

Frontend: the API address defaults to `http://localhost:8000`. Set `VITE_API_URL` at build time to point somewhere else.

## How to run

Terminal 1, backend:

```bash
cd backend
venv-turl\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2, frontend:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The database (`safebrowse.db`) is created automatically on first run.

### API

| Endpoint                                             | Purpose                                                 |
| ---------------------------------------------------- | ------------------------------------------------------- |
| `GET /health`                                        | Status, model name, whether the model loaded, threshold |
| `POST /predict`, `POST /api/check`                   | Check a URL (`{"url": "..."}`)                          |
| `POST /api/signup`, `POST /api/login`, `GET /api/me` | Accounts                                                |
| `GET /api/history`                                   | The signed-in user's saved checks                       |
| `GET /api/admin/users`                               | Registered users and check counts (needs the admin key) |

## Test accounts

No test account is needed. Checking a URL never requires an account. This is a deliberate design decision (NFR2 in the project report), not a missing feature: the core workflow is fully usable as a guest, with every check still logged to the database regardless of login state.

To test the optional account features (sign-up, sign-in, Dashboard/history), use Sign Up on the live site with any email address. No pre-seeded credentials are provided.

## Testing

- Automated evaluation metrics (accuracy, precision, recall, F1, PR-AUC, ROC-AUC) were produced for the model and its eight base classifiers during training; see the results table above.
- Manual scenario-based testing used URLs outside the training data, including typosquats, compound-TLD domains and IP-hosted links.
- The assessed version's full test case table, results and two documented bugs (with root cause and fix) are in the MIT208 Assessment 2 report (`/docs/SafeBrowse_MIT208_Assessment2.docx`), Appendix B and Section 6. That report describes the earlier model.

## Limitations

- The model judges **URL text only**. It cannot see page content, domain age, ownership or reputation, so a clean-looking address on a malicious site can pass.
- It was trained and tested on one public dataset at a fixed point in time. Accuracy on future attack styles or other data sources has not been measured.
- In this app, ordinary modern sites, even well-known ones, are often scored Unsafe, because the training data under-represents them. The reputation allowlist reduces this for the domains it contains, but it is a list of domains, not a guarantee about any page.
- Other noted limits: a single BERT training run, and fusion cross-validation that was row-based, not domain-based.
- Confidence is a model score, not a calibrated probability. Treat borderline results with caution.
- This is a **research demo**, not a security product. Do not rely on it as your only protection.
- Free-tier hosting: the backend sleeps when idle, and accounts and history reset when it restarts.

## AI-use note

Claude (Anthropic) was used to assist with testing and implementing parts of the codebase, including integrating the research model into the app and deploying it. All AI-assisted output was reviewed, tested and adapted before inclusion. The TURL-MV-LeafFuse model and its paper are the work of the authors named above.
