from pathlib import Path
from typing import (
    TYPE_CHECKING,
)

from nomad import archive

from nomad_filter_plugin.schema_packages.schema_package import NewSchemaPackage

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
from .utils import convert_to_hdf

configuration = config.get_plugin_entry_point(
    "nomad_filter_plugin.parsers:parser_entry_point"
)


def clean_dataframe_columns(dataframe, file):
    datetime_format = "%d.%m.%y %H:%M:%S"

    set_aktuell_variants = ["Set aktu", "aktu"]
    correct_variant = "Set_aktuell"
    for variant in set_aktuell_variants:
        if variant in dataframe.columns:
            print(variant, file)
            dataframe.rename(columns={variant: correct_variant}, inplace=True)

    dataframe.columns = [
        column.replace(" ", "_").replace("/", "_").replace(".", "_")
        for column in dataframe.columns
    ]

    first_column = dataframe.columns[0]
    dataframe.rename(columns={first_column: "Datum"}, inplace=True)
    # remove the last 3 characters from the 'Datum' column and convert to datetime
    dataframe["Datum"] = pd.to_datetime(
        dataframe["Datum"].str[:-3], format="mixed"
    ).dt.strftime(datetime_format)
    return dataframe


class NewParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: "EntryArchive",
        logger: "BoundLogger",
        child_archives: dict[str, "EntryArchive"] = None,
    ) -> None:
        logger.info("NewParser.parse", parameter=configuration.parameter)
        upload_id = (
            archive.m_context.upload_id if archive.m_context.upload_id else "unknown"
        )
        upload_id_first_chars = upload_id[:2]
        archive.metadata.upload_id = upload_id
        archive.metadata.entry_id = "h5_dataset"
        archive.data = NewSchemaPackage()

        StagingUploadFiles(upload_id=upload_id, create=True)

        parent_dir = Path(mainfile).parent
        files_without_extension = [
            f
            for f in parent_dir.iterdir()
            if f.is_file() and f.suffix == "" and f.name != ".gitkeep"
        ]

        datafiles = files_without_extension if files_without_extension else None

        filter_file = pd.read_excel(mainfile, sheet_name="filter")
        filter_as_json = filter_file.to_dict(orient="records")

        roh_daten_dataframes = []
        for file in datafiles:

            roh_daten_dataframe = pd.read_csv(
                file, sep="\t", decimal=",", encoding="ISO-8859-1"
            )

            roh_daten_dataframes.append(roh_daten_dataframe)

        roh_daten_dataframes = pd.concat(roh_daten_dataframes, ignore_index=True)

        roh_daten_dataframes = clean_dataframe_columns(roh_daten_dataframes, file)
        convert_to_hdf(archive, "original_file.h5", roh_daten_dataframes)

        # CLEANING
        roh_daten_dataframes.dropna(how="all", inplace=True)

        roh_daten_dataframes["Kommentar"] = (
            roh_daten_dataframes["Kommentar"]
            .str.replace(r"^SpannungsrampeOCV=>", "", regex=True)
            .str.strip()
        )

        roh_daten_dataframes = roh_daten_dataframes[
            roh_daten_dataframes["Kommentar"] == "0,6V"
        ]

        result_df = []
        for item in filter_as_json:
            temp_df = pd.DataFrame()
            rows_with_id = roh_daten_dataframes[
                roh_daten_dataframes["Set_aktuell"] == item["setID"]
            ]

            last_N_items = rows_with_id.tail(item["avgN"])
            for column in last_N_items.columns:
                if pd.api.types.is_numeric_dtype(last_N_items[column]):
                    average_value = last_N_items[column].mean()
                    temp_df[column] = average_value
                else:
                    value = last_N_items[column]
                    temp_df[column] = value

            result_df.append(temp_df)

        result_df = pd.concat(result_df, ignore_index=True)

        print(len(result_df))
        output_file_excel_name = "output.xlsx"

        # filename = f"{Path(mainfile).stem}.h5"
        filename = f"output_file.h5"

        hdf5_filename = (
            f".volumes/fs/staging/{upload_id_first_chars}/{upload_id}/raw/{filename}"
        )

        with h5py.File(hdf5_filename, "w"):
            pass

        with open(
            f".volumes/fs/staging/{upload_id_first_chars}/{upload_id}/raw/{output_file_excel_name}",
            "w",
        ) as f:
            f.write("")
            pass

        with archive.m_context.raw_file(output_file_excel_name) as excel_file:
            result_df.to_excel(excel_file.name, index=False)

        num_array_length = list(range(len(roh_daten_dataframes)))

        # when using 'nomad parse' this returns None but when used as a plugin in Nomad OASIS, it has a value!
        # contx = archive.m_context.upload_id
        print("contx value ", upload_id)

        # now write to file. This is only for displaying data in the hdf5 viewer
        convert_to_hdf(archive, filename, roh_daten_dataframes)
        # with archive.m_context.raw_file(filename, "w") as newfile:
        #     with h5py.File(newfile.name, "w") as hdf:
        #         for key in roh_daten_dataframes.columns:

        #             values = roh_daten_dataframes[key].tolist()

        #             group = hdf.create_group(key)
        #             group.create_dataset("value", data=values)
        #             group.create_dataset(
        #                 "time", data=roh_daten_dataframes["Datum"].tolist()
        #             )
        #             group.attrs["axes"] = "time"
        #             group.attrs["signal"] = "value"
        #             group.attrs["NX_class"] = "NXdata"

        for key in roh_daten_dataframes.columns:
            values = roh_daten_dataframes[key].tolist()

            try:
                dataset_path = f"/uploads/{upload_id}/raw/{filename}#/{key}/value"
                setattr(archive.data, key, dataset_path)
            except Exception as e:
                print(e)

        archive.workflow2 = Workflow(name="test")
