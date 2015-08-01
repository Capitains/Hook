import git

class Progress(git.RemoteProgress):

    def __init__(self):
        super(Progress, self).__init__()
        self.start  = ["Cloning repository"]
        self.end  = []
        self.download = ""
        self.__progress = None

        self.current = 0
        self.maximum = 0

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.current = cur_count
        self.maximum = max_count

        if message:
            if message[-2:] == "/s":
                if self.__progress is None:
                    self.__progress = True
                self.download = message
            else:
                if self.__progress:
                    self.__progress = False
                    self.end.append(message)
                else:
                    self.start.append(message)

    def json(self):
        return [ 
            "\n".join(self.start),
            "Downladed {0}/{1} ({2})".format(self.current, self.maximum, self.download),
            "\n".join(self.end)
        ]
