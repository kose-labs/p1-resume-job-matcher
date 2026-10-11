# S6 results: PDF parser comparison

Synthetic fixtures (6) and real CVs (0). Times are the median of 5 runs; memory is the peak of the whole Python process (interpreter + library + extraction).

| Parser | Version · licence | One column | Two columns (column order) | Two columns (row order) | 3 pages | Scanned PDF flagged | Encrypted | Median ms / file | Peak MB |
|---|---|---|---|---|---|---|---|---|---|
| pypdf | 6.20.0 · BSD-3-Clause | 98% | 97% | 74% | 98% | yes | fails cleanly (UnreadablePdf) | 3.1 | 104 |
| pdfplumber | 0.11.10 · MIT | 98% | 74% | 74% | 98% | yes | fails cleanly (PdfminerException) | 12.0 | 93 |
| pdfplumber-columns | 0.11.10 · MIT | 98% | 97% | 97% | 98% | yes | fails cleanly (PdfminerException) | 12.3 | 80 |
| pymupdf | 1.28.2 · AGPL-3.0 or commercial | 100% | 100% | 76% | 100% | yes | fails cleanly (UnreadablePdf) | 1.9 | 164 |
| pymupdf-sorted | 1.28.2 · AGPL-3.0 or commercial | 100% | 76% | 76% | 100% | yes | fails cleanly (UnreadablePdf) | 5.1 | 164 |

Accuracy is word-level similarity to the text drawn on the page. For the two-column CV, either column first counts as correct; interleaved columns score low.
