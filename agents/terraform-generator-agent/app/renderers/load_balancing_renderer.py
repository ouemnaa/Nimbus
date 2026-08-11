from .base import BaseRenderer


class LoadBalancingRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"load_balancing.tf": self.render("load_balancing.tf.j2", context)}
