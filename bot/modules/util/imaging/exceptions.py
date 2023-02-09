class CharacterLimitExceeded(Exception):
    def __init__(self, length: int, limit: int, *args: object) -> None:
        self.length = length
        self.limit = limit
        
        super().__init__(*args)