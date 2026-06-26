import { useState, type ChangeEvent, type FormEvent } from "react";
import { personalDetailsSchema } from "../validation";
import { useCreateApplication } from "../hooks/useOnboarding";
import FieldError from "@/components/ui/FieldError";
import type { ApplicationResponse } from "../types";

const COUNTRY_CODES = [
  { code: "+91", label: "IN +91", flag: "\u{1F1EE}\u{1F1F3}" },
  { code: "+1", label: "US +1", flag: "\u{1F1FA}\u{1F1F8}" },
] as const;

interface Props { onComplete: (app: ApplicationResponse) => void }

export default function PersonalDetailsStep({ onComplete }: Props) {
  const [form, setForm] = useState({
    investor_type: "individual", full_name: "", email: "", mobile: "", pan: "",
    proposed_investment_inr: 5_000_000,
  });
  const [countryCode, setCountryCode] = useState("+91");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const mutation = useCreateApplication();

  const set = (field: string) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    let val: string | number = e.target.value;
    if (field === "proposed_investment_inr") val = Number(val);
    else if (field === "pan") val = (val as string).toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10);
    else if (field === "mobile") val = (val as string).replace(/\D/g, "").slice(0, 10);
    setForm((p) => ({ ...p, [field]: val }));
    setErrors((p) => ({ ...p, [field]: "" }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const parsed = personalDetailsSchema.safeParse(form);
    if (!parsed.success) {
      const fe: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { fe[String(i.path[0])] = i.message; });
      setErrors(fe);
      return;
    }
    mutation.mutate(form, {
      onSuccess: onComplete,
      onError: (err: any) => setErrors({ _form: err.message }),
    });
  };

  const g = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 } as const;

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ marginBottom: 20 }}>Personal Details</h3>
      <div style={g}>
        <div>
          <label>Investor Type</label>
          <select value={form.investor_type} onChange={set("investor_type")}>
            <option value="individual">Individual</option>
            <option value="huf">HUF</option>
            <option value="nri">NRI</option>
            <option value="corporate">Corporate</option>
            <option value="partnership">Partnership</option>
            <option value="trust">Trust</option>
          </select>
        </div>
        <div>
          <label>Full Name</label>
          <input value={form.full_name} onChange={set("full_name")} placeholder="As on PAN card" />
          <FieldError error={errors.full_name} />
        </div>
        <div>
          <label>Email</label>
          <input type="email" value={form.email} onChange={set("email")} placeholder="you@example.com" />
          <FieldError error={errors.email} />
        </div>
        <div>
          <label>Mobile</label>
          <div style={{ display: "flex", gap: 8 }}>
            <select
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              style={{ width: 110, flexShrink: 0 }}
            >
              {COUNTRY_CODES.map((c) => (
                <option key={c.code} value={c.code}>{c.flag} {c.label}</option>
              ))}
            </select>
            <input
              value={form.mobile}
              onChange={set("mobile")}
              placeholder="9876543210"
              maxLength={10}
              style={{ flex: 1 }}
            />
          </div>
          <FieldError error={errors.mobile} />
        </div>
        <div>
          <label>PAN</label>
          <input value={form.pan} onChange={set("pan")} placeholder="ABCDE1234F" maxLength={10} style={{ textTransform: "uppercase" }} />
          <FieldError error={errors.pan} />
        </div>
        <div>
          <label>Proposed Investment (INR)</label>
          <input type="number" value={form.proposed_investment_inr} onChange={set("proposed_investment_inr")} min={5000000} step={100000} />
          <FieldError error={errors.proposed_investment_inr} />
        </div>
      </div>
      {errors._form && <p className="error-text" style={{ marginTop: 12 }}>{errors._form}</p>}
      <div style={{ marginTop: 24, textAlign: "right" }}>
        <button className="btn btn-primary" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Submitting..." : "Continue to KYC"}
        </button>
      </div>
    </form>
  );
}
