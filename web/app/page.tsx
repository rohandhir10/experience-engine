import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/JsonLd";
import { webPageJsonLd, faqPageJsonLd } from "@/lib/schema";
import { homepageFaqs } from "@/lib/faqs";
import "./hatchable-home.css";

export const metadata: Metadata = {
  title: "CASTIA — Every panel. Every feeling. Every language.",
  description: "Creative webtoon localization that preserves character voice, emotional intent, and panel context across languages.",
  alternates: { canonical: "/" },
  openGraph: { title: "CASTIA — Every panel. Every feeling. Every language.", description: "Creative webtoon localization that preserves character voice, emotional intent, and panel context across languages.", url: "/" },
};
const PAGE_UPDATED_DATE = "2026-10-25";
const HOMEPAGE_FAQS = homepageFaqs();

const steps = [
  { n: "01", title: "Bring the scene", body: "Start with dialogue and the context your team has: character notes, scene summaries, and panel references.", tag: "CONTEXT IN", icon: "▤" },
  { n: "02", title: "Read between lines", body: "Surface potential issues with voice, tone, cultural nuance, subtext, and consistency across a scene.", tag: "CREATIVE ANALYSIS", icon: "✳" },
  { n: "03", title: "Compare adaptations", body: "Explore alternatives with clear trade-offs, then let editors and translators make the final call.", tag: "HUMAN IN CONTROL", icon: "↗" },
  { n: "04", title: "Ship with confidence", body: "Review a structured record of creative choices and consistency checks before publication.", tag: "EDITORIAL QA", icon: "✓" },
];

const capabilities = [
  { n: "A / 01", title: "Character voice, episode to episode", body: "Help flag when a character's diction, formality, or emotional register drifts across a long-running series.", kind: "speech" },
  { n: "A / 02", title: "Dialogue that fits the panel", body: "Keep the artwork and surrounding scene in view when reviewing a line.", kind: "frames" },
  { n: "A / 03", title: "Tone, subtext & nuance", body: "Highlight moments where literal meaning and intended feeling may diverge.", kind: "tone" },
  { n: "A / 04", title: "Alternatives, not one “correct” answer", body: "Compare creative options and their trade-offs instead of accepting a black-box rewrite.", kind: "compare" },
];

export default function Home() {
  return (
    <main className="castia-home">
      <JsonLd data={webPageJsonLd({ path: "/", name: "CASTIA — Every panel. Every feeling. Every language.", description: "Creative webtoon localization that preserves character voice, emotional intent, and panel context across languages.", updatedDate: PAGE_UPDATED_DATE })} />
      <JsonLd data={faqPageJsonLd(HOMEPAGE_FAQS)} />
      <div className="ch-announcement"><span className="ch-pulse" /> BUILT FOR THE PEOPLE WHO BRING STORIES TO THE WORLD <span className="ch-announcement-right">CREATIVE LOCALIZATION, REIMAGINED ↗</span></div>
      <header className="ch-nav ch-wrap">
        <Link className="ch-wordmark" href="/" aria-label="CASTIA home"><span className="ch-mark">C<span>✳</span></span> CASTIA</Link>
        <nav className="ch-nav-links" aria-label="Main navigation"><a href="#platform">Platform</a><a href="#workflow">How it works</a><a href="#teams">For teams</a></nav>
        <Link className="ch-nav-cta" href="/comics">Open workspace <span>↗</span></Link>
        <details className="ch-mobile-nav"><summary aria-label="Open navigation">☰</summary><nav aria-label="Mobile navigation"><a href="#platform">Platform</a><a href="#workflow">How it works</a><a href="#teams">For teams</a></nav></details>
      </header>

      <section className="ch-hero ch-wrap">
        <div className="ch-hero-copy">
          <div className="ch-eyebrow"><span /> THE CREATIVE LOCALIZATION ENGINE</div>
          <h1>Every panel.<br />Every feeling.<br /><em>Every language.</em></h1>
          <p className="ch-lede">Webtoons travel across borders. Their <strong>heart should travel with them.</strong> CASTIA helps localization teams adapt dialogue with character voice, emotional intent, and panel context intact.</p>
          <div className="ch-hero-actions"><Link className="ch-button ch-button-dark" href="/comics">Explore the workspace <span>↗</span></Link><a className="ch-text-link" href="#workflow"><span className="ch-play">▶</span> See how it works</a></div>
          <div className="ch-proof"><div className="ch-avatars"><span>한</span><span>文</span><span>あ</span></div><p>Made for localization teams<br /><strong>Not just word-for-word translation.</strong></p></div>
        </div>
        <div className="ch-hero-art" aria-label="Illustrative webtoon localization workspace">
          <div className="ch-art-top"><span>CASTIA / WORKSPACE 01</span><span className="ch-live"><i /> CONCEPT PREVIEW</span></div>
          <div className="ch-comic-sheet"><div className="ch-comic-panel ch-panel-main"><div className="ch-sun" /><div className="ch-silhouette" /><div className="ch-speech ch-speech-one">You came back.</div><div className="ch-panel-caption">01 — THE RETURN</div></div><div className="ch-comic-panel ch-panel-side"><div className="ch-speed-lines" /><div className="ch-speech ch-speech-two">I said I would.</div><div className="ch-panel-caption">02 — THE PROMISE</div></div></div>
          <div className="ch-translation-card"><div className="ch-tc-head"><span className="ch-tc-icon">✳</span><div><strong>Creative fidelity</strong><small>SCENE CONTEXT · DETECTED</small></div><span className="ch-score">92<span>/100</span></span></div>
            <div className="ch-tc-row"><span className="ch-dot ch-purple" /><div><strong>Character voice</strong><small>Reserved, emotionally guarded</small></div><span className="ch-check">✓</span></div>
            <div className="ch-tc-row"><span className="ch-dot ch-orange" /><div><strong>Subtext</strong><small>Relief beneath restraint</small></div><span className="ch-check">✓</span></div>
            <div className="ch-tc-row"><span className="ch-dot ch-green" /><div><strong>Panel continuity</strong><small>Meaning preserved in context</small></div><span className="ch-check">✓</span></div>
            <div className="ch-tc-foot">ILLUSTRATIVE PRODUCT CONCEPT <span>↗</span></div>
          </div><div className="ch-floating-note"><span>✧</span> Meaning lives between the lines.</div>
        </div>
        <div className="ch-hero-bottom"><span>01 / A BETTER WAY TO LOCALIZE</span><span>LANGUAGE IS ONLY THE BEGINNING ↓</span></div>
      </section>

      <div className="ch-marquee"><div className="ch-marquee-inner"><span>CHARACTER VOICE</span><b>✳</b><span>EMOTIONAL FIDELITY</span><b>✳</b><span>PANEL CONTEXT</span><b>✳</b><span>CULTURAL NUANCE</span><b>✳</b><span>CHARACTER VOICE</span><b>✳</b><span>EMOTIONAL FIDELITY</span><b>✳</b></div></div>

      <section className="ch-section ch-wrap" id="platform">
        <div className="ch-kicker">01 — THE PROBLEM</div><div className="ch-problem-grid"><h2>A translation can be<br />accurate and still feel <em>wrong.</em></h2><div className="ch-copy"><p>A character's hesitation. A joke that only works in context. A confession hidden behind a casual line. In webtoons, meaning is carried by dialogue, artwork, pacing, and everything left unsaid.</p><p>Generic translation tools can miss that. CASTIA is designed to help teams spot the difference—and make more intentional creative choices.</p></div></div>
        <div className="ch-contrast-grid"><article className="ch-contrast ch-muted"><div className="ch-card-label"><span>↘</span> WORD-FOR-WORD</div><div className="ch-dialogue">“I don't care about you.”</div><p>Literal wording, detached from the scene. The emotional signal may be lost.</p><div className="ch-card-status">SURFACE MEANING ONLY</div></article><article className="ch-contrast ch-vivid"><div className="ch-card-label"><span>✳</span> CONTEXT-AWARE REVIEW</div><div className="ch-dialogue">“It's not like I care.”</div><p>A possible adaptation that keeps the defensive tone and hints at feelings the character won't admit.</p><div className="ch-card-status">INTENT · VOICE · SUBTEXT <span>↗</span></div></article></div>
        <p className="ch-fineprint">Illustrative example only. The best adaptation depends on the original language, scene, character, and editorial direction.</p>
      </section>

      <section className="ch-workflow-section" id="workflow"><div className="ch-wrap ch-workflow"><div className="ch-kicker ch-light-kicker">02 — THE WORKFLOW</div><div className="ch-workflow-heading"><h2>Human creativity.<br /><em>Better tools.</em></h2><p>CASTIA is designed to support the people who make localization great—not replace their judgment.</p></div><div className="ch-steps">{steps.map((step) => <article className="ch-step" key={step.n}><span className="ch-step-num">{step.n}</span><div className="ch-step-icon">{step.icon}</div><h3>{step.title}</h3><p>{step.body}</p><span className="ch-step-tag">{step.tag}</span></article>)}</div></div></section>

      <section className="ch-section ch-wrap" id="teams"><div className="ch-kicker">03 — MADE FOR WEBTOONS</div><div className="ch-cap-heading"><h2>More than translation.<br /><em>A creative safety net.</em></h2><p>Built around the details that make serialized visual stories feel alive.</p></div><div className="ch-cap-grid">{capabilities.map((cap) => <article className="ch-cap-card" key={cap.n}><div className="ch-cap-number">{cap.n}</div><div className={`ch-cap-illustration ch-cap-${cap.kind}`}>{cap.kind === "speech" ? <><span className="ch-bubble ch-bubble-a">…</span><span className="ch-bubble ch-bubble-b">!</span><span className="ch-spark">✳</span></> : cap.kind === "frames" ? <><span className="ch-frame ch-frame-1" /><span className="ch-frame ch-frame-2" /><span className="ch-frame ch-frame-3" /><span className="ch-context-line" /></> : cap.kind === "tone" ? <><span className="ch-tone-circle">♡</span><span className="ch-tone-orbit" /></> : <><span>Original</span><span>Option A</span><span>Option B</span><b>↔</b></>}</div><h3>{cap.title}</h3><p>{cap.body}</p><span className="ch-cap-arrow">↗</span></article>)}</div><div className="ch-cap-disclaimer">These are the product capabilities CASTIA is being designed around; availability depends on the current build. No publisher integrations or performance results are implied.</div></section>

      <section className="ch-quote-section"><div className="ch-wrap ch-quote-wrap"><div className="ch-quote-mark">“</div><blockquote>A great localization doesn't just tell readers what happened. It makes them <em>feel</em> what happened.</blockquote><div className="ch-quote-credit"><span /> THE CASTIA PRINCIPLE</div><div className="ch-quote-decoration">感情<br /><span>FEELING</span></div></div></section>
      <section className="ch-section ch-wrap ch-audience"><div className="ch-kicker">04 — WHO IT'S FOR</div><h2>For the teams behind<br />the stories we love.</h2><div className="ch-audience-grid"><div><span>01</span><h3>Webtoon publishers</h3><p>Bring editorial consistency to multi-language releases and growing catalogs.</p></div><div><span>02</span><h3>Localization studios</h3><p>Give translators and editors a shared framework for creative quality review.</p></div><div><span>03</span><h3>Independent translators</h3><p>Explore alternatives, document choices, and protect your creative intent.</p></div></div></section>
      <section className="ch-cta-section"><div className="ch-wrap ch-cta-wrap"><div className="ch-kicker ch-light-kicker">05 — YOUR NEXT CHAPTER</div><h2>Your stories cross borders.<br /><em>Let's keep their soul.</em></h2><p>Bring a chapter into CASTIA, inspect the extracted dialogue, and decide which rewrites deserve to stay. You remain in control at every step.</p><Link className="ch-button ch-button-purple" href="/comics">Open the webtoon workspace <span>↗</span></Link><div className="ch-cta-side-note"><span>✳</span><p>Built for creative fidelity.<br />Designed with humans in control.</p></div></div></section>
      <footer className="ch-footer"><div className="ch-wrap ch-footer-top"><Link className="ch-wordmark" href="/"><span className="ch-mark">C<span>✳</span></span> CASTIA</Link><p>Creative localization for visual stories.</p><Link href="/comics">Open workspace ↗</Link></div><div className="ch-wrap ch-footer-bottom"><span>© 2026 CASTIA. MADE FOR STORIES THAT TRAVEL.</span><span>AN EARLY PRODUCT CONCEPT · NOT AFFILIATED WITH WEBTOON ENTERTAINMENT</span><a href="#">BACK TO TOP ↑</a></div></footer>
    </main>
  );
}
