from .base import BaseRenderer


class CommonFilesRenderer(BaseRenderer):
    def render_files(self, context: dict) -> dict[str, str]:
        return {
            "versions.tf": self.render("versions.tf.j2", context),
            "providers.tf": self.render("providers.tf.j2", context),
            "variables.tf": self.render("variables.tf.j2", context),
            "locals.tf": self.render("locals.tf.j2", context),
            "terraform.tfvars.example": self.render("terraform.tfvars.example.j2", context),
            "README.generated.md": self.render("README.generated.md.j2", context),
        }
