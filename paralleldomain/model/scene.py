from datetime import datetime
from typing import Dict, List, TypeVar

from paralleldomain.model.annotation import AnnotationType
from paralleldomain.model.unordered_scene import UnorderedScene, UnorderedSceneDecoderProtocol

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # type: ignore

from paralleldomain.model.frame import Frame
from paralleldomain.model.type_aliases import FrameId, SceneName

T = TypeVar("T")


class SceneDecoderProtocol(UnorderedSceneDecoderProtocol[datetime]):
    def get_frame_id_to_date_time_map(self, scene_name: SceneName) -> Dict[FrameId, datetime]:
        pass


class Scene(UnorderedScene[datetime]):
    """A collection of time-ordered sensor data.

    Args:
        name: Name of scene
        decoder: Decoder instance to be used for loading all relevant objects (frames, annotations etc.)
    """

    def __init__(
        self,
        name: SceneName,
        decoder: SceneDecoderProtocol,
    ):
        super().__init__(name=name, decoder=decoder)
        self._decoder = decoder

    @property
    def frames(self) -> List[Frame]:
        """Returns a list of :obj:`Frame` objects available in the scene."""
        return [self.get_frame(frame_id=frame_id) for frame_id in self.frame_ids]

    @property
    def frame_ids(self) -> List[FrameId]:
        """Returns a list of frame IDs available in the scene."""
        fids = list(self._decoder.get_frame_ids(scene_name=self.name))
        return sorted(fids, key=self._decoder.get_frame_id_to_date_time_map(scene_name=self.name).get)
