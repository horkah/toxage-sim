import re

from django.test import SimpleTestCase

from explorer import docs


class RenderTest(SimpleTestCase):
    def test_blocks(self):
        html, headings = docs.render(
            "# Title\n\nFirst line\nsecond line.\n\n## Part one\n\n- a\n  - a1\n- b\n\n1. x\n2. y\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n\n```bash\nx < 1\n```\n")
        self.assertEqual(headings, [(1, "Title", "title"), (2, "Part one", "part-one")])
        self.assertIn("<p>First line second line.</p>", html)
        self.assertIn("<ul><li>a<ul><li>a1</li></ul></li><li>b</li></ul>", html)
        self.assertIn("<ol><li>x</li><li>y</li></ol>", html)
        self.assertIn("<th>A</th><th>B</th>", html)
        self.assertIn("<td>1</td><td>2</td>", html)
        self.assertIn("<pre>x &lt; 1</pre>", html)

    def test_inline(self):
        self.assertEqual(docs.inline("**b** and *i* and `a<b>`"),
                         "<strong>b</strong> and <em>i</em> and <code>a&lt;b&gt;</code>")
        self.assertEqual(docs.inline("<script>"), "&lt;script&gt;")
        self.assertEqual(docs.inline("<https://example.org/a>"),
                         '<a href="https://example.org/a">https://example.org/a</a>')
        self.assertEqual(docs.inline("2 * 3 * 4"), "2 * 3 * 4")

    def test_links_lead_to_documents_of_the_app(self):
        self.assertEqual(docs.inline("[s](../schema/)", "engine/README.md"), '<a href="/schema/">s</a>')
        self.assertEqual(docs.inline("[a](../app/)", "engine/README.md"), "a")     # not shown in the app
        self.assertEqual(docs.inline("[r](references.md)", "background/toxicity-report.md"),
                         '<a href="../references/">r</a>')
        self.assertEqual(docs.inline("[x](EXTENSIONS.md#a)", "risk-model/README.md"),
                         '<a href="../risk-extensions/#a">x</a>')
        self.assertEqual(docs.inline("[file](papers/x.pdf)", "background/references.md"), "file")
        self.assertEqual(docs.inline("[web](https://example.org)"), '<a href="https://example.org">web</a>')

    def test_all_documents_render(self):
        for document in docs.DOCUMENTS.values():
            html, _ = docs.page(document)
            self.assertGreater(len(html), 500, document.key)
            self.assertNotIn("<script", html)
        self.assertEqual([g for g, _ in docs.groups()], ["Scientific background", "Models"])

    def test_the_app_shows_no_developer_documents(self):
        for key in ("prompts", "internal", "app", "project"):
            self.assertNotIn(key, docs.DOCUMENTS)
        self.assertFalse(any(d.path.startswith("project/") for d in docs.DOCUMENTS.values()))
        titles = [t for _, t, _ in docs.page(docs.DOCUMENTS["engine"])[1]]
        self.assertNotIn("Run", titles)
        self.assertNotIn("Files", titles)
        self.assertIn("Hazard model", titles)

    def test_without_drops_sections(self):
        text = "# A\nintro\n## Run\n```\n# not a heading\n```\n### Sub\nx\n## Keep\ny\n"
        self.assertEqual(docs.without(text, ("Run",)), "# A\nintro\n## Keep\ny")
        self.assertEqual(docs.without(text, ()), text)


class CitationTest(SimpleTestCase):
    """Citations such as "Basch et al. (2022)" link to the entry in the reference list."""

    def test_every_entry_has_an_anchor_and_its_pdf_only_if_it_is_in_the_repository(self):
        text = (docs.REPO / docs.REFERENCES).read_text(encoding="utf-8")
        entries = [line for line in text.splitlines() if docs.ANCHOR.match(line)]
        self.assertEqual(len(entries), len(docs.reference_ids()))
        self.assertIn("basch-2022", docs.reference_ids())
        self.assertIn("lizee-2019", docs.reference_ids())
        papers = {p.name for p in (docs.REPO / "background" / "papers").glob("*.pdf")}
        linked = set()
        for entry in entries:
            for name in re.findall(r"PDF: \[([^\]]+)\]\(" + re.escape(docs.PAPERS_URL) + r"([^)]+)\)", entry):
                self.assertEqual(name[0], name[1])
                linked.add(name[1])
        self.assertEqual(linked, papers)                    # every PDF of the repository, and no other

    def test_all_markdown_files_have_their_citations_linked(self):
        for path in docs.markdown_files():
            text = (docs.REPO / path).read_text(encoding="utf-8")
            self.assertEqual(docs.link_citations(text, path), text,
                             f"{path}: run python manage.py link_citations")

    def test_links_point_to_existing_entries(self):
        for path in docs.markdown_files():
            text = (docs.REPO / path).read_text(encoding="utf-8")
            for target in re.findall(r"\]\((?:[./]*background/|)references\.md#([a-z0-9-]+)\)|\]\(#([a-z0-9-]+-\d{4})\)", text):
                ref = target[0] or target[1]
                self.assertIn(ref, docs.reference_ids(), path)

    def test_linking(self):
        self.assertEqual(docs.link_citations("as (Basch et al., 2022) and Shore et al. (2020), Lyon 2022.", "engine/README.md"),
                         "as ([Basch et al., 2022](../background/references.md#basch-2022)) and "
                         "[Shore et al. (2020)](../background/references.md#shore-2020), "
                         "[Lyon 2022](../background/references.md#lyon-2022).")
        self.assertEqual(docs.link_citations("de Bono et al. (2020)", "background/toxicity-report.md"),
                         "[de Bono et al. (2020)](references.md#de-bono-2020)")
        # Unknown references, headings, code and existing links stay.
        for text in ("Smith et al. (2015)", "## Basch et al. (2022)", "`Basch 2022`", "[Basch 2022](x.md)"):
            self.assertEqual(docs.link_citations(text, "README.md"), text)

    def test_the_reference_list_of_the_app_has_the_anchors(self):
        html, _ = docs.page(docs.DOCUMENTS["references"])
        self.assertIn('<p id="basch-2022">Basch, E.', html)
        self.assertIn(f'<a href="{docs.PAPERS_URL}Basch-2022', html)
        html, _ = docs.page(docs.DOCUMENTS["report"])
        self.assertIn('<a href="../references/#basch-2022">Basch et al., 2022</a>', html)

    def test_cite_links_plain_text_of_the_app(self):
        self.assertEqual(docs.cite("HR of Powell et al. (2022) & <b>", "/documents/references/"),
                         'HR of <a href="/documents/references/#powell-2022">Powell et al. (2022)</a> &amp; &lt;b&gt;')
