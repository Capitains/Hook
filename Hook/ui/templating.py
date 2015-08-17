from Hook.app import app
from flask import Markup
from Hook.utils import slugify

@app.template_filter('slugify')
def _slugify(string):
    if not string:
        return ""
    return slugify(string)

@app.template_filter('checked')
def _bool(boolean):
    if boolean:
        return " checked "
    return ""

@app.template_filter('btn')
def _bool(boolean):
    if boolean:
        return "btn-success"
    return "btn-danger"

@app.template_filter('format_log')
def _format_log(string):
    if not string:
        return ""
    else:
        if string.startswith(">>>> "):
            string = Markup("<b>{0}</b>".format(string.strip(">")))
        elif string.startswith(">>>>> "):
            string = Markup("<i>\t{0}</i>".format(string.strip(">")))
        elif string.startswith(">>> "):
            string = Markup("<u>{0}</u>".format(string.strip(">")))
        elif string.startswith(">>>>>> "):
            string = Markup("<span class='verbose'>{0}</span>".format(string.strip(">>>>>> ")))
        elif string.startswith("[success]"):
            string = Markup("<span class='success'>{0}</span>".format(string.strip("[success]")))
        elif string.startswith("[failure]"):
            string = Markup("<span class='failure'>{0}</span>".format(string.strip("[failure]")))
        return string

@app.template_filter('tei')
def _check_tei(string):
    if string == "t":
        return "checked"
    return ""

@app.template_filter('epidoc')
def _check_epidoc(string):
    if string == "e":
        return "checked"
    return ""

@app.template_filter('success_class')
def _success_class(status):
    string = ""
    try:
        if status is True:
            string = "success"
        elif status is False:
            string = "failure"
    except:
        string = ""
    finally:
        return string