export function DataDeletionPage() {
  return (
    <div style={{ maxWidth: 800, margin: "40px auto", padding: "0 24px", fontFamily: "system-ui, sans-serif", color: "#333", lineHeight: 1.7 }}>
      <h1 style={{ fontSize: "2rem", marginBottom: 8 }}>User Data Deletion</h1>
      <p style={{ color: "#666", marginBottom: 32 }}>How to request deletion of your data</p>

      <h2>Request Data Deletion</h2>
      <p>
        You can request deletion of your personal data from Aurum PMS at any time.
        We will process your request within 30 days, subject to any regulatory retention
        requirements mandated by SEBI.
      </p>

      <h2>How to Submit a Request</h2>
      <p>Send an email to <strong>privacy@aurumpms.com</strong> with the following information:</p>
      <ul style={{ paddingLeft: 24 }}>
        <li>Subject line: "Data Deletion Request"</li>
        <li>Your registered email address</li>
        <li>Your full name as registered on the platform</li>
        <li>Reason for deletion (optional)</li>
      </ul>

      <h2>What Gets Deleted</h2>
      <p>Upon processing your request, we will delete:</p>
      <ul style={{ paddingLeft: 24 }}>
        <li>Your account credentials and profile information</li>
        <li>Phone number and WhatsApp messaging data</li>
        <li>Session tokens and login history</li>
        <li>Platform usage data and preferences</li>
      </ul>

      <h2>What We Must Retain</h2>
      <p>
        Under SEBI regulations, certain records must be retained for a minimum of 5 years
        after account closure. This includes:
      </p>
      <ul style={{ paddingLeft: 24 }}>
        <li>KYC documents (PAN, identity verification records)</li>
        <li>Transaction and portfolio records</li>
        <li>Audit trail and compliance records</li>
      </ul>
      <p>
        These records are retained in encrypted form and are only accessible for regulatory
        compliance purposes. They will be permanently deleted after the retention period expires.
      </p>

      <h2>Confirmation</h2>
      <p>
        You will receive an email confirmation once your data deletion request has been
        processed. If you have any questions, contact us at privacy@aurumpms.com.
      </p>

      <div style={{ marginTop: 48, padding: "16px 0", borderTop: "1px solid #eee", fontSize: "0.85rem", color: "#999" }}>
        <a href="/privacy" style={{ color: "#b8860b" }}>Privacy Policy</a>
        {" | "}
        <a href="/login" style={{ color: "#b8860b" }}>Back to Aurum PMS</a>
      </div>
    </div>
  );
}
