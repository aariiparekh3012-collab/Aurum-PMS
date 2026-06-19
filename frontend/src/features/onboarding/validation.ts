import { z } from "zod";

export const personalDetailsSchema = z.object({
  investor_type: z.enum(["individual", "huf", "nri", "corporate", "partnership", "trust"]),
  full_name: z.string().min(2, "Name must be at least 2 characters").max(200),
  email: z.string().email("Invalid email address"),
  mobile: z.string().regex(/^[6-9]\d{9}$/, "Must be a valid 10-digit Indian mobile number"),
  pan: z.string().regex(/^[A-Z]{5}[0-9]{4}[A-Z]$/, "Invalid PAN format (e.g. ABCDE1234F)"),
  proposed_investment_inr: z.number().min(5_000_000, "Minimum investment is ₹50,00,000"),
});

export const kycDetailsSchema = z.object({
  aadhaar_full: z.string().regex(/^[2-9]\d{11}$/, "Must be a valid 12-digit Aadhaar number"),
  bank_account_number: z.string().regex(/^\d{8,18}$/, "Account number must be 8-18 digits"),
  bank_ifsc: z.string().regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, "Invalid IFSC code"),
  bank_holder_name: z.string().min(2, "Name required"),
  // NSDL: "IN" + 14 digits; CDSL: 16 digits
  demat_bo_id: z.string().regex(/^(IN\d{14}|\d{16})$/, "Must be a valid NSDL (IN + 14 digits) or CDSL (16 digits) BO ID"),
  demat_depository: z.enum(["NSDL", "CDSL"]),
});

export const riskAnswerSchema = z.object({
  question_id: z.string(),
  weight: z.number().min(1).max(5),
});

export type PersonalDetailsForm = z.infer<typeof personalDetailsSchema>;
export type KycDetailsForm = z.infer<typeof kycDetailsSchema>;

// ── Formatting utilities used by step components ──────────────────────────

/** Strip all non-digit characters. */
export const digitsOnly = (v: string) => v.replace(/\D/g, "");

/** Format a number as Indian-locale rupee string (e.g. 5000000 → "50,00,000"). */
export const formatINR = (n: number) =>
  new Intl.NumberFormat("en-IN").format(n);

/** Uppercase and strip non-alphanumeric chars, max 10. */
export const formatPAN = (v: string) =>
  v.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10);

/** Keep only digits, max 10 characters. */
export const formatMobile = (v: string) => digitsOnly(v).slice(0, 10);

/** Format Aadhaar as 4-4-4 groups of digits. */
export const formatAadhaar = (v: string) => {
  const d = digitsOnly(v).slice(0, 12);
  return d.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
};

/** Uppercase IFSC, max 11 chars. */
export const formatIFSC = (v: string) =>
  v.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 11);

/** Digits only, max 18 characters. */
export const formatBankAccount = (v: string) => digitsOnly(v).slice(0, 18);

/** NSDL BO ID: "IN" + up to 14 digits. */
export const formatNSDLBoId = (v: string): string => {
  const upper = v.toUpperCase().replace(/[^IN0-9]/g, "");
  if (!upper.startsWith("IN")) return "IN" + digitsOnly(upper).slice(0, 14);
  return "IN" + digitsOnly(upper.slice(2)).slice(0, 14);
};

/** CDSL BO ID: 16 digits. */
export const formatCDSLBoId = (v: string) => digitsOnly(v).slice(0, 16);
