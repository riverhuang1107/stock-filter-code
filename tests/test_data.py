from stock_filter_tool.data import _market_prefix, is_non_st_name, load_a_share_universe


def test_st_stock_is_excluded():
    assert not is_non_st_name("*ST测试")
    assert not is_non_st_name("退市测试")
    assert is_non_st_name("平安银行")


def test_market_prefix_handles_beijing_exchange_codes():
    assert _market_prefix("920080") == "bj"
    assert _market_prefix("830799") == "bj"
    assert _market_prefix("430047") == "bj"
    assert _market_prefix("600000") == "sh"
    assert _market_prefix("000001") == "sz"


def test_universe_falls_back_to_packaged_csv(monkeypatch, tmp_path):
    fallback = tmp_path / "a_share_universe.csv"
    fallback.write_text("code,name,market,pe,pb,turnover\n000001,Sample Bank,,5,1,2\n", encoding="utf-8")

    def fail_eastmoney(limit=None):
        raise RuntimeError("network unavailable")

    class BrokenAkshare:
        def stock_info_a_code_name(self):
            raise RuntimeError("akshare unavailable")

    monkeypatch.setattr("stock_filter_tool.data._load_eastmoney_universe_raw", fail_eastmoney)
    monkeypatch.setattr("stock_filter_tool.data._import_akshare", lambda: BrokenAkshare())
    monkeypatch.setattr("stock_filter_tool.data.PACKAGE_UNIVERSE_FILE", fallback)

    stocks = load_a_share_universe()

    assert [(stock.code, stock.name) for stock in stocks] == [("000001", "Sample Bank")]
