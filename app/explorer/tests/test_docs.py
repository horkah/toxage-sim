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
