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
        self.assertIn("Data model", html)
        self.assertIn("Sales", html)
        self.assertIn("Amount", html)

    def test_empty_report_renders_placeholder(self):
        html = self.render(sections=[])
        self.assertIn("No report pages found.", html)


if __name__ == "__main__":
    unittest.main()
