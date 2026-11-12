# Internal documentation

Technical and organisational details that go beyond the public [README](../README.md). All documentation in this repository describes the current status only. The history is in the git log.

## Working rules

- Work happens on `main`. Every change is committed and pushed unless a prompt says otherwise.
- Every prompt is logged in [prompting.log](prompting.log) with date-time, selected model, attachments and the prompt text. Nothing else goes into the log.
- [initial-prompt.txt](initial-prompt.txt) is the start prompt of the project.

## Folders

| Folder | Purpose | Status |
|---|---|---|
| `background/` | Literature, report, concepts | 20 references, report on therapy toxicity, 2 PDFs |
| `engine/` | Synthetic data generator | empty |
| `risk-model/` | Toxicity risk model | empty |
| `app/` | Inspection app | empty |
| `project/` | Project management, internal documentation | prompt log, start prompt, this file |

## Literature

### Selection

The 20 references cover the three patient groups and the main therapy classes: combination chemotherapy, taxanes, androgen deprivation and androgen receptor inhibitors, PARP inhibitors, radioligand therapy, antibody–drug conjugates, checkpoint inhibitors, and CDK4/6 inhibitors. They are ten phase 3 trials, two cluster-randomised trials, one pooled safety analysis, one meta-analysis, one review and five guidelines, from The New England Journal of Medicine, The Lancet, JAMA, JAMA Network Open, Journal of Clinical Oncology, Annals of Oncology, European Heart Journal, Nature Reviews Clinical Oncology and ESMO Open.

Section 9 of the report lists the topics that the references do not cover.

### How references are checked

- Every reference is looked up in PubMed through the NCBI E-utilities. Title, authors, journal, year, volume, issue, pages and DOI come from the PubMed record.
- Author names are compared with Crossref, which keeps accents that PubMed drops.
- A reference only enters `references.md` after this check.

### Sources for the report

The report uses full texts where they are available through the PubMed Central article datasets, and abstracts from PubMed otherwise. The table "Full texts" in `background/references.md` shows the source for each paper. Numbers in the report are taken from these texts only.

Three guidelines (Conroy 2023, Haanen 2022, Lyon 2022) have no abstract in PubMed and no accessible full text. The report names their scope but does not use their content.

### PDFs

| PDF status | Count | Papers |
|---|---|---|
| In `background/papers/` | 2 | Powell 2022 (publisher version), Wainberg 2023 (accepted manuscript) |
| Free, to be downloaded by hand | 1 | Nichetti 2024 (open access) |
| Usually free on the journal website, to be checked | 5 | Conroy 2023, Haanen 2022, Lyon 2022, Schneider 2021, Loprinzi 2020 |
| Free accepted manuscript or full text in PubMed Central, publisher PDF via university account | 5 | Basch 2022, Modi 2022, Mohile 2021, Sartor 2021, Smith 2022 |
| University account needed | 7 | Bardia 2021, Cortes 2022, de Bono 2020, Fizazi 2022, Hortobagyi 2022, Shore 2020, Tarantino 2023 |

Automated download is limited because the publisher websites and the Europe PMC website block scripted access. The only automated source for PDFs is the PubMed Central article dataset on AWS (`pmc-oa-opendata`), which holds PDFs only for articles with an open licence.

File names in `background/papers/` follow the pattern `<first author><year>_<short title>.pdf`.

### Licences of the stored PDFs

- Powell 2022: CC BY. May be redistributed.
- Wainberg 2023 (accepted manuscript): CC BY-NC-ND. May be redistributed unchanged for non-commercial use.

PDFs from the university account are under publisher copyright. They must not be in the repository when it becomes public. Before publication, `background/papers/` has to be reduced to openly licensed files, and the git history has to be checked for the others.

## Cloud environment

Sessions for this repository run in the cloud environment `toxage-sim`. Its network allows the package registries and these hosts:

- Literature services: `pubmed.ncbi.nlm.nih.gov`, `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `europepmc.org`, `api.crossref.org`, `doi.org`
- Publishers: `www.annalsofoncology.org`, `ascopubs.org`, `academic.oup.com`, `jamanetwork.com`, `www.esmoopen.com`, `www.nejm.org`, `www.thelancet.com`, `www.nature.com`

The literature services work from scripts. The publisher hosts answer scripted requests with a bot check and are of no use for downloads.

## Open points

- Add the missing PDFs to `background/papers/`.
- Read the three guidelines and add their content to the report (section 7 of the report).
- Extend the literature to the topics in section 9 of the report, first of all prediction models and early detection.
- Decide on a licence for the repository before it becomes public.
