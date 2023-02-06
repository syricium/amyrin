class MediaException:
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message
    
    def __repr__(self) -> str:
        return f"<MediaException error=\"{self.__str__()}\">"


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

class AgeLimited(Exception):
    pass
