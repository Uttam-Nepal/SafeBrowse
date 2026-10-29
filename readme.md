# SafeBrowse

SafeBrowse checks whether a link is safe before you open it. You paste a URL and it tells you Safe or Unsafe, with a confidence score and a short explanation. It only looks at the text of the address, so it can warn you before the page loads.

The model behind it, TURL-MV-LeafFuse, comes from my research paper with Saugata Bose (Nepal and Bose, 2026). I built this app to put that model in front of real users.

Live demo: https://safe-browse-sigma.vercel.app/
API docs: https://safebrowse-api-764112628669.us-central1.run.app/docs

The demo runs on free hosting. The backend shuts down when nobody is using it, so the first check after a quiet spell can take 30 to 60 seconds while the model loads. Accounts and history are wiped when it restarts.

## Why I built it

Phishing links move faster than blocklists. A site usually has to be reported and confirmed before browsers block it, and in that gap people click. SafeBrowse is meant to be a quick second opinion you can get before you click, in plain language, without needing a security background.

## What it does

- Checks a URL and returns Safe or Unsafe with a confidence score and reasons
- Checks a list of 2,064 well-known domains first, before the model runs
- Has a model page in the app that explains how it works, its results and its weak points
- Works without an account. Signing up adds a dashboard with your check history
- Has a small admin endpoint that lists registered users and how many checks each has made

## The model

TURL-MV-LeafFuse stands for Transformer URL, Multi-View, with tree-leaf fusion.

It reads each URL in three ways: its structure (length, symbols, suspicious words), its character patterns, and its meaning, using a BERT model adapted to URLs. Eight classifiers each give their own opinion. A final model then combines those opinions, the BERT embedding, 36 handcrafted features, and a "leaf fingerprint" taken from the decision trees of one of the XGBoost models. That fingerprint shows which group of similar URLs a link falls into, and it gives the final model more to work with than eight scores alone. The decision threshold is 0.513, chosen on out-of-fold predictions. The test set was scored once.

The eight base classifiers are XGBoost on the handcrafted features, two TF-IDF logistic models (characters and words), a fine-tuned BERT classifier, and XGBoost and random forest models on both the BERT embedding and a hybrid of the embedding plus the features.

### Results

These are scores on 16,690 test URLs. The split was by domain, so no website appears in both training and test.

| Model                    | Precision | Recall | F1     | PR-AUC | ROC-AUC |
| ------------------------ | --------- | ------ | ------ | ------ | ------- |
| TURL-MV-LeafFuse         | 0.9236    | 0.9115 | 0.9175 | 0.9687 | 0.9837  |
| BERT-Standalone          | 0.9095    | 0.9160 | 0.9127 | 0.9702 | 0.9828  |
| Hybrid + Random Forest   | 0.8922    | 0.9238 | 0.9077 | 0.9696 | 0.9836  |
| BERT-Emb + XGBoost       | 0.8818    | 0.9294 | 0.9050 | 0.9713 | 0.9842  |
| Hybrid + XGBoost         | 0.8840    | 0.9268 | 0.9049 | 0.9714 | 0.9843  |
| BERT-Emb + Random Forest | 0.8792    | 0.9303 | 0.9040 | 0.9692 | 0.9827  |
| TF-IDF Character         | 0.8803    | 0.8927 | 0.8865 | 0.9455 | 0.9699  |
| XGBoost Lexical          | 0.7218    | 0.8432 | 0.7778 | 0.8889 | 0.9404  |
| TF-IDF Token             | 0.7035    | 0.8555 | 0.7721 | 0.8899 | 0.9395  |

LeafFuse has the best F1, and the gain over all eight baselines is statistically significant (paired bootstrap, 10,000 resamples). It does not have the best PR-AUC or ROC-AUC. Its advantage is in the final decisions at the chosen threshold. On a second dataset, Kaggle Phishing Site URLs, it reached an F1 of 0.9232. The copy deployed here scores slightly differently: precision 0.9232, recall 0.9117, F1 0.9174, accuracy 0.9545.

The training data is the Kaggle Malicious URLs Dataset (651,191 URLs). After cleaning I drew a fixed sample of 80,000. Benign counts as Safe, and phishing, malware and defacement all count as Unsafe.

Reference: Nepal, U. and Bose, S. (2026) "TURL-MV-LeafFuse: Multi-View Fusion with Tree-Leaf Features for Malicious URL Detection". Submitted, under review.

## How it fits together

The frontend is a React and Vite app on Vercel. It talks to a FastAPI backend on Google Cloud Run, which stores users and check history in SQLite through SQLAlchemy. Passwords are hashed with bcrypt and sessions use JWT. The model code sits in its own modules, so it can be retrained or swapped without touching the API or the frontend.

When you check a URL, the backend first validates it. Then it looks at the hostname against the allowlist, matching either the exact domain or a subdomain of it, never a substring. Sites where anyone can publish pages, like sites.google.com, are deliberately left off the list. If the domain isn't on the list, the model scores the URL. The verdict is returned and saved to your history.

## Running it locally

The model files are not in this repository because the paper is still under review. Without them the app starts, but `/health` shows `model_loaded: false` and checks return a 503. If you have the model folder, put it at `backend/models/turl_mv/`.

You need Python 3.13, which is the version the model was trained with, plus Node.js and Git. The versions in `requirements.txt` are pinned exactly because part of the model is a pickle file.

```bash
git clone https://github.com/Uttam-Nepal/SafeBrowse.git
cd SafeBrowse
```

Backend:

```bash
cd backend
py -3.13 -m venv venv-turl          # on macOS/Linux: python3.13 -m venv venv-turl
venv-turl\Scripts\activate          # on macOS/Linux: source venv-turl/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The database file is created on first run.

The backend reads these environment variables, and the defaults are fine for local use:

| Variable          | What it does                                             | Default                     |
| ----------------- | -------------------------------------------------------- | --------------------------- |
| `JWT_SECRET_KEY`  | Signs login tokens. Set it in production.                | a dev-only value            |
| `ADMIN_KEY`       | Protects `/api/admin/users`. Set it in production.       | `dev-admin-key`             |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to call the API | `*`                         |
| `DATABASE_URL`    | Database connection string                               | `sqlite:///./safebrowse.db` |

The frontend calls `http://localhost:8000` unless you set `VITE_API_URL` when building.

### Endpoints

| Endpoint                                             | What it does                                     |
| ---------------------------------------------------- | ------------------------------------------------ |
| `GET /health`                                        | Status, model name, whether it loaded, threshold |
| `POST /predict` and `POST /api/check`                | Check a URL, body `{"url": "..."}`               |
| `POST /api/signup`, `POST /api/login`, `GET /api/me` | Accounts                                         |
| `GET /api/history`                                   | Your saved checks                                |
| `GET /api/admin/users`                               | Users and check counts, needs the admin key      |

You don't need an account to check a URL. That's on purpose, and every check is still logged either way. To try the account features, sign up on the live site with any email address.

## Testing

The model was evaluated on a held-out test set split by domain, using accuracy, precision, recall, F1, PR-AUC and ROC-AUC, and compared with eight baselines using paired bootstrap tests. The app itself was tested by hand with URLs outside the training data: typosquats, compound-TLD domains, IP-hosted links and well-known sites.

## Limitations

- The model only sees the URL text. It can't see page content, domain age, who owns the site or its reputation, so a clean-looking address on a malicious site can get through.
- It was trained and tested on one public dataset from one point in time. How it does on newer attack styles or other data sources hasn't been measured.
- Ordinary modern websites, even famous ones, often get scored as Unsafe, because the training data doesn't include many of them. The allowlist helps for the domains on it, but it's a list of domains and says nothing about any single page.
- BERT was trained once, with a single seed, and the cross-validation for the final model was split by row, not by domain.
- The confidence is a model score, not a calibrated probability. Be careful with results close to the threshold.
- This is a research demo, not a security product. Don't rely on it as your only protection.

## AI use

I used Claude (Anthropic) to help with parts of the app's code, including connecting the model to the backend and deploying it. I reviewed and tested what it produced. The model and the paper are our own work.

## Authors

Built by Uttam Nepal, Melbourne Institute of Higher Education. Research co-author: Dr. Saugata Bose.
