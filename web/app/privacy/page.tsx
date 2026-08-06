import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Privacy Policy",
  description: "What Castia collects, which third parties process it, and how long it's kept.",
  alternates: { canonical: "/privacy" },
};

// DRAFT, not legal advice - see terms/page.tsx's docstring for the same
// caveat. Every data-flow claim below is checked against the real
// implementation (engine/llm_client.py, engine/comics_ocr.py,
// server/db_models.py, server/accounts.py) rather than generic
// boilerplate, so it stays accurate as the product changes - but it
// still needs a lawyer's review before publishing, particularly the
// GDPR/CCPA rights section, which describes real practices without
// asserting a compliance certification this repo can't make on its own.
export default function PrivacyPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Privacy Policy
          </h1>
          <p className="mt-3 text-[13px] text-ink/40 dark:text-ink-dark/40">
            Last updated: [DATE] · DRAFT — pending legal review, not yet in effect
          </p>
        </div>

        <div className="mt-10 space-y-9 text-[14px] leading-relaxed text-ink/70 dark:text-ink-dark/70">
          <Section title="1. What we collect">
            <p>Directly from you:</p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>
                <strong className="text-ink dark:text-ink-dark">Account info</strong> — email address and display name (from Google sign-in, or the email you register with directly); a hashed password if you sign up with email/password (the plaintext password is never stored); email-verification status.
              </li>
              <li>
                <strong className="text-ink dark:text-ink-dark">Content you submit</strong> — lyrics or dialogue text, and comic panel images, for the purpose of generating an adaptation.
              </li>
              <li>
                <strong className="text-ink dark:text-ink-dark">Payment metadata</strong> — where paid credit purchases are live, transaction identifiers and amounts from our payment processor. We do not receive or store your full card number; that's handled entirely by the payment processor.
              </li>
              <li>
                <strong className="text-ink dark:text-ink-dark">API keys</strong> — if you generate one, we store a one-way hash of it, not the raw key (the raw key is shown to you once, at creation, and cannot be recovered by us afterward).
              </li>
            </ul>
            <p className="mt-3">Generated automatically:</p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>Your adaptation history (what you submitted, the result, and its language) if you're signed in and choose to keep it — see §3.</li>
              <li>Usage/quota counters (request counts per day, per IP address or API key) used to enforce rate limits.</li>
              <li>Standard server logs (IP address, timestamps, error details) for operating and debugging the Service.</li>
            </ul>
          </Section>

          <Section title="2. Third parties we send your content to">
            <p>
              To generate an adaptation, the text (and, for comics, the panel
              image) you submit is sent to the AI providers Castia's pipeline
              is built on:
            </p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li><strong className="text-ink dark:text-ink-dark">OpenAI</strong> (and/or <strong className="text-ink dark:text-ink-dark">Anthropic</strong>, depending on deployment configuration) — for the translation/adaptation language models.</li>
              <li><strong className="text-ink dark:text-ink-dark">Google Cloud Vision</strong> — for extracting text from an uploaded comic panel image (OCR).</li>
            </ul>
            <p className="mt-3">
              Each provider processes what we send under its own terms and
              privacy policy; we do not control how long they retain data on
              their side. We only send what a given feature actually needs —
              for example, an image is sent to Google Cloud Vision to read
              its text, and separately may be sent to an AI vision model if
              that optional reading-quality feature is enabled for a given
              deployment.
            </p>
            <p className="mt-3">
              Where paid credit purchases are live, payment processing is
              handled entirely by <Placeholder>Paddle (or the live payment processor at time of launch)</Placeholder>,
              acting as merchant of record — they receive what's needed to
              process your payment (billing details, card information)
              directly; we do not.
            </p>
          </Section>

          <Section title="3. Caching and how adaptation results are shared">
            <p>
              To avoid re-running the AI pipeline on identical input (which
              costs real money and time), a completed adaptation is cached
              on our servers, addressed by a hash of the submitted content
              and target language — not by who submitted it. If a different
              user submits the exact same text, they may be served the
              cached result rather than triggering a new AI run. This cache
              is not linked to any account by default.
            </p>
            <p className="mt-3">
              If you're signed in and the adaptation is recorded to your
              account (automatically for adaptations you run, or explicitly
              if you star/save someone else's shared result), that link
              between your account and the result — and the result itself —
              is retained until you delete it or your account.
            </p>
            <p className="mt-3">
              For comic panel redraws specifically: the erased-and-relettered
              output image is cached the same content-addressed way described
              above. The original image you upload for OCR is processed to
              extract text and is not separately stored beyond that
              processing.
            </p>
          </Section>

          <Section title="4. How long we keep data">
            <p>
              Account records (email, credit balance, adaptation history) are
              kept for as long as your account exists. Content-addressed
              cached results (§3) may persist independently of any one
              account, since they can be shared across users who submit
              identical content. Server logs are retained for a limited
              operational window before routine deletion.
            </p>
          </Section>

          <Section title="5. Your choices and rights">
            <p>
              You can review your adaptation history, favorites, and
              collections from your account dashboard at any time. Deleting
              individual saved adaptations or collections is available from
              the dashboard. Full account deletion is not yet a self-service
              feature — email{" "}
              <Placeholder>support@usecastia.com or your real support inbox</Placeholder>{" "}
              to request it, and we'll delete your account record and its
              linked history (content already shared via the caching
              mechanism in §3, submitted by other users, is not deleted,
              since it isn't yours to delete).
            </p>
            <p className="mt-3">
              If you are located in the EEA, UK, or another jurisdiction with
              its own data protection law (such as the CCPA/CPRA in
              California), you may have additional rights over your personal
              data — including access, correction, deletion, and
              portability — beyond what's described above.{" "}
              <Placeholder>This section should be reviewed and expanded by counsel for the specific jurisdictions you operate in before publishing</Placeholder>.
            </p>
          </Section>

          <Section title="6. Children's privacy">
            <p>
              The Service is not directed at children under 13 (or the
              equivalent minimum age in your jurisdiction), and we do not
              knowingly collect personal information from them.
            </p>
          </Section>

          <Section title="7. Changes to this policy">
            <p>
              We may update this policy as the Service changes. Material
              changes will be reflected by updating the "Last updated" date
              above.
            </p>
          </Section>

          <Section title="8. Contact">
            <p>
              Questions about this policy or your data:{" "}
              <Placeholder>support@usecastia.com or your real support inbox</Placeholder>.
            </p>
          </Section>
        </div>

        <Footer />
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-serif text-lg text-ink dark:text-ink-dark">{title}</h2>
      <div className="mt-2.5">{children}</div>
    </div>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-700 dark:text-amber-400">
      [{children}]
    </span>
  );
}
