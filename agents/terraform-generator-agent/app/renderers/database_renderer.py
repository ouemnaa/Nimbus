from .base import BaseRenderer


class DatabaseRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"database.tf": self.render("database.tf.j2", context)}
