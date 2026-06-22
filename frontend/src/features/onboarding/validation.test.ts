/**
 * Tests for onboarding Zod schemas and formatting utilities.
 *
 * These validate the SEBI PMS business rules encoded in the client-side schemas:
 * PAN format, Aadhaar format, minimum investment, IFSC, demat BO IDs, etc.
 */
import { describe, expect, it } from "vitest";
import {
  personalDetailsSchema,
  kycDetailsSchema,
  digitsOnly,
  formatINR,
  formatPAN,
  formatMobile,
  formatAadhaar,
  formatIFSC,
  formatBankAccount,
  formatNSDLBoId,
  formatCDSLBoId,
} from "./validation";

// ── personalDetailsSchema ───────────────────────────────────────────────

const validPersonal = {
  investor_type: "individual" as const,
  full_name: "Asha Rao",
  email: "asha@example.com",
  mobile: "9876543210",
  pan: "ABCDE1234F",
  proposed_investment_inr: 5_000_000,
};

describe("personalDetailsSchema", () => {
  it("accepts valid input", () => {
    expect(personalDetailsSchema.safeParse(validPersonal).success).toBe(true);
  });

  it("rejects investment below SEBI ₹50L minimum", () => {
    const result = personalDetailsSchema.safeParse({
      ...validPersonal,
      proposed_investment_inr: 1_000_000,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toMatch(/50,00,000/);
    }
  });

  it("rejects invalid PAN format", () => {
    const cases = ["abcde1234f", "12345ABCDE", "ABC123", "ABCDE1234"];
    for (const pan of cases) {
      expect(
        personalDetailsSchema.safeParse({ ...validPersonal, pan }).success,
      ).toBe(false);
    }
  });

  it("accepts all valid PAN formats", () => {
    expect(
      personalDetailsSchema.safeParse({ ...validPersonal, pan: "ZZZZZ9999Z" }).success,
    ).toBe(true);
  });

  it("rejects invalid mobile numbers", () => {
    const cases = ["1234567890", "98765", "98765432101", "abcdefghij"];
    for (const mobile of cases) {
      expect(
        personalDetailsSchema.safeParse({ ...validPersonal, mobile }).success,
      ).toBe(false);
    }
  });

  it("rejects invalid investor types", () => {
    expect(
      personalDetailsSchema.safeParse({ ...validPersonal, investor_type: "llp" }).success,
    ).toBe(false);
  });

  it("accepts all valid investor types", () => {
    for (const t of ["individual", "huf", "nri", "corporate", "partnership", "trust"]) {
      expect(
        personalDetailsSchema.safeParse({ ...validPersonal, investor_type: t }).success,
      ).toBe(true);
    }
  });
});

// ── kycDetailsSchema ────────────────────────────────────────────────────

const validKyc = {
  aadhaar_full: "234567890123",
  bank_account_number: "12345678901234",
  bank_ifsc: "HDFC0001234",
  bank_holder_name: "Asha Rao",
  demat_bo_id: "1234567890123456",
  demat_depository: "CDSL" as const,
};

describe("kycDetailsSchema", () => {
  it("accepts valid KYC input", () => {
    expect(kycDetailsSchema.safeParse(validKyc).success).toBe(true);
  });

  it("rejects Aadhaar starting with 0 or 1", () => {
    expect(kycDetailsSchema.safeParse({ ...validKyc, aadhaar_full: "012345678901" }).success).toBe(false);
    expect(kycDetailsSchema.safeParse({ ...validKyc, aadhaar_full: "123456789012" }).success).toBe(false);
  });

  it("rejects Aadhaar with wrong length", () => {
    expect(kycDetailsSchema.safeParse({ ...validKyc, aadhaar_full: "23456789012" }).success).toBe(false);
    expect(kycDetailsSchema.safeParse({ ...validKyc, aadhaar_full: "2345678901234" }).success).toBe(false);
  });

  it("rejects invalid IFSC codes", () => {
    const bad = ["hdfc0001234", "HDFC1001234", "HDFC000123", "1234ABCDEFG"];
    for (const ifsc of bad) {
      expect(kycDetailsSchema.safeParse({ ...validKyc, bank_ifsc: ifsc }).success).toBe(false);
    }
  });

  it("accepts NSDL BO ID format", () => {
    const nsdl = { ...validKyc, demat_bo_id: "IN12345678901234", demat_depository: "NSDL" as const };
    expect(kycDetailsSchema.safeParse(nsdl).success).toBe(true);
  });

  it("rejects invalid depository values", () => {
    expect(kycDetailsSchema.safeParse({ ...validKyc, demat_depository: "BSE" }).success).toBe(false);
  });
});

// ── Formatting utilities ────────────────────────────────────────────────

describe("formatting utilities", () => {
  it("digitsOnly strips non-digits", () => {
    expect(digitsOnly("abc-123.45")).toBe("12345");
    expect(digitsOnly("")).toBe("");
  });

  it("formatINR formats as Indian locale", () => {
    expect(formatINR(5_000_000)).toBe("50,00,000");
    expect(formatINR(100)).toBe("100");
  });

  it("formatPAN uppercases and strips non-alphanumeric, max 10", () => {
    expect(formatPAN("abcde1234f")).toBe("ABCDE1234F");
    expect(formatPAN("AB-CD E1234FXX")).toBe("ABCDE1234F");
  });

  it("formatMobile keeps only digits, max 10", () => {
    expect(formatMobile("+91 98765-43210")).toBe("9198765432");
    expect(formatMobile("9876")).toBe("9876");
  });

  it("formatAadhaar groups as 4-4-4", () => {
    expect(formatAadhaar("234567890123")).toBe("2345 6789 0123");
    expect(formatAadhaar("2345")).toBe("2345");
  });

  it("formatIFSC uppercases, max 11", () => {
    expect(formatIFSC("hdfc0001234")).toBe("HDFC0001234");
    expect(formatIFSC("hdfc0001234extra")).toBe("HDFC0001234");
  });

  it("formatBankAccount keeps only digits, max 18", () => {
    expect(formatBankAccount("1234-5678-9012-3456-78")).toBe("123456789012345678");
  });

  it("formatNSDLBoId prefixes IN and keeps 14 digits", () => {
    expect(formatNSDLBoId("12345678901234")).toBe("IN12345678901234");
    expect(formatNSDLBoId("IN12345678901234")).toBe("IN12345678901234");
  });

  it("formatCDSLBoId keeps only 16 digits", () => {
    expect(formatCDSLBoId("1234567890123456789")).toBe("1234567890123456");
  });
});
