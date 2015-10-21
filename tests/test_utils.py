import unittest
import Hook.utils


class TestUtilsFunctions(unittest.TestCase):
    """ Test utils tools """

    def test_slugify(self):
        """ Test slugify is constant """
        self.assertEqual(Hook.utils.slugify("this is Sparta"), "this-is-sparta")