from .base import BaseRenderer


class ObservabilityRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"observability.tf": self.render("observability.tf.j2", context)}
