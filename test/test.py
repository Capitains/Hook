import tracking
from lxml import etree
import MyCapytain.resources.texts.local

class CTSUnit(object):
    """ CTS testing object

    :param path: Path to the file
    :type path: basestring

    """
    def __init__(self, path):
        self.path = path
        self.xml = None
        self.testable = True
        self.__logs = []
        self.__archives = []
        self.Text = False

    @property
    def logs(self):
        return self.__logs
    
    def log(self, message):
        self.__logs.append(">>>>>> "+ message )

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
            self.log(e.value)
        finally:
            yield self.testable

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

    def passages(self):
        for i in range(0, len(self.Text.citation)):
            passages = self.Text.getValidReff(level=i+1)
            status = len(passages) > 0
            self.log(str(len(passages)) + " found")
            yield status

    def test(self):
        tests = ["parsable", "capitain", "refsDecl", "passages"]
        human = {
            "parsable" : "File parsing",
            "capitain" : "File ingesting in MyCapytain",
            "refsDecl" : "RefsDecl parsing",
            "passages" : "Passage level parsing"
        }
        for test in tests:
            # Show the logs and return the status
            self.flush()

            try:
                for status in getattr(self, test)():
                    yield (human[test], status, self.logs)
                    self.flush()
            except Exception as E:
                status = False
                self.log(E.value)
                yield (human[test], status, self.logs)
