class ErorrAPI(Exception):
    """Исключение ошибка API."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class WrongAnswerApiError(Exception):
    """Сервер API не доступен."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class BadRequestError(Exception):
    """Сервер API не доступен."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
