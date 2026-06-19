# Data Access — getting validation data the correct (compliant) way

How we feed real patients into the model WITHOUT breaking PhysioNet's rules.

## The rule (why this exists)
PhysioNet's data-use agreement forbids sharing MIMIC patient data with third-party
AI / online services. So the data stays on **your** machine; Claude only ever sees
**aggregate** results (averages, counts, plots) — never patient rows.
(Sources: physionet.org/news/post/gpt-responsible-use · .../llm-responsible-use)

## Who does what
- **Credentialed user** (whoever completed the PhysioNet + CITI credentialing): downloads and runs everything that touches patient data.
- **Claude:** writes the code; reads only the aggregate output you paste back.

## Step-by-step (used when we start Track B)
1. Confirm **who is credentialed** on PhysioNet (the manuscript notes one investigator was). That person does steps 2–5.
2. Download the hourly dataset used in the manuscript: **"A Temporal Dataset for Respiratory Support in Critically Ill Patients" (v1.1.0)** from PhysioNet (plus MIMIC-IV v3.1 if outcome links are needed).
3. Save the files in a local folder **outside this git repo** (we never commit patient data).
4. Paste Claude only the **column names / data dictionary** (just the field-name list) so the loader can map them. Field names are not patient data → safe.
5. Run locally: `python engine/validate_mimic.py <path-to-your-data>`. Paste back only the printed **aggregate results**. Any plots save locally for your eyes only.

## Safe vs not-safe to share with Claude
| ✅ Safe | 🚫 Never |
|---|---|
| Column / field names | Individual patient rows |
| Data dictionary | Identifiers (subject_id values, dates) |
| Aggregate stats (means, SDs, counts) | Raw extracts / CSV dumps |
| Error tables, distribution summaries | Anything traceable to one patient |

**If ever unsure whether something is safe to paste — don't, and ask first.**
