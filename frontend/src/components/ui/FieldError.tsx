export default function FieldError({ error }: { error?: string }) {
  if (!error) return null;
  return <p className="error-text">{error}</p>;
}
