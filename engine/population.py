"""Baseline characteristics of synthetic patients."""
import math


def _clip(value, low, high):
    return max(low, min(high, value))


def _choice(rng, probabilities):
    """Draw a key of a {key: probability} mapping."""
    keys = list(probabilities)
    return rng.choices(keys, weights=[probabilities[k] for k in keys])[0]


def draw_baseline(rng, index, regimens, params):
    """Return one baseline record that follows schema/baseline.schema.json."""
    p = params["population"]
    regimen = rng.choice(list(regimens))
    tumour = regimens[regimen]["tumour_type"]

    age_p = p["age"]
    age = round(rng.gauss(age_p[tumour]["mean"], age_p[tumour]["sd"]))
    age = _clip(age, age_p["minimum"], age_p["maximum"])

    if tumour == "prostate":
        sex = "male"
    elif tumour == "breast":
        sex = "female"
    else:
        sex = "male" if rng.random() < p["share_male_pancreas"] else "female"

    if age >= p["ga_assessed_from_age"]:
        prob = p["ga_impairment_probability_at_65"] + p[
            "ga_impairment_probability_per_year"
        ] * (age - p["ga_assessed_from_age"])
        ga = sum(rng.random() < prob for _ in range(7))
    else:
        ga = None

    renal = {k: v for k, v in p["renal_function_probabilities"].items() if k != "basis"}
    spo2 = round(rng.gauss(p["spo2"]["mean"], p["spo2"]["sd"]))
    ysd = p["years_since_diagnosis"][tumour]

    return {
        "patient_id": f"P{index:06d}",
        "tumour_type": tumour,
        "regimen": regimen,
        "age_years": age,
        "sex": sex,
        "ecog": int(_choice(rng, p["ecog_probabilities"])),
        "ga_impaired_domains": ga,
        "renal_function": _choice(rng, renal),
        "spo2_percent": _clip(spo2, p["spo2"]["minimum"], 100),
        "lung_comorbidity": rng.random() < p["lung_comorbidity_probability"]["value"],
        "years_since_diagnosis": round(
            rng.lognormvariate(math.log(ysd["median"]), ysd["sigma"]), 1
        ),
    }
