import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import iso8601

from paralleldomain.common.dgp.v0.constants import ANNOTATION_TYPE_MAP
from paralleldomain.common.dgp.v0.dtos import DatasetDTO, SceneDataDTO, SceneDTO, SceneSampleDTO
from paralleldomain.decoding.common import DecoderSettings
from paralleldomain.decoding.decoder import DatasetDecoder, FrameDecoder, SceneDecoder, TDateTime
from paralleldomain.decoding.dgp.common import decode_class_maps
from paralleldomain.decoding.dgp.frame_decoder import DGPFrameDecoder
from paralleldomain.decoding.dgp.sensor_decoder import DGPCameraSensorDecoder, DGPLidarSensorDecoder
from paralleldomain.decoding.sensor_decoder import CameraSensorDecoder, LidarSensorDecoder, RadarSensorDecoder
from paralleldomain.model.annotation import AnnotationIdentifier
from paralleldomain.model.class_mapping import ClassMap
from paralleldomain.model.dataset import DatasetMeta
from paralleldomain.model.type_aliases import FrameId, SceneName, SensorName
from paralleldomain.utilities.any_path import AnyPath
from paralleldomain.utilities.fsio import read_json
from paralleldomain.utilities.transformation import Transformation

logger = logging.getLogger(__name__)


class _DatasetDecoderMixin:
    def __init__(self, dataset_path: Union[str, AnyPath], **kwargs):
        self._dataset_path: AnyPath = AnyPath(dataset_path)
        self._decode_dataset_dto = lru_cache(maxsize=1)(self._decode_dataset_dto)

    def _decode_scene_paths(self) -> List[Path]:
        dto = self._decode_dataset_dto()
        return [
            Path(path)
            for split_key in sorted(dto.scene_splits.keys())
            for path in dto.scene_splits[split_key].filenames
        ]

    def _decode_dataset_dto(self) -> DatasetDTO:
        dataset_cloud_path: AnyPath = self._dataset_path
        scene_dataset_json_path: AnyPath = dataset_cloud_path / "scene_dataset.json"
        if not scene_dataset_json_path.exists():
            raise FileNotFoundError(f"File {scene_dataset_json_path} not found.")

        scene_dataset_json = read_json(path=scene_dataset_json_path)
        scene_dataset_dto = DatasetDTO.from_dict(scene_dataset_json)

        return scene_dataset_dto

    def _decode_scene_names(self) -> List[SceneName]:
        return [p.parent.name for p in self._decode_scene_paths()]


class DGPDatasetDecoder(_DatasetDecoderMixin, DatasetDecoder):
    def __init__(
        self,
        dataset_path: Union[str, AnyPath],
        umd_file_paths: Optional[Dict[SceneName, Union[str, AnyPath]]] = None,
        custom_reference_to_box_bottom: Optional[Transformation] = None,
        settings: Optional[DecoderSettings] = None,
        **kwargs,
    ):
        self._init_kwargs = dict(
            dataset_path=dataset_path,
            settings=settings,
            umd_file_paths=umd_file_paths,
            custom_reference_to_box_bottom=custom_reference_to_box_bottom,
        )
        _DatasetDecoderMixin.__init__(self, dataset_path=dataset_path)
        DatasetDecoder.__init__(self, dataset_name=str(dataset_path), settings=settings)
        self._umd_file_paths = umd_file_paths
        self.custom_reference_to_box_bottom = (
            Transformation() if custom_reference_to_box_bottom is None else custom_reference_to_box_bottom
        )

        self._dataset_path: AnyPath = AnyPath(dataset_path)

    def create_scene_decoder(self, scene_name: SceneName) -> "SceneDecoder":
        umd_map_path = None
        if self._umd_file_paths is not None and scene_name in self._umd_file_paths:
            umd_map_path = self._umd_file_paths[scene_name]

        return DGPSceneDecoder(
            dataset_path=self._dataset_path,
            custom_reference_to_box_bottom=self.custom_reference_to_box_bottom,
            settings=self.settings,
            umd_map_path=umd_map_path,
        )

    def _decode_unordered_scene_names(self) -> List[SceneName]:
        return [p.parent.name for p in self._decode_scene_paths()]

    def _decode_dataset_metadata(self) -> DatasetMeta:
        dto = self._decode_dataset_dto()
        meta_dict = dto.metadata.to_dict()
        anno_types = [ANNOTATION_TYPE_MAP[str(a)] for a in dto.metadata.available_annotation_types]
        anno_identifiers = [AnnotationIdentifier(annotation_type=t) for t in anno_types]
        return DatasetMeta(
            name=dto.metadata.name, available_annotation_identifiers=anno_identifiers, custom_attributes=meta_dict
        )

    @staticmethod
    def get_format() -> str:
        return "dgp"

    def get_path(self) -> Optional[AnyPath]:
        return self._dataset_path

    def get_decoder_init_kwargs(self) -> Dict[str, Any]:
        return self._init_kwargs


class DGPSceneDecoder(SceneDecoder[datetime], _DatasetDecoderMixin):
    def __init__(
        self,
        dataset_path: Union[str, AnyPath],
        umd_map_path: Optional[Union[str, AnyPath]],
        settings: DecoderSettings,
        custom_reference_to_box_bottom: Optional[Transformation] = None,
    ):
        _DatasetDecoderMixin.__init__(self, dataset_path=dataset_path)
        SceneDecoder.__init__(self, dataset_name=str(dataset_path), settings=settings)
        if umd_map_path is not None:
            umd_map_path = AnyPath(path=umd_map_path)
        self._umd_map_path = umd_map_path
        self.custom_reference_to_box_bottom = (
            Transformation() if custom_reference_to_box_bottom is None else custom_reference_to_box_bottom
        )

        self._dataset_path: AnyPath = AnyPath(dataset_path)
        self._decode_scene_dto = lru_cache(maxsize=1)(self._decode_scene_dto)
        self._data_by_key_with_name = lru_cache(maxsize=1)(self._data_by_key_with_name)
        self._sample_by_index = lru_cache(maxsize=1)(self._sample_by_index)

    def _create_camera_sensor_decoder(
        self, scene_name: SceneName, camera_name: SensorName, dataset_name: str
    ) -> CameraSensorDecoder[TDateTime]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return DGPCameraSensorDecoder(
            dataset_name=dataset_name,
            scene_name=scene_name,
            dataset_path=self._dataset_path,
            scene_samples=self._sample_by_index(scene_name=scene_name),
            scene_data=scene_dto.data,
            ontologies=scene_dto.ontologies,
            custom_reference_to_box_bottom=self.custom_reference_to_box_bottom,
            settings=self.settings,
        )

    def _create_lidar_sensor_decoder(
        self, scene_name: SceneName, lidar_name: SensorName, dataset_name: str
    ) -> LidarSensorDecoder[TDateTime]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return DGPLidarSensorDecoder(
            dataset_name=dataset_name,
            scene_name=scene_name,
            dataset_path=self._dataset_path,
            scene_samples=self._sample_by_index(scene_name=scene_name),
            scene_data=scene_dto.data,
            ontologies=scene_dto.ontologies,
            custom_reference_to_box_bottom=self.custom_reference_to_box_bottom,
            settings=self.settings,
        )

    def _decode_available_annotation_identifiers(self, scene_name: SceneName) -> List[AnnotationIdentifier]:
        dto = self._decode_dataset_dto()
        return [
            AnnotationIdentifier(annotation_type=ANNOTATION_TYPE_MAP[str(a)])
            for a in dto.metadata.available_annotation_types
        ]

    def _decode_frame_id_to_date_time_map(self, scene_name: SceneName) -> Dict[FrameId, datetime]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return {sample.id.index: self._scene_sample_to_date_time(sample=sample) for sample in scene_dto.samples}

    def _decode_set_metadata(self, scene_name: SceneName) -> Dict[str, Any]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return scene_dto.metadata

    def _decode_set_description(self, scene_name: SceneName) -> str:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return scene_dto.description

    def _decode_frame_id_set(self, scene_name: SceneName) -> Set[FrameId]:
        return set(self._decode_frame_id_to_date_time_map(scene_name=scene_name).keys())

    def _decode_sensor_names(self, scene_name: SceneName) -> List[SensorName]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return sorted(list({datum.id.name for datum in scene_dto.data}))

    def _decode_camera_names(self, scene_name: SceneName) -> List[SensorName]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return sorted(list({datum.id.name for datum in scene_dto.data if datum.datum.image}))

    def _decode_lidar_names(self, scene_name: SceneName) -> List[SensorName]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return sorted(list({datum.id.name for datum in scene_dto.data if datum.datum.point_cloud}))

    def _decode_radar_names(self, scene_name: SceneName) -> List[SensorName]:
        """Radar not supported in v0"""
        return list()

    def _create_radar_sensor_decoder(
        self, scene_name: SceneName, radar_name: SensorName, dataset_name: str
    ) -> RadarSensorDecoder[TDateTime]:
        raise ValueError("DGP V0 does not support radar data!")

    def _decode_class_maps(self, scene_name: SceneName) -> Dict[AnnotationIdentifier, ClassMap]:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return decode_class_maps(
            ontologies=scene_dto.ontologies, dataset_path=self._dataset_path, scene_name=scene_name
        )

    def _create_frame_decoder(self, scene_name: SceneName, frame_id: FrameId, dataset_name: str) -> FrameDecoder:
        scene_dto = self._decode_scene_dto(scene_name=scene_name)
        return DGPFrameDecoder(
            dataset_name=dataset_name,
            scene_name=scene_name,
            dataset_path=self._dataset_path,
            scene_samples=self._sample_by_index(scene_name=scene_name),
            scene_data=scene_dto.data,
            ontologies=scene_dto.ontologies,
            custom_reference_to_box_bottom=self.custom_reference_to_box_bottom,
            settings=self.settings,
        )

    @staticmethod
    def _scene_sample_to_date_time(sample: SceneSampleDTO) -> datetime:
        return iso8601.parse_date(sample.id.timestamp)

    def _decode_scene_dto(self, scene_name: str) -> SceneDTO:
        scene_names = self._decode_scene_names()
        scene_index = scene_names.index(scene_name)

        scene_paths = self._decode_scene_paths()
        scene_path = scene_paths[scene_index]

        scene_file = self._dataset_path / scene_path

        scene_data = read_json(path=scene_file)

        scene_dto = SceneDTO.from_dict(scene_data)
        return scene_dto

    def _data_by_key_with_name(self, scene_name: str, data_name: str) -> Dict[str, SceneDataDTO]:
        dto = self._decode_scene_dto(scene_name=scene_name)
        return {d.key: d for d in dto.data if d.id.name == data_name}

    def _sample_by_index(self, scene_name: str) -> Dict[str, SceneSampleDTO]:
        dto = self._decode_scene_dto(scene_name=scene_name)
        return {s.id.index: s for s in dto.samples}
