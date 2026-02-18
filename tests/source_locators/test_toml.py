from dature.errors import LineRange
from dature.source_locators.toml_ import TomlPathFinder


class TestTomlFindLineRange:
    def test_key_after_multiline_double_quotes(self):
        content = 'str1 = """\nx=1\nViolets are blue"""\nx = 1\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["x"]) == LineRange(start=4, end=4)

    def test_key_inside_multiline_not_matched_as_real_key(self):
        content = 'str1 = """\nhost = localhost\n"""\nhost = production\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["host"]) == LineRange(start=4, end=4)

    def test_key_after_multiline_single_quotes(self):
        content = "str1 = '''\nport = 8080\n'''\nport = 3000\n"
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["port"]) == LineRange(start=4, end=4)

    def test_key_only_inside_multiline_returns_not_found(self):
        content = 'str1 = """\nx = 1\n"""\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["x"]) is None

    def test_scalar_value(self):
        content = "timeout = 30\n"
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["timeout"]) == LineRange(start=1, end=1)

    def test_multiline_double_quote_string(self):
        content = 'key = """\nline1\nline2\n"""\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=4)

    def test_multiline_single_quote_string(self):
        content = "key = '''\nline1\nline2\n'''\n"
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=4)

    def test_single_line_triple_quote_string(self):
        content = 'key = """single-line"""\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["key"]) == LineRange(start=1, end=1)

    def test_multiline_array(self):
        content = 'tags = [\n  "a",\n  "b"\n]\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["tags"]) == LineRange(start=1, end=4)

    def test_multiline_inline_table(self):
        content = 'db = {\n  host = "localhost",\n  port = 5432\n}\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["db"]) == LineRange(start=1, end=4)

    def test_not_found(self):
        content = 'name = "test"\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["missing"]) is None

    def test_inline_array(self):
        content = 'tags = ["a", "b"]\n'
        finder = TomlPathFinder(content)

        assert finder.find_line_range(["tags"]) == LineRange(start=1, end=1)
