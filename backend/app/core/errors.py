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


class AgentUnavailableError(AppError):
    def __init__(self, agent_url: str) -> None:
        super().__init__(
            "Could not reach the Solution Architect Agent. "
            f"Make sure it is running on {agent_url}.",
            status_code=503,
            code="agent_unavailable",
        )


class AgentResponseError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Solution Architect Agent returned an invalid response.",
            status_code=502,
            code="agent_invalid_response",
        )


class AgentRequestError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Solution Architect Agent could not analyze the requirement.",
            status_code=502,
            code="agent_request_failed",
        )


class InvalidOperationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            status_code=409,
            code="invalid_operation",
        )
