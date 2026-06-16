from stock_filter_tool.data import _market_prefix, is_non_st_name


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
