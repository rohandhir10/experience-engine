// Renders a schema.org JSON-LD block. `dangerouslySetInnerHTML` is safe
// here specifically because every caller passes a value produced by
// JSON.stringify on this server - never user input - so there's no
// injection surface, unlike the same pattern with untrusted strings.
export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
