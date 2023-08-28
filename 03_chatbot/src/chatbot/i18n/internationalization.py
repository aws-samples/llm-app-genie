""" Internationalization of text to other locals. """
import gettext
import os


def install_language(locale: str):
    """Installs a given local and returns the gettext translation function for that language.

    Args:
        locale: The locale to install.

    Returns:
        gettext.gettext: The gettext translation function for the given locale.

    Example:
        ```python
        gettext = install_language("en_US")
        _ = gettext
        _("translates string")
        ```
    """
    i18n_dir = os.path.dirname(__file__)
    lang = gettext.translation("chatbot", localedir=i18n_dir, languages=[locale])
    lang.install()

    return lang.gettext
