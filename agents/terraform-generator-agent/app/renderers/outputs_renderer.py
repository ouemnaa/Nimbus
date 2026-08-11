from .base import BaseRenderer


class OutputsRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"outputs.tf": self.render("outputs.tf.j2", context)}
