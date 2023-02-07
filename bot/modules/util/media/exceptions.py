class MediaException(Exception):
    pass


class InvalidFormat(Exception):
    def __init__(self, valid_formats) -> None:
        self.valid_formats = valid_formats


class NoPartsException(Exception):
    pass


class FailedCompressionException(Exception):
    pass
    
class MissingNginxHandler(Exception):
    pass
    
class MediaServerException(Exception):
    pass

class ValidityCheckFailed(Exception):
    pass

class AgeLimited(Exception):
    pass