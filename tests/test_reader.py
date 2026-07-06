import io
import unittest

from pbix2html.reader import PbixError, read_pbix

from tests.helpers import build_pbix, section, visual_container


class ReadPbixTests(unittest.TestCase):
    def test_reads_pages_and_visuals(self):
        pbix = build_pbix(
            sections=[
                section(
                    "Overview",
                    visuals=[
                        visual_container(
                            "columnChart",
                            title="Sales by Region",
                            projections={
                                "Category": [{"queryRef": "Geo.Region"}],
                                "Y": [{"queryRef": "Sum(Sales.Amount)"}],
                            },
                        ),
                        visual_container("slicer", name="visual2", x=400, z=1),
                    ],
                ),
                section("Detail", name="ReportSection2", ordinal=1),
            ]
        )
        report = read_pbix(pbix)

        self.assertEqual(report.version, "1.28")
        self.assertEqual([p.display_name for p in report.pages], ["Overview", "Detail"])
        page = report.pages[0]
        self.assertEqual(page.width, 1280)
        self.assertEqual(len(page.visuals), 2)
        chart = next(v for v in page.visuals if v.visual_type == "columnChart")
        self.assertEqual(chart.title, "Sales by Region")
        self.assertEqual(chart.width, 300)
        self.assertIn("Category: Geo.Region", chart.fields)
        self.assertIn("Y: Sum(Sales.Amount)", chart.fields)

    def test_pages_sorted_by_ordinal(self):
        pbix = build_pbix(
            sections=[
                section("Second", name="s2", ordinal=1),
                section("First", name="s1", ordinal=0),
            ]
        )
        report = read_pbix(pbix)
        self.assertEqual([p.display_name for p in report.pages], ["First", "Second"])

    def test_hidden_page_flag(self):
        report = read_pbix(build_pbix(sections=[section("Hidden", hidden=True)]))
        self.assertTrue(report.pages[0].hidden)

    def test_reads_utf16_layout_with_bom(self):
        pbix = build_pbix(layout_encoding="utf-16")  # writes a BOM
        report = read_pbix(pbix)
        self.assertEqual(len(report.pages), 1)

    def test_reads_utf8_layout(self):
        pbix = build_pbix(layout_encoding="utf-8")
        report = read_pbix(pbix)
        self.assertEqual(len(report.pages), 1)

    def test_reads_data_model_schema(self):
        schema = {
            "model": {
                "tables": [
                    {
                        "name": "Sales",
                        "columns": [{"name": "Amount"}, {"name": "Date"}],
                        "measures": [{"name": "Total Sales"}],
                    },
                    {"name": "LocalDateTable_abc", "columns": [{"name": "Date"}]},
                ]
            }
        }
        report = read_pbix(build_pbix(schema=schema))
        self.assertEqual(len(report.tables), 1)
        self.assertEqual(report.tables[0].name, "Sales")
        self.assertEqual(report.tables[0].columns, ["Amount", "Date"])
        self.assertEqual(report.tables[0].measures, ["Total Sales"])

    def test_lists_static_resources(self):
        report = read_pbix(build_pbix(static_resources={"RegisteredResources/logo.png": b"\x89PNG"}))
        self.assertEqual(report.static_resources, ["RegisteredResources/logo.png"])

    def test_rejects_non_zip(self):
        with self.assertRaises(PbixError):
            read_pbix(io.BytesIO(b"this is not a zip file"))

    def test_rejects_zip_without_layout(self):
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("README.txt", b"nope")
        buffer.seek(0)
        with self.assertRaises(PbixError):
            read_pbix(buffer)

    def test_malformed_container_config_is_tolerated(self):
        container = visual_container()
        container["config"] = "{not json"
        report = read_pbix(build_pbix(sections=[section(visuals=[container])]))
        visual = report.pages[0].visuals[0]
        self.assertEqual(visual.visual_type, "unknown")
        self.assertEqual(visual.x, 10)  # falls back to container-level position


if __name__ == "__main__":
    unittest.main()
