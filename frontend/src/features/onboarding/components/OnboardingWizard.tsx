import { useState } from "react";
import Stepper from "@/components/ui/Stepper";
import PersonalDetailsStep from "./PersonalDetailsStep";
import KycStep from "./KycStep";
import DocumentUploadStep from "./DocumentUploadStep";
import RiskProfileStep from "./RiskProfileStep";
import AgreementStep from "./AgreementStep";
import type { ApplicationResponse, OnboardingStep } from "../types";

const STEPS = [
  { label: "Personal Details", key: "personal" },
  { label: "KYC Verification", key: "kyc" },
  { label: "Documents", key: "documents" },
  { label: "Risk Profile", key: "risk" },
  { label: "Agreement", key: "agreement" },
];

export default function OnboardingWizard() {
  const [step, setStep] = useState<OnboardingStep>("personal");
  const [application, setApplication] = useState<ApplicationResponse | null>(null);

  const handleCreated = (app: ApplicationResponse) => {
    setApplication(app);
    setStep("kyc");
  };

  const handleKycDone = (app: ApplicationResponse) => {
    setApplication(app);
    if (app.status === "kyc_rejected") return; // stay on KYC step to show error
    setStep("documents");
  };

  const handleDocsDone = () => {
    setStep("risk");
  };

  const handleRiskDone = (app: ApplicationResponse) => {
    setApplication(app);
    setStep("agreement");
  };

  const handleEsignDone = (app: ApplicationResponse) => {
    setApplication(app);
    setStep("done");
  };

  if (step === "done") {
    return (
      <div className="card" style={{ textAlign: "center", padding: 48 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
        <h2 style={{ marginBottom: 8 }}>Application Submitted</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
          Your application is now under compliance review. You'll be notified once approved.
        </p>
        <p style={{ fontSize: 14 }}>
          Application ID: <code>{application?.id}</code>
        </p>
        <p style={{ fontSize: 14 }}>
          Status: <span className="badge badge-pending">{application?.status}</span>
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Client Onboarding</h1>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
        Complete each step to open your PMS account
      </p>
      <Stepper steps={STEPS} current={step} />
      <div className="card">
        {step === "personal" && <PersonalDetailsStep onComplete={handleCreated} />}
        {step === "kyc" && application && <KycStep applicationId={application.id} onComplete={handleKycDone} />}
        {step === "documents" && application && <DocumentUploadStep applicationId={application.id} onComplete={handleDocsDone} />}
        {step === "risk" && application && <RiskProfileStep applicationId={application.id} onComplete={handleRiskDone} />}
        {step === "agreement" && application && <AgreementStep applicationId={application.id} onComplete={handleEsignDone} />}
      </div>
    </div>
  );
}
