import { redirect } from "next/navigation";

export const metadata = {
  title: "CASTIA — Comic and webtoon localization",
  description: "Adapt comic and webtoon dialogue with character voice, emotional intent, and panel context in mind.",
  robots: { index: false, follow: false },
};

export default function LyricsTranslationPage(): never {
  redirect("/comics");
}
