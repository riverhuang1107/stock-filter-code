from stock_filter_tool.data import is_non_st_name


def test_st_stock_is_excluded():
    assert not is_non_st_name("*ST测试")
    assert not is_non_st_name("退市测试")
    assert is_non_st_name("平安银行")
