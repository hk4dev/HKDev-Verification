class CaptchaException(Exception):
    pass


class HTTPException(CaptchaException):
    def __init__(self, response, message):
        self.status = response.status
        if isinstance(message, dict):
            self.status = message.get('errorCode', self.status)
            self.error = message.get('errorMessage', 'Exception')
        else:
            self.error = message
        super().__init__(f"{self.status}: {self.error}")


class InvalidKey(HTTPException):
    pass


class UnissuedSource(HTTPException):
    pass


class CaptchaSystemError(HTTPException):
    pass
