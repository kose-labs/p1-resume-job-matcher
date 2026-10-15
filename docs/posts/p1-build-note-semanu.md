# P1 build note (Semanu, engineering angle)

**Status:** draft, for Kobi to review · publish around the mid-project check (J3)
**Lesson:** a passing test can still be wrong, so break the code on purpose to prove a test works.

---

**Build note from our Resume–Job Matcher: a passing test can still be wrong.**

This week I started asking one question about every test: *what change would make this fail?*

📄 **The bug our tests hid.** Our PDF reader splits two-column CVs into columns. On our test CVs it
scored 97%, against 74–76% for the PDF libraries on their own. Then, moving it into the API, a new
test CV with short lines in the right column came out scrambled: the code took the empty space after
those short lines for the gap between the columns. The fix was one rule, a real gap has text on both
sides. The old tests passed only because every test CV happened to have long lines.

🧪 **So now I break the code on purpose.** Our API has to keep its health check fast while CVs are
being matched. To prove the test guards that, I moved the matching back onto the server's main loop:
the health check took 1.5 s instead of under a quarter of a second, and the test failed. Same for
privacy: making the code log 80 characters of a job description failed two tests.

🔍 **Review works both ways.** Kobi caught a rate-limit bypass in my pull request: a forged header
could give every request a fresh IP.

Next: plugging in the matcher and measuring it against our own ratings.

*[visual: the same two-column CV twice, with the wrong gap (after the short lines) and the real gap
(between the columns) highlighted]*

---

**Word count:** about 200 (body only).

**Checks before publishing:**
- Every number is from this week's runs: 97% vs 74–76% (S6 results table), 1.5 s (mutation check on
  #44), 80 characters / two tests (mutation check on #46). Re-run nothing; quote these.
- Kobi is happy to be named for the rate-limit review; tag her.
- No real CV in the visual: draw it from the synthetic "Jordan Example" test CV.
