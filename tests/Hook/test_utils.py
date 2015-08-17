import unittest
import Hook.utils


class TestUtilsFunctions(unittest.TestCase):
    """ Test utils tools """

    def test_slugify(self):
        """ Test slugify is constant """
        self.assertEqual(Hook.utils.slugify("this is Sparta"), "this-is-sparta")


class TestProgress(unittest.TestCase):
    """ Test Github.Progress own implementation """
    def test_json(self):
        """ Test Own Progress function """
        P = Hook.utils.Progress()
        self.assertEqual(len(P.json()), 3)

        P.start = ["This is a start", "AHAH"]
        P.end = ["This is an end"]
        P.current = 5
        P.maximum = 10
        P.download = 20

        self.assertEqual(P.json(), [ 
            "This is a start\nAHAH",
            "Downladed 5/10 (20)",
            "This is an end"
        ])

    def test_update(self):
        P = Hook.utils.Progress()

        # Testing first logs
        P.update(1, 2, max_count=3, message="Starting Download")
        self.assertEqual(P.start, ["Cloning repository", "Starting Download"])

        # Testing when there is a speed
        P.update(1, 2, max_count=3, message='55 kb/s')
        self.assertEqual(P.progress, True)
        self.assertEqual(P.download, '55 kb/s')

        # Testing end logs
        P.update(1, 2, max_count=3, message="Ending Download")
        self.assertEqual(P.progress, False)
        self.assertEqual(P.end, ["Ending Download"])