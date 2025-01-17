# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from pathlib import Path

import pandas as pd
import eva.utils.audio_utils as audio_utils

from eva.catalog.catalog_manager import CatalogManager
from eva.configuration.configuration_manager import ConfigurationManager
from eva.executor.abstract_executor import AbstractExecutor
from eva.models.storage.batch import Batch
from eva.planner.load_data_plan import LoadDataPlan
from eva.storage.storage_engine import RichVideoStorageEngine
from eva.utils.logging_manager import logger


class LoadRichVideoExecutor(AbstractExecutor):
    def __init__(self, node: LoadDataPlan):
        super().__init__(node)
        config = ConfigurationManager()
        self.upload_dir = Path(config.get_value("storage", "upload_dir"))

    def validate(self):
        pass

    def exec(self):

        video_file_path = None
        # Validate file_path
        if Path(self.node.file_path).exists():
            video_file_path = self.node.file_path
        # check in the upload directory
        else:
            video_path = Path(Path(self.upload_dir) / self.node.file_path)
            if video_path.exists():
                video_file_path = video_path

        if video_file_path is None:
            error = "Failed to find a video file at location: {}".format(
                self.node.file_path
            )
            logger.error(error)
            raise RuntimeError(error)

        RichVideoStorageEngine.create(self.node.table_metainfo, if_not_exists=True)
        success = RichVideoStorageEngine.write(
            self.node.table_metainfo,
            Batch(pd.DataFrame([{"video_file_path": str(video_file_path)}])),
        )

        if success:
            # TODO: make results typed
            catalog = CatalogManager()
            results = audio_utils.transcribe_file_with_word_time_offsets(self.node.file_path)
            filename = str(self.node.file_path).split('/')[-1]
            id = self.node.table_metainfo.id
            for result in results:
                catalog.create_transcript_metadata(id, filename, result['word'], result['start'],
                                                   result['end'], result['conf'])

            yield Batch(
                pd.DataFrame(
                    [f"Rich video successfully added at location: {self.node.file_path}"]
                )
            )
