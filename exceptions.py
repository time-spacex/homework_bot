class MissingTokenException(Exception):
    """Класс для вызова исключения при отсутствии токенов."""

    pass

class InvalidResponseStatusException(Exception):
    """
    Класс для вызова исключения если API Практикум.Домашка
    возвращает неверный статус ответа.
    """

    pass