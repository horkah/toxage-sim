"""Generate synthetic patients with the engine under all scenarios and store
them as a data set. Without --keep the data sets that exist are deleted."""
from django.core.management.base import BaseCommand, CommandError

from explorer import store


class Command(BaseCommand):
    """Command line: python manage.py load_cohort --n 1500 --seed 1 [--keep]
    [--scenarios ...]."""
    help = __doc__

    def add_arguments(self, parser):
        """Options of the command."""
        parser.add_argument("--n", type=int, default=1500, help="number of patients")
        parser.add_argument("--seed", type=int, default=1, help="random seed")
        parser.add_argument("--scenarios", nargs="*", help="scenario ids; default: all")
        parser.add_argument("--keep", action="store_true", help="keep the data sets that exist")

    def handle(self, *args, n, seed, scenarios, keep, **options):
        """Generate the data set in this process and report the result, or fail with
        the engine's message."""
        try:
            dataset = store.generate(n, seed, scenarios, replace=not keep, wait=True)
        except store.TooLarge as refused:
            raise CommandError(str(refused)) from None
        if not dataset.ready:
            raise CommandError(dataset.message)
        self.stdout.write(f"{n} patients stored under {len(dataset.scenarios)} scenarios (seed {seed})")
