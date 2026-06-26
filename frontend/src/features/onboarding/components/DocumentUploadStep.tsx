import { useState, useRef, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";

interface UploadedDoc {
  id: string;
  document_type: string;
  sha256: string;
  uploaded_at: string;
  download_url: string | null;
}

interface Props {
  applicationId: string;
  onComplete: () => void;
}

const DOCUMENT_TYPES = [
  { key: "pan_card", label: "PAN Card", required: true },
  { key: "aadhaar", label: "Aadhaar Card", required: true },
  { key: "bank_proof", label: "Bank Statement / Cancelled Cheque", required: true },
  { key: "demat_cmr", label: "Demat CMR Copy", required: true },
  { key: "address_proof", label: "Address Proof", required: false },
  { key: "photo", label: "Passport Photo", required: false },
] as const;

const ACCEPTED = ".pdf,.jpg,.jpeg,.png,.webp";

export default function DocumentUploadStep({ applicationId, onComplete }: Props) {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents", applicationId],
    queryFn: () =>
      apiClient
        .get<{ documents: UploadedDoc[] }>(`/documents/applications/${applicationId}`)
        .then((r) => r.data.documents),
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ type, file }: { type: string; file: File }) => {
      const form = new FormData();
      form.append("file", file);
      const resp = await apiClient.post(
        `/documents/applications/${applicationId}/upload?document_type=${type}`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", applicationId] });
      setUploading(null);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
      setUploading(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) =>
      apiClient.delete(`/documents/documents/${docId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", applicationId] });
    },
  });

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedType) return;

    if (file.size > 10 * 1024 * 1024) {
      setError("File too large. Maximum size: 10 MB");
      return;
    }

    setUploading(selectedType);
    setError(null);
    uploadMutation.mutate({ type: selectedType, file });

    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = "";
    setSelectedType(null);
  };

  const triggerUpload = (type: string) => {
    setSelectedType(type);
    setTimeout(() => fileInputRef.current?.click(), 50);
  };

  const uploaded = new Set(docs.map((d) => d.document_type));
  const requiredTypes = DOCUMENT_TYPES.filter((t) => t.required);
  const allRequiredUploaded = requiredTypes.every((t) => uploaded.has(t.key));

  return (
    <div>
      <h3 style={{ marginBottom: 8 }}>Document Upload</h3>
      <p className="muted" style={{ marginBottom: 20, fontSize: ".88rem" }}>
        Upload your KYC documents. PDF, JPG, PNG accepted (max 10 MB each).
      </p>

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED}
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />

      <div style={{ display: "grid", gap: 12 }}>
        {DOCUMENT_TYPES.map((dt) => {
          const doc = docs.find((d) => d.document_type === dt.key);
          const isUploading = uploading === dt.key;

          return (
            <div
              key={dt.key}
              className="card"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 18px",
                border: doc
                  ? "1px solid var(--success)"
                  : dt.required
                    ? "1px solid var(--border-light)"
                    : "1px solid var(--border-light)",
                opacity: isUploading ? 0.6 : 1,
              }}
            >
              <div>
                <div style={{ fontWeight: 500, fontSize: ".92rem" }}>
                  {dt.label}
                  {dt.required && !doc && (
                    <span style={{ color: "var(--danger)", marginLeft: 6, fontSize: ".78rem" }}>
                      Required
                    </span>
                  )}
                </div>
                {doc && (
                  <div className="faint" style={{ fontSize: ".78rem", marginTop: 2 }}>
                    Uploaded {new Date(doc.uploaded_at).toLocaleDateString("en-IN")}
                  </div>
                )}
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {doc && (
                  <>
                    <span className="badge badge--success" style={{ fontSize: ".75rem" }}>
                      Uploaded
                    </span>
                    <button
                      className="btn btn--xs btn--ghost"
                      onClick={() => triggerUpload(dt.key)}
                      disabled={isUploading}
                    >
                      Replace
                    </button>
                    <button
                      className="btn btn--xs btn--ghost"
                      style={{ color: "var(--danger)" }}
                      onClick={() => deleteMutation.mutate(doc.id)}
                      disabled={deleteMutation.isPending}
                    >
                      Remove
                    </button>
                  </>
                )}
                {!doc && (
                  <button
                    className="btn btn--sm btn--primary"
                    onClick={() => triggerUpload(dt.key)}
                    disabled={isUploading}
                  >
                    {isUploading ? "Uploading..." : "Upload"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <p className="error-text" style={{ marginTop: 12 }}>{error}</p>
      )}

      <div style={{ marginTop: 16, padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: 8 }}>
        <div className="row row--between">
          <span className="faint" style={{ fontSize: ".85rem" }}>
            {docs.length} of {requiredTypes.length} required documents uploaded
          </span>
          <div
            style={{
              width: 120, height: 6,
              background: "var(--border-light)", borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(docs.filter((d) => requiredTypes.some((r) => r.key === d.document_type)).length / requiredTypes.length) * 100}%`,
                height: "100%",
                background: allRequiredUploaded ? "var(--success)" : "var(--primary)",
                borderRadius: 3,
                transition: "width .3s ease",
              }}
            />
          </div>
        </div>
      </div>

      <div style={{ marginTop: 24, textAlign: "right" }}>
        <button
          className="btn btn-primary"
          onClick={onComplete}
          disabled={!allRequiredUploaded}
        >
          Continue
        </button>
        {!allRequiredUploaded && (
          <p className="faint" style={{ fontSize: ".78rem", marginTop: 6 }}>
            Upload all required documents to continue
          </p>
        )}
      </div>
    </div>
  );
}
