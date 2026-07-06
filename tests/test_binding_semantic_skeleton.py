import unittest

from pbix2html.reader import read_pbix
from tests.helpers import build_pbix, section, visual_container


class BindingSemanticSkeletonTests(unittest.TestCase):
    def test_recovers_tables_and_columns_when_pbix_has_no_schema_part(self):
        report = read_pbix(
            build_pbix(
                sections=[
                    section(
                        "Home",
                        visuals=[
                            visual_container(
                                "columnChart",
                                projections={
                                    "Category": [{"queryRef": "Sheet1.Business Category"}],
                                    "Y": [{"queryRef": "Sum(Sheet1.Project Cost)"}],
                                },
                            ),
                            visual_container(
                                "slicer",
                                projections={"Values": [{"queryRef": "Scoring Sheet.Project Name"}]},
                            ),
                        ],
                    )
                ]
            )
        )

        tables = {table.name: table for table in report.tables}
        self.assertIn("Sheet1", tables)
        self.assertIn("Business Category", tables["Sheet1"].columns)
        self.assertIn("Project Cost", tables["Sheet1"].columns)
        self.assertIn("Scoring Sheet", tables)
        self.assertIn("Project Name", tables["Scoring Sheet"].columns)

    def test_does_not_treat_non_field_tokens_as_tables(self):
        report = read_pbix(
            build_pbix(
                sections=[
                    section(
                        visuals=[
                            visual_container(
                                "columnChart",
                                projections={"Tooltips": [{"queryRef": "select"}]},
                            )
                        ]
                    )
                ]
            )
        )
        self.assertEqual(report.tables, [])


if __name__ == "__main__":
    unittest.main()
