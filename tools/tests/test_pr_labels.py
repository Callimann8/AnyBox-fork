import unittest

import helpers

import pr_labels

TEMPLATE = """### Checklist
- [x] Fixes: Fixes #2
- [x] Unblocks: <!-- title ID and Game bring-up discussion, e.g. 4D5307E6 #12, or none -->{value}
"""


class PrLabelsTest(unittest.TestCase):
    def test_title_ids_ignore_template_example(self):
        self.assertEqual(pr_labels.title_ids(TEMPLATE.format(value=" none")), [])
        self.assertEqual(pr_labels.title_ids(TEMPLATE.format(value=" 1234abcd #12, 9F00BEEF")), ["1234ABCD", "9F00BEEF"])
        self.assertEqual(pr_labels.title_ids("Unblocks: 1234ABCD"), ["1234ABCD"])
        self.assertEqual(pr_labels.title_ids("Mentions 1234ABCD outside the line"), [])
        self.assertEqual(pr_labels.title_ids(None), [])

    def test_labels_for(self):
        body = TEMPLATE.format(value=" 1234ABCD")
        self.assertEqual(pr_labels.labels_for(body, True, []), (["fixes issue", "unblocks title"], []))
        self.assertEqual(pr_labels.labels_for(body, True, ["fixes issue", "unblocks title", "docs"]), ([], []))
        self.assertEqual(pr_labels.labels_for(TEMPLATE.format(value=" none"), False, ["fixes issue", "unblocks title", "docs"]),
                         ([], ["fixes issue", "unblocks title"]))


if __name__ == "__main__":
    unittest.main()
