from .base import BaseRenderer


class EcsRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"ecs.tf": self.render("ecs.tf.j2", context)}
