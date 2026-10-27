# -*- coding: utf-8 -*-
"""检查类型判定器 v3（本地无 radiology_detail，依据"检查名行"判定模态）

判定规则
A. 逐行扫描报告头部（前 1200 字符），把满足下列全部条件的行视为"检查名行"：
   - 长度 <= 60 字符、词数 <= 10；
   - 全大写（字母大写占比 >= 0.8），或以检查名关键词开头（CHEST/PORTABLE/AP/PA/CT/MRI/US/...）；
   - 不以 INDICATION/HISTORY/COMPARISON/FINDINGS/IMPRESSION/TECHNIQUE 等非检查名关键词开头。
B. 用检查名行判定模态：CT/CTA > MRI/MRA > US/超声 > 其他（透视、造影、核医学）> 胸部X线。
C. 找不到检查名行时，退回正文典型胸片描述（single view of the chest / portable AP …），
   记为 CXR_body；仍无法判定记为 UNKNOWN（不纳入暴露）。
"""
import re

STRICT_HDR = re.compile(
    r"(?i)^(TYPE\s+OF\s+EXAMINATION|EXAMINATION|EXAM|STUDY|PROCEDURE)\s*:\s*(.+)$")
NONEXAM = re.compile(
    r"(?i)^(INDICATION|CLINICAL\s+INDICATION|CLINICAL\s+INFORMATION|CLINICAL\s+HISTORY|"
    r"HISTORY|REASON\s+FOR|COMPARISON|FINDINGS?|IMPRESSION|TECHNIQUE|NOTE|ADDENDUM|"
    r"REPORT|SIGNED|ELECTRONICALLY|DICTATED|ATTENDING|RESULT|CONCLUSION|COMMENT|"
    r"MEDICATIONS?|ALLERGIES|VITALS|LABS|ORDER|SPECIMEN|DESCRIPTION|PATIENT|THE\s+PATIENT|"
    r"WHEN\s+THE|PICC|PORT\s+A\s+CATH|CATHETER|BLOOD|URINE|SPECIMEN)")

EXAM_START = re.compile(
    r"(?i)^((TYPE\s+OF\s+)?(EXAM(INATION)?|STUDY)|DX|CHEST|PORTABLE|SINGLE|VIEW|(^|\s)AP(\s|$)|PA\b|LATERAL|LAT\b|"
    r"RIB|CT|CTA|MRI|MR\b|MRA|US\b|ABDOMEN|ABDOMINAL|HEAD|NECK|SPINE|PELVIS|CARDIAC|"
    r"FLUOROSCOP|ANGIOGRAPH|ANGIO\b|PET\b|MAMMOGRAPH|BONE\s+DENSIT|KUB|EXTREMITY|"
    r"BILATERAL|LOWER|UPPER|SOFT\s+TISSUE|DOPPLER|ULTRASOUND|ECHO)")

CT_RE = re.compile(r"(?i)(\bCT\b|COMPUTED\s+TOMOGRAPH|\bCTA\b|\bMDCT\b|\bPET[- ]CT\b)")
MRI_RE = re.compile(r"(?i)(\bMRI\b|MAGNETIC\s+RESONANCE|\bMRA\b|MR\s+ANGIOGRAPH)")
US_RE = re.compile(r"(?i)(ULTRASOUND|SONOGRAPH|DOPPLER|\bECHOCARDIOGRAM|\bTEE\b|(^|\W)US(\W|$))")
OTH_RE = re.compile(r"(?i)(FLUOROSCOP|ANGIOGRAPH|NUCLEAR|SCINTIGRAPH|\bPET\b|MAMMOGRAPH|"
                    r"RADIATION\s+THERAPY|LOCALIZATION|BONE\s+DENSIT|KUB)")
CHEST_RE = re.compile(r"(?i)(CHEST|RIB|THORAX|PORTAB|PORT\.|PLCMT|LINE|TUBE)")
CXR_CUES = re.compile(r"(?i)(PORTABLE|PORT\.|(^|\W)AP(\W|$)|(^|\W)PA(\W|$)|LATERAL|LAT\b|"
                      r"SINGLE\s+VIEW|TWO\s+VIEWS|2\s+VIEWS|FRONTAL|RADIOGRAPH|X-?RAY|"
                      r"(^|\W)XR(\W|$)|DECUBITUS|UPRIGHT|SUPINE|EXPIRATORY|VIEW|PLCMT|LINE|TUBE)")

NOT_CHEST = re.compile(
    r"(?i)(ABDOMEN|ABDOMINAL|KUB|HIP|KNEE|FEMUR|TIBIA|ANKLE|FOOT|SHOULDER|HUMERUS|WRIST|"
    r"HAND\b|FOREARM|CLAVICLE|CAROTID|HEAD\b|NECK\b|SPINE|CERVICAL|THORACIC\s+SPINE|"
    r"LUMBAR|PELVIS|SACRUM|ERCP|CHOLANGIO|LIVER|KIDNEY|RENAL|BLADDER|TESTES|BREAST|"
    r"MAMMOGRAPH|THYROID|ORBIT|FACIAL|SINUS|DENTAL|PROSTATE|UTERUS|OVARY)")

BODY_CXR = re.compile(
    r"(?i)(single\s+view\s+of\s+the\s+chest|frontal\s+radiograph\s+of\s+the\s+chest|"
    r"pa\s+and\s+lateral|portable\s+ap|ap\s+view\s+of\s+the\s+chest|"
    r"pa\s+view\s+of\s+the\s+chest|lateral\s+view\s+of\s+the\s+chest|chest\s+radiograph|"
    r"radiograph\s+of\s+the\s+chest|ap\s+upright|ap\s+supine|semi-?erect|"
    r"chest\s+(ap|pa)\s+(single\s+)?view|chest\s+x-?ray|portable\s+chest|"
    r"(ap|pa)\s+portable|frontal\s+view\s+of\s+the\s+chest|ap\s+portable\s+view|"
    r"single\s+ap\s+portable\s+view|portable\s+view\s+of\s+the\s+chest|"
    r"views?\s+of\s+the\s+chest|chest\s+(x-?ray|radiograph|film)|"
    r"single\s+(upright|ap|pa|frontal)\s+view)")

BODY_MODAL = re.compile(
    r"(?i)(multidetector\s+CT|CT\s+of\s+the\s+chest|CT\s+of\s+the\s+thorax|computed\s+tomograph|"
    r"contiguous\s+axial|axial\s+images|slice\s+thickness|intravenous\s+contrast|"
    r"magnetic\s+resonance|sonograph|ultrasound|fluoroscop)")

TECH_LINE = re.compile(r"(?im)^\s*TECHNIQUE\s*:\s*(.+)$")


def _norm(s):
    s = s.replace("___", "X")
    return re.sub(r"\s+", " ", s).strip()


def _all_caps(s):
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) >= 0.8


def _exam_like(s):
    if not s or len(s) > 60:
        return False
    if len(s.split()) > 10:
        return False
    if NONEXAM.match(s):
        return False
    return _all_caps(s) or bool(EXAM_START.match(s))


def find_exam_line(text, n=1200):
    for raw in (text or "")[:n].split("\n"):
        s = _norm(raw)
        if not _exam_like(s):
            continue
        m = STRICT_HDR.match(s)
        cand = m.group(2).strip() if m else s
        U = cand.upper()
        if CT_RE.search(U):
            return cand, "CT"
        if MRI_RE.search(U):
            return cand, "MRI"
        if US_RE.search(U):
            return cand, "US"
        if OTH_RE.search(U):
            return cand, "OTHER"
        if NOT_CHEST.search(U) and not CHEST_RE.search(U):
            return cand, "OTHER"
        if CHEST_RE.search(U) and CXR_CUES.search(U):
            return cand, "CXR"
        if CHEST_RE.search(U) and len(U.split()) <= 6:
            return cand, "CXR"
    return "", ""


def classify(text):
    t = text or ""
    line, kind = find_exam_line(t)
    if kind:
        src = "header" if STRICT_HDR.match(_norm(line)) else "examline"
        return kind, line, src
    # TECHNIQUE 行
    m = TECH_LINE.search(t[:1500])
    if m:
        tech = _norm(m.group(1))
        U = tech.upper()
        if CT_RE.search(U):
            return "CT", tech, "technique"
        if MRI_RE.search(U):
            return "MRI", tech, "technique"
        if US_RE.search(U):
            return "US", tech, "technique"
        if CHEST_RE.search(U) and CXR_CUES.search(U):
            return "CXR", tech, "technique"
    # 正文描述
    if BODY_MODAL.search(t[:800]):
        return "NONCXR_body", "", "body"
    if BODY_CXR.search(t[:1200]):
        return "CXR_body", "", "body"
    return "UNKNOWN", line, "none"


CXR_TYPES = {"CXR", "CXR_body"}
