import { useState, useEffect } from "react";
import { Search, Moon, Sun, User, Check, X, Shield } from "lucide-react";

const MODEL_LABEL = "TURL-MV LeafFuse";

// Points at your local FastAPI backend. When you deploy, change this to
// your real backend URL (e.g. via an environment variable).
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function checkUrl(url, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}/api/check`, {
    method: "POST",
    headers,
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }

  const data = await res.json();
  return {
    verdict: data.verdict,
    confidence: Math.round(data.confidence * 100),
    reasons: data.reasons,
    note: data.note || null,
  };
}

async function apiSignup(email, password) {
  const res = await fetch(`${API_BASE_URL}/api/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Signup failed.");
  return body; // { access_token, token_type, email }
}

async function apiLogin(email, password) {
  const res = await fetch(`${API_BASE_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Login failed.");
  return body;
}

async function apiHistory(token) {
  const res = await fetch(`${API_BASE_URL}/api/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Could not load history.");
  return body;
}

function Navbar({
  dark,
  setDark,
  onAccountClick,
  onLogoClick,
  userEmail,
  onDashboardClick,
  onLogout,
}) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white">
      <button
        onClick={onLogoClick}
        className="flex items-center gap-2 font-semibold text-slate-900"
      >
        <span className="w-7 h-7 rounded-lg bg-slate-900 grid place-items-center">
          <Shield size={15} className="text-teal-400" />
        </span>
        SafeBrowse
      </button>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setDark(!dark)}
          className="w-9 h-9 rounded-full border border-slate-200 grid place-items-center text-slate-500 hover:border-teal-500 hover:text-teal-700"
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {userEmail ? (
          <>
            <button
              onClick={onDashboardClick}
              className="text-sm font-semibold text-slate-700 hover:text-teal-700 px-3 py-1.5 rounded-lg hover:bg-slate-50"
            >
              Dashboard
            </button>
            <span className="text-sm text-slate-400 hidden sm:inline">
              {userEmail}
            </span>
            <button
              onClick={onLogout}
              className="text-sm font-semibold text-slate-500 hover:text-red-600 px-3 py-1.5 rounded-lg hover:bg-red-50"
            >
              Sign out
            </button>
          </>
        ) : (
          <button
            onClick={onAccountClick}
            className="w-9 h-9 rounded-full border border-slate-200 grid place-items-center text-slate-500 hover:border-teal-500 hover:text-teal-700"
          >
            <User size={16} />
          </button>
        )}
      </div>
    </header>
  );
}

function ResultPanel({ url, result, model, onNewSearch }) {
  const isSafe = result.verdict === "safe";

  function normalizeUrl(raw) {
    return /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
  }
  function handleContinue() {
    window.open(normalizeUrl(url), "_blank", "noopener,noreferrer");
  }
  function handleProceedAnyway() {
    const ok = window.confirm(
      "This link was flagged as unsafe. Are you sure you want to continue anyway?",
    );
    if (ok) window.open(normalizeUrl(url), "_blank", "noopener,noreferrer");
  }

  return (
    <section className="w-full max-w-xl mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-6 pt-5 flex-wrap">
        <span
          className={
            "inline-flex items-center gap-1.5 font-mono font-bold text-sm px-3.5 py-1.5 rounded-full border " +
            (isSafe
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : "bg-red-50 text-red-700 border-red-200")
          }
        >
          {isSafe ? <Check size={14} /> : <X size={14} />}
          {isSafe ? "SAFE" : "UNSAFE"}
        </span>
        <span className="text-xs font-mono text-slate-500">
          {result.confidence}% confidence · {model}
        </span>
      </div>
      <p className="text-xs text-slate-400 px-6 pt-1 italic">
        Confidence is the model's own estimate, not a guarantee.
      </p>
      {!isSafe && (
        <p className="text-xs text-amber-700 px-6 pt-1">
          Research demo: this model was trained on one older dataset and
          sometimes flags ordinary, well-known sites as unsafe. Treat an Unsafe
          result as a prompt to double-check, not proof.
        </p>
      )}
      {result.note && (
        <div className="mx-6 mt-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          {result.note}
        </div>
      )}
      <div className="font-mono text-sm text-slate-500 px-6 pt-3 break-all">
        {url}
      </div>
      <div className="mx-6 mt-4 bg-slate-900 rounded-xl p-4">
        <p className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-2.5">
          Why
        </p>
        <ul className="flex flex-col gap-2">
          {result.reasons.map((r, i) => (
            <li key={i} className="font-mono text-sm text-slate-100 flex gap-2">
              <span className="text-teal-400 font-bold">›</span>
              {r}
            </li>
          ))}
        </ul>
      </div>
      <div className="flex justify-between items-center px-6 py-5 gap-3">
        <button
          onClick={onNewSearch}
          className="px-5 py-2.5 rounded-lg border border-slate-200 font-semibold text-sm text-slate-900 hover:border-teal-500 hover:text-teal-700"
        >
          New search
        </button>
        {isSafe ? (
          <button
            onClick={handleContinue}
            className="px-5 py-2.5 rounded-lg bg-teal-600 text-white font-semibold text-sm hover:bg-teal-700"
          >
            Continue in browser
          </button>
        ) : (
          <button
            onClick={handleProceedAnyway}
            className="px-5 py-2.5 rounded-lg border border-red-200 text-red-600 font-semibold text-sm hover:bg-red-50"
          >
            Proceed anyway
          </button>
        )}
      </div>
    </section>
  );
}

function CheckerScreen({ token }) {
  const [url, setUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  async function handleCheck() {
    if (!url.trim()) return;
    setResult(null);
    setErrorMsg(null);
    setScanning(true);
    try {
      const data = await checkUrl(url, token);
      setResult(data);
    } catch (err) {
      setErrorMsg(
        err.message?.includes("Failed to fetch")
          ? "Couldn't reach the backend. Is it running on http://localhost:8000?"
          : err.message,
      );
    } finally {
      setScanning(false);
    }
  }

  return (
    <main className="flex-1 flex flex-col items-center px-5 pt-16 pb-10">
      <span className="font-mono text-xs uppercase tracking-widest text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full mb-4">
        Real-time link analysis
      </span>
      <h1 className="font-semibold text-3xl sm:text-4xl text-center max-w-xl mb-2 tracking-tight text-slate-900">
        Paste a link. We'll scan it before you click.
      </h1>
      <p className="text-slate-500 text-center max-w-md mb-9">
        SafeBrowse scores the URL with TURL-MV LeafFuse, a hybrid
        machine-learning model, and explains why it's safe or not — no account
        needed.
      </p>

      <div className="w-full max-w-xl bg-white border border-slate-200 rounded-2xl shadow-sm p-2.5">
        <div className="relative flex items-center rounded-xl overflow-hidden">
          <Search
            size={18}
            className="absolute left-3.5 text-slate-400 pointer-events-none"
          />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCheck()}
            placeholder="https://example.com/verify-account"
            className="flex-1 font-mono text-sm pl-11 pr-3.5 py-3.5 bg-slate-50 rounded-xl outline-none focus:ring-2 focus:ring-teal-500 focus:ring-inset"
          />
        </div>

        <div className="flex justify-end px-1.5 pt-2">
          <button
            onClick={handleCheck}
            disabled={scanning}
            className="bg-slate-900 text-white font-semibold text-sm px-5 py-2.5 rounded-lg disabled:opacity-60"
          >
            {scanning ? "Scanning…" : "Check"}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="w-full max-w-xl mt-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {result?.note && (
        <div className="w-full max-w-xl mt-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
          {result.note}
        </div>
      )}

      {result && (
        <ResultPanel
          url={url}
          result={result}
          model={MODEL_LABEL}
          onNewSearch={() => {
            setUrl("");
            setResult(null);
            setErrorMsg(null);
          }}
        />
      )}
    </main>
  );
}

function AuthCard({ eyebrow, title, sub, children }) {
  return (
    <main className="flex-1 grid place-items-center px-5 py-10">
      <div className="w-full max-w-sm bg-white border border-slate-200 rounded-2xl shadow-sm px-8 pt-9 pb-7">
        <p className="font-mono text-xs uppercase tracking-wider text-teal-700 mb-1.5">
          {eyebrow}
        </p>
        <h1 className="font-semibold text-2xl mb-1.5 tracking-tight text-slate-900">
          {title}
        </h1>
        <p className="text-slate-500 text-sm mb-6">{sub}</p>
        {children}
      </div>
    </main>
  );
}

function Field({ label, type = "text", hint, value, onChange }) {
  return (
    <div className="mb-4 text-left">
      <label className="block text-sm font-semibold mb-1.5 text-slate-900">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={type === "password" ? "••••••••" : "you@example.com"}
        className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-sm focus:border-teal-500 focus:bg-white outline-none"
      />
      {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
  );
}

function SignInScreen({ goSignup, onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!email.includes("@") || !password) {
      setError("Enter a valid email and password to continue.");
      return;
    }
    setLoading(true);
    try {
      const data = await apiLogin(email, password);
      onLoginSuccess(data.access_token, data.email);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      eyebrow="Welcome back"
      title="Sign in"
      sub="Check your history and saved results."
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 mb-4">
            {error}
          </div>
        )}
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-slate-900 text-white font-semibold text-sm py-2.5 rounded-lg mt-1 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="flex justify-between text-sm mt-4">
        <a className="text-teal-700 font-semibold cursor-pointer hover:underline">
          Forgot password?
        </a>
        <a
          onClick={goSignup}
          className="text-teal-700 font-semibold cursor-pointer hover:underline"
        >
          Create an account
        </a>
      </div>
    </AuthCard>
  );
}

const MODEL_STATS = [
  { label: "Accuracy", value: "95.45%" },
  { label: "Precision", value: "92.32%" },
  { label: "Recall", value: "91.17%" },
  { label: "F1-Score", value: "0.9174" },
];

function AboutScreen({ onModelClick }) {
  return (
    <main className="flex-1 px-5 py-14">
      <div className="max-w-2xl mx-auto">
        <p className="font-mono text-xs uppercase tracking-wider text-teal-700 mb-1.5">
          About
        </p>
        <h1 className="font-semibold text-3xl tracking-tight text-slate-900 mb-6">
          How SafeBrowse works
        </h1>

        <section className="mb-8">
          <h2 className="font-semibold text-lg text-slate-900 mb-2">
            How it decides
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            TURL-MV LeafFuse reads the URL text only; it never visits the page.
            Eight base models (a fine-tuned BERT, TF-IDF text models and
            gradient-boosted trees on lexical features) each score the link, and
            a final fusion layer combines their scores with tree-path features
            into one verdict. A short list of well-known trusted domains is
            checked first.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="font-semibold text-lg text-slate-900 mb-2">
            Training data
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Trained on a locked 80,000-URL sample of the{" "}
            <a
              href="https://www.kaggle.com/datasets/sid321axn/malicious-urls-dataset"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-700 font-semibold hover:underline"
            >
              Kaggle Malicious URLs Dataset
            </a>{" "}
            (651,191 URLs before cleaning). Benign is "Safe"; phishing, malware
            and defacement are "Unsafe". The data is split by website, so no
            site appears in both training and testing.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="font-semibold text-lg text-slate-900 mb-2">
            TURL-MV LeafFuse — reported performance
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Measured once on a held-out test set of 16,690 URLs from websites
            unseen during training.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {MODEL_STATS.map((s) => (
              <div
                key={s.label}
                className="bg-white border border-slate-200 rounded-xl px-3 py-3 text-center"
              >
                <p className="font-mono text-lg font-bold text-slate-900">
                  {s.value}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        <button
          onClick={onModelClick}
          className="mb-6 text-sm font-semibold text-teal-700 hover:underline"
        >
          Read the full model details →
        </button>

        <section className="mb-2 bg-amber-50 border border-amber-200 rounded-xl px-5 py-4">
          <h2 className="font-semibold text-sm text-amber-900 mb-1.5">
            A note on confidence scores
          </h2>
          <p className="text-amber-800 text-sm leading-relaxed">
            The confidence shown is the model's own probability estimate, not a
            guarantee. This app is a research demonstration of TURL-MV-LeafFuse.
            The model was trained on a single, older public dataset whose "Safe"
            examples are mostly older, deep-path pages. As a result it can flag
            many modern, well-known sites as Unsafe, and it has not been tested
            on other data sources. A short list of well-known domains is checked
            first, but treat any result as guidance and double-check links you
            weren't expecting.
          </p>
        </section>
      </div>
    </main>
  );
}

const PAPER_ROWS = [
  ["TURL-MV-LeafFuse", "0.9236", "0.9115", "0.9175", "0.9687", "0.9837"],
  ["BERT-Standalone", "0.9095", "0.9160", "0.9127", "0.9702", "0.9828"],
  ["Hybrid + Random Forest", "0.8922", "0.9238", "0.9077", "0.9696", "0.9836"],
  ["BERT-Emb + XGBoost", "0.8818", "0.9294", "0.9050", "0.9713", "0.9842"],
  ["Hybrid + XGBoost", "0.8840", "0.9268", "0.9049", "0.9714", "0.9843"],
  [
    "BERT-Emb + Random Forest",
    "0.8792",
    "0.9303",
    "0.9040",
    "0.9692",
    "0.9827",
  ],
  ["TF-IDF Character", "0.8803", "0.8927", "0.8865", "0.9455", "0.9699"],
  ["XGBoost Lexical", "0.7218", "0.8432", "0.7778", "0.8889", "0.9404"],
  ["TF-IDF Token", "0.7035", "0.8555", "0.7721", "0.8899", "0.9395"],
];

const BASE_MODELS = [
  [
    "M1",
    "XGBoost",
    "36 handcrafted features: lengths, character counts, entropy, IP/port/https flags, subdomains, suspicious words",
  ],
  [
    "M2",
    "Logistic regression (SGD)",
    "Character 3–5-gram TF-IDF (50,000 features)",
  ],
  [
    "M3",
    "Logistic regression (SGD)",
    "Word 1–2-gram TF-IDF (up to 30,000 features)",
  ],
  ["M4", "BERT classifier", "The URL text, up to 64 tokens"],
  ["M5", "XGBoost", "BERT's 768-dimension [CLS] vector"],
  ["M6", "Random forest", "BERT's [CLS] vector"],
  ["M7", "XGBoost", "Hybrid: [CLS] + 36 features (804 dimensions)"],
  ["M8", "Random forest", "The same hybrid"],
];

function ModelScreen({ onBack }) {
  const h2 = "font-semibold text-lg text-slate-900 mb-2";
  const p = "text-slate-600 text-sm leading-relaxed";
  return (
    <main className="flex-1 px-5 py-14">
      <div className="max-w-2xl mx-auto">
        <button
          onClick={onBack}
          className="text-sm font-semibold text-teal-700 hover:underline mb-4"
        >
          ← Back to About
        </button>
        <p className="font-mono text-xs uppercase tracking-wider text-teal-700 mb-1.5">
          The model
        </p>
        <h1 className="font-semibold text-3xl tracking-tight text-slate-900 mb-2">
          TURL-MV-LeafFuse
        </h1>
        <p className="text-slate-500 text-sm mb-6">
          <strong>T</strong>ransformer <strong>URL</strong>, <strong>M</strong>
          ulti-<strong>V</strong>iew, with tree-leaf fusion.
        </p>

        <p className={p + " mb-8"}>
          SafeBrowse checks links with TURL-MV-LeafFuse, a model that reads a
          URL in three different ways and combines eight classifiers into one
          decision. On websites it had never seen before, it flagged about 91%
          of malicious links, and about 92% of the links it flagged really were
          malicious.
        </p>

        <section className="mb-8">
          <h2 className={h2}>In plain English</h2>
          <ul className={p + " list-disc pl-5 flex flex-col gap-1.5"}>
            <li>
              It looks only at the web address, so it can warn you before the
              page ever loads.
            </li>
            <li>
              It reads the address three ways: its structure (length, symbols,
              suspicious words), its letter patterns, and its meaning, using a
              language model adapted to URLs.
            </li>
            <li>
              Eight different detectors each give an opinion, and a final model
              weighs them all.
            </li>
            <li>
              It also uses "fingerprints" from decision trees, showing which
              group of similar URLs a link falls into.
            </li>
            <li>
              It was tested only on websites it never saw during training, so
              the scores reflect new sites, not memorised ones.
            </li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className={h2}>The eight base models</h2>
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            {BASE_MODELS.map(([id, name, sees]) => (
              <div
                key={id}
                className="grid grid-cols-[2.5rem_1fr] gap-2 px-4 py-2.5 border-b border-slate-100 last:border-0 text-sm"
              >
                <span className="font-mono font-bold text-slate-900">{id}</span>
                <span className="text-slate-600">
                  <strong className="text-slate-800">{name}</strong> — {sees}
                </span>
              </div>
            ))}
          </div>
          <p className={p + " mt-3"}>
            The BERT model starts from{" "}
            <span className="font-mono">bert-base-uncased</span>, gets one
            masked-language-modelling epoch on training URLs (URLs look very
            different from the English it was first trained on), then up to
            three fine-tuning epochs. The best epoch is chosen on a separate
            selection set.
          </p>
        </section>

        <section className="mb-8">
          <h2 className={h2}>LeafFuse: the final decision</h2>
          <p className={p}>
            Each tree in model M7 sorts a URL into a "leaf", a small group of
            URLs it considers similar. Recording the leaf across all 100 trees
            (1,482 possible leaves) gives the final model a detailed fingerprint
            that eight single scores would lose. The final classifier is a
            logistic model on 2,294 inputs: the 8 base-model probabilities, the
            768-dimension BERT vector and the 36 features (812 standardised
            values), plus the 1,482 one-hot leaves. The decision threshold
            (0.513) was chosen on out-of-fold predictions, and the test set was
            scored once.
          </p>
        </section>

        <section className="mb-8">
          <h2 className={h2}>Data</h2>
          <p className={p}>
            The{" "}
            <a
              href="https://www.kaggle.com/datasets/sid321axn/malicious-urls-dataset"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-700 font-semibold hover:underline"
            >
              Kaggle Malicious URLs Dataset
            </a>{" "}
            has 651,191 URLs. After removing parse failures, conflicting labels
            and duplicates, 630,492 remained, and a fixed 80,000-URL sample was
            drawn. Benign is Safe; phishing, malware and defacement are Unsafe.
            The sample is split by registrable domain into train / select / meta
            / test sets (46,224 / 8,202 / 8,884 / 16,690 URLs), so a website
            never appears on both sides of the test.
          </p>
        </section>

        <section className="mb-8">
          <h2 className={h2}>Results (test set, 16,690 URLs)</h2>
          <div className="overflow-x-auto bg-white border border-slate-200 rounded-xl">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-200">
                  <th className="px-3 py-2 font-semibold">Model</th>
                  <th className="px-2 py-2 font-semibold">Prec.</th>
                  <th className="px-2 py-2 font-semibold">Recall</th>
                  <th className="px-2 py-2 font-semibold">F1</th>
                  <th className="px-2 py-2 font-semibold">PR-AUC</th>
                  <th className="px-2 py-2 font-semibold">ROC-AUC</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {PAPER_ROWS.map((r, i) => (
                  <tr
                    key={r[0]}
                    className={
                      "border-b border-slate-100 last:border-0 " +
                      (i === 0
                        ? "bg-teal-50 font-bold text-slate-900"
                        : "text-slate-600")
                    }
                  >
                    <td className="px-3 py-2 font-sans text-sm">{r[0]}</td>
                    {r.slice(1).map((v, j) => (
                      <td key={j} className="px-2 py-2">
                        {v}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={p + " mt-3"}>
            LeafFuse has the best F1, a statistically significant gain over all
            eight baselines (paired bootstrap, 10,000 resamples). It does not
            have the best ranking scores (PR-AUC and ROC-AUC); its advantage is
            better final decisions at the chosen threshold. On a second dataset
            (Kaggle Phishing Site URLs) it reached F1 0.9232. The deployed model
            scores slightly differently from the table (precision 0.9232, recall
            0.9117, F1 0.9174, accuracy 0.9545).
          </p>
        </section>

        <section className="mb-8 bg-amber-50 border border-amber-200 rounded-xl px-5 py-4">
          <h2 className="font-semibold text-sm text-amber-900 mb-1.5">
            Limitations
          </h2>
          <p className="text-amber-800 text-sm leading-relaxed">
            The model judges only the URL text; it cannot see page content,
            domain age, ownership or reputation lists, so a clean-looking
            address on a malicious site can pass. It was trained and tested on
            one public dataset at a fixed point in time, and its accuracy on
            future attack styles or other data sources has not been measured. In
            this app, that shows up as ordinary modern sites, even well-known
            ones, often scored as Unsafe, because the training data
            under-represents them. Other noted limits: a single BERT training
            run, and fusion cross-validation that was row-based, not
            domain-based. Its confidence is a model score, not a calibrated
            probability, so treat borderline results with caution.
          </p>
        </section>

        <section>
          <h2 className={h2}>Reference</h2>
          <p className={p}>
            Nepal, U. and Bose, S. (2026) ‘TURL-MV-LeafFuse: Multi-View Fusion
            with Tree-Leaf Features for Malicious URL Detection’. Submitted;
            under review.
          </p>
        </section>
      </div>
    </main>
  );
}

function DashboardScreen({ token }) {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiHistory(token)
      .then(setHistory)
      .catch((err) => setError(err.message));
  }, [token]);

  const totalChecks = history?.length || 0;
  const unsafeCount =
    history?.filter((h) => h.verdict === "unsafe").length || 0;

  return (
    <main className="flex-1 px-5 py-14">
      <div className="max-w-3xl mx-auto">
        <p className="font-mono text-xs uppercase tracking-wider text-teal-700 mb-1.5">
          Your account
        </p>
        <h1 className="font-semibold text-3xl tracking-tight text-slate-900 mb-6">
          Dashboard
        </h1>

        <div className="grid grid-cols-2 gap-3 mb-8 max-w-sm">
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
            <p className="font-mono text-2xl font-bold text-slate-900">
              {totalChecks}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Total checks</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
            <p className="font-mono text-2xl font-bold text-red-600">
              {unsafeCount}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Flagged unsafe</p>
          </div>
        </div>

        <h2 className="font-semibold text-lg text-slate-900 mb-3">
          Recent checks
        </h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {!error && history === null && (
          <p className="text-slate-500 text-sm">Loading…</p>
        )}

        {!error && history?.length === 0 && (
          <p className="text-slate-500 text-sm">
            No checks yet — head to the checker and try a link.
          </p>
        )}

        {!error && history?.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            {history.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between gap-4 px-4 py-3 border-b border-slate-100 last:border-0"
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm text-slate-800 truncate">
                    {h.url}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(h.created_at).toLocaleString()} · {h.model}
                  </p>
                </div>
                <span
                  className={
                    "shrink-0 font-mono text-xs font-bold px-2.5 py-1 rounded-full " +
                    (h.verdict === "safe"
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-red-50 text-red-700")
                  }
                >
                  {h.verdict.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function SignUpScreen({ goSignin, onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!email.includes("@") || password.length < 8 || password !== password2) {
      setError(
        "Check that your email is valid and both passwords match (min 8 characters).",
      );
      return;
    }
    setLoading(true);
    try {
      const data = await apiSignup(email, password);
      onLoginSuccess(data.access_token, data.email);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      eyebrow="Get started"
      title="Create an account"
      sub="Save your check history and revisit past results."
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2 mb-4">
            {error}
          </div>
        )}
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          label="Password"
          type="password"
          hint="Use at least 8 characters."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Field
          label="Re-enter password"
          type="password"
          value={password2}
          onChange={(e) => setPassword2(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-slate-900 text-white font-semibold text-sm py-2.5 rounded-lg mt-1 disabled:opacity-60"
        >
          {loading ? "Creating account…" : "Sign up"}
        </button>
      </form>
      <p className="text-center text-sm text-slate-500 mt-5">
        Already have an account?{" "}
        <a
          onClick={goSignin}
          className="text-teal-700 font-semibold cursor-pointer hover:underline"
        >
          Sign in
        </a>
      </p>
    </AuthCard>
  );
}

export default function SafeBrowseApp() {
  const [screen, setScreen] = useState("checker");
  const [dark, setDark] = useState(false);
  const [token, setToken] = useState(null);
  const [userEmail, setUserEmail] = useState(null);

  // Restore session on load, if there's a saved token from a previous visit.
  useEffect(() => {
    const savedToken = localStorage.getItem("safebrowse-token");
    const savedEmail = localStorage.getItem("safebrowse-email");
    if (savedToken && savedEmail) {
      setToken(savedToken);
      setUserEmail(savedEmail);
    }
  }, []);

  function handleLoginSuccess(newToken, email) {
    setToken(newToken);
    setUserEmail(email);
    localStorage.setItem("safebrowse-token", newToken);
    localStorage.setItem("safebrowse-email", email);
    setScreen("checker");
  }

  function handleLogout() {
    setToken(null);
    setUserEmail(null);
    localStorage.removeItem("safebrowse-token");
    localStorage.removeItem("safebrowse-email");
    setScreen("checker");
  }

  return (
    <div
      className={
        "min-h-screen flex flex-col " + (dark ? "bg-slate-950" : "bg-slate-50")
      }
    >
      <Navbar
        dark={dark}
        setDark={setDark}
        onAccountClick={() => setScreen("signin")}
        onLogoClick={() => setScreen("checker")}
        userEmail={userEmail}
        onDashboardClick={() => setScreen("dashboard")}
        onLogout={handleLogout}
      />
      {screen === "checker" && <CheckerScreen token={token} />}
      {screen === "signin" && (
        <SignInScreen
          goSignup={() => setScreen("signup")}
          onLoginSuccess={handleLoginSuccess}
        />
      )}
      {screen === "signup" && (
        <SignUpScreen
          goSignin={() => setScreen("signin")}
          onLoginSuccess={handleLoginSuccess}
        />
      )}
      {screen === "about" && (
        <AboutScreen onModelClick={() => setScreen("model")} />
      )}
      {screen === "model" && <ModelScreen onBack={() => setScreen("about")} />}
      {screen === "dashboard" &&
        (token ? (
          <DashboardScreen token={token} />
        ) : (
          <SignInScreen
            goSignup={() => setScreen("signup")}
            onLoginSuccess={handleLoginSuccess}
          />
        ))}
      <footer className="text-center py-5 text-xs text-slate-500">
        SafeBrowse — a phishing detection prototype. Verdicts are guidance, not
        a guarantee.{" "}
        <button
          onClick={() => setScreen("about")}
          className="text-teal-700 font-semibold hover:underline"
        >
          About this model
        </button>
      </footer>
    </div>
  );
}
