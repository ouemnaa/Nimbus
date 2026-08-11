from .base import BaseRenderer


class NetworkingRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"networking.tf": self.render("networking.tf.j2", context)}
