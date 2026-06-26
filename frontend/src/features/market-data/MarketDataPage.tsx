import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { Card, Button, useToast } from "../../components/ui";

interface IngestResult {
  trade_date: string;
  rows_parsed: number;
  prices_upserted: number;
}

interface ValuationResult {
  as_of: string;
  accounts_processed: number;
}

export function MarketDataPage() {
  const toast = useToast();
  const [ingestDate, setIngestDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);
  const [valuationResult, setValuationResult] = useState<ValuationResult | null>(null);

  const ingestMutation = useMutation({
    mutationFn: (date: string) =>
      apiClient
        .post<IngestResult>(`/market-data/ingest/${date}`)
        .then((r) => r.data),
    onSuccess: (data) => {
      setIngestResult(data);
      toast.success(
        `Ingested ${data.prices_upserted} prices from ${data.rows_parsed} rows`,
      );
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const valuateMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ValuationResult>("/market-data/valuate").then((r) => r.data),
    onSuccess: (data) => {
      setValuationResult(data);
      toast.success(`Valuation complete: ${data.accounts_processed} accounts`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1>Market Data</h1>
        <p className="muted">
          Ingest NSE bhavcopy prices and run portfolio mark-to-market
        </p>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <Card>
          <h2 style={{ marginBottom: 12 }}>Ingest Bhavcopy</h2>
          <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
            Parse the downloaded NSE bhavcopy ZIP for a given trading date and
            update security close prices.
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
            <div>
              <label style={{ fontSize: ".82rem", fontWeight: 500 }}>
                Trade Date
              </label>
              <input
                type="date"
                className="form-input"
                style={{ marginTop: 4 }}
                value={ingestDate}
                onChange={(e) => setIngestDate(e.target.value)}
              />
            </div>
            <Button
              variant="primary"
              onClick={() => ingestMutation.mutate(ingestDate)}
              disabled={ingestMutation.isPending}
            >
              {ingestMutation.isPending ? "Ingesting..." : "Ingest Prices"}
            </Button>
          </div>

          {ingestResult && (
            <div
              style={{
                marginTop: 16,
                padding: "12px 16px",
                background: "var(--bg-secondary)",
                borderRadius: 8,
                fontSize: ".88rem",
              }}
            >
              <div>
                Date: <strong>{ingestResult.trade_date}</strong>
              </div>
              <div>
                Rows parsed: <strong>{ingestResult.rows_parsed}</strong>
              </div>
              <div>
                Prices upserted: <strong>{ingestResult.prices_upserted}</strong>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <h2 style={{ marginBottom: 12 }}>Daily Valuation</h2>
          <p className="muted" style={{ marginBottom: 16, fontSize: ".88rem" }}>
            Mark all active portfolios to market using the latest available
            prices. Creates valuation snapshots and recomputes performance
            returns.
          </p>
          <Button
            variant="primary"
            onClick={() => valuateMutation.mutate()}
            disabled={valuateMutation.isPending}
          >
            {valuateMutation.isPending
              ? "Running valuation..."
              : "Run Daily Valuation"}
          </Button>

          {valuationResult && (
            <div
              style={{
                marginTop: 16,
                padding: "12px 16px",
                background: "var(--bg-secondary)",
                borderRadius: 8,
                fontSize: ".88rem",
              }}
            >
              <div>
                As of: <strong>{valuationResult.as_of}</strong>
              </div>
              <div>
                Accounts processed:{" "}
                <strong>{valuationResult.accounts_processed}</strong>
              </div>
            </div>
          )}

          <div
            className="faint"
            style={{ marginTop: 12, fontSize: ".78rem" }}
          >
            This runs automatically at 8:00 PM IST after bhavcopy download.
          </div>
        </Card>
      </div>
    </div>
  );
}
