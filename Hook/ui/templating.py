from Hook.app import app
from flask import Markup
from Hook.utils import slugify
import re

verbose = re.compile("(>>>>>>[^>]+)")
pr_finder = re.compile("pull\/([0-9]+)\/head")


@app.template_filter("nice_ref")
def _nice_ref(branch, commit):
    if pr_finder.match(branch):
        return "PR #{0}".format(branch.strip("pull/").strip("/head"))
    return commit[0:8]

@app.template_filter("nice_branch")
def _nice_branch(branch):
    if pr_finder.match(branch):
        return "PR #{0}".format(branch.strip("pull/").strip("/head"))
    else:
        return branch.split("/")[-1]

@app.template_filter('slugify')
def _slugify(string):
    if not string:
        return ""
    return slugify(string)

@app.template_filter('checked')
def _checked_bool(boolean):
    if boolean:
        return " checked "
    return ""

@app.template_filter('btn')
def _btn_bool(boolean):
    if boolean:
        return "btn-success"
    return "btn-danger"

@app.template_filter('format_log')
def _format_log(string):
    if not string:
        return ""
    else:
        print(verbose.findall(string))
        if string.startswith(">>> "):
            string = Markup("<u>{0}</u>".format(string.strip(">>> ")))
        elif string.startswith(">>>> "):
            string = Markup("<b>{0}</b>".format(string.strip(">>>> ")))
        elif string.startswith(">>>>> "):
            string = Markup("<i>{0}</i>".format(string.strip(">>>>> ")))
        elif verbose.findall(string):
            string = Markup("</li><li>".join(["<span class='verbose'>{0}</span>".format(found.strip(">>>>>> ")) for found in verbose.findall()]))
        elif string.startswith("[success]"):
            string = Markup("<span class='success'>{0}</span>".format(string.strip("[success]")))
        elif string.startswith("[failure]"):
            string = Markup("<span class='failure'>{0}</span>".format(string.strip("[failure]")))
        return string

@app.template_filter('tei')
def _check_tei(string):
    if string == "tei":
        return "checked"
    return ""

@app.template_filter('epidoc')
def _check_epidoc(string):
    if string == "epidoc":
        return "checked"
    return ""

@app.template_filter('success_class')
def _success_class(status):
    string = ""
    if status is True:
        string = "success"
    elif status is False:
        string = "failed"
    return string

@app.template_filter("ctsized")
def _ctsized(cts_tuple):
    return "{0}/{1}".format(*cts_tuple)