"""Ambiente efêmero: cada execução da suíte sobe a stack com um nome de projeto único e a destrói
no final (containers, redes e volumes). Nada vaza de uma execução para outra."""
import subprocess
import uuid


class ComposeError(RuntimeError):
    pass


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ComposeError(f"{' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()


class EphemeralEnvironment:
    def __init__(self, compose_file: str, project: str | None = None, build: bool = True):
        self.compose_file = compose_file
        self.project = project or f"itf-{uuid.uuid4().hex[:8]}"
        self.build = build
        self._base = ["docker", "compose", "-f", compose_file, "-p", self.project]

    def up(self) -> None:
        cmd = self._base + ["up", "-d", "--wait"]
        if self.build:
            cmd.append("--build")
        try:
            _run(cmd)
        except ComposeError as exc:
            logs = self.logs()
            self.down()
            raise ComposeError(f"{exc}\n--- logs ---\n{logs}") from None

    def port(self, service: str, container_port: int) -> int:
        out = _run(self._base + ["port", service, str(container_port)])
        return int(out.rsplit(":", 1)[1])

    def logs(self, tail: int = 80) -> str:
        proc = subprocess.run(
            self._base + ["logs", "--no-color", f"--tail={tail}"], capture_output=True, text=True
        )
        return proc.stdout + proc.stderr

    def down(self) -> None:
        subprocess.run(self._base + ["down", "-v", "--remove-orphans"], capture_output=True, text=True)

    def __enter__(self) -> "EphemeralEnvironment":
        self.up()
        return self

    def __exit__(self, *exc) -> None:
        self.down()
