export function PrivacyPolicyPage() {
  return (
    <div style={{ maxWidth: 800, margin: "40px auto", padding: "0 24px", fontFamily: "system-ui, sans-serif", color: "#333", lineHeight: 1.7 }}>
      <h1 style={{ fontSize: "2rem", marginBottom: 8 }}>Privacy Policy</h1>
      <p style={{ color: "#666", marginBottom: 32 }}>Last updated: June 2026</p>

      <p>
        Aurum PMS ("we", "our", "us") operates the Aurum PMS platform, a SEBI-registered
        Discretionary Portfolio Management Service. This Privacy Policy explains how we collect,
        use, disclose, and safeguard your information when you use our platform.
      </p>

      <h2>1. Information We Collect</h2>
      <p>
        We collect information you provide directly: full name, email address, phone number,
        PAN, Aadhaar number, bank account details, demat account details, and investment
        preferences. We also collect usage data such as IP address, browser type, pages visited,
        and timestamps for security and analytics purposes.
      </p>

      <h2>2. How We Use Your Information</h2>
      <p>
        We use your information to provide portfolio management services, complete KYC verification
        as required by SEBI, send transactional communications (OTP codes, account notifications,
        portfolio reports), comply with regulatory obligations, and improve our platform.
      </p>

      <h2>3. Data Protection</h2>
      <p>
        Sensitive personal information (PAN, Aadhaar, bank details) is encrypted at rest using
        industry-standard Fernet symmetric encryption. Passwords are hashed using PBKDF2-SHA256
        with 200,000 iterations. All data is transmitted over TLS-encrypted connections.
      </p>

      <h2>4. Third-Party Services</h2>
      <p>
        We use the following third-party services to operate our platform:
        WhatsApp Business API (Meta) for OTP delivery, Gmail SMTP for email communications,
        and KYC verification providers as mandated by SEBI. These services process your data
        only as necessary to provide their specific function.
      </p>

      <h2>5. Data Retention</h2>
      <p>
        We retain your account data for as long as your account is active and for the period
        required by SEBI regulations (currently 5 years after account closure). You may request
        deletion of your data at any time, subject to regulatory retention requirements.
      </p>

      <h2>6. Your Rights</h2>
      <p>
        You have the right to access, correct, or delete your personal data. You may also
        withdraw consent for non-essential data processing. To exercise these rights, contact
        us at privacy@aurumpms.com or visit our{" "}
        <a href="/data-deletion" style={{ color: "#b8860b" }}>Data Deletion page</a>.
      </p>

      <h2>7. Contact Us</h2>
      <p>
        If you have questions about this Privacy Policy, contact us at:<br />
        Email: privacy@aurumpms.com<br />
        Aurum Portfolio Management Services
      </p>

      <div style={{ marginTop: 48, padding: "16px 0", borderTop: "1px solid #eee", fontSize: "0.85rem", color: "#999" }}>
        <a href="/login" style={{ color: "#b8860b" }}>Back to Aurum PMS</a>
      </div>
    </div>
  );
}
