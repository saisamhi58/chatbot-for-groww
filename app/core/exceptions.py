"""Custom application exceptions."""


class RAGException(Exception):
    """Base exception for RAG application."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(RAGException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(RAGException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class RateLimitError(RAGException):
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, status_code=429)


class NotFoundError(RAGException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class LLMServiceError(RAGException):
    def __init__(self, message: str = "AI service unavailable"):
        super().__init__(message, status_code=502)


class VectorDBError(RAGException):
    def __init__(self, message: str = "Search service unavailable"):
        super().__init__(message, status_code=503)
