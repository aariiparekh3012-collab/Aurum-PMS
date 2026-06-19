import { useState } from "react";
import { useConfirmEsign } from "../hooks/useOnboarding";
import type { ApplicationResponse } from "../types";

interface Props { applicationId: string; onComplete: (app: ApplicationResponse) => void }

export default function AgreementStep({ applicationId, onComplete }: Props) {
  const [agreed, setAgreed] = useState(false);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState("");
  const mutation = useConfirmEsign(applicationId);

  const handleSign = () => {
    setSigning(true);
    setError("");
    // In production, this would redirect to the Aadhaar eSign provider.
    // For dev/demo, we simulate it with a fake transaction ID after a delay.
    setTimeout(() => {
      const fakeTransactionId = `ESIGN-${Date.now()}`;
      mutation.mutate(fakeTransactionId, {
        onSuccess: onComplete,
        onError: (err: any) => { setError(err.message); setSigning(false); },
      });
    }, 1500);
  };

  return (
    <div>
      <h3 style={{ marginBottom: 20 }}>PMS Agreement</h3>
      <div style={{
        background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
        padding: 20, marginBottom: 20, maxHeight: 300, overflowY: "auto", fontSize: 14, lineHeight: 1.7,
      }}>
        <p style={{ fontWeight: 600, marginBottom: 12 }}>PORTFOLIO MANAGEMENT SERVICES AGREEMENT</p>
        <p style={{ marginBottom: 8 }}>
          This Agreement is entered into between the Client and the Portfolio Manager in accordance
          with SEBI (Portfolio Managers) Regulations, 2020 and Schedule IV thereof.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong>1. Services:</strong> The Portfolio Manager shall manage the Client's portfolio on a
          discretionary basis, making investment decisions in accordance with the agreed-upon strategy
          and risk profile.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong>2. Minimum Investment:</strong> The minimum investment amount shall be INR 50,00,000
          (Rupees Fifty Lakhs) as mandated by SEBI.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong>3. Fees:</strong> Management fees and performance fees shall be charged as per the
          fee schedule disclosed at the time of onboarding.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong>4. Risk Disclosure:</strong> Investment in securities is subject to market risks.
          Past performance does not guarantee future returns. The Client acknowledges understanding
          the risks involved.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong>5. Reporting:</strong> The Portfolio Manager shall provide periodic reports including
          monthly account statements and performance reports.
        </p>
        <p>
          <strong>6. Termination:</strong> Either party may terminate this agreement with 30 days written
          notice, subject to settlement of outstanding positions and fees.
        </p>
      </div>

      <label style={{
        display: "flex", alignItems: "center", gap: 10, marginBottom: 20,
        fontSize: 14, cursor: "pointer",
      }}>
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)}
          style={{ width: 18, height: 18, accentColor: "var(--primary)" }} />
        I have read and agree to the PMS Agreement terms and conditions
      </label>

      {error && <p className="error-text" style={{ marginBottom: 12 }}>{error}</p>}

      <div style={{ textAlign: "right" }}>
        <button className="btn btn-primary" onClick={handleSign} disabled={!agreed || signing || mutation.isPending}>
          {signing ? "Signing via Aadhaar eSign..." : "Sign Agreement (eSign)"}
        </button>
      </div>
    </div>
  );
}
