# conftest.py
from pathlib import Path

import pytest
from slugify import slugify

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin("html")
    outcome = yield
    screen_file = ''
    report = outcome.get_result()
    extra = getattr(report, "extra", [])
    if report.when == "call":
        if report.failed and "page" in item.funcargs:
            page = item.funcargs["page"]
            extra.append(pytest_html.extras.url(page.url))
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            screen_file = str(screenshot_dir / f"{slugify(item.nodeid)}.png")
            page.screenshot(path=screen_file)
        xfail = hasattr(report, "wasxfail")
        if (report.skipped and xfail) or (report.failed and not xfail):
            # add the screenshots to the html report
            extra.append(pytest_html.extras.png(screen_file))
        report.extra = extra
