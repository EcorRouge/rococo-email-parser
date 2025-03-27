from abc import ABC


class EmailParserException(Exception, ABC):
    message = "Error while parsing email"

    def __init__(self, message=None):
        self.message = message or self.message
        super().__init__(self.message)

    def __str__(self):
        return repr(self.message)


class EncodingNotFoundException(EmailParserException):
    message = "Encoding not found in encoding map"


class DateNotFoundException(EmailParserException):
    message = "Valid date not found in email"


class InvalidEmailException(EmailParserException):
    message = "The email is not valid"


class IgnorableEmailException(EmailParserException):
    message = "The email is not valid and can be ignored"
