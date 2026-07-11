import { useState } from "react";
import { Search, Moon, Sun, User, Check, X, Shield } from "lucide-react";

const STAT_MODELS = [
  { key: "rf", label: "Random Forest" },
  { key: "xgb", label: "XGBoost" },
  { key: "lr", label: "Logistic Regression" },
  { key: "dt", label: "Decision Tree" },
  { key: "svm", label: "SVM" },
  { key: "nb", label: "Naive Bayes" },
];
const DL_MODELS = [
  { key: "mlp", label: "MLP" },
  { key: "cnn", label: "CNN" },
  { key: "lstm", label: "LSTM" },
  { key: "bilstm", label: "BiLSTM" },
  { key: "gru", label: "GRU" },
  { key: "cnnbilstm", label: "CNN-BiLSTM" },
];
const TRANSFORMER_MODELS = [
  { key: "bert", label: "BERT-base-uncased" },
  { key: "distilbert", label: "DistilBERT" },
  { key: "roberta", label: "RoBERTa" },
  { key: "albert", label: "ALBERT" },
];

// Points at your local FastAPI backend. When you deploy, change this to
// your real backend URL (e.g. via an environment variable).
const API_BASE_URL = "http://localhost:8000";

async function checkUrl(url, model) {
  const res = await fetch(`${API_BASE_URL}/api/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, model }),
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

function Navbar({ dark, setDark, onAccountClick, onLogoClick }) {
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
        <button
          onClick={onAccountClick}
          className="w-9 h-9 rounded-full border border-slate-200 grid place-items-center text-slate-500 hover:border-teal-500 hover:text-teal-700"
        >
          <User size={16} />
        </button>
      </div>
    </header>
  );
}

function ModelChip({ active, label, onClick, disabled }) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={disabled ? "Coming soon" : undefined}
      className={
        "font-mono text-xs px-3 py-1.5 rounded-full border transition " +
        (disabled
          ? "bg-transparent text-slate-300 border-slate-100 cursor-not-allowed"
          : active
            ? "bg-slate-900 text-white border-slate-900"
            : "bg-transparent text-slate-500 border-slate-200 hover:text-slate-900 hover:border-teal-500")
      }
    >
      {label}
    </button>
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
        Confidence reflects model certainty on a balanced test set, not
        real-world URL prevalence.
      </p>
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

function CheckerScreen() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState("default");
  const [activeModel, setActiveModel] = useState("default");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const allModels = [...STAT_MODELS, ...DL_MODELS, ...TRANSFORMER_MODELS];
  const modelLabel = (key) =>
    key === "default"
      ? "Default (Hybrid)"
      : allModels.find((m) => m.key === key)?.label || "Default";

  function handleModeChange(next) {
    setMode(next);
    if (next === "experiment" && activeModel === "default") {
      setActiveModel(STAT_MODELS[0].key);
    } else if (next === "default") {
      setActiveModel("default");
    }
  }

  async function handleCheck() {
    if (!url.trim()) return;
    setResult(null);
    setErrorMsg(null);
    setScanning(true);
    try {
      const data = await checkUrl(url, activeModel);
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
        SafeBrowse checks the URL against trained detection models and explains
        exactly why it's safe or not — no account needed.
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

        <div className="inline-flex gap-0.5 p-0.5 mt-3 ml-1.5 bg-slate-50 border border-slate-200 rounded-full">
          <button
            onClick={() => handleModeChange("default")}
            className={
              "font-semibold text-sm px-4 py-1.5 rounded-full " +
              (mode === "default"
                ? "bg-slate-900 text-white"
                : "text-slate-500 hover:text-slate-900")
            }
          >
            Default
          </button>
          <button
            onClick={() => handleModeChange("experiment")}
            className={
              "font-semibold text-sm px-4 py-1.5 rounded-full " +
              (mode === "experiment"
                ? "bg-slate-900 text-white"
                : "text-slate-500 hover:text-slate-900")
            }
          >
            Experiment
          </button>
        </div>
        <p className="text-xs text-slate-500 px-2.5 pt-2">
          {mode === "default"
            ? "Default gives the clearest result for most people, using the hybrid model."
            : "Pick one model below to see how it scores this link on its own."}
        </p>

        {mode === "experiment" && (
          <div className="flex flex-col gap-3 px-1.5 pt-2 pb-1">
            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-teal-700 mb-1.5">
                Statistical
              </p>
              <div className="flex flex-wrap gap-1.5">
                {STAT_MODELS.map((m) => (
                  <ModelChip
                    key={m.key}
                    label={m.label}
                    active={activeModel === m.key}
                    onClick={() => setActiveModel(m.key)}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-1.5">
                Deep Learning{" "}
                <span className="normal-case text-slate-300">
                  — coming soon
                </span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {DL_MODELS.map((m) => (
                  <ModelChip key={m.key} label={m.label} disabled />
                ))}
              </div>
            </div>
            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-slate-400 mb-1.5">
                Transformer{" "}
                <span className="normal-case text-slate-300">
                  — coming soon
                </span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {TRANSFORMER_MODELS.map((m) => (
                  <ModelChip key={m.key} label={m.label} disabled />
                ))}
              </div>
            </div>
          </div>
        )}

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
          model={modelLabel(activeModel)}
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

function Field({ label, type = "text", hint }) {
  return (
    <div className="mb-4 text-left">
      <label className="block text-sm font-semibold mb-1.5 text-slate-900">
        {label}
      </label>
      <input
        type={type}
        placeholder={type === "password" ? "••••••••" : "you@example.com"}
        className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-sm focus:border-teal-500 focus:bg-white outline-none"
      />
      {hint && <p className="text-xs text-slate-500 mt-1.5">{hint}</p>}
    </div>
  );
}

function SignInScreen({ goSignup }) {
  return (
    <AuthCard
      eyebrow="Welcome back"
      title="Sign in"
      sub="Check your history and saved results."
    >
      <Field label="Email" type="email" />
      <Field label="Password" type="password" />
      <button className="w-full bg-slate-900 text-white font-semibold text-sm py-2.5 rounded-lg mt-1">
        Sign in
      </button>
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

const HYBRID_STATS = [
  { label: "Accuracy", value: "98.01%" },
  { label: "Precision", value: "98.06%" },
  { label: "Recall", value: "97.96%" },
  { label: "F1-Score", value: "0.9801" },
  { label: "ROC-AUC", value: "0.9953" },
];

function AboutScreen() {
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
          <h2 className="font-semibold text-lg text-slate-900 mb-2">Dataset</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Models are trained on the{" "}
            <a
              href="https://www.kaggle.com/datasets/marryjanety/phishing-url-dataset-url-and-label"
              target="_blank"
              rel="noopener noreferrer"
              className="text-teal-700 font-semibold hover:underline"
            >
              Kaggle Malicious URL Dataset
            </a>{" "}
            — 651,191 URLs originally labeled across four categories (benign,
            phishing, malware, defacement). For this app,
            phishing/malware/defacement were collapsed into a single "Unsafe"
            label against "Safe" (benign), since that's the decision a user
            actually needs.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="font-semibold text-lg text-slate-900 mb-2">
            Default (hybrid) model — reported performance
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed mb-4">
            Measured on a held-out, class-balanced 10,000-URL test set during
            training.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {HYBRID_STATS.map((s) => (
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

        <section className="mb-8 bg-amber-50 border border-amber-200 rounded-xl px-5 py-4">
          <h2 className="font-semibold text-sm text-amber-900 mb-1.5">
            A note on confidence scores
          </h2>
          <p className="text-amber-800 text-sm leading-relaxed">
            The model above was trained and evaluated on a{" "}
            <strong>class-balanced</strong> dataset (50% Safe / 50% Unsafe)
            specifically for fair comparison across models during research. That
            means confidence scores reflect the model's certainty under that
            balanced setup — not a calibrated real-world probability, since the
            vast majority of URLs encountered day-to-day are actually safe.
            Treat the confidence score as a relative signal, not a literal "X%
            chance this is dangerous."
          </p>
        </section>

        <section>
          <h2 className="font-semibold text-lg text-slate-900 mb-2">
            Experiment models
          </h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            The Statistical, Deep Learning, and Transformer models under
            "Experiment" are trained separately on the same dataset, for
            comparing how different modeling approaches score the same link.
            They're for exploration — Default (hybrid) is the recommended model
            for everyday use.
          </p>
        </section>
      </div>
    </main>
  );
}

function SignUpScreen({ goSignin }) {
  return (
    <AuthCard
      eyebrow="Get started"
      title="Create an account"
      sub="Save your check history and revisit past results."
    >
      <Field label="Email" type="email" />
      <Field
        label="Password"
        type="password"
        hint="Use at least 8 characters."
      />
      <Field label="Re-enter password" type="password" />
      <button className="w-full bg-slate-900 text-white font-semibold text-sm py-2.5 rounded-lg mt-1">
        Sign up
      </button>
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
      />
      {screen === "checker" && <CheckerScreen />}
      {screen === "signin" && (
        <SignInScreen goSignup={() => setScreen("signup")} />
      )}
      {screen === "signup" && (
        <SignUpScreen goSignin={() => setScreen("signin")} />
      )}
      {screen === "about" && <AboutScreen />}
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
