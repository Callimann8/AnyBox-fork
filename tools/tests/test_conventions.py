import unittest
from pathlib import Path

from helpers import library, temp_root, write

import check_conventions


class ConventionsTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def errors(self):
        return check_conventions.run(self.root, commits=False)

    def test_clean_library_passes(self):
        library(self.root, "demo", ["demo.dll"], "ABX_API HRESULT Done();\n", {"Export.cpp": "ABX_API HRESULT Done() { return S_OK; }\n"})
        self.assertEqual(self.errors(), [])

    def test_comments_are_rejected(self):
        library(self.root, "demo", ["demo.dll"], "", {"Export.cpp": "int x = 1; // why\n#endif // FOO\n}  // namespace demo\n"})
        errors = self.errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Export.cpp:1: comment in code", errors[0])

    def test_licence_header_is_allowed(self):
        library(self.root, "demo", ["demo.dll"], "", {"Export.cpp": "/* Copyright 2020 Upstream. MIT licence. */\nint x;\n"})
        self.assertEqual(self.errors(), [])

    def test_declarations(self):
        library(self.root, "demo", ["demo.dll"], "ABX_API HRESULT Orphan();\n", {"Export.cpp": "ABX_API HRESULT Undeclared() { return S_OK; }\n"})
        errors = "\n".join(self.errors())
        self.assertIn("Undeclared needs exactly one declaration", errors)
        self.assertIn("Orphan is declared but never defined", errors)

    def test_dll_claimed_twice(self):
        library(self.root, "one", ["shared.dll"])
        library(self.root, "two", ["shared.dll"])
        self.assertTrue(any("already served by one" in error for error in self.errors()))

    def test_forwarded_and_defined(self):
        library(self.root, "demo", ["demo.dll"], "ABX_API HRESULT Both();\n", {"Export.cpp": "ABX_API HRESULT Both() { return S_OK; }\n"}, ["Both=kernel32.Both"])
        self.assertTrue(any("both defined and forwarded" in error for error in self.errors()))

    def test_utf8(self):
        (self.root / "notes.md").write_bytes(b"\xff\xfe bad")
        self.assertTrue(any("not UTF-8" in error for error in self.errors()))

    def test_commit_subjects(self):
        self.assertRegex("feat(xgameruntime): implement XAsyncRun", check_conventions.COMMIT)
        self.assertRegex("fix!: drop bound imports", check_conventions.COMMIT)
        self.assertNotRegex("Added stuff", check_conventions.COMMIT)


if __name__ == "__main__":
    unittest.main()
