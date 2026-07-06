import unittest

from pbix2html.reader import read_pbix
from pbix2html.render import render_html

from tests.helpers import build_pbix, section, visual_container


class RenderHtmlTests(unittest.TestCase):
    def render(self, **kwargs) -> str:
        return render_html(read_pbix(build_pbix(**kwargs)))

    def test_document_structure(self):
        html = self.render()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>", html)
        self.assertIn("Page 1", html)
        self.assertIn('class="page-tabs"', html)
        self.assertIn("<script>", html)

    def test_visual_positions_rendered_as_percentages(self):
        html = self.render(
            sections=[section(visuals=[visual_container(x=128, y=72, width=640, height=360)])]
        )
        self.assertIn("left:10.000%", html)
        self.assertIn("top:10.000%", html)
        self.assertIn("width:50.000%", html)
        self.assertIn("height:50.000%", html)

    def test_titles_and_fields_are_escaped(self):
        html = self.render(
            sections=[
                section(
                    '<script>alert("page")</script>',
                    visuals=[
                        visual_container(
                            title='<img src=x onerror="1">',
                            projections={"Y": [{"queryRef": "T.<b>Field</b>"}]},
                        )
                    ],
                )
            ]
        )
        self.assertNotIn("<script>alert", html)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn("<b>Field</b>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_data_model_table_rendered(self):
        html = self.render(
            schema={"model": {"tables": [{"name": "Sales", "columns": [{"name": "Amount"}]}]}}
        )
        self.assertIn("Semantic metadata", html)
        self.assertIn("Sales", html)
        self.assertIn("Amount", html)

    def test_empty_report_renders_placeholder(self):
        html = self.render(sections=[])
        self.assertIn("No report pages found.", html)

    def test_only_one_page_is_active_initially(self):
        html = self.render(
            sections=[
                section("Home", name="home", ordinal=0),
                section("Detail", name="detail", ordinal=1),
            ]
        )
        self.assertEqual(html.count('class="report-page active"'), 1)
        self.assertIn('class="report-page" id="page-2-detail"', html)
        self.assertIn('id="page-2-detail" role="tabpanel" data-hidden-page="false" hidden', html)

    def test_hidden_pages_are_not_in_normal_tab_flow(self):
        html = self.render(
            sections=[
                section("Home", name="home", ordinal=0),
                section("Secret", name="secret", ordinal=1, hidden=True),
            ]
        )
        self.assertIn('class="page-tab hidden-tab"', html)
        self.assertIn("Show hidden pages", html)
        self.assertIn('data-hidden-page="true" hidden', html)

    def test_hidden_visuals_are_not_rendered(self):
        visible = visual_container("columnChart", name="visible")
        hidden = visual_container("slicer", name="hidden")
        # Power BI legacy layout stores visual hidden state inside singleVisual.display.
        import json
        config = json.loads(hidden["config"])
        config["singleVisual"]["display"] = {"mode": "hidden"}
        hidden["config"] = json.dumps(config)
        html = self.render(sections=[section("Home", visuals=[visible, hidden])])
        self.assertIn('title="visible"', html)
        self.assertNotIn('title="hidden"', html)

    def test_page_navigator_visual_is_replaced_by_real_tabs(self):
        html = self.render(
            sections=[section("Home", visuals=[visual_container("pageNavigator", name="nav")])]
        )
        self.assertIn('class="page-tabs"', html)
        self.assertIn('class="visual visual-pageNavigator"', html)
        self.assertIn(".visual-pageNavigator { display: none; }", html)

    def test_layout_only_mode_is_explicit(self):
        html = self.render()
        self.assertIn("Layout-only compatibility mode", html)
        self.assertIn("no portable row data", html)


if __name__ == "__main__":
    unittest.main()
