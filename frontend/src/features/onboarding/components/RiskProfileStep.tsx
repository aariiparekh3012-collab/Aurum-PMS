import { useState, type FormEvent } from "react";
import { useRiskProfile } from "../hooks/useOnboarding";
import type { ApplicationResponse, RiskAnswer } from "../types";

interface Props { applicationId: string; onComplete: (app: ApplicationResponse) => void }

const QUESTIONS = [
  { id: "q1", text: "What is your investment horizon?", options: [
    { label: "Less than 1 year", w: 1 }, { label: "1-3 years", w: 2 }, { label: "3-5 years", w: 3 },
    { label: "5-10 years", w: 4 }, { label: "10+ years", w: 5 },
  ]},
  { id: "q2", text: "How would you react to a 20% portfolio decline?", options: [
    { label: "Sell everything immediately", w: 1 }, { label: "Sell some holdings", w: 2 },
    { label: "Hold and wait", w: 3 }, { label: "Buy a little more", w: 4 }, { label: "Buy significantly more", w: 5 },
  ]},
  { id: "q3", text: "What portion of your net worth is this investment?", options: [
    { label: "More than 50%", w: 1 }, { label: "30-50%", w: 2 }, { label: "15-30%", w: 3 },
    { label: "5-15%", w: 4 }, { label: "Less than 5%", w: 5 },
  ]},
  { id: "q4", text: "What is your primary investment objective?", options: [
    { label: "Capital preservation", w: 1 }, { label: "Regular income", w: 2 },
    { label: "Balanced growth & income", w: 3 }, { label: "Capital appreciation", w: 4 },
    { label: "Aggressive growth", w: 5 },
  ]},
  { id: "q5", text: "What is your experience with equity markets?", options: [
    { label: "No experience", w: 1 }, { label: "Basic knowledge", w: 2 },
    { label: "Some trading experience", w: 3 }, { label: "Active investor", w: 4 },
    { label: "Professional / extensive", w: 5 },
  ]},
];

export default function RiskProfileStep({ applicationId, onComplete }: Props) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const mutation = useRiskProfile(applicationId);

  const allAnswered = Object.keys(answers).length === QUESTIONS.length;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!allAnswered) { setError("Please answer all questions"); return; }
    const payload: RiskAnswer[] = Object.entries(answers).map(([qid, w]) => ({
      question_id: qid, weight: w,
    }));
    mutation.mutate(payload, {
      onSuccess: onComplete,
      onError: (err: any) => setError(err.message),
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ marginBottom: 20 }}>Risk Suitability Questionnaire</h3>
      {QUESTIONS.map((q, qi) => (
        <div key={q.id} style={{ marginBottom: 24 }}>
          <p style={{ fontWeight: 500, marginBottom: 8 }}>{qi + 1}. {q.text}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {q.options.map((opt) => (
              <label key={opt.w} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
                borderRadius: "var(--radius)", border: "1px solid",
                borderColor: answers[q.id] === opt.w ? "var(--primary)" : "var(--border)",
                background: answers[q.id] === opt.w ? "var(--primary-light)" : "transparent",
                cursor: "pointer", fontSize: 14, transition: "all .15s",
              }}>
                <input type="radio" name={q.id} checked={answers[q.id] === opt.w}
                  onChange={() => setAnswers((p) => ({ ...p, [q.id]: opt.w }))}
                  style={{ accentColor: "var(--primary)" }} />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      ))}
      {error && <p className="error-text">{error}</p>}
      <div style={{ textAlign: "right" }}>
        <button className="btn btn-primary" type="submit" disabled={!allAnswered || mutation.isPending}>
          {mutation.isPending ? "Scoring..." : "Submit & Continue"}
        </button>
      </div>
    </form>
  );
}
