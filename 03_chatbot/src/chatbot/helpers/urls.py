""" Helper for dealing with URLs. """
import urllib


def is_url(potential_url):
    """Return whether the string is a URL.

    Args:
        potential_url: the string to check.

    Returns:
        True if the string is a URL, False otherwise.
    """
    return urllib.parse.urlparse(potential_url).scheme != ""
