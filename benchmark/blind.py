"""Builds blinded review packets.

For each reviewer, every song's outputs are shuffled independently (a
fresh order per reviewer counters position bias) and labeled A, B, C...
The mapping letter->system goes into key.json, which is the ONLY place
system identity exists — the reviewer HTML never contains a system name,
and a test asserts that.

    benchmark/runs/<run_id>/blind/key.json            (keep this private)
    benchmark/runs/<run_id>/blind/packet_<reviewer>.html
"""
from __future__ import annotations

import html
import json
import random
import string
from pathlib import Path

from engine.models import SongInput

from .schema import DIMENSION_LABELS, DIMENSIONS, BlindKeyEntry, SystemOutput
from .systems import _slug


def make_blind_packets(
    outputs_by_song: dict[str, list[SystemOutput]],
    songs: list[SongInput],
    reviewers: list[str],
    run_dir: Path,
    seed: int = 7,
) -> Path:
    blind_dir = run_dir / "blind"
    blind_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    source_by_id = {_slug(s.title or "untitled"): s for s in songs}

    key: list[BlindKeyEntry] = []
    for reviewer in reviewers:
        items = []
        for song_id, outputs in outputs_by_song.items():
            if len(outputs) < 2:
                continue  # nothing to compare
            shuffled = list(outputs)
            rng.shuffle(shuffled)
            letters = string.ascii_uppercase[: len(shuffled)]
            for letter, output in zip(letters, shuffled):
                key.append(
                    BlindKeyEntry(
                        reviewer=reviewer,
                        song_id=song_id,
                        letter=letter,
                        system=output.system,
                    )
                )
            source = source_by_id.get(song_id)
            items.append((song_id, source, list(zip(letters, shuffled))))

        packet_html = _render_packet(reviewer, items)
        (blind_dir / f"packet_{_slug(reviewer)}.html").write_text(packet_html)

    key_path = blind_dir / "key.json"
    key_path.write_text(
        json.dumps([k.model_dump() for k in key], ensure_ascii=False, indent=2)
    )
    return blind_dir


def _render_packet(
    reviewer: str,
    items: list[tuple[str, SongInput | None, list[tuple[str, SystemOutput]]]],
) -> str:
    """A single self-contained HTML file: original + blinded outputs +
    rating controls, exporting a ReviewerSubmission JSON on finish. No
    server, no dependencies — send the file, get a JSON back.
    """
    blocks = []
    for song_id, source, lettered in items:
        source_html = ""
        if source is not None:
            source_text = "\n\n".join(s.source_text for s in source.sections)
            source_html = (
                f"<details open><summary>Original ({html.escape(source.source_language)})</summary>"
                f"<pre class='orig'>{html.escape(source_text)}</pre></details>"
            )
        out_blocks = []
        for letter, output in lettered:
            dims = "".join(
                f"<div class='dim'><span>{html.escape(DIMENSION_LABELS[d])}</span>"
                + "".join(
                    f"<label><input type='radio' name='r_{song_id}_{letter}_{d}' "
                    f"value='{v}'>{v}</label>"
                    for v in range(1, 6)
                )
                + "</div>"
                for d in DIMENSIONS
            )
            out_blocks.append(
                f"<div class='output' id='out_{song_id}_{letter}'>"
                f"<h4>Version {letter}</h4>"
                f"<pre>{html.escape(output.joined())}</pre>"
                f"{dims}"
                f"<div class='dim best'><span>Best overall version of this song</span>"
                f"<label><input type='radio' name='best_{song_id}' value='{letter}'>"
                f"This one</label></div>"
                "</div>"
            )
        blocks.append(
            f"<section class='song' data-song='{song_id}'>"
            f"<h2>{html.escape(song_id.replace('_', ' ').title())}</h2>"
            f"{source_html}"
            f"{''.join(out_blocks)}"
            "</section>"
        )

    dims_json = json.dumps(list(DIMENSIONS))
    song_letters = {
        song_id: [letter for letter, _ in lettered] for song_id, _, lettered in items
    }
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blind lyric review</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }}
  h1 {{ font-size: 1.5rem; }} h2 {{ margin-top: 3rem; border-bottom: 1px solid #ddd; padding-bottom: .4rem; }}
  pre {{ white-space: pre-wrap; font-family: inherit; background: #f7f6f4; padding: 1rem; border-radius: 8px; }}
  pre.orig {{ background: #f0efe9; }}
  .output {{ margin: 1.5rem 0; }} h4 {{ margin-bottom: .3rem; }}
  .dim {{ display: flex; align-items: center; gap: .6rem; font-size: .9rem; margin: .25rem 0; font-family: -apple-system, sans-serif; }}
  .dim span {{ flex: 1; }} .dim label {{ margin-right: .4rem; }}
  .dim.best {{ font-weight: 600; margin-top: .6rem; }}
  button {{ font-size: 1rem; padding: .7rem 1.6rem; border-radius: 999px; border: none; background: #1a1a1a; color: #fff; cursor: pointer; margin: 2rem 0; }}
  .note {{ font-size: .9rem; color: #666; font-family: -apple-system, sans-serif; }}
  #status {{ color: #b00; font-family: -apple-system, sans-serif; }}
</style></head><body>
<h1>Blind lyric review</h1>
<p class="note">You are comparing several English versions of the same songs.
You are not told where any version came from — judge only what you read.
Rate every version on all four qualities (1 = poor, 5 = excellent), pick one
best version per song, then press Finish to download your answers and send
the file back.</p>
{''.join(blocks)}
<button onclick="finish()">Finish &amp; download my answers</button>
<p id="status"></p>
<script>
const DIMENSIONS = {dims_json};
const SONG_LETTERS = {json.dumps(song_letters)};
const REVIEWER = {json.dumps(reviewer)};
function finish() {{
  const ratings = []; const missing = [];
  for (const [song, letters] of Object.entries(SONG_LETTERS)) {{
    const best = document.querySelector(`input[name="best_${{song}}"]:checked`);
    if (!best) missing.push(`best pick for ${{song}}`);
    for (const letter of letters) {{
      const scores = {{}};
      for (const d of DIMENSIONS) {{
        const el = document.querySelector(`input[name="r_${{song}}_${{letter}}_${{d}}"]:checked`);
        if (!el) missing.push(`${{song}} version ${{letter}}: ${{d}}`);
        else scores[d] = parseInt(el.value, 10);
      }}
      ratings.push({{ reviewer: REVIEWER, song_id: song, letter: letter,
                      scores: scores, best_overall: !!(best && best.value === letter) }});
    }}
  }}
  if (missing.length) {{
    document.getElementById('status').textContent =
      'Missing ' + missing.length + ' answer(s): ' + missing.slice(0, 3).join('; ') + (missing.length > 3 ? ' …' : '');
    return;
  }}
  const blob = new Blob([JSON.stringify({{ reviewer: REVIEWER, ratings: ratings }}, null, 2)],
                        {{ type: 'application/json' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ratings_' + REVIEWER.replace(/[^a-z0-9]/gi, '_') + '.json';
  a.click();
  document.getElementById('status').textContent = 'Done — send the downloaded file back. Thank you!';
}}
</script></body></html>
"""
