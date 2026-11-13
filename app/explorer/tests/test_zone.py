import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from explorer import archive
from toxage_app import version, zone

from .helpers import CohortTestCase


class ZoneTest(SimpleTestCase):
    def folder(self, timezone_file=None, link=None):
        etc = Path(tempfile.mkdtemp())
        if timezone_file is not None:
            (etc / "timezone").write_text(timezone_file + "\n")
        if link:
            os.symlink(link, etc / "localtime")
        return etc

    def test_the_zone_of_the_server_is_found(self):
        self.assertEqual(zone.local_zone({"TZ": "Europe/Berlin"}, self.folder("Etc/UTC")), "Europe/Berlin")
        self.assertEqual(zone.local_zone({"TZ": ":Europe/Berlin"}, self.folder()), "Europe/Berlin")
        self.assertEqual(zone.local_zone({}, self.folder("Europe/Berlin")), "Europe/Berlin")
        self.assertEqual(zone.local_zone({}, self.folder(link="/usr/share/zoneinfo/Europe/Berlin")), "Europe/Berlin")
        self.assertEqual(zone.local_zone({"TZ": "Nowhere/Town"}, self.folder("garbage")), "UTC")
        self.assertEqual(zone.local_zone({}, self.folder()), "UTC")

    def test_build_stamps_are_shown_in_the_zone_of_the_server(self):
        moment = "1763070300"      # 2025-11-13 21:45 UTC
        self.assertEqual(version.stamp(f"{moment} abc1234", "Europe/Berlin"), "20251113.2245 (abc1234)")
        self.assertEqual(version.stamp(moment, "UTC"), "20251113.2145")
        summer = "1752437100"      # 2025-07-13 20:05 UTC, summer time in Berlin
        self.assertEqual(version.stamp(summer, "Europe/Berlin"), "20250713.2205")
        self.assertEqual(version.stamp("20261113.1747 (09a1fa3)"), "20261113.1747 (09a1fa3)")   # older form


@override_settings(TIME_ZONE="Europe/Berlin", ASYNC_JOBS=False)
class LocalTimesTest(CohortTestCase):
    n = 6

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.DISCLAIMER_COOKIE] = settings.DISCLAIMER_VERSION

    def test_pages_and_archives_use_the_zone_of_the_server(self):
        page = self.client.get("/data/")
        self.assertNotContains(page, " UTC")
        local = timezone.localtime(self.dataset.created)
        self.assertContains(page, local.strftime("%Y-%m-%d %H:%M ") + local.tzname())
        self.assertIn(timezone.localtime().strftime("%Y%m%d-"), archive.filename())
        header = next(archive.lines())
        self.assertRegex(header, r'"created":"[^"]+\+0[12]:00"')
