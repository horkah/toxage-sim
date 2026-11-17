"""Build the figures of the risk models and the project overview as HTML.

The numbers in the figures of the risk models come from the model
configuration (risk-model/config/models.json) and from the calculations of
risk-model/models.py, the references from background/references.md. After a
change of the models, run this script and render.mjs again (just figures).

Usage: python3 background/figures/build.py
"""
import html
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "risk-model"))

import models  # noqa: E402

CFG = models.load_config()
REFERENCES = (REPO / "background" / "references.md").read_text(encoding="utf-8")

REGIMENS = {
    "nalirifox": "NALIRIFOX",
    "gemcitabine_nab_paclitaxel": "Gem/nab-paclitaxel",
    "adt_docetaxel": "ADT + docetaxel",
    "adt_docetaxel_abiraterone": "ADT + doc + abiraterone",
    "adt_docetaxel_darolutamide": "ADT + doc + darolutamide",
    "lu_psma_617": "<sup>177</sup>Lu-PSMA-617",
    "olaparib": "Olaparib",
    "trastuzumab_deruxtecan": "Trastuzumab deruxtecan",
    "chemotherapy_single_agent": "Single-agent chemo",
    "pembrolizumab_chemotherapy": "Pembrolizumab + chemo",
    "sacituzumab_govitecan": "Sacituzumab govitecan",
}

E = html.escape


def pct(x, digits=None):
    """A probability in percent: one decimal below 10%, else none."""
    if digits is None:
        digits = 1 if x < 0.1 else 0
    return f"{100 * x:.{digits}f}%"


def ratio(v):
    """A ratio with two decimals, three where it is close to 1."""
    return f"{v:.3f}" if abs(v - 1) < 0.05 else f"{v:.2f}"


def m(text):
    """A variable in the italic serif of the formulas."""
    return f'<span class="m">{text}</span>'


# References ------------------------------------------------------------------

CITATION = re.compile(r"((?:de |Di |van )?[A-Z][A-Za-zà-ÿ'-]+) et al\.(?:,| \() ?((?:19|20)\d\d)")


def anchor(name, year):
    """Anchor of a reference: "Lizée", 2019 -> "lizee-2019"."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") + f"-{year}"


def cited(*texts):
    """Anchors of the references cited in the texts, in the order of the reference list."""
    found = {anchor(n, y) for t in texts for n, y in CITATION.findall(t)}
    order = re.findall(r'^<a id="([a-z0-9-]+)"></a>', REFERENCES, re.M)
    return [a for a in order if a in found]


def short_reference(key):
    """A reference in short form: first author, et al., journal, volume, year."""
    line = next(l for l in REFERENCES.splitlines() if l.startswith(f'<a id="{key}"></a>'))
    text = line.split("</a>", 1)[1]
    first = text.split(",", 1)[0].strip()
    year = re.search(r"\((\d{4})\)", text).group(1)
    authors = text.split(f"({year})", 1)[0]
    several = authors.count(".,") > 1 or "&" in authors
    journal = re.search(r"\*([^*]+)\*,", text)
    volume = re.search(r"\*,\s*\*(\d+)\*", text)
    source = journal.group(1) if journal else ""
    source = source.replace("The New England Journal of Medicine", "N Engl J Med").replace(
        "Journal of Clinical Oncology", "J Clin Oncol").replace("Annals of Oncology", "Ann Oncol").replace(
        "European Heart Journal", "Eur Heart J").replace("British Journal of Cancer", "Br J Cancer").replace(
        "Journal of Thoracic Oncology", "J Thorac Oncol").replace("Nature Reviews Clinical Oncology", "Nat Rev Clin Oncol").replace(
        "Cancer Treatment Reviews", "Cancer Treat Rev").replace("JAMA Network Open", "JAMA Netw Open").replace(
        "European Urology", "Eur Urol").replace("The Lancet", "Lancet")
    vol = f" {volume.group(1)}" if volume else ""
    return f"{E(first)}{' et al.' if several else ''} {source}{vol} ({year})"


def config_texts(block):
    """All sources and bases of a block of the model configuration."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("source", "basis", "description", "rate_note", "prior_event_note", "regimen_shares_basis") and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
    walk(block)
    return out


# Pieces ----------------------------------------------------------------------

def dot_plot(value, assumed, width=158, height=18):
    """A ratio as a dot on a log scale from 0.1 to 10, with a line at 1.
    Filled green: published value; open grey: assumption."""
    x = lambda v: 6 + (math.log10(v) + 1) / 2 * (width - 12)
    ticks = "".join(f'<line x1="{x(t):.1f}" y1="{height / 2 - 3}" x2="{x(t):.1f}" y2="{height / 2 + 3}" stroke="#c9d1d4"/>'
                    for t in (0.1, 0.5, 2, 10))
    cx = x(min(10, max(0.1, value)))
    dot = (f'<circle cx="{cx:.1f}" cy="{height / 2}" r="4.6" fill="#fff" stroke="#9aa6ab" stroke-width="1.6"/>' if assumed
           else f'<circle cx="{cx:.1f}" cy="{height / 2}" r="4.6" fill="#179c7d"/>')
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<line x1="6" y1="{height / 2}" x2="{width - 6}" y2="{height / 2}" stroke="#e3e8ea"/>{ticks}'
            f'<line x1="{x(1):.1f}" y1="1" x2="{x(1):.1f}" y2="{height - 1}" stroke="#5d6a70" stroke-width="1"/>{dot}</svg>')


def axis_row(width=158):
    """Labels of the log scale above the dot plots."""
    x = lambda v: 6 + (math.log10(v) + 1) / 2 * (width - 12)
    labels = "".join(f'<text x="{x(t):.1f}" y="10" text-anchor="{a}">{l}</text>'
                     for t, l, a in ((0.1, "0.1", "start"), (0.5, "0.5", "middle"), (1, "1", "middle"),
                                     (2, "2", "middle"), (10, "10", "end")))
    return (f'<svg width="{width}" height="13" viewBox="0 0 {width} 13" font-size="10" fill="#5d6a70" '
            f'font-family="Inter, sans-serif">{labels}</svg>')


def predictors(rows, kind):
    """Table of the factors: [(label, detail, value, assumed)]. kind: odds or hazard ratio."""
    body = "".join(
        f'<tr><td class="name">{label}{f"<small>{detail}</small>" if detail else ""}</td>'
        f'<td class="val">{ratio(v)}</td><td class="plot">{dot_plot(v, assumed)}</td></tr>'
        for label, detail, v, assumed in rows)
    legend = ('<div class="legend">'
              '<span><svg width="12" height="12"><circle cx="6" cy="6" r="4.6" fill="#179c7d"/></svg> published</span>'
              '<span><svg width="12" height="12"><circle cx="6" cy="6" r="4.2" fill="#fff" stroke="#9aa6ab" stroke-width="1.6"/></svg> assumption</span>'
              f'<span>{kind}, log scale; 1 = no effect</span></div>')
    short = "OR" if kind.startswith("odds") else "HR"
    return (f'<table class="pred"><tr class="head"><td></td><td class="val small">{short}</td>'
            f'<td class="plot">{axis_row()}</td></tr>{body}</table>{legend}')


def assumed(entry):
    """True if a value of the configuration is an assumption."""
    return entry.get("basis", "").lower().startswith("assumption")


def categories(c):
    """The risk categories as a thin scale with the thresholds."""
    low, high = c["intermediate_from"], c["high_from"]
    w = 268
    seg = [(1, w / 3, "#179c7d", "low"), (w / 3, 2 * w / 3, "#7fbfae", "intermediate"), (2 * w / 3, w - 1, "#005b7f", "high")]
    lines = "".join(f'<line x1="{a + 1:.1f}" y1="6" x2="{b - 1:.1f}" y2="6" stroke="{c_}" stroke-width="3"/>'
                    f'<text x="{(a + b) / 2:.1f}" y="34" font-size="11" text-anchor="middle" fill="#5d6a70" font-family="Inter">{name}</text>'
                    for a, b, c_, name in seg)
    marks = "".join(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="12" stroke="#1f2a30"/>'
                    f'<text x="{x:.1f}" y="21" font-size="10.5" text-anchor="middle" fill="#1f2a30" font-family="Inter">{pct(v)}</text>'
                    for x, v in ((w / 3, low), (2 * w / 3, high)))
    return f'<div class="scale"><svg width="{w}" height="38" viewBox="0 0 {w} 38">{lines}{marks}</svg></div>'


def props(items):
    """The properties column: [(term, html)]."""
    return '<dl class="props">' + "".join(f"<dt>{t}</dt><dd>{d}</dd>" for t, d in items) + "</dl>"


def rates_table(rows, head=None, two=False):
    """Table of regimens with their rate and reference risk: [(name, rate, r0 or None)].
    two=True splits the rows into two tables side by side."""
    def table(part):
        head_html = ""
        if head:
            head_html = "<tr class=\"head\">" + "".join(f'<td class="{c}">{h}</td>' for c, h in head) + "</tr>"
        body = "".join(f'<tr><td>{n}</td><td class="r">{pct(r)}</td>'
                       + (f'<td class="r0">{pct(r0)}</td>' if r0 is not None else "") + "</tr>" for n, r, r0 in part)
        return f'<table class="rates">{head_html}{body}</table>'
    if not two:
        return table(rows)
    half = (len(rows) + 1) // 2
    return f'<div class="two">{table(rows[:half])}{table(rows[half:])}</div>'


def example(who, steps, alt=""):
    """A worked example: the patient, the steps of the calculation, a comparison."""
    lines = "".join(f'<div class="step">{s}</div>' for s in steps)
    return (f'<div class="sub">Example</div><div class="example"><div class="who">{who}</div>{lines}'
            + (f'<div class="alt">{alt}</div>' if alt else "") + "</div>")


def odds_steps(r, terms, risk):
    """Steps of a logistic model: odds of the reference, product of the ratios, risk."""
    product = math.prod(x for *_, x in terms)
    factors = " &middot; ".join(ratio(x) for *_, x in terms if abs(x - 1) > 1e-9)
    return [f"OR = {factors} = {product:.2f}",
            f"odds = {r:.3f}/{1 - r:.3f} &middot; {product:.2f} = {r / (1 - r) * product:.2f}",
            f'{m("p")} = odds/(1 + odds) = <span class="result">{pct(risk)}</span>']


def hazard_steps(r0, terms, risk):
    """Steps of a proportional hazards model: product of the ratios, risk."""
    product = math.prod(x for *_, x in terms)
    factors = " &middot; ".join(ratio(x) for *_, x in terms if abs(x - 1) > 1e-9)
    return [f"HR = {factors} = {product:.2f}",
            f'{m("p")} = 1 &minus; (1 &minus; {r0:.3f})<sup>{product:.2f}</sup> = <span class="result">{pct(risk)}</span>']


def page(cols, refs, title):
    """The whole figure: three columns and the references."""
    ref_html = "".join(f"<span>{short_reference(k)}</span>" for k in refs)
    wide = f'\n<div class="wide">{cols[3]}</div>' if len(cols) > 3 else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="figures.css"></head>
<body><div id="figure"{' class="has-wide"' if wide else ""}>
<div class="col">{cols[0]}</div>
<div class="col">{cols[1]}</div>
<div class="col">{cols[2]}</div>{wide}
<div class="refs"><b>References</b>{ref_html}</div>
</div></body></html>
"""


# The five models ---------------------------------------------------------------

def columns(rows, kind, reference, formula, where, ex, properties, reference_wide=False):
    """The three columns: predictors and reference risks, calculation with an
    example, properties. With many predictors the reference risks go in a band
    below the calculation and the properties (reference_wide)."""
    left = f'<div class="label">Predictors</div>{predictors(rows, kind)}{"" if reference_wide else reference}'
    middle = (f'<div class="label">Calculation</div><div class="formula">{formula}</div>'
              f'<ul class="where">{"".join(f"<li>{w}</li>" for w in where)}</ul>{ex}')
    right = f'<div class="label">Properties</div>{props(properties)}'
    return (left, middle, right, reference) if reference_wide else (left, middle, right)


def eq(text, small=False):
    """One line of a formula."""
    return f'<div class="eq{" s" if small else ""}">{text}</div>'


def severe():
    """Candidate 1: any severe toxicity within 90 days."""
    c = CFG["severe_toxicity_90d"]
    o, ref = c["odds_ratios"], c["reference_patient"]
    rows = [
        ("Age", f"per 10 years from {ref['age_years']}", o["per_10_years_of_age"]["value"], assumed(o["per_10_years_of_age"])),
        ("ECOG 2 or higher", "against 0 or 1", o["ecog_2_or_higher"]["value"], assumed(o["ecog_2_or_higher"])),
        ("Impaired geriatric domain", "per domain of seven", o["per_impaired_ga_domain"]["value"], assumed(o["per_impaired_ga_domain"])),
        ("Haemoglobin", f"per g/dl below {ref['haemoglobin_g_dl']:g}", o["per_g_dl_haemoglobin_below_reference"]["value"],
         assumed(o["per_g_dl_haemoglobin_below_reference"])),
        ("Albumin", f"per 10 g/l below {ref['albumin_g_l']:g}", o["per_10_g_l_albumin_below_reference"]["value"],
         assumed(o["per_10_g_l_albumin_below_reference"])),
        ("Reduced starting dose", f"dose level below {c['thresholds']['reduced_starting_dose_below']:g}",
         o["reduced_starting_dose"]["value"], assumed(o["reduced_starting_dose"])),
    ]
    reference = ('<div class="sub">Reference risk: published rate of the regimen</div>'
                 + rates_table([(REGIMENS[k], v["rate"], None) for k, v in c["regimen_rates"].items()], two=True))
    patient = {"regimen": "trastuzumab_deruxtecan", "age_years": 75, "ecog": 2, "ga_impaired_domains": 2,
               "haemoglobin_g_dl": ref["haemoglobin_g_dl"] - 1, "albumin_g_l": ref["albumin_g_l"] - 5, "starting_dose_level": 1.0}
    r = c["regimen_rates"][patient["regimen"]]["rate"]
    ex = example(f"Trastuzumab deruxtecan ({pct(r)}); 75 years, ECOG 2, two impaired domains, "
                 f"Hb {patient['haemoglobin_g_dl']:g} g/dl, albumin {patient['albumin_g_l']:g} g/l, full dose",
                 odds_steps(r, models.severe_toxicity_terms(patient, CFG), models.severe_toxicity_risk(patient, CFG)))
    gap = {"regimen": "x", "age_years": 77, "ecog": 1, "ga_impaired_domains": 4.5, "haemoglobin_g_dl": ref["haemoglobin_g_dl"],
           "albumin_g_l": ref["albumin_g_l"], "starting_dose_level": 1.0}
    gap_risk = models.severe_toxicity_risk(gap, {"severe_toxicity_90d": dict(c, regimen_rates={"x": {"rate": 0.6}})})
    cols = columns(rows, "odds ratio", reference,
                   eq(f"logit {m('p')} = logit {m('r')}<sub>{m('R')}</sub> + &sum;<sub>{m('k')}</sub> ln(OR<sub>{m('k')}</sub>) {m('x')}<sub>{m('k')}</sub>"),
                   [f"{m('r')}<sub>{m('R')}</sub>: published rate of severe toxicity with regimen {m('R')}, the risk of the reference patient",
                    f"{m('x')}<sub>{m('k')}</sub>: (age &minus; {ref['age_years']})/10, 1[ECOG &ge; 2], number of impaired domains, "
                    f"{ref['haemoglobin_g_dl']:g} &minus; Hb, ({ref['albumin_g_l']:g} &minus; albumin)/10, 1[reduced dose]"],
                   ex,
                   [("Event", "Adverse event of CTCAE grade 3 to 5"),
                    ("Time window", "90 days from the start of a therapy line"),
                    ("Applies to", "All regimens"),
                    ("Model", "Logistic, with the regimen rate as offset"),
                    ("Reference patient", f"{ref['age_years']} years, ECOG 0 or 1, no impaired domain, Hb {ref['haemoglobin_g_dl']:g} g/dl, "
                                          f"albumin {ref['albumin_g_l']:g} g/l, full dose"),
                    ("Risk categories", categories(c["categories"])),
                    ("Check", f"Average GAP70+ patient (77 years, 4.5 impaired domains, rate 60%): {pct(gap_risk)}; "
                              "71% observed under usual care")])
    return page(cols, cited(*config_texts(c), "Mohile et al. (2021)", "Dale et al. (2023)"), "Severe toxicity within 90 days")


def lung():
    """Candidate 2: lung toxicity, and the detection model."""
    c = CFG["ild"]
    h, t = c["hazard_ratios"], c["thresholds"]
    rows = [
        ("Age", f"below {t['younger_below_age']} years", h["younger_age"]["value"], assumed(h["younger_age"])),
        ("Lung comorbidity", "asthma, COPD, earlier ILD, fibrosis, emphysema", h["lung_comorbidity"]["value"], assumed(h["lung_comorbidity"])),
        ("Renal function", "mildly decreased", h["renal_mild_decrease"]["value"], assumed(h["renal_mild_decrease"])),
        ("Renal function", "moderately or severely decreased", h["renal_moderate_severe_decrease"]["value"],
         assumed(h["renal_moderate_severe_decrease"])),
        ("Time since diagnosis", f"more than {t['long_since_diagnosis_more_than_years']:g} years", h["long_since_diagnosis"]["value"],
         assumed(h["long_since_diagnosis"])),
        ("Oxygen saturation", f"below {t['low_spo2_below_percent']:g}% at rest", h["low_spo2"]["value"], assumed(h["low_spo2"])),
    ]
    r0 = models.ild_baseline_risk("trastuzumab_deruxtecan", CFG)
    onset, d, rate = c["onset_days"], CFG["lung_detection"], c["regimen_rates"]
    reference = ('<div class="sub">Reference risk</div>'
                 + rates_table([("Trastuzumab deruxtecan", rate["trastuzumab_deruxtecan"]["rate"], r0),
                                ("Single-agent chemotherapy", rate["chemotherapy_single_agent"]["rate"],
                                 rate["chemotherapy_single_agent"]["rate"])],
                               head=(("", "Regimen"), ("r", "Rate"), ("r0", "r<sub>0</sub>")))
                 + '<div class="sub">Detection model during therapy</div><ul class="where">'
                 f"<li>Weekly SpO<sub>2</sub> at rest, cough and breathlessness against the patient's first report</li>"
                 f"<li>Alert if SpO<sub>2</sub> falls by &ge; {d['fall_once']} points, or by &ge; {d['fall_confirmed']} points "
                 f"in two reports in a row or with a symptom rise of &ge; {d['symptom_rise']} levels</li></ul>")
    patient = {"regimen": "trastuzumab_deruxtecan", "age_years": 58, "lung_comorbidity": False, "renal_function": "mild_decrease",
               "years_since_diagnosis": 2.0, "spo2_percent": 93}
    risk = models.ild_risk(patient, CFG)
    ex = example("Trastuzumab deruxtecan; 58 years, renal function mildly decreased, SpO<sub>2</sub> 93%, diagnosis 2 years ago",
                 hazard_steps(r0, models.ild_terms(patient, CFG), risk),
                 f"By day 180: {pct(models.ild_risk_by_day(patient, 180, CFG))}. Free of it after one year: "
                 f"{pct(models.ild_remaining_risk(patient, 365, CFG))} remain. Grade 2 or higher: {pct(c['grade2plus_share']['value'] * risk)}.")
    cols = columns(rows, "hazard ratio", reference,
                   eq(f"{m('p')} = 1 &minus; (1 &minus; {m('r')}<sub>0</sub>)<sup>HR</sup>, &nbsp; HR = &prod;<sub>{m('k')}</sub> HR<sub>{m('k')}</sub><sup>{m('x')}<sub>{m('k')}</sub></sup>")
                   + eq(f"{m('p')}({m('t')}) = {m('p')} &middot; {m('F')}({m('t')}) / {m('F')}({c['window_days']})", True)
                   + eq(f"{m('F')}({m('t')}) = &Phi;((ln {m('t')} &minus; ln {onset['median']}) / {onset['sigma']:g})", True),
                   [f"{m('r')}<sub>0</sub>: risk without any factor, set so that the mean risk in the pooled population of the "
                    f"published model equals the rate of the regimen",
                    f"Onset log-normal with a median of {onset['median']} days; grade 2 or higher: {c['grade2plus_share']['value']:g} &middot; {m('p')}",
                    f"Remaining risk, free of the event on day {m('t')}: ({m('p')} &minus; {m('p')}({m('t')})) / (1 &minus; {m('p')}({m('t')}))"],
                   ex,
                   [("Event", "Interstitial lung disease or pneumonitis, any grade"),
                    ("Time window", f"{c['window_days']} days; risk up to any day"),
                    ("Applies to", "Trastuzumab deruxtecan with the six factors; single-agent chemotherapy with its rate"),
                    ("Model", "Proportional hazards; hazard ratios of a published multivariable Cox model"),
                    ("Reference patient", "None of the six risk factors"),
                    ("Risk categories", categories(c["categories"])),
                    ("Gap in usual care", "Onset recognised a median of 43 days late in 53% of the events")])
    return page(cols, cited(*config_texts(c), *config_texts(CFG["lung_detection"]), "Powell et al. (2022)"), "Lung toxicity")


NEUTROPENIA_ROWS = [
    ("prior_chemotherapy", "Earlier chemotherapy", "at least one earlier line"),
    ("age_65_or_older", "Age", "65 years or older"),
    ("ast_above_35", "AST", "above {ast_above_u_l} U/l"),
    ("alkaline_phosphatase_above_120", "Alkaline phosphatase", "above {alkaline_phosphatase_above_u_l} U/l"),
    ("bilirubin_above_normal", "Bilirubin", "above the upper limit of normal"),
    ("per_ml_min_of_egfr", "Renal function", "per ml/min of eGFR from {egfr}"),
    ("per_10e9_l_of_white_cells", "White blood cells", "per 10<sup>9</sup>/l from {wbc:g}"),
    ("immunosuppressive_medication", "Immunosuppressive medication", "incl. a corticosteroid in the regimen"),
    ("reduced_starting_dose", "Reduced starting dose", "planned dose intensity below 85%"),
    ("gcsf_prophylaxis", "G-CSF prophylaxis", "from the first cycle"),
    ("ugt1a1_28_homozygous_with_irinotecan", "UGT1A1*28 homozygous", "with irinotecan or SN-38"),
]


def neutropenia():
    """Candidate 3: severe or febrile neutropenia within 90 days."""
    c = CFG["neutropenia"]
    o, t, ref = c["odds_ratios"], c["thresholds"], c["reference_patient"]
    fill = dict(t, egfr=ref["egfr_ml_min"], wbc=ref["white_cells_10e9_l"])
    rows = [(label, detail.format(**fill), o[key]["value"], assumed(o[key])) for key, label, detail in NEUTROPENIA_ROWS]
    r0 = {k: models.neutropenia_reference_risk(k, CFG) for k in c["regimen_rates"]}
    reference = ('<div class="sub">Rate of the regimen and reference risk</div>'
                 + rates_table([(REGIMENS[k], v["rate"], r0[k]) for k, v in c["regimen_rates"].items()],
                               head=(("", "Regimen"), ("r", "r<sub>R</sub>"), ("r0", "r<sub>0,R</sub>")), two=True))
    patient = {"regimen": "adt_docetaxel", "prior_therapy_lines": 0, "age_years": 70, "ast_u_l": 24, "alkaline_phosphatase_u_l": 90,
               "bilirubin_ratio_uln": 0.6, "immunosuppressive_medication": False, "starting_dose_level": 1.0, "gcsf_prophylaxis": False,
               "ugt1a1_28_homozygous": False, "egfr_ml_min": 60, "white_cells_10e9_l": 6.0}
    risk = models.neutropenia_risk(patient, CFG)
    with_gcsf = models.neutropenia_risk(dict(patient, gcsf_prophylaxis=True), CFG)
    ex = example("ADT + docetaxel; 70 years, no earlier chemotherapy, eGFR 60 ml/min, white cells 6.0, no G-CSF",
                 odds_steps(r0["adt_docetaxel"], models.neutropenia_terms(patient, CFG), risk),
                 f"The same patient with G-CSF from the first cycle: {pct(with_gcsf)}.")
    cols = columns(rows, "odds ratio", reference,
                   eq(f"logit {m('p')} = logit {m('r')}<sub>0,{m('R')}</sub> + &sum;<sub>{m('k')}</sub> ln(OR<sub>{m('k')}</sub>) {m('x')}<sub>{m('k')}</sub>")
                   + eq(f"{m('r')}<sub>0,{m('R')}</sub> such that E<sub>ref</sub>[{m('p')}] = {m('r')}<sub>{m('R')}</sub>", True),
                   [f"{m('r')}<sub>{m('R')}</sub>: published rate of the event with regimen {m('R')}",
                    f"{m('r')}<sub>0,{m('R')}</sub>: risk of the reference patient; the mean over a reference population with the "
                    f"published shares of the factors equals {m('r')}<sub>{m('R')}</sub>",
                    f"{m('x')}<sub>{m('k')}</sub>: yes-or-no factors, eGFR &minus; {ref['egfr_ml_min']}, white cells &minus; {ref['white_cells_10e9_l']:g}"],
                   ex,
                   [("Event", "Neutropenia of CTCAE grade 3 or higher, or febrile neutropenia"),
                    ("Time window", f"{c['window_days']} days"),
                    ("Applies to", "Regimens with a published rate of severe neutropenia"),
                    ("Model", "Logistic; odds ratios of a validated model for the first cycle (AUC 0.81 in validation)"),
                    ("Reference patient", f"None of the yes-or-no factors, eGFR {ref['egfr_ml_min']} ml/min, white cells {ref['white_cells_10e9_l']:g}"),
                    ("Risk categories", categories(c["categories"])),
                    ("Use", "G-CSF from the first cycle from a risk of 20%")], reference_wide=True)
    return page(cols, cited(*config_texts(c)), "Severe neutropenia within 90 days")


def diarrhoea():
    """Candidate 4: severe diarrhoea within 90 days."""
    c = CFG["diarrhoea"]
    o, t = c["odds_ratios"], c["thresholds"]
    rows = [
        ("Age", f"{t['older_from_age']} years or older", o["age_70_or_older"]["value"], assumed(o["age_70_or_older"])),
        ("ECOG 2 or higher", "against 0 or 1", o["ecog_2_or_higher"]["value"], assumed(o["ecog_2_or_higher"])),
        ("Albumin", f"below {t['low_albumin_below_g_l']} g/l", o["low_albumin"]["value"], assumed(o["low_albumin"])),
        ("UGT1A1*28 homozygous", "with irinotecan or SN-38", o["ugt1a1_28_homozygous_with_irinotecan"]["value"],
         assumed(o["ugt1a1_28_homozygous_with_irinotecan"])),
    ]
    r0 = {k: models.diarrhoea_reference_risk(k, CFG) for k in c["regimen_rates"]}
    reference = ('<div class="sub">Rate of the regimen and reference risk</div>'
                 + rates_table([(REGIMENS[k], v["rate"], r0[k]) for k, v in c["regimen_rates"].items()],
                               head=(("", "Regimen"), ("r", "r<sub>R</sub>"), ("r0", "r<sub>0,R</sub>")))
                 + '<div class="sub">Signals during therapy</div><ul class="where">'
                   "<li>Stools per day against the patient's own baseline, weight, potassium, reported diarrhoea</li></ul>")
    patient = {"regimen": "nalirifox", "age_years": 72, "ecog": 1, "albumin_g_l": 33, "ugt1a1_28_homozygous": True}
    risk = models.diarrhoea_risk(patient, CFG)
    without = models.diarrhoea_risk(dict(patient, ugt1a1_28_homozygous=False), CFG)
    ex = example("NALIRIFOX; 72 years, ECOG 1, albumin 33 g/l, two copies of UGT1A1*28",
                 odds_steps(r0["nalirifox"], models.diarrhoea_terms(patient, CFG), risk),
                 f"The same patient without the genotype: {pct(without)}.")
    cols = columns(rows, "odds ratio", reference,
                   eq(f"logit {m('p')} = logit {m('r')}<sub>0,{m('R')}</sub> + &sum;<sub>{m('k')}</sub> ln(OR<sub>{m('k')}</sub>) {m('x')}<sub>{m('k')}</sub>")
                   + eq(f"{m('r')}<sub>0,{m('R')}</sub> such that E<sub>ref</sub>[{m('p')}] = {m('r')}<sub>{m('R')}</sub>", True),
                   [f"{m('r')}<sub>{m('R')}</sub>: published rate of the event with regimen {m('R')}",
                    f"{m('r')}<sub>0,{m('R')}</sub>: risk without any factor; the mean over a reference population equals {m('r')}<sub>{m('R')}</sub>",
                    "UGT1A1*28 counts with NALIRIFOX and sacituzumab govitecan, which both act through SN-38"],
                   ex,
                   [("Event", "Diarrhoea of CTCAE grade 3 or higher"),
                    ("Time window", f"{c['window_days']} days"),
                    ("Applies to", "NALIRIFOX, gemcitabine + nab-paclitaxel, sacituzumab govitecan"),
                    ("Model", "Logistic; risk factors named in the literature, effect sizes assumed"),
                    ("Reference patient", "None of the four factors"),
                    ("Risk categories", categories(c["categories"])),
                    ("Link", "Severe diarrhoea brings low potassium, a correctable risk factor for QT prolongation")])
    return page(cols, cited(*config_texts(c), "Bardia et al. (2021)", "Gennari et al. (2021)"), "Severe diarrhoea within 90 days")


def cardiovascular():
    """Candidate 5: major cardiovascular events under androgen deprivation."""
    c = CFG["cardiovascular"]
    h, prior, ref = c["hazard_ratios"], c["prior_event_hazard_ratios"], c["reference_patient"]
    rows = [
        ("Earlier MI or stroke", "under a GnRH agonist", prior["gnrh_agonist"]["value"], assumed(prior["gnrh_agonist"])),
        ("Earlier MI or stroke", "under a GnRH antagonist", prior["gnrh_antagonist"]["value"], assumed(prior["gnrh_antagonist"])),
        ("Age", f"per 10 years from {ref['age_years']}", h["per_10_years_of_age"]["value"], assumed(h["per_10_years_of_age"])),
        ("Diabetes", "", h["diabetes"]["value"], assumed(h["diabetes"])),
        ("Arterial hypertension", "", h["arterial_hypertension"]["value"], assumed(h["arterial_hypertension"])),
        ("Smoking", "current", h["current_smoker"]["value"], assumed(h["current_smoker"])),
        ("Smoking", "former", h["former_smoker"]["value"], assumed(h["former_smoker"])),
        ("Renal function", "moderately or severely decreased", h["renal_moderate_severe_decrease"]["value"],
         assumed(h["renal_moderate_severe_decrease"])),
        ("Cardiovascular disease", "without an earlier event", h["cardiovascular_disease_without_event"]["value"],
         assumed(h["cardiovascular_disease_without_event"])),
    ]
    share = c["cardiovascular_share_of_events"]["value"]
    adt = (("gnrh_agonist", "GnRH agonist"), ("gnrh_antagonist", "GnRH antagonist"))
    reference = ('<div class="sub">Rates by type of androgen deprivation</div><table class="rates"><tr class="head">'
                 '<td>Type</td><td class="r">HERO</td><td class="r">r<sub>A</sub></td><td class="r0">r<sub>0,A</sub></td></tr>'
                 + "".join(f'<tr><td>{n}</td><td class="r">{pct(c["adt_rates"][k]["rate"])}</td>'
                           f'<td class="r">{pct(models.cv_reference_rate(k, CFG))}</td><td class="r0">{pct(models.cv_baseline_risk(k, CFG))}</td></tr>'
                           for k, n in adt) + "</table>")
    patient = {"adt_type": "gnrh_agonist", "prior_cardiovascular_event": True, "cardiovascular_disease": True, "age_years": 75,
               "diabetes": True, "arterial_hypertension": False, "smoking_status": "never", "renal_function": "normal"}
    risk = models.cv_risk(patient, CFG)
    ex = example("GnRH agonist; 75 years, earlier myocardial infarction, diabetes",
                 hazard_steps(models.cv_baseline_risk("gnrh_agonist", CFG), models.cv_terms(patient, CFG), risk),
                 f"The same man on a GnRH antagonist: {pct(models.cv_risk_on(patient, 'gnrh_antagonist', CFG))}.")
    cols = columns(rows, "hazard ratio", reference,
                   eq(f"{m('p')} = 1 &minus; (1 &minus; {m('r')}<sub>0,{m('A')}</sub>)<sup>HR</sup>")
                   + eq(f"HR = HR<sub>prior,{m('A')}</sub><sup>{m('e')}</sup> &middot; {h['per_10_years_of_age']['value']:g}<sup>(age &minus; {ref['age_years']})/10</sup>"
                        f" &middot; &prod;<sub>{m('k')}</sub> HR<sub>{m('k')}</sub><sup>{m('x')}<sub>{m('k')}</sub></sup>", True)
                   + eq(f"{m('r')}<sub>{m('A')}</sub> = 1 &minus; (1 &minus; {share:g} &middot; {m('q')}<sub>{m('A')}</sub>)<sup>{c['window_days']}/{c['rate_window_days']}</sup>", True),
                   [f"{m('A')}: type of androgen deprivation; {m('e')}: earlier myocardial infarction or stroke",
                    f"{m('q')}<sub>{m('A')}</sub>: rate in HERO within 48 weeks, death from any cause included; "
                    f"{share:g}: cardiovascular share of these events in PRONOUNCE",
                    f"{m('r')}<sub>0,{m('A')}</sub>: risk of a man of {ref['age_years']} without factors; "
                    f"the mean over a reference population equals {m('r')}<sub>{m('A')}</sub>"],
                   ex,
                   [("Event", "Myocardial infarction, stroke or cardiovascular death"),
                    ("Time window", f"{c['window_days']} days"),
                    ("Applies to", "Men with prostate cancer under androgen deprivation"),
                    ("Model", "Proportional hazards; the effect of an earlier event depends on the type of androgen deprivation"),
                    ("Reference patient", f"Man of {ref['age_years']} years, the median age in HERO, without risk factors"),
                    ("Risk categories", categories(c["categories"])),
                    ("Also gives", "The risk of the same man on the other type of androgen deprivation")])
    return page(cols, cited(*config_texts(c), "Lyon et al. (2022)"), "Cardiovascular events under androgen deprivation")


# The project overview -----------------------------------------------------------

def card(title, kind, body, cls="", ident=""):
    """A card of the overview."""
    return (f'<div class="card {cls}"{f" id={chr(34)}{ident}{chr(34)}" if ident else ""}>'
            f'<h3>{title}</h3><div class="kind">{kind}</div>{body}</div>')


def bullets(*items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


OVERVIEW_LINKS = [
    # source, target, class, label
    ("literature", "report", "", ""),
    ("literature", "intervention", "", ""),
    ("report", "generator", "", ""),
    ("report", "models", "", ""),
    ("intervention", "generator", "", ""),
    ("generator", "cohorts", "", ""),
    ("models", "evaluation", "", ""),
    ("cohorts", "evaluation", "down", ""),
    ("evaluation", "app", "down", ""),
    ("models", "generator", "up models", "model-guided start &middot; lung monitoring"),
]

OVERVIEW_SCRIPT = """
const box = (id) => { const f = document.getElementById('figure').getBoundingClientRect();
  const r = document.getElementById(id).getBoundingClientRect();
  return { l: r.left - f.left, r: r.right - f.left, t: r.top - f.top, b: r.bottom - f.top, w: r.width, h: r.height }; };
const svg = document.getElementById('links');
let out = '<defs><marker id="head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">'
  + '<path d="M0,0 L8,4 L0,8 z" fill="#c9ced6"/></marker>'
  + '<marker id="head-o" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">'
  + '<path d="M0,0 L8,4 L0,8 z" fill="#eb6834"/></marker></defs>';
for (const [from, to, cls, label] of LINKS) {
  const a = box(from), b = box(to), head = cls.includes('models') ? 'head-o' : 'head';
  if (cls.includes('down')) {
    const x = a.l + a.w / 2;
    out += `<path class="link ${cls}" marker-end="url(#${head})" d="M${x},${a.b + 1} L${x},${b.t - 2}"/>`;
  } else if (cls.includes('up')) {
    const x = a.l + 46;
    out += `<path class="link ${cls}" marker-end="url(#${head})" d="M${x},${a.t - 1} L${x},${b.b + 2}"/>`;
    out += `<text class="tag" x="${x + 9}" y="${(a.t + b.b) / 2 + 4}">${label}</text>`;
  } else {
    const x1 = a.r + 1, y1 = a.t + a.h / 2, x2 = b.l - 2, y2 = b.t + b.h / 2, m = (x1 + x2) / 2;
    out += `<path class="link ${cls}" marker-end="url(#${head})" d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}"/>`;
  }
}
svg.innerHTML = out;
"""


def overview():
    """The project overview: from the literature to the generator of synthetic
    cohorts and the risk models, and on to the data, the evaluation and the app."""
    scenarios = json.loads((REPO / "engine" / "config" / "interventions.json").read_text(encoding="utf-8"))["scenarios"]
    tables = sorted(f.name.removesuffix(".schema.json") for f in (REPO / "schema").glob("*.schema.json"))
    order = ["scenario", "baseline", "observation", "event", "alert", "outcome", "risk_score"]
    tables = sorted(tables, key=lambda n: order.index(n) if n in order else len(order))
    logo = (REPO / "app" / "explorer" / "static" / "explorer" / "img" / "logo.svg").read_text(encoding="utf-8")
    logo = re.sub(r"^<svg ", '<svg aria-hidden="true" ', logo.strip())

    model_rows = [
        ("1", "Severe toxicity", "logistic &middot; 90 days"),
        ("2", "Lung toxicity", f"prop. hazards &middot; {CFG['ild']['window_days']} days"),
        ("3", "Severe neutropenia", f"logistic &middot; {CFG['neutropenia']['window_days']} days"),
        ("4", "Severe diarrhoea", f"logistic &middot; {CFG['diarrhoea']['window_days']} days"),
        ("5", "Cardiovascular events (ADT)", f"prop. hazards &middot; {CFG['cardiovascular']['window_days']} days"),
    ]
    models_html = "".join(f'<div class="model"><span class="n">{n}</span><span class="t">{name}</span>'
                          f'<span class="meta">{meta}</span></div>' for n, name, meta in model_rows)
    models_html += ('<div class="model"><span class="n d">D</span><span class="t">Detection of lung toxicity</span>'
                    '<span class="meta">weekly home measurements</span></div>')

    literature = card("Literature", "Published evidence", bullets(
        "Phase 3 trials of the regimens: rates of adverse events",
        "Meta-analyses and cohort studies: risk factors with odds and hazard ratios",
        "Validated risk scores",
        "Guidelines on risk assessment and monitoring",
        "Trials of symptom monitoring and early treatment"), "", "literature")
    report = card("Toxicity report", "What the literature says", bullets(
        "Event rates per regimen and tumour type",
        "Risk factors and their effect sizes",
        "What guidelines ask for",
        "Candidates for risk models"), "", "report")
    intervention = card("Intervention model", "Concept", bullets(
        "Risk prediction and adapted start",
        "Monitoring during therapy",
        "Earlier recognition, earlier treatment",
        "Effects anchored in trials"), "", "intervention")
    steps = " <i>&rarr;</i> ".join(f"<span>{s}</span>" for s in (
        "frailty", "baseline", "regimen, dose", "weekly hazards", "events, alerts", "outcome"))
    generator = card("Generator for synthetic cohorts", "Microsimulation, patient by patient, week by week",
                     f'<div class="steps">{steps}</div>'
                     '<p>Calibrated to the published rates; published uncertainty of the parameters carried through. '
                     'The same patients under every scenario:</p>'
                     '<div class="chips">' + "".join(f'<span class="chip">{s["title"]}</span>' for s in scenarios.values())
                     + '</div>', "accent", "generator")
    risk_models = card("Risk models", "Risk at therapy start, from published effect sizes",
                       models_html, "models", "models")
    cohorts = card("Synthetic cohorts", "One schema for all data",
                   '<div class="chips">' + "".join(f'<span class="chip plain">{n}</span>' for n in tables)
                   + '</div>', "", "cohorts")
    evaluation = card("Evaluation", "On synthetic data", bullets(
        "Discrimination and calibration of the models",
        "Refit of the models on the cohorts",
        "Effect of each scenario against usual care"), "", "evaluation")
    app = card("Explorer app", "Web app", bullets(
        "Risk of severe side effects",
        "Course of single patients",
        "What the interventions change"), "accent", "app")

    tumours = "".join(f'<span class="chip orange">{t}</span>' for t in ("Pancreatic cancer", "Prostate cancer", "Breast cancer"))
    links = json.dumps(OVERVIEW_LINKS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Project overview</title>
<link rel="stylesheet" href="overview.css"></head>
<body><div id="figure">
<div class="brand">{logo}<span class="name">toxage<b>-sim</b></span><span class="tumours">{tumours}</span></div>
<div class="flow">
<div class="stage">{literature}</div>
<div class="stage">{report}{intervention}</div>
<div class="stage" style="gap:28px">{generator}{risk_models}</div>
<div class="stage" style="gap:22px">{cohorts}{evaluation}{app}</div>
</div>
<div class="note"><span><b>Same sources, separate parameters.</b> Generator and risk models each take their values from
the literature; the models do not read the parameters of the generator.</span><span><b>Synthetic data only.</b></span></div>
<svg id="links"></svg>
</div>
<script>const LINKS = {links};{OVERVIEW_SCRIPT}</script>
</body></html>
"""


FIGURES = {
    "risk-model-1-severe-toxicity": severe,
    "risk-model-2-lung-toxicity": lung,
    "risk-model-3-neutropenia": neutropenia,
    "risk-model-4-diarrhoea": diarrhoea,
    "risk-model-5-cardiovascular": cardiovascular,
    "project-overview": overview,
}


def main():
    """Write the HTML of every figure next to this script."""
    for name, build in FIGURES.items():
        (HERE / f"{name}.html").write_text(build(), encoding="utf-8")
        print(f"written {name}.html")


if __name__ == "__main__":
    main()
