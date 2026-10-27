# -*- coding: utf-8 -*-
"""v11 冻结规则：分节感知 + 修正否定语义 + 严重程度取最高级。

关键修订（相对 v10，全部有对抗性测试用例）：
1) 分节：只在 FINDINGS / IMPRESSION 段内判定阳性；INDICATION / HISTORY /
   CLINICAL HISTORY / REASON FOR EXAM / COMPARISON / TECHNIQUE 段内的提及仅计
   为"语境提及"，不计为阳性。若报告无 FINDINGS/IMPRESSION 段，则退化为全文
   （排除上述语境段的标题行）。
2) "no interval change" / "no significant interval change" / "no change" 表示
   病灶持续存在，不再作为否定词；从回看窗口中先剔除这些短语再匹配否定词。
3) 术语后置的转归表述（"cardiomegaly has resolved"）判为阴性。
4) 严重程度：在全部阳性句中取最高级；"mild to moderate" 取较高级；无修饰词
   记 unspec。
"""
import re

CM_RE = re.compile(r"(?i)cardiomegaly")

SENT_SPLIT = re.compile(r"(?<=[.;:\n])\s+")

# ---- 分节 ----
SECTION_RE = re.compile(
    r"(?im)^[ \t>]*(FINDINGS|IMPRESSION|INDICATION|HISTORY|CLINICAL HISTORY|"
    r"REASON FOR EXAM(?:INATION)?|COMPARISON|TECHNIQUE|EXAMINATION|EXAM)[ \t]*:")
FIND_SECTIONS = {"FINDINGS", "IMPRESSION"}
CTX_SECTIONS = {"INDICATION", "HISTORY", "CLINICAL HISTORY", "REASON FOR EXAM",
                "REASON FOR EXAMINATION", "COMPARISON", "TECHNIQUE",
                "EXAMINATION", "EXAM"}

# ---- 否定 ----
NEG_CUE = re.compile(
    r"(?i)(\bno\b|\bnot\b|\bwithout\b|\babsent\b|\bnegative\s+for\b|"
    r"\bno\s+evidence\s+of\b|\bresolution\s+of\b|\bresolved\b|\bfree\s+of\b|"
    r"\br/o\b|\brule\s+out\b|\bno\s+definite\b|\bno\s+significant\b|"
    r"\bno\s+new\b)")

# 表示"持续存在"的短语：先从句中剔除，避免其 "no" 触发否定
PERSIST_RE = re.compile(
    r"(?i)\bno\s+(?:significant\s+|appreciable\s+|substantial\s+)?"
    r"(?:interval\s+)?change(?:s)?(?:\s+in(?:\s+the)?)?\b")

# 术语之后的转归否定
POST_NEG_RE = re.compile(
    r"(?i)^[^.;:\n]{0,40}?\b(?:has\s+|have\s+|is\s+|was\s+)?(?:now\s+)?"
    r"(?:resolved|cleared|no\s+longer\s+(?:present|seen|identified|evident))\b")

# ---- 严重程度 ----
GRADE_WORDS = r"(mild|moderate|severe|marked|massive|gross)"
SEV_PRE = re.compile(
    r"(?i)\b" + GRADE_WORDS + r"\b"
    r"(?:\s*(?:-|\u2013|to|and|/)\s*(mild|moderate|severe|marked|massive|gross)\b)?"
    r"[\s,\-]{0,3}(?:[A-Za-z]+[\s,\-]{1,3}){0,1}cardiomegaly")
SEV_POST = re.compile(
    r"(?i)cardiomegaly\s*(?:,\s*|\s+is\s+|\s+appears?\s+|\s+was\s+)?"
    r"(mild|moderate|severe|marked|massive|gross)\b")

SEV_MAP = {"mild": "mild", "moderate": "mod_sev", "severe": "mod_sev",
           "marked": "mod_sev", "massive": "mod_sev", "gross": "mod_sev"}
SEV_RANK = {"unspec": 0, "mild": 1, "mod_sev": 2}


def split_sections(text):
    """返回 [(section_name_or_None, body), ...]"""
    marks = [(m.start(), m.end(), m.group(1).upper()) for m in SECTION_RE.finditer(text)]
    if not marks:
        return [(None, text)]
    blocks = []
    if marks[0][0] > 0:
        blocks.append((None, text[:marks[0][0]]))
    for i, (s, e, name) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.append((name, text[e:stop]))
    return blocks


def peel_first_sentence(body):
    """剥掉语境段的首句（指征句），其余视为正文。"""
    m = re.search(r"[.?!\n]", body)
    if not m:
        return ""
    return body[m.end():]


IND_CUE = re.compile(
    r"(?i)^\s*(evaluate|assess|assessment|rule\s+out|question|history\s+of|"
    r"reason\s+for|check|look\s+for|clinical\s+history|indication|status\s+post)\b")


def filter_context_block(body):
    """语境段内剔除指征句，保留其余句子（正文常跟在指征之后）。"""
    kept = []
    for i, s in enumerate(SENT_SPLIT.split(body)):
        st = s.strip()
        if not st:
            continue
        if i == 0:                      # 指征几乎总在首句
            continue
        if st.endswith("?"):
            continue
        if IND_CUE.match(st):
            continue
        kept.append(st)
    return " ".join(kept)


def _grade(word1, word2=None):
    if word2:
        a, b = SEV_MAP.get(word1.lower()), SEV_MAP.get(word2.lower())
        return b if SEV_RANK[b] > SEV_RANK[a] else a
    return SEV_MAP.get(word1.lower(), "unspec")


def label_report(text):
    """返回 (exposed, severity, n_mention, n_negated, n_context_only, section)"""
    if not text:
        return 0, "none", 0, 0, 0, "none"

    t = str(text).replace("\r", " ")
    blocks = split_sections(t)
    names = [b[0] for b in blocks]
    has_find = any(n in FIND_SECTIONS for n in names)

    # 语境段（INDICATION / HISTORY / REASON FOR EXAM ...）里既可能是指征句，也可能
    # 紧跟着真正的正文。整段丢弃会漏掉真阳性，故改为句级过滤：剔除指征句（首句、
    # 以问号结尾者、或以 Evaluate/Assess/Question 等开头者），其余按正文处理。
    usable = []
    for n, b in blocks:
        if n in FIND_SECTIONS or n is None:
            usable.append((n, b))
        else:
            usable.append((n, filter_context_block(b)))
    if has_find:
        section = "+".join(sorted({n or "BODY" for n, _ in usable}))
    else:
        section = "whole_text"

    n_mention = n_neg = n_ctx = 0
    best = "unspec"
    positive = False

    for name, body in usable:
        for sent in SENT_SPLIT.split(body):
            if not CM_RE.search(sent):
                continue
            span = len(sent)
            for m in CM_RE.finditer(sent):
                n_mention += 1
                start = max(0, m.start() - 40)
                window = sent[start:m.start()]
                window = PERSIST_RE.sub(" ", window)      # 持续存在短语不构成否定
                tail = sent[m.end():m.end() + 45]
                neg = bool(NEG_CUE.search(window)) or bool(POST_NEG_RE.search(tail))
                if neg:
                    n_neg += 1
                    continue
                positive = True
                # 严重程度：优先前置，其次后置；取最高级
                g = "unspec"
                for mm in SEV_PRE.finditer(sent):
                    g2 = _grade(mm.group(1), mm.group(2) if mm.lastindex and mm.lastindex >= 2 else None)
                    if SEV_RANK[g2] > SEV_RANK[g]:
                        g = g2
                if g == "unspec":
                    mm = SEV_POST.search(sent)
                    if mm:
                        g = _grade(mm.group(1))
                if SEV_RANK[g] > SEV_RANK[best]:
                    best = g
            continue

    if not has_find:
        # 没有 FINDINGS/IMPRESSION：统计仅出现在语境段的提及，便于审计
        for name, body in blocks:
            if name in CTX_SECTIONS and CM_RE.search(body):
                n_ctx += len(CM_RE.findall(body))

    if not positive:
        return 0, "none", n_mention, n_neg, n_ctx, section
    return 1, best, n_mention, n_neg, n_ctx, section
