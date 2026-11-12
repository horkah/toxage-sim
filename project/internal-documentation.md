# Internal documentation

Technical and organisational details that go beyond the public [README](../README.md). All documentation in this repository describes the current status only. The history is in the git log.

## Working rules

- Work happens on `main`. Every change is committed and pushed unless a prompt says otherwise.
- Every prompt is logged in [prompting.log](prompting.log) with date-time, selected model, attachments and the prompt text. Nothing else goes into the log.
- [initial-prompt.txt](initial-prompt.txt) is the start prompt of the project.

## Folders

| Folder | Purpose | Status |
|---|---|---|
| `background/` | Literature, report, concepts | 28 references, report with ten risk model candidates, 20 PDFs |
| `schema/` | Central data schema | version 0.1.0: baseline and outcome table, Python loader and validator |
| `engine/` | Synthetic data generator | simple models for candidates 1 and 2, ten regimens, tests |
| `risk-model/` | Toxicity risk model | empty |
| `app/` | Inspection app | empty |
| `project/` | Project management, internal documentation | prompt log, start prompt, this file |

## Literature

### Selection

The first 20 references cover the three patient groups and the main therapy classes: combination chemotherapy, taxanes, androgen deprivation and androgen receptor inhibitors, PARP inhibitors, radioligand therapy, antibody–drug conjugates, checkpoint inhibitors, and CDK4/6 inhibitors. They are ten phase 3 trials, two cluster-randomised trials, one pooled safety analysis, one meta-analysis, one review and five guidelines, from The New England Journal of Medicine, The Lancet, JAMA, JAMA Network Open, Journal of Clinical Oncology, Annals of Oncology, European Heart Journal, Nature Reviews Clinical Oncology and ESMO Open.

Eight further guidelines were added for the derivation of risk models:

- Treatment guidelines that define the therapy settings: ASCO on metastatic pancreatic cancer, ASCO and EAU on advanced prostate cancer, ESMO on metastatic breast cancer.
- Guidelines on risk assessment and monitoring: ASCO on older patients, ASCO on venous thromboembolism, ASCO and IDSA on febrile neutropenia, ESMO on patient-reported outcome measures.

The febrile neutropenia guideline is from 2018 and so older than the six-year window of the first selection.

Section 9 of the report lists the topics that the references do not cover.

### How references are checked

- Every reference is looked up in PubMed through the NCBI E-utilities. Title, authors, journal, year, volume, issue, pages and DOI come from the PubMed record.
- Author names are compared with Crossref, which keeps accents that PubMed drops.
- A reference only enters `references.md` after this check.

### Sources for the report

The report uses the PDFs in `background/papers/`, converted to text with `pdftotext`. For references without a PDF it uses the accepted manuscript from the PubMed Central article datasets where one exists, and the PubMed abstract otherwise. The table "Full texts" in `background/references.md` shows the source for each reference. Numbers in the report are taken from these texts only.

Sections 2 to 7 of the report state what the sources say. Section 8, the risk model candidates, is our own derivation and is marked as such.

Limits of the current reading:

- The two longest guidelines (Lyon 2022 with 133 pages, Schneider 2021 with 64 pages) were read in selected sections.
- The online supplements of the papers are not in the repository. This affects Haanen 2022 most, where baseline screening and details on several organs are in the supplement.
- In the text extracted from Conroy 2023, the signs "≥" and "≤" are lost. The thresholds for Karnofsky score and bilirubin in section 3 of the report follow from the wording of the neighbouring recommendations.

### PDFs

All 20 PDFs of the first selection are in `background/papers/`. File names follow the pattern `<first author>-<year>-<publisher file name>.pdf`. The file of Haanen 2022 is spelled `Haanan-…` .

The PDFs of the eight added guidelines are missing: Dale 2023, Di Maio 2022, Gennari 2021, Key 2020, Sohal 2020, Taplitz 2018, Tilki 2024, Virgo 2021.

Automated download is limited because the publisher websites and the Europe PMC website block scripted access. The only automated source for PDFs is the PubMed Central article dataset on AWS (`pmc-oa-opendata`), which holds PDFs only for articles with an open licence.

### Licences of the stored PDFs

- Powell 2022 and Nichetti 2024 are open access under CC BY and may be redistributed.
- All other PDFs are publisher versions under publisher copyright, obtained through the university account or free to read on the journal website.

The copyrighted PDFs must not be in the repository when it becomes public. Before publication, `background/papers/` has to be reduced to openly licensed files, and the PDFs have to be removed from the git history as well.

## Schema and engine

- The schema in `schema/` is the single source for field names, types and allowed values. Code in other folders reads it from there and does not repeat field lists. Rules for extending it are in `schema/README.md`.
- The engine is plain Python 3 without further packages. `engine/README.md` describes the models and marks every parameter as literature value or assumption. The parameters themselves are in `engine/config/`.
- Generated data go to `engine/output/`, which is not under version control. Data are reproduced from the seed.
- Tests run with `python3 -m unittest discover engine/tests`.

## Cloud environment

Sessions for this repository run in the cloud environment `toxage-sim`. Its network allows the package registries and these hosts:

- Literature services: `pubmed.ncbi.nlm.nih.gov`, `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `europepmc.org`, `api.crossref.org`, `doi.org`
- Publishers: `www.annalsofoncology.org`, `ascopubs.org`, `academic.oup.com`, `jamanetwork.com`, `www.esmoopen.com`, `www.nejm.org`, `www.thelancet.com`, `www.nature.com`

The literature services work from scripts. The publisher hosts answer scripted requests with a bot check and are of no use for downloads.

## Open points

- Add the PDFs of the eight added guidelines to `background/papers/` and read the six that are not yet covered by a full text.
- Extend the literature to the topics in section 9 of the report, first of all published prediction models and the evidence for home measurements.
- Replace the assumed parameters of the engine by literature values where possible: effects of age, performance status and geriatric impairments on severe toxicity, and the age distributions per regimen.
- Add measurements during therapy to schema and engine, so that detection models become possible.
- Build the first risk models on the generated data.
- Decide on a licence for the repository before it becomes public.
