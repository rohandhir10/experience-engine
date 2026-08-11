import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Terms of Service",
  description: "The terms governing use of Castia's lyric and comic/webtoon adaptation platform.",
  alternates: { canonical: "/terms" },
};

// DRAFT, not legal advice. Every factual claim here (what data flows
// where, what auto-refunds on failure, that credits don't expire, that
// account deletion is manual today) is checked against the real
// implementation, same discipline as every other page on this site - but
// a document like this still needs a lawyer's review before it's
// actually binding, especially the arbitration/liability/governing-law
// sections, which are jurisdiction-specific decisions this repo has no
// authority to make. Bracketed placeholders mark facts only the
// business owner can supply (legal entity name, registered address,
// governing law, support inbox) - never invented here.
export default function TermsPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Terms of Service
          </h1>
          <p className="mt-3 text-[13px] text-ink/62 dark:text-ink-dark/62">
            Last updated: [DATE] · DRAFT — pending legal review, not yet in effect
          </p>
        </div>

        <div className="mt-10 space-y-9 text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
          <Section title="1. Who these terms are with">
            <p>
              Castia ("Castia," "we," "us," or "our") is operated by{" "}
              <Placeholder>Legal Entity Name, e.g. "Castia, Inc." or "Castia LLC," and its registered address</Placeholder>.
              These Terms of Service ("Terms") govern your access to and use of
              the Castia website, API, and lyric/comic adaptation services
              (together, the "Service"). By creating an account, purchasing
              credits, or using the Service without an account, you agree to
              these Terms.
            </p>
          </Section>

          <Section title="2. What the Service does">
            <p>
              Castia rewrites song lyrics and comic/webtoon dialogue you
              submit into a target language, using a multi-stage AI pipeline
              (a literal-anchor translation, several creative rewrites, and
              an automated review step). Optionally, for comics, Castia can
              erase the original lettering from an uploaded panel image and
              typeset the adapted line back in.
            </p>
            <p className="mt-3">
              A limited number of adaptations work without an account, subject
              to daily rate limits. Creating an account (via Google sign-in or
              email/password) adds a history of your adaptations, the ability
              to star and organize results into collections, and — where
              billing is live — a credit balance used to pay for further
              adaptations.
            </p>
          </Section>

          <Section title="3. Your content and the license you grant us">
            <p>
              You retain all ownership rights in the lyrics, dialogue text,
              and images you submit ("User Content"). By submitting User
              Content, you grant Castia a limited, worldwide, non-exclusive
              license to host, process, transmit, and display that content
              solely as necessary to operate the Service — including sending
              it to the third-party AI providers described in our{" "}
              <a href="/privacy" className="underline decoration-ink/20 underline-offset-4">
                Privacy Policy
              </a>{" "}
              to generate a translation, and caching the resulting output so
              an identical submission doesn't have to be reprocessed. This
              license ends when the underlying content is deleted, except for
              cached results already shared with other users who submitted
              the same content (see the Privacy Policy for how that caching
              works).
            </p>
            <p className="mt-3">
              You represent that you have the right to submit the User
              Content you upload — including that you own it, it's in the
              public domain, or your use falls under an applicable copyright
              exception (such as fair use) in your jurisdiction. Castia does
              not review submissions for copyright status before processing
              them; see our{" "}
              <a href="/dmca" className="underline decoration-ink/20 underline-offset-4">
                DMCA / Copyright Policy
              </a>{" "}
              for how we respond to infringement claims.
            </p>
          </Section>

          <Section title="4. AI output — accuracy, no guarantee">
            <p>
              Adapted lyrics and dialogue are generated by large language
              models and are creative, interpretive rewrites, not certified
              or literal translations. Output may contain errors,
              mistranslations, invented details ("hallucinations"), or
              content you find inappropriate or offensive, including where
              that reflects offensive language present in content you
              submitted. Castia includes an internal review step (see{" "}
              <a href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
                how it works
              </a>
              ) intended to catch specific failure modes, but this is not a
              guarantee of accuracy, appropriateness, or fitness for any
              particular purpose. You are responsible for reviewing output
              before relying on, publishing, or distributing it.
            </p>
            <p className="mt-3">
              THE SERVICE AND ALL OUTPUT ARE PROVIDED "AS IS" WITHOUT
              WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE MAXIMUM
              EXTENT PERMITTED BY LAW, CASTIA DISCLAIMS ALL WARRANTIES OF
              MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
              NON-INFRINGEMENT, AND CASTIA'S TOTAL LIABILITY FOR ANY CLAIM
              ARISING FROM YOUR USE OF THE SERVICE IS LIMITED TO THE AMOUNT
              YOU PAID CASTIA IN THE 12 MONTHS BEFORE THE CLAIM AROSE.{" "}
              <Placeholder>This limitation-of-liability language must be reviewed by a lawyer for your jurisdiction before publishing</Placeholder>.
            </p>
          </Section>

          <Section title="5. Credits, purchases, and billing">
            <p>
              Some use of the Service is metered in credits. Credits are
              consumed per adaptation and, as implemented today, do not
              expire. If an adaptation fails on Castia's side after credits
              are deducted (for example, an AI provider error), the credits
              are automatically returned to your balance — you don't need to
              request this.
            </p>
            <p className="mt-3">
              Where paid credit purchases are enabled, payments are processed
              by <Placeholder>Paddle (or the live payment processor at time of launch)</Placeholder>,
              acting as merchant of record. Your purchase is subject to that
              processor's own terms in addition to these Terms. See our{" "}
              <a href="/refunds" className="underline decoration-ink/20 underline-offset-4">
                Refund &amp; Cancellation Policy
              </a>{" "}
              for how refunds on purchased credits are handled. Credits have
              no cash value, are non-transferable between accounts, and
              cannot be redeemed for cash except as required by law.
            </p>
          </Section>

          <Section title="6. Acceptable use">
            <p>You agree not to use the Service to:</p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>Submit content you don't have the right to submit, including pirated or unlicensed copyrighted material;</li>
              <li>Submit content that is illegal, defamatory, or that depicts real people without their consent in a sexual or non-consensual context;</li>
              <li>Attempt to circumvent rate limits, quotas, or credit charges;</li>
              <li>Reverse-engineer, scrape, or use automated means to access the Service beyond documented API use;</li>
              <li>Use the Service to generate content intended to harass, defraud, or impersonate any person or organization.</li>
            </ul>
            <p className="mt-3">
              Castia may suspend or terminate access for violations of this
              section, or upon repeat copyright infringement (see the DMCA
              policy), without refunding unused credits obtained through
              violating activity.
            </p>
          </Section>

          <Section title="7. Account termination">
            <p>
              You may stop using the Service at any time. To request account
              deletion, contact{" "}
              <Placeholder>support@usecastia.com or your real support inbox</Placeholder>
              . Self-service account deletion is not yet available in the
              product; deletion requests are handled manually. See the{" "}
              <a href="/privacy" className="underline decoration-ink/20 underline-offset-4">
                Privacy Policy
              </a>{" "}
              for what happens to your data on deletion.
            </p>
          </Section>

          <Section title="8. Changes to these terms">
            <p>
              We may update these Terms as the Service changes. Material
              changes will be reflected by updating the "Last updated" date
              above; continued use of the Service after a change constitutes
              acceptance of the revised Terms.
            </p>
          </Section>

          <Section title="9. Governing law">
            <p>
              These Terms are governed by the laws of{" "}
              <Placeholder>Jurisdiction — must be set by the business owner, ideally with legal counsel</Placeholder>
              , without regard to conflict-of-law principles.
            </p>
          </Section>

          <Section title="10. Contact">
            <p>
              Questions about these Terms:{" "}
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
