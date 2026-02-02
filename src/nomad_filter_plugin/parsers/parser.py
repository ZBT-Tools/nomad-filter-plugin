from pathlib import Path
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

import h5py
from nomad.config import config
from nomad.datamodel.metainfo.workflow import Workflow
from nomad.parsing.parser import MatchingParser
from nomad.files import StagingUploadFiles
import pandas as pd
import os

configuration = config.get_plugin_entry_point(
    "nomad_filter_plugin.parsers:parser_entry_point"
)


class NewParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: "EntryArchive",
        logger: "BoundLogger",
        child_archives: dict[str, "EntryArchive"] = None,
    ) -> None:
        logger.info("NewParser.parse", parameter=configuration.parameter)
        upload_id = archive.m_context.upload_id
        upload_id_first_chars = upload_id[:2]
        archive.metadata.upload_id = archive.m_context.upload_id  # upload_id
        archive.metadata.entry_id = "h5_dataset"

        datetime_format = "%d.%m.%y %H:%M:%S"
        StagingUploadFiles(upload_id=upload_id, create=True)

        dataframe = pd.read_csv(mainfile, sep="\t", decimal=",", encoding="ISO-8859-1")

        print("Original DataFrame:", len(dataframe))

        # CLEANING
        dataframe.dropna(how="all", inplace=True)
        first_column = dataframe.columns[0]
        dataframe.rename(columns={first_column: "Datum"}, inplace=True)
        # remove the last 3 characters from the 'Datum' column and convert to datetime
        dataframe["Datum"] = pd.to_datetime(
            dataframe["Datum"].str[:-3], format="mixed"
        ).dt.strftime(datetime_format)

        dataframe["Kommentar"] = (
            dataframe["Kommentar"]
            .str.replace(r"^SpannungsrampeOCV=>", "", regex=True)
            .str.strip()
        )

        dataframe = dataframe[dataframe["Kommentar"] == "0,6V"]

        print(dataframe.head())
        print("Filtered DataFrame:", len(dataframe))
        filename = f"{Path(mainfile).stem}.h5"
        hdf5_filename = (
            f".volumes/fs/staging/{upload_id_first_chars}/{upload_id}/raw/{filename}"
        )

        with h5py.File(hdf5_filename, "w"):
            pass

        num_array_length = list(range(len(dataframe)))

        # when using 'nomad parse' this returns None but when used as a plugin in Nomad OASIS, it has a value!
        # contx = archive.m_context.upload_id
        print("contx value ", upload_id)
        logger.info("cotx value ", upload_id)

        # now write to file. This is only for displaying data in the hdf5 viewer
        with archive.m_context.raw_file(filename, "w") as newfile:
            with h5py.File(newfile.name, "w") as hdf:
                for key in dataframe.columns:

                    values = dataframe[key].tolist()

                    group = hdf.create_group(key)
                    group.create_dataset("value", data=values)
                    group.create_dataset("time", data=num_array_length)
                    group.attrs["axes"] = "time"
                    group.attrs["signal"] = "value"
                    group.attrs["NX_class"] = "NXdata"

        for key in dataframe.columns:
            values = dataframe[key].tolist()

            try:
                dataset_path = f"/uploads/{upload_id}/raw/{filename}#/{key}/value"
                setattr(archive.data, key, dataset_path)
            except:
                logger.warning(f"Failed to set dataset path for key {key}")

        archive.workflow2 = Workflow(name="test")
