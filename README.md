# Report-processing code for a study of cardiomegaly on ICU chest radiographs and in-hospital heart failure in autoimmune rheumatic disease

Code accompanying:

> **Report-based cardiomegaly on early ICU chest radiographs and in-hospital heart-failure
> diagnoses in critically ill patients with autoimmune rheumatic diseases: a MIMIC-IV cohort
> study**
> Qi Wang, Kai Wang

This repository is the versioned copy of Supplementary Code S1 of the manuscript. Everything here
runs on Python 3 with the standard library only — no third-party packages, no network access, no
database. **No patient data are included**, and no file requires access to MIMIC-IV.

## Files

| File | Contents |
|---|---|
| `rule_cardiomegaly.py` | The frozen text rule. Splits a report at its section headings, filters context sections at the sentence level, searches for `cardiomegaly`, applies the 40-character preceding negation window and the 45-character following resolution window, removes persistence phrases before the negation search, and aggregates severity as the highest grade in a report. |
| `exam_type.py` | The examination-type classifier. Identifies the examination-name line printed at the head of a report and maps it to chest radiograph, CT, MRI, ultrasound or other, with a non-chest body-site veto list; falls back to the report body and returns `UNKNOWN` when no determination can be made. |
| `synthetic_test_reports.tsv` | The 29 hand-written probe reports of Supplementary Table S3, each with the label expected under the operational definition, the expected grade, and the property it probes. |
| `test_rule.py` | Applies the rule to the 29 probes and prints the observed label and grade next to the expected ones, counting agreement on each separately. |
| `blind_review_form_blank.docx` | The empty review form used in the label-blinded review (Supplementary S3(7)): chest radiograph yes/no, heart enlarged yes/no/uncertain, stated grade, and whether every mention was confined to the history, indication or clinical question. |

## Run

```
python test_rule.py
```

Expected output ends with

```
29 / 29 synthetic reports returned the expected label
29 / 29 synthetic reports returned the expected grade
```

which is the statement made in Methods 2.2 and in Supplementary S12. The run needs no arguments,
no configuration and no data files: the probes travel with the driver.

## What this code does and does not show

Running the probes checks that the implemented rule behaves as the manuscript and Supplementary
Methods S3 say it does on the specific constructions listed in Table S3. It is a check of the
description against the implementation, not evidence that the rule is clinically correct, and it
says nothing about how the rule performs on real reports beyond the agreement statistics reported
in the paper.

Applying the rule to MIMIC-IV requires credentialed access: the report text lives in
`mimiciv_note.radiology` of the MIMIC-IV-Note module, which is distributed under its own data-use
agreement and cannot be redistributed here. The report texts used in the blinded review and the
corresponding answer key are withheld for that reason; the review can be repeated by any
credentialed user from the blank form and the sampling description in Supplementary S3.

## What this repository deliberately does not contain

- **Patient-level data of any kind** — no report text, no cohort table, no extracted variables.
  These fall under the PhysioNet data-use agreements for MIMIC-IV and MIMIC-IV-Note.
- **The cohort-assembly and model-fitting pipeline.** That pipeline reads the credentialed extract
  and produces the study tables and figures; it cannot run without the patient-level data, so
  publishing it would add no step that a reader could reproduce. The models themselves are
  specified in full in Methods 2.5–2.6 and in Supplementary Tables S4 and S6–S10, which is enough
  to re-implement them from a credentialed copy of the database.
- **Manuscript and submission build scripts.**

Researchers who need the cohort queries or the model code for peer review can contact the
corresponding author.

## Data sources

MIMIC-IV v2.2 and MIMIC-IV-Note v2.2 (Beth Israel Deaconess Medical Center) are available to
credentialed users through PhysioNet under their respective data-use agreements. eICU-CRD and
NWICU were used for the cross-database comparisons described in the manuscript.

## Citation

```
Wang Q, Wang K. Report-processing code for a study of cardiomegaly on early ICU chest
radiographs and in-hospital heart-failure diagnoses in critically ill patients with
autoimmune rheumatic diseases. Zenodo. 2026. doi:10.5281/zenodo.23694471
```

`10.5281/zenodo.23694471` is the version DOI of release v1.0.0; the concept DOI
(`10.5281/zenodo.23694470`) always resolves to the most recent version.

## Licence

MIT — see `LICENSE`.

## Version

v1.0.0, matching the submitted manuscript and its Supplementary Code S1. Archived at
`10.5281/zenodo.23694471`; the tag `v1.0.0` is frozen at that archive.
