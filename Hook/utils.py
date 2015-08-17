import git
import re

import slugify as slugify_library


class Progress(git.RemoteProgress):

    def __init__(self):
        super(Progress, self).__init__()
        self.start  = ["Cloning repository"]
        self.end  = []
        self.download = ""
        self.progress = None

        self.current = 0
        self.maximum = 0

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.current = cur_count
        self.maximum = max_count

        if message:
            if message[-2:] == "/s":
                if self.progress is None:
                    self.progress = True
                self.download = message
            else:
                if self.progress:
                    self.progress = False
                    self.end.append(message)
                else:
                    self.start.append(message)

    def json(self):
        return [ 
            "\n".join(self.start),
            "Downladed {0}/{1} ({2})".format(self.current, self.maximum, self.download),
            "\n".join(self.end)
        ]

def slugify(value):
    return slugify_library.slugify(value, only_ascii=True)
