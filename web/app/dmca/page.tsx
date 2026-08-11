import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "DMCA / Copyright Policy",
  description: "How to submit a copyright takedown notice for content processed by Castia.",
  alternates: { canonical: "/dmca" },
};

// DRAFT, not legal advice - see terms/page.tsx's docstring for the same
// caveat. This page describes a standard notice-and-takedown process,
// but §1's DMCA Agent registration is a REAL ACTION the business owner
// must take with the U.S. Copyright Office (a fee-based online filing at
// copyright.gov) before this page can actually provide safe-harbor
// protection under 17 U.S.C. § 512 - nothing here can substitute for
// that filing, and the agent's name/address/email below must exactly
// match what's registered there.
export default function DmcaPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            DMCA / Copyright Policy
          </h1>
          <p className="mt-3 text-[13px] text-ink/62 dark:text-ink-dark/62">
            Last updated: [DATE] · DRAFT — pending legal review and DMCA agent registration, not yet in effect
          </p>
        </div>

        <div className="mt-10 space-y-9 text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
          <Section title="1. Designated agent">
            <p>
              Castia's designated agent for copyright infringement notices
              under the Digital Millennium Copyright Act (DMCA) is:
            </p>
            <div className="mt-3 rounded-lg border border-black/[0.12] bg-white/50 p-4 dark:border-white/[0.12] dark:bg-white/[0.03]">
              <Placeholder>Agent name</Placeholder>
              <br />
              <Placeholder>Mailing address</Placeholder>
              <br />
              <Placeholder>Email address dedicated to DMCA notices, e.g. dmca@usecastia.com</Placeholder>
            </div>
            <p className="mt-3">
              This agent must be registered with the U.S. Copyright Office's
              DMCA Designated Agent Directory before this policy provides
              safe-harbor protection. Notices sent to any other address may
              not be processed under this policy.
            </p>
          </Section>

          <Section title="2. What Castia does with user-submitted content">
            <p>
              Users can submit song lyrics, comic/webtoon dialogue text, and
              comic panel images to be adapted into another language. Castia
              does not pre-screen submissions for copyright ownership before
              processing them — see our{" "}
              <a href="/terms" className="underline decoration-ink/20 underline-offset-4">
                Terms of Service
              </a>
              , where users represent that they have the right to submit what
              they upload. If you believe content processed, cached, or
              displayed by Castia infringes your copyright, follow the notice
              process below.
            </p>
          </Section>

          <Section title="3. How to submit a takedown notice">
            <p>To be effective, a notice must include, in writing, to the agent above:</p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>A physical or electronic signature of the copyright owner or a person authorized to act on their behalf;</li>
              <li>Identification of the copyrighted work claimed to have been infringed;</li>
              <li>Identification of the material claimed to be infringing, and information reasonably sufficient to locate it on the Service (e.g. the specific URL, such as a <code className="rounded bg-black/5 px-1 py-0.5 text-[12.5px] dark:bg-white/10">/s/[id]</code> or <code className="rounded bg-black/5 px-1 py-0.5 text-[12.5px] dark:bg-white/10">/comics/s/[id]</code> share link);</li>
              <li>Your contact information (address, telephone number, and email address);</li>
              <li>A statement that you have a good-faith belief that use of the material is not authorized by the copyright owner, its agent, or the law;</li>
              <li>A statement, under penalty of perjury, that the information in the notice is accurate and that you are authorized to act on behalf of the copyright owner.</li>
            </ul>
          </Section>

          <Section title="4. What happens after a valid notice">
            <p>
              On receiving a notice that substantially complies with §3, we
              will remove or disable access to the identified content (which,
              for a cached adaptation result, means removing it from the
              cache and any share link) and make a reasonable effort to
              notify the user who submitted the content, where we have
              contact information for them.
            </p>
          </Section>

          <Section title="5. Counter-notice">
            <p>
              If you believe content was removed in error or misidentification,
              you may submit a counter-notice to the agent above, including
              your identification of the removed material, a statement under
              penalty of perjury that you have a good-faith belief the
              material was removed by mistake, and your consent to the
              jurisdiction of the federal court for your district (or, if
              outside the U.S., an appropriate judicial district). We may
              restore the content per the DMCA's standard counter-notice
              timeline, subject to whether the original complainant files a
              court action.
            </p>
          </Section>

          <Section title="6. Repeat infringer policy">
            <p>
              Accounts that are the subject of repeated, valid infringement
              notices will have their access to the Service terminated,
              consistent with 17 U.S.C. § 512(i).
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
