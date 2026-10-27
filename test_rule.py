# -*- coding: utf-8 -*-
"""Run the frozen cardiomegaly rule against the 29 synthetic test reports of
Supplementary Table S3.

The reports in synthetic_test_reports.tsv are hand-written probes, not patient
records; they run without any access to MIMIC-IV. Both the exposure label and
the severity grade are checked against the expected value of each probe, because
the manuscript states that all 29 returned the expected label and grade.

    python test_rule.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rule_cardiomegaly import label_report  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = os.path.join(HERE, "synthetic_test_reports.tsv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    ok_label = ok_grade = 0
    fails = []
    for r in rows:
        text = r["report_text"].replace("\\n", "\n")
        exposed, grade = label_report(text)[:2]
        exp_label = int(r["expected_exposed"])
        exp_grade = r["expected_grade"]

        good_label = int(exposed) == exp_label
        good_grade = grade == exp_grade
        ok_label += good_label
        ok_grade += good_grade
        good = good_label and good_grade
        if not good:
            fails.append((r["id"], r["property_tested"], exp_label, int(exposed),
                          exp_grade, grade, good_label, good_grade))
        print("%s  %-2s exp=%d got=%d grade=%-7s (exp %-7s) %s"
              % ("ok  " if good else "FAIL", r["id"], exp_label, int(exposed),
                 grade, exp_grade, r["property_tested"]))

    print("\n%d / %d synthetic reports returned the expected label" % (ok_label, len(rows)))
    print("%d / %d synthetic reports returned the expected grade" % (ok_grade, len(rows)))
    if fails:
        print("failures:")
        for f in fails:
            print("  id=%s  %s  label %s vs %s (ok=%s)  grade %s vs %s (ok=%s)"
                  % (f[0], f[1], f[3], f[2], f[6], f[5], f[4], f[7]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
