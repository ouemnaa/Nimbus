from .base import BaseRenderer


class IamRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"iam.tf": self.render("iam.tf.j2", context)}
