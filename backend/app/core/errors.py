class AppError(Exception):
    def __init__(self, message: str, *, status_code: int, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class InvalidObjectIdError(AppError):
    def __init__(self, field_name: str = "id") -> None:
        super().__init__(
            f"Invalid {field_name}.", status_code=422, code="invalid_object_id"
        )


class NotFoundError(AppError):
    def __init__(self, resource: str) -> None:
        super().__init__(
            f"{resource} not found.", status_code=404, code="not_found"
        )


class DatabaseUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Database is unavailable.",
            status_code=503,
            code="database_unavailable",
        )
