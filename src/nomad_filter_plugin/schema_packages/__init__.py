from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class NewSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description="Custom configuration parameter")

    def load(self):
        from nomad_filter_plugin.schema_packages.schema_package import m_package

        return m_package


schema_package_entry_point = NewSchemaPackageEntryPoint(
    name="FilterSchemaPackage",
    description="Schema for handling Holger's data.",
)
