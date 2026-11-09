class PipelineError(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        code: str,
        title: str,
        message: str,
        recovery: str,
        technical_detail: str = "",
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.title = title
        self.message = message
        self.recovery = recovery
        self.technical_detail = technical_detail.strip()

    def __str__(self) -> str:
        return self.message