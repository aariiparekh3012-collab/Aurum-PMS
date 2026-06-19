import { useState, type ChangeEvent, type FormEvent } from "react";
import { kycDetailsSchema } from "../validation";
import { useSubmitKyc } from "../hooks/useOnboarding";
import FieldError from "@/components/ui/FieldError";
import type { ApplicationResponse } from "../types";

interface Props { applicationId: string; onComplete: (app: ApplicationResponse) => void }

export default function KycStep({ applicationId, onComplete }: Props) {
  const [form, setForm] = useState({
    aadhaar_full: "", bank_account_number: "", bank_ifsc: "",
    bank_holder_name: "", demat_bo_id: "", demat_depository: "NSDL",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const mutation = useSubmitKyc(applicationId);

  const set = (field: string) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((p) => ({ ...p, [field]: e.target.value }));
    setErrors((p) => ({ ...p, [field]: "" }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const parsed = kycDetailsSchema.safeParse(form);
    if (!parsed.success) {
      const fe: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { fe[String(i.path[0])] = i.message; });
      setErrors(fe);
      return;
    }
    mutation.mutate(form, {
      onSuccess: (app) => {
        if (app.status === "kyc_rejected") {
          setErrors({ _form: "KYC verification failed. Please check your details and try again." });
        } else {
          onComplete(app);
        }
      },
      onError: (err: any) => setErrors({ _form: err.message }),
    });
  };

  const g = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 } as const;

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ marginBottom: 20 }}>KYC Verification</h3>
      <div style={g}>
        <div style={{ gridColumn: "1 / -1" }}>
          <label>Aadhaar Number</label>
          <input value={form.aadhaar_full} onChange={set("aadhaar_full")} placeholder="12-digit Aadhaar" maxLength={12} />
          <FieldError error={errors.aadhaar_full} />
        </div>
        <div>
          <label>Bank Account Number</label>
          <input value={form.bank_account_number} onChange={set("bank_account_number")} placeholder="Account number" />
          <FieldError error={errors.bank_account_number} />
        </div>
        <div>
          <label>IFSC Code</label>
          <input value={form.bank_ifsc} onChange={set("bank_ifsc")} placeholder="HDFC0001234" maxLength={11} style={{ textTransform: "uppercase" }} />
          <FieldError error={errors.bank_ifsc} />
        </div>
        <div>
          <label>Account Holder Name</label>
          <input value={form.bank_holder_name} onChange={set("bank_holder_name")} placeholder="As on bank records" />
          <FieldError error={errors.bank_holder_name} />
        </div>
        <div>
          <label>Demat BO ID</label>
          <input value={form.demat_bo_id} onChange={set("demat_bo_id")} placeholder="16-digit BO ID" maxLength={16} />
          <FieldError error={errors.demat_bo_id} />
        </div>
        <div>
          <label>Depository</label>
          <select value={form.demat_depository} onChange={set("demat_depository")}>
            <option value="NSDL">NSDL</option>
            <option value="CDSL">CDSL</option>
          </select>
        </div>
      </div>
      {errors._form && <p className="error-text" style={{ marginTop: 12 }}>{errors._form}</p>}
      <div style={{ marginTop: 24, textAlign: "right" }}>
        <button className="btn btn-primary" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Verifying..." : "Verify & Continue"}
        </button>
      </div>
    </form>
  );
}
