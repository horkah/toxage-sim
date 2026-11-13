"""Generate synthetic patients with the engine under all scenarios and store
them as a data set. Without --keep the data sets that exist are deleted."""
from django.core.management.base import BaseCommand, CommandError

from explorer import store


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=1500, help="number of patients")
        parser.add_argument("--seed", type=int, default=1, help="random seed")
        parser.add_argument("--scenarios", nargs="*", help="scenario ids; default: all")
        parser.add_argument("--keep", action="store_true", help="keep the data sets that exist")

    def handle(self, *args, n, seed, scenarios, keep, **options):
        dataset = store.generate(n, seed, scenarios, replace=not keep, wait=True)
        if not dataset.ready:
            raise CommandError(dataset.message)
        self.stdout.write(f"{n} patients stored under {len(dataset.scenarios)} scenarios (seed {seed})")
