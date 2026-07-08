import unittest

from pbix2html.fidelity import (
    EXACT,
    SEMANTICALLY_EQUIVALENT,
    UNSUPPORTED,
    VISUALLY_EQUIVALENT,
    build_fidelity_report,
)
from pbix2html.reader import read_pbix

from tests.helpers import build_pbix, section, visual_container


class FidelityReportTests(unittest.TestCase):
    def build(self, **kwargs):
        return build_fidelity_report(read_pbix(build_pbix(**kwargs)))

    def test_known_visual_family_is_visually_equivalent(self):
        fidelity = self.build(
            sections=[section(visuals=[visual_container("barChart", name="v1")])]
        )
        by_type = {v.visual_type: v for v in fidelity.visuals}
        self.assertEqual(by_type["barChart"].classification, VISUALLY_EQUIVALENT)
        self.assertEqual(by_type["barChart"].count, 1)

    def test_unknown_visual_type_is_unsupported(self):
        fidelity = self.build(
            sections=[section(visuals=[visual_container("acmeCustomSankey", name="v1")])]
        )
        by_type = {v.visual_type: v for v in fidelity.visuals}
        self.assertEqual(by_type["acmeCustomSankey"].classification, UNSUPPORTED)

    def test_page_navigator_is_semantically_equivalent(self):
        fidelity = self.build(
            sections=[section(visuals=[visual_container("pageNavigator", name="nav")])]
        )
        by_type = {v.visual_type: v for v in fidelity.visuals}
        self.assertEqual(by_type["pageNavigator"].classification, SEMANTICALLY_EQUIVALENT)

    def test_hidden_visuals_are_excluded_but_counted(self):
        import json

        hidden = visual_container("slicer", name="hidden")
        config = json.loads(hidden["config"])
        config["singleVisual"]["display"] = {"mode": "hidden"}
        hidden["config"] = json.dumps(config)
        fidelity = self.build(sections=[section(visuals=[hidden])])
        self.assertEqual(fidelity.visuals, [])
        self.assertEqual(fidelity.hidden_visual_count, 1)

    def test_hidden_pages_are_counted(self):
        fidelity = self.build(
            sections=[
                section("Home", name="home", ordinal=0),
                section("Secret", name="secret", ordinal=1, hidden=True),
            ]
        )
        self.assertEqual(fidelity.hidden_page_count, 1)

    def test_same_visual_type_is_aggregated_with_a_count(self):
        fidelity = self.build(
            sections=[
                section(
                    visuals=[
                        visual_container("card", name="v1"),
                        visual_container("card", name="v2"),
                    ]
                )
            ]
        )
        cards = [v for v in fidelity.visuals if v.visual_type == "card"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].count, 2)

    def test_row_data_dimension_is_always_unsupported(self):
        fidelity = self.build()
        by_key = {d.key: d for d in fidelity.dimensions}
        self.assertEqual(by_key["row_data"].classification, UNSUPPORTED)
        self.assertEqual(by_key["measure_calculations"].classification, UNSUPPORTED)

    def test_page_layout_dimension_is_exact(self):
        fidelity = self.build()
        by_key = {d.key: d for d in fidelity.dimensions}
        self.assertEqual(by_key["page_layout"].classification, EXACT)

    def test_semantic_model_dimension_reflects_recovered_tables(self):
        with_tables = self.build(
            schema={"model": {"tables": [{"name": "Sales", "columns": [{"name": "Amount"}]}]}}
        )
        without_tables = self.build()
        by_key_with = {d.key: d for d in with_tables.dimensions}
        by_key_without = {d.key: d for d in without_tables.dimensions}
        self.assertEqual(
            by_key_with["semantic_model_metadata"].classification, SEMANTICALLY_EQUIVALENT
        )
        self.assertEqual(by_key_without["semantic_model_metadata"].classification, UNSUPPORTED)

    def test_static_resources_dimension_reflects_presence(self):
        with_resources = self.build(static_resources={"logo.png": b"\x89PNG"})
        without_resources = self.build()
        by_key_with = {d.key: d for d in with_resources.dimensions}
        by_key_without = {d.key: d for d in without_resources.dimensions}
        self.assertEqual(by_key_with["static_resources"].classification, UNSUPPORTED)
        self.assertEqual(by_key_without["static_resources"].classification, EXACT)

    def test_to_dict_is_json_serializable(self):
        import json

        fidelity = self.build(
            sections=[section(visuals=[visual_container("barChart", name="v1")])]
        )
        payload = json.dumps(fidelity.to_dict())
        self.assertIn("VISUALLY_EQUIVALENT", payload)
        self.assertIn("visualFamilies", payload)
        self.assertIn("reportDimensions", payload)

    def test_to_text_lists_dimensions_and_visuals(self):
        fidelity = self.build(
            sections=[section(visuals=[visual_container("barChart", name="v1")])]
        )
        text = fidelity.to_text()
        self.assertIn("Report-wide features:", text)
        self.assertIn("Visual families:", text)
        self.assertIn("barChart", text)


if __name__ == "__main__":
    unittest.main()
