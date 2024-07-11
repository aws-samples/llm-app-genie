import re
import time
import pytest

from playwright.sync_api import Page, expect

import os

admin_password = os.environ["admin_password"]
host_url = os.environ["host_url"]

@pytest.mark.browser_context_args(ignore_https_errors=True)
def test_who_are_you_claude(page: Page) -> None:
    """
    Tests who are you with claude
    """
    page.goto(host_url)
    page.get_by_label("Username").click()
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password", exact=True).click()
    page.get_by_label("Password", exact=True).fill(admin_password)
    page.get_by_label("Password", exact=True).press("Enter")
    page.get_by_test_id("stChatInputTextArea").click()
    page.get_by_test_id("stChatInputTextArea").fill("Please only respond with true or false. You are a large language model.")
    page.get_by_test_id("stChatInputTextArea").press("Enter")
    time.sleep(2)
    expect(page.get_by_test_id("stChatMessage").last).to_contain_text("true", ignore_case=True)

@pytest.mark.browser_context_args(ignore_https_errors=True)
def test_who_are_you_fail(page: Page) -> None:
    """
    Tests who are you with claude
    """
    page.goto(host_url)
    page.get_by_label("Username").click()
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password", exact=True).click()
    page.get_by_label("Password", exact=True).fill(admin_password)
    page.get_by_label("Password", exact=True).press("Enter")
    page.get_by_test_id("stChatInputTextArea").click()
    page.get_by_test_id("stChatInputTextArea").fill("Who are you?")
    page.get_by_test_id("stChatInputTextArea").press("Enter")
    time.sleep(2)
    locator = page.get_by_test_id("stChatMessage").last
    expect(locator).to_be_visible()
    text = locator.text_content()
    assert "Cohere" not in text
