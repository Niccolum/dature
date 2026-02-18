from dature.errors import LineRange
from dature.source_locators.yaml_ import YamlPathFinder


class TestYamlFindLineRange:
    def test_key_after_literal_block(self):
        content = "str1: |\n  x: 1\n  Violets are blue\nx: 1\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["x"]) == LineRange(start=4, end=4)

    def test_key_after_folded_block(self):
        content = "str1: >\n  host: localhost\n  more text\nhost: production\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["host"]) == LineRange(start=4, end=4)

    def test_scalar_value(self):
        content = "timeout: 30\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["timeout"]) == LineRange(start=1, end=1)

    def test_multiline_dict(self):
        content = "db:\n  host: localhost\n  port: 5432\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["db"]) == LineRange(start=1, end=3)

    def test_multiline_list(self):
        content = "tags:\n  - a\n  - b\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["tags"]) == LineRange(start=1, end=3)

    def test_literal_block_scalar(self):
        content = "key: |\n  line1\n  line2\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=3)

    def test_folded_block_scalar(self):
        content = "key: >\n  line1\n  line2\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=3)

    def test_block_scalar_with_strip_modifier(self):
        content = "key: |-\n  line1\n  line2\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=3)

    def test_block_scalar_with_keep_modifier(self):
        content = "key: >+\n  line1\n  line2\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=3)

    def test_not_found(self):
        content = "name: test\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["missing"]) is None

    def test_inline_value(self):
        content = "name: test\n"
        finder = YamlPathFinder(content)

        assert finder.find_line_range(["name"]) == LineRange(start=1, end=1)
