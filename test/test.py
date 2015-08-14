from lxml import etree
import MyCapytain.resources.texts.local
import os

import jingtrang
import pkg_resources
import subprocess

curr_dir = os.path.dirname(__file__)

EPIDOC = os.path.join(curr_dir, "../data/external/tei-epidoc.rng")
TEI_ALL = os.path.join(curr_dir, "../data/external/tei_all.rng")
JING = pkg_resources.resource_filename("jingtrang", "jing.jar")

class TESTUnit(object):
    def __init__(self, path):
        self.path = path
        self.xml = None
        self.testable = True
        self.__logs = []
        self.__archives = []
        self.Text = False
        self.urn = None

    @property
    def logs(self):
        return self.__logs
    
    def log(self, message):
        self.__logs.append(">>>>>> "+ message )
    
    def error(self, error):
        self.__logs.append(">>>>>> "+ str(type(error)) + " : " + str(error) )

    def flush(self):
        self.__archives = self.__archives + self.__logs
        self.__logs = []

    def parsable(self):
        """ Check and parse the xml file

        :returns: Indicator of success and messages
        :rtype: boolean

        """
        try:
            f = open(self.path)
            xml = etree.parse(f)
            self.xml = xml
            self.testable = True
            self.log("Parsed")
            f.close()
        except Exception as e:
            self.testable = False
            self.error(e)
        finally:
            yield self.testable


class INVUnit(TESTUnit):
    """ CTS testing object

    :param path: Path to the file
    :type path: basestring
    """

    tests = ["parsable"]
    readable = {
        "parsable" : "File parsing"
    }

    def capitain(self):
        """ Load the file in MyCapytain
        """
        self.Text = MyCapytain.resources.texts.local.Text(resource=self.xml.getroot())
        if self.Text:
            yield True
        else:
            yield False

    def test(self):
        """ Test a file with various checks

        :returns: List of urns
        :rtype: list.<str>
        
        """
        self.urns = []

        for test in INVUnit.tests:
            # Show the logs and return the status
            self.flush()
            try:
                for status in getattr(self, test)():
                    yield (INVUnit.readable[test], status, self.logs)
                    self.flush()
            except Exception as E:
                status = False
                self.error(E)
                yield (INVUnit.readable[test], status, self.logs)

class CTSUnit(TESTUnit):
    """ CTS testing object

    :param path: Path to the file
    :type path: basestring

    """
    tests = ["parsable", "capitain", "has_urn", "naming_convention", "refsDecl", "passages", "inventory"]
    readable = {
        "parsable" : "File parsing",
        "capitain" : "File ingesting in MyCapytain",
        "refsDecl" : "RefsDecl parsing",
        "passages" : "Passage level parsing",
        "epidoc" : "Epidoc DTD validation",
        "tei" : "TEI DTD Validation",
        "has_urn" : "URN informations",
        "naming_convention" : "Naming conventions",
        "inventory" : "Available in inventory"
    }
    def capitain(self):
        """ Load the file in MyCapytain
        """
        self.Text = MyCapytain.resources.texts.local.Text(resource=self.xml.getroot())
        if self.Text:
            yield True
        else:
            yield False

    def refsDecl(self):
        """ Contains refsDecl informations
        """
        self.log(str(len(self.Text.citation)) + " citations found")
        yield len(self.Text.citation) > 0

    def epidoc(self):
        test = subprocess.Popen(
            ["java", "-jar", JING, EPIDOC, self.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )

        out, error = test.communicate()

        if len(out) > 0:
            for error in out.decode("utf-8").split("\n"):
                self.log(error)
        yield len(out) == 0 and len(error) == 0

    def tei(self):
        test = subprocess.Popen(
            ["java", "-jar", JING, TEI_ALL, self.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )

        out, error = test.communicate()

        if len(out) > 0:
            for error in out.decode("utf-8").split("\n"):
                self.log(error)
        yield len(out) == 0 and len(error) == 0

    def passages(self):
        for i in range(0, len(self.Text.citation)):
            passages = self.Text.getValidReff(level=i+1)
            status = len(passages) > 0
            self.log(str(len(passages)) + " found")
            yield status

    def has_urn(self):
        """ Test that a file has its urn saved
        """
        ns = {"tei" : "http://www.tei-c.org/ns/1.0"}
        urns = self.xml.xpath("//tei:text[starts-with(@n, 'urn:cts:')]", namespaces=ns)
        urns += self.xml.xpath("//tei:div[starts-with(@n, 'urn:cts:')]", namespaces=ns)
        status = len(urns) > 0
        if status:
            logs = urns[0].get("n")
            self.log(logs)
            self.urn = logs
        yield status

    def naming_convention(self):
        """ Check the naming convention of the file
        """
        if self.urn:
            yield self.urn.split(":")[-1] in self.path
        else:
            yield False

    def inventory(self):
        """ Check the naming convention of the file
        """
        if self.urn:
            yield self.urn in self.inv
        else:
            yield False

    def test(self, tei, epidoc, inv=None):
        """ Test a file with various checks

        :param tei: Test with TEI DTD
        :type tei: bool
        :param epidoc: Test with EPIDOC DTD
        :type epidoc: bool
        
        """
        if inv is None:
            inv = []
        self.inv = inv

        tests = CTSUnit.tests
        if tei:
            tests.append("tei")
        if epidoc:
            tests.append("epidoc")

        for test in CTSUnit.tests:
            # Show the logs and return the status
            self.flush()
            try:
                for status in getattr(self, test)():
                    yield (CTSUnit.readable[test], status, self.logs)
                    self.flush()
            except Exception as E:
                status = False
                self.error(E)
                yield (CTSUnit.readable[test], status, self.logs)
