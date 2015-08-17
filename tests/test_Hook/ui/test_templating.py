import unittest

import flask
import Hook.ui.templating

class TestTemplating(unittest.TestCase):
    """ Test UI templating functions """

    def test_slugify(self):
        """ Test the slugify template """
        self.assertEqual(Hook.ui.templating._slugify(None), "")
        self.assertEqual(Hook.ui.templating._slugify("this is sparta"), "this-is-sparta")

    def test_checked_bool(self):
        """ Test boolean checked property template """
        self.assertEqual(Hook.ui.templating._checked_bool(True), " checked ")
        self.assertEqual(Hook.ui.templating._checked_bool(False), "")

    def test_checked_class(self):
        """ Test boolean checked property template """
        self.assertEqual(Hook.ui.templating._btn_bool(True), "btn-success")
        self.assertEqual(Hook.ui.templating._btn_bool(False), "btn-danger")

    def test_format_logs(self):
        """ Test how logs strings are formated into HTML """
        self.assertEqual(Hook.ui.templating._format_log(None), "")
        self.assertEqual(Hook.ui.templating._format_log(">>> My String"), flask.Markup("<u>My String</u>"))
        self.assertEqual(Hook.ui.templating._format_log(">>>> My String"), flask.Markup("<b>My String</b>"))
        self.assertEqual(Hook.ui.templating._format_log(">>>>> My String"), flask.Markup("<i>My String</i>"))
        self.assertEqual(Hook.ui.templating._format_log(">>>>>> My String"), flask.Markup("<span class='verbose'>My String</span>"))
        self.assertEqual(Hook.ui.templating._format_log("[success]My String"), flask.Markup("<span class='success'>My String</span>"))
        self.assertEqual(Hook.ui.templating._format_log("[failure]My String"), flask.Markup("<span class='failure'>My String</span>"))

    def _check_tei(self):
        """ Test if tei should be checked """
        self.assertEqual(Hook.ui.templating._check_tei(None), "")
        self.assertEqual(Hook.ui.templating._check_tei("t"), "checked")

    def _check_epidoc(self):
        """ Test if epidoc should be checked """
        self.assertEqual(Hook.ui.templating._check_epidoc(None), "")
        self.assertEqual(Hook.ui.templating._check_epidoc("e"), "checked")

    def _check_status(self):
        """ Test if success or failure should be returned """
        self.assertEqual(Hook.ui.templating._check_status(None), "")
        self.assertEqual(Hook.ui.templating._check_status("ahah"), "")
        self.assertEqual(Hook.ui.templating._check_status(True), "success")
        self.assertEqual(Hook.ui.templating._check_status(False), "failure")