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

---

## Dataset options (scouted 2026-06-20)
What we need: hourly ventilator settings (VT, RR, PEEP, peak/plateau pressure) + arterial blood gases, in a ventilated population.

| Dataset | Size | Vent data | Access friction | Shareable w/ Claude? |
|---|---|---|---|---|
| **MIMIC-IV demo** | 100 patients | sparse | **None — open license, download today** | Likely yes (open ODbL license) |
| MIMIC-IV (full) | ~tens of thousands ventilated | good | credentialed — **you already have it** | No (credentialed) |
| AmsterdamUMCdb | 23,106 admissions | **richest respiratory** | CITI course + signed license + a **reference intensivist** (~5 days) | No |
| HiRID | ~33k | high time-resolution | PhysioNet credentialed | No |
| eICU | ~200k | moderate | PhysioNet credentialed | No |
| VitalDB | ~6k | OR ventilator waveforms | open (no credentialing) | likely yes — but OR/anaesthesia (healthy lungs) → physics checks only, not ARDS |

**Honest conclusion:** there is **no large, ARDS-rich, fully-open** ventilator dataset — but we **don't need ARDS-rich data**: the model targets *all* ventilated patients, so a general ventilated cohort (MIMIC or its open demo) is perfectly suitable. The richer respiratory DBs (Amsterdam/HiRID) need the *same or more* credentialing than MIMIC anyway. So the smart path is two-stage:
1. **Build + test the pipeline NOW on the open MIMIC-IV demo** (zero friction, likely shareable).
2. **Do the real accuracy run on the full MIMIC-IV you already have** (lowest extra friction), or AmsterdamUMCdb if you want the richest respiratory data.

**Caveat (true of every dataset):** measured *plateau* pressure is rarely charted (it needs an inspiratory-hold maneuver). We may validate against *peak* / driving pressure instead — the same reason your manuscript used the dynamic (peak-based) MP. Confirm by checking the dataset's column list.
