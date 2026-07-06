import json
import re
import unittest

from pbix2html.reader import read_pbix
from pbix2html.render import render_html
from tests.helpers import build_pbix, section, visual_container


class PmoDashboardRegressionTests(unittest.TestCase):
    """Regression profile derived from the user-reported PMO output artifact.

    The failing artifact contained 13 pages, 208 visuals, six hidden pages,
    22 hidden visuals, no runtime script, and all pages stacked in one document.
    """

    def test_large_multi_page_report_has_single_active_page_and_offline_runtime(self):
        pages = []
        remaining = 208
        hidden_visual_budget = 22

        for page_index in range(13):
            page_visual_count = 16 if page_index < 12 else remaining
            remaining -= page_visual_count
            visuals = []
            for visual_index in range(page_visual_count):
                kind = ["columnChart", "slicer", "tableEx", "card", "textbox"][visual_index % 5]
                visual = visual_container(
                    kind,
                    name=f"p{page_index}-v{visual_index}",
                    x=(visual_index % 5) * 200,
                    y=(visual_index % 4) * 120,
                    width=180,
                    height=100,
                    projections={"Values": [{"queryRef": f"Sheet{page_index}.Field{visual_index}"}]},
                )
                if hidden_visual_budget > 0:
                    config = json.loads(visual["config"])
                    config["singleVisual"]["display"] = {"mode": "hidden"}
                    visual["config"] = json.dumps(config)
                    hidden_visual_budget -= 1
                visuals.append(visual)
            pages.append(
                section(
                    f"Page {page_index + 1}",
                    name=f"page{page_index + 1}",
                    ordinal=page_index,
                    hidden=page_index >= 7,
                    visuals=visuals,
                )
            )

        report = read_pbix(build_pbix(sections=pages))
        output = render_html(report)

        self.assertEqual(report.visual_count, 208)
        self.assertEqual(output.count('class="report-page active"'), 1)
        self.assertEqual(output.count('class="report-page"'), 12)
        self.assertEqual(output.count('class="page-tab hidden-tab"'), 6)
        self.assertIn("Show hidden pages", output)
        self.assertIn("<script>", output)
        self.assertIn("addEventListener('click'", output)
        self.assertIn("Layout-only compatibility mode", output)

        # Hidden visuals are omitted from rendered visual nodes, not merely faded.
        self.assertNotIn('title="p0-v0"', output)
        self.assertNotIn('title="p1-v0"', output)

        # Standalone output must not require external script/style/image resources.
        self.assertIsNone(re.search(r'(?:src|href)=["\']https?://', output, re.I))


if __name__ == "__main__":
    unittest.main()
