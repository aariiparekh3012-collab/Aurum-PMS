import { useState } from "react";

export default function FieldError({ error }: { error?: string }) {
  const [show, setShow] = useState(false);
  if (!error) return null;
  return (
    <div style={{ position: "relative", marginTop: 4 }}>
      <p
        className="error-text"
        style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4 }}
        onClick={() => setShow(!show)}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 16, height: 16, borderRadius: "50%",
          background: "var(--danger, #e24b4a)", color: "#fff",
          fontSize: 11, fontWeight: 700, flexShrink: 0,
        }}>!</span>
        {error}
      </p>
      {show && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: 0,
          background: "var(--bg-primary, #fff)", border: "1px solid var(--border, #ddd)",
          borderRadius: 8, padding: "10px 14px", fontSize: 13,
          color: "var(--text, #333)", boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
          zIndex: 100, maxWidth: 320, lineHeight: 1.5,
        }}>
          <div style={{ fontWeight: 600, color: "var(--danger, #e24b4a)", marginBottom: 4 }}>
            {"What's wrong?"}
          </div>
          <div>{getHelpText(error)}</div>
          <div
            style={{
              position: "absolute", bottom: -6, left: 16,
              width: 12, height: 12, background: "var(--bg-primary, #fff)",
              border: "1px solid var(--border, #ddd)", borderTop: "none", borderLeft: "none",
              transform: "rotate(45deg)",
            }}
          />
        </div>
      )}
    </div>
  );
}

function getHelpText(error: string): string {
  const lower = error.toLowerCase();
  if (lower.includes("pan"))
    return "PAN must be exactly 10 characters: 5 uppercase letters, 4 digits, 1 uppercase letter. Example: ABCDE1234F. The 4th letter indicates holder type (P = Individual).";
  if (lower.includes("email"))
    return "Enter a valid email address like name@company.com. Check for typos, missing @ symbol, or spaces.";
  if (lower.includes("mobile") || lower.includes("phone"))
    return "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9. Don't include country code or spaces.";
  if (lower.includes("aadhaar"))
    return "Aadhaar must be exactly 12 digits, starting with 2-9. Don't include spaces or dashes.";
  if (lower.includes("ifsc"))
    return "IFSC is 11 characters: 4 uppercase letters, then 0, then 6 alphanumeric characters. Example: HDFC0001234.";
  if (lower.includes("investment") || lower.includes("50"))
    return "SEBI mandates a minimum PMS investment of ₹50,00,000 (50 lakh). Enter the amount in rupees without commas.";
  if (lower.includes("bo id") || lower.includes("demat"))
    return "NSDL BO ID starts with 'IN' followed by 14 digits. CDSL BO ID is 16 digits. Check your demat account statement.";
  if (lower.includes("password"))
    return "Password must be at least 8 characters. Use a mix of letters, numbers, and symbols for better security.";
  if (lower.includes("name"))
    return "Enter your full legal name as it appears on your PAN card. Minimum 2 characters.";
  return error;
}
