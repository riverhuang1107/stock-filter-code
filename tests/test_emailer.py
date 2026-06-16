from stock_filter_tool.emailer import build_report_message


def test_report_message_uses_readable_chinese_subject_and_fallback():
    msg = build_report_message("<h1>ok</h1>", ["to@example.com"])

    assert msg["Subject"] == "A股大阳包小阴筛选报告"
    assert "请使用支持 HTML 的邮件客户端查看 A股大阳包小阴筛选报告。" in msg.get_body(("plain",)).get_content()
