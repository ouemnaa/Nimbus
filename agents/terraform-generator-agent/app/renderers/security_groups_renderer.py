from .base import BaseRenderer


class SecurityGroupsRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {"security_groups.tf": self.render("security_groups.tf.j2", context)}
