# Manuscript Review Notes — Action Items Before Submission

Review date: March 2026
Target journal: Anesthesia & Analgesia (IARS, Wolters Kluwer/LWW)
Submission portal: https://www.editorialmanager.com/aa/

---

## Placeholders That Must Be Filled

The following items in `MANUSCRIPT_MEDICAL_JOURNAL.md` contain placeholder text that must be completed before submission:

### Author Information (Line 3-9)
- `[Your Name, MD/MBBS]` — Replace with full author name(s) and credentials
- `[Co-author(s)]` — Add all contributing authors
- `[Your Institution]` — Department and institutional affiliation
- `[Additional affiliations if applicable]` — Secondary affiliations
- `[Your contact information]` — Corresponding author email and address

### Acknowledgments Section (Line 559)
- `[collaborators, technical support staff, funding sources]` — List specific contributors

### Funding Statement (Line 563)
- `[Specify funding sources or "No external funding received"]`

### Data Availability (Line 565)
- `[repository URL if applicable]` — Add the GitHub/repository URL once published

### Citation in README.md
- `[Author names]` and `[Year]` — Update with actual author list and publication year

### LICENSE file
- `[Author Name / Institution]` — Update copyright holder

---

## Formatting Considerations for A&A

1. **Word count**: A&A typically allows 3,000-4,000 words for original research articles (excluding abstract, references, tables, figures). The current manuscript is approximately 6,000+ words — consider trimming the Discussion section.

2. **Abstract format**: A&A uses a structured abstract (Background, Methods, Results, Conclusions) limited to 250 words. The current abstract appears to exceed this. Verify against current author guidelines.

3. **References**: A&A uses numbered superscript citations in Vancouver/NLM style. The current manuscript uses superscript numbers, which is correct. Verify all 15 references are formatted per journal requirements.

4. **Tables and Figures**: A&A requires tables and figures as separate files, not embedded in the manuscript body. You will need to extract Tables 1-3 and Figures 1-3 into separate files for submission.

5. **Figures**: The ASCII-art architecture diagrams (Figures 1-3) should be replaced with proper vector graphics (PDF, EPS, or high-resolution TIFF). Consider creating these in a tool like draw.io, Lucidchart, or PowerPoint.

6. **Cover letter**: A&A requires a cover letter stating originality, conflicts of interest, and that the work has not been published elsewhere.

7. **IRB statement**: The manuscript mentions IRB exemption (Line 105). Ensure you have documentation of this determination.

8. **MIMIC-III data use**: Verify compliance with the PhysioNet Data Use Agreement regarding publication of derived results.

---

## Manuscript Strengths

- Well-structured IMRaD format
- Clear clinical framing for the anesthesia audience
- Good limitations section with honest assessment
- Practical clinical scenarios in the Discussion
- Reasonable future directions with phased validation plan

## Manuscript Weaknesses to Address

1. **Confidence score is static (0.85)**: The Discussion (Section 4.5.3) acknowledges this, but reviewers will likely flag it. Consider reframing as "similarity threshold" rather than "confidence."

2. **No comparison to baseline**: No formal comparison to keyword search or manual review. Consider adding even a simple keyword-match baseline for the same query set.

3. **Single dataset evaluation**: Only MIMIC-III critical care data. Acknowledge the generalizability limitation more prominently.

4. **"Retrieval success rate: 98.7%"**: The denominator (1,703 queries) appears in the manuscript but the testing methodology for these queries isn't detailed. Clarify how query success was defined and measured.

5. **ClinicalBERT vs. newer models**: Reviewers may ask why ClinicalBERT was chosen over more recent models (PubMedBERT, BiomedBERT, etc.). Strengthen the justification in Section 4.4.1.
