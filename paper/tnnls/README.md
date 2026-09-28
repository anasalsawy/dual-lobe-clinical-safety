# TNNLS resubmission package

The first submission (TNNLS-2026-P-51070) was rescinded by the editorial office because it
was not prepared in the IEEE TNNLS template. This folder rebuilds the same paper in the official
IEEE Transactions Word template for resubmission as a **new** manuscript.

| File | Purpose |
|---|---|
| `TNNLS_manuscript.docx` | Manuscript to upload (IEEE Transactions template, two columns) |
| `TNNLS_manuscript_preview.pdf` | LibreOffice rendering, for checking layout only |
| `figures/*.pdf` | Vector figures (upload these if figure files are requested separately) |
| `build_manuscript.py` | Regenerates the .docx from the template |
| `make_figures.py` | Regenerates the figures |
| `template/` | The IEEE template the manuscript is built from |

Rebuild: `python make_figures.py && python build_manuscript.py`
(needs `python-docx`, `lxml`, `matplotlib`).

## What was wrong with the rescinded version

1. **Not the IEEE template (the reason for the rescission).** The PDF was a generic
   single-column LaTeX `article` layout: no IEEE two-column format, title block,
   first-page footnote, IEEE heading style, or biography.
2. **Placeholder author block:** "Author Name / Department of AI and Healthcare, University
   Name / author.email@example.com".
3. **Broken section numbering:** Sections 5 through 13 had lost their numbers.
4. **References never cited:** none of [1]–[10] appeared in the text. [9] and [10] had no
   authors.
5. **Truncated sentence:** "...a persistent hallucination rate of approximately 30" (the
   number and the rest of the sentence were missing).
6. **Missing figure:** the text said "illustrated in Figure 5", but there was no Fig. 5. A
   decorative cover image sat on page 1 with no caption.
7. **Figures not suitable for print:** dark backgrounds, and text clipped or overflowing in
   Figs. 1–3.
8. **Lists run together:** several lists were typed inline as " - a - b - c".
9. **Mixed quotation marks:** `”Open Sesame barrier,”` and `’prompt-space prediction,’`.

## What was changed

- The content was moved into the official IEEE Transactions template (styles, two-column
  geometry, header, first-page footnote, `[n]` reference numbering, biography).
- Sections are numbered I–XIII with lettered subsections. Equations are numbered (1)–(9).
  Figures are "Fig. n." with IEEE-style captions.
- In-text citations were added throughout. [9] and [10] now have full bibliographic data.
- Six well-known references were added: [11]–[12] (chain-of-thought), [13]–[16] (Self-Refine,
  Chain-of-Verification, multiagent debate, Constitutional AI). They support a new Related Work
  subsection III-B (self-critique and verification), which a reviewer would expect next to the
  dual-lobe supervisor.
- The truncated sentence was rewritten to state only what [10] reports: modest accuracy gains,
  more computation, and persistent hallucinations. The "~30%" figure could not be verified.
- All figures were redrawn as white-background, column-width vector graphics. A new Fig. 5
  shows the dual-lobe architecture.
- The prose was lightly copy-edited for clarity. Claims, structure, and hypotheses are
  unchanged. A sentence in Section XI now states that the work is conceptual and the hypotheses
  still need empirical validation.

## You must complete before uploading (highlighted yellow in the .docx)

- First-page footnote: funding statement, department, institution, address, e-mail.
- Biography: degree, field, university, year, current position, pronoun. Deleting the
  biography is also acceptable for review.
- Check the author name spelling. Add an IEEE membership grade after the name if you have one.
- Remove all yellow highlighting.
