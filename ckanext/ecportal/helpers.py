import pylons.i18n as i18n
import ckan
import genshi


def format_description(description):
    try:
        formatted = ckan.misc.MarkdownFormat().to_html(description)
        return genshi.HTML(formatted)
    except Exception:
        error_msg = "<span class='inline-warning'>%s</span>" % \
            i18n._("Cannot render package description")
        return genshi.HTML(error_msg)
