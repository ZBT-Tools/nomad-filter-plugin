from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.metainfo import Quantity, SchemaPackage, Section
from nomad.datamodel.hdf5 import HDF5Reference, HDF5Dataset, H5WebAnnotation

configuration = config.get_plugin_entry_point(
    "nomad_filter_plugin.schema_packages:schema_package_entry_point"
)

m_package = SchemaPackage()


class NewSchemaPackage(Schema):
    m_def = Section(a_h5web=H5WebAnnotation(axes="x", signal="value"))
    Datum = Quantity(type=HDF5Reference)
    F_Si_CL = Quantity(type=HDF5Reference)
    nc2 = Quantity(type=HDF5Reference)
    nc3_ = Quantity(type=HDF5Reference)
    Kommentar = Quantity(type=HDF5Reference)
    Strom_I___A = Quantity(type=HDF5Reference, shape=[])
    U_1 = Quantity(type=HDF5Reference, shape=[])

    def normalize(self, archive: "EntryArchive", logger: "BoundLogger") -> None:
        super().normalize(archive, logger)

        logger.info("NewSchema.normalize", parameter=configuration.parameter)


m_package.__init_metainfo__()
