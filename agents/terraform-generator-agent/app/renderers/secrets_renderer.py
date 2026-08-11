from .base import BaseRenderer


class SecretsRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"secrets.tf": self.render("secrets.tf.j2", context)}
