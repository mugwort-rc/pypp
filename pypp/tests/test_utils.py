from ..utils import name2snake


class TestName2Snake:
    def test_name(self):
        assert name2snake("name") == "name"

    def test_path(self):
        assert name2snake("path/to/hoge") == "path_to_hoge"
        # see also test_lead_char
        assert name2snake("/path/to/hoge") == "path_to_hoge"

    def test_double_escape(self):
        assert name2snake("hoge(fuga++)") == "hoge_fuga_"

    def test_lead_char(self):
        assert name2snake("./hoge/fuga") == "hoge_fuga"
