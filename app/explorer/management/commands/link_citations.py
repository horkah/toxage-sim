"""Link every citation in the Markdown files of the repository to its entry in
the reference list: python manage.py link_citations"""
from django.core.management.base import BaseCommand

from explorer import docs


class Command(BaseCommand):
    help = "Link the citations of all Markdown files to the reference list."

    def handle(self, *args, **options):
        for path in docs.markdown_files():
            file = docs.REPO / path
            text = file.read_text(encoding="utf-8")
            linked = docs.link_citations(text, path)
            if linked != text:
                file.write_text(linked, encoding="utf-8")
                self.stdout.write(f"linked citations in {path}")
