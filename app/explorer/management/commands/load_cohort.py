"""Generate synthetic patients with the engine under all scenarios and store
them, replacing the data set that was there before."""
from django.core.management.base import BaseCommand

from explorer import store


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=1500, help="number of patients")
        parser.add_argument("--seed", type=int, default=1, help="random seed")
        parser.add_argument("--scenarios", nargs="*", help="scenario ids; default: all")

    def handle(self, *args, n, seed, scenarios, **options):
        dataset = store.generate(n, seed, scenarios, replace=True)
        self.stdout.write(f"{n} patients stored under {len(dataset.scenarios)} scenarios (seed {seed})")
