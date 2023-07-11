import csv
import logging
from typing import Callable, List, Optional, Tuple, Union

import numpy as np
from pd.core import PdError
from pd.data_lab.context import load_map, setup_datalab
from pd.data_lab.render_instance import RenderInstance
from pd.data_lab.sim_instance import SimulationInstance

import paralleldomain.data_lab as data_lab
from paralleldomain.data_lab.config.map import MapQuery, Area
from paralleldomain.model.annotation import AnnotationType, AnnotationTypes
from paralleldomain.utilities.any_path import AnyPath
from paralleldomain.utilities.fsio import write_png
from paralleldomain.utilities.logging import setup_loggers
from paralleldomain.utilities.transformation import Transformation
from paralleldomain.visualization.sensor_frame_viewer import show_sensor_frame

setup_loggers(logger_names=["__main__", "paralleldomain", "pd"])
logging.getLogger("pd.state.serialize").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

setup_datalab("v2.2.0-beta")


class EgoDroneFlightProfileBehaviour(data_lab.CustomSimulationAgentBehaviour):
    def __init__(
        self,
        start_position: Union[List[float], np.ndarray],
        flight_profile: List[Tuple[float, Transformation]],
        minimum_altitude_override: Optional[float] = None,
    ):
        super().__init__()

        self._start_position: Union[List[float], np.ndarray] = start_position
        self._flight_profile: List[Tuple[float, Transformation]] = flight_profile

        # if user specified other than None, set the lowest point in flight profile to this value above ground.
        # Allows to offset the flight profile to any altitude
        self._minimum_altitude_override: float = minimum_altitude_override
        self._start_time: Optional[float] = None
        self._flight_profile_normalized: Optional[List[Tuple[float, Transformation]]] = None

        # Flight profiles come in potentially other world coordinates. "Normalize" towards PD map and start position
        self.normalize_flight_profile(
            start_position=start_position, minimum_altitude_override=minimum_altitude_override
        )

        self._initial_pose: Transformation = self._flight_profile[0][1]

    def normalize_flight_profile(
        self, start_position: Union[List[float], np.ndarray], minimum_altitude_override: Optional[float]
    ):
        root_pose = self._flight_profile[0][1]

        altitude_offset = (
            minimum_altitude_override - min(tf.translation[2] for _, tf in self._flight_profile)
            if minimum_altitude_override is not None
            else 0
        )

        self._flight_profile_normalized = [
            (
                ts,
                Transformation(
                    translation=tf.translation  # take every pose's translation
                    - root_pose.translation  # center it around first pose's original translation
                    + [
                        start_position[0],
                        start_position[1],
                        root_pose.translation[2] + altitude_offset,
                    ],  # and offset it with PD translation but keep original altitude or set to user-specified altitude
                    quaternion=tf.quaternion,
                ),
            )
            for ts, tf in self._flight_profile
        ]

    def set_initial_state(
        self,
        sim_state: data_lab.ExtendedSimState,
        agent: data_lab.CustomSimulationAgent,
        random_seed: int,
        raycast: Optional[Callable] = None,
    ):
        agent.set_pose(pose=self._initial_pose.transformation_matrix)

    def update_state(
        self,
        sim_state: data_lab.ExtendedSimState,
        agent: data_lab.CustomSimulationAgent,
        raycast: Optional[Callable] = None,
    ):
        current_time = sim_state.sim_time

        if self._start_time is None:
            self._start_time = current_time  # set first frame as start time even if not exactly 0.0 seconds

        flight_profile_time = current_time - self._start_time

        flight_profile_timestamps = np.asarray(
            [ts for ts, _ in self._flight_profile_normalized]
        )  # get all timestamps into np.ndarray for easier analysis

        # Get indices of bounding times, where lower_ts <= ts < upper_ts
        upper_bounding_index = np.searchsorted(flight_profile_timestamps, flight_profile_time, "right")
        lower_bounding_index = upper_bounding_index - 1

        # Check for out-of-bounds index when hitting first or last element in timestamp array
        upper_bounding_index = (
            upper_bounding_index
            if upper_bounding_index < len(flight_profile_timestamps)
            else len(flight_profile_timestamps) - 1
        )
        lower_bounding_index = lower_bounding_index if lower_bounding_index >= 0 else 0

        # Get bounding timestamps and associated Transformation poses
        lower_bounding_ts, lower_bounding_tf = self._flight_profile_normalized[lower_bounding_index]
        upper_bounding_ts, upper_bounding_tf = self._flight_profile_normalized[upper_bounding_index]

        if lower_bounding_ts == upper_bounding_ts:  # if timestamps the same, just take any, don't need to interpolate
            interpolated_pose = lower_bounding_tf
        else:
            # interpolate between two recorded timestamps and find the appropriate translation/rotation
            bounding_value_factor = (flight_profile_time - lower_bounding_ts) / (upper_bounding_ts - lower_bounding_ts)
            interpolated_pose = Transformation.interpolate(
                tf0=lower_bounding_tf, tf1=upper_bounding_tf, factor=bounding_value_factor
            )

        logger.info(f"Using interpolated pose: {interpolated_pose} at {flight_profile_time}")
        agent.set_pose(pose=interpolated_pose.transformation_matrix)

    def clone(self) -> "EgoDroneFlightProfileBehaviour":
        return EgoDroneFlightProfileBehaviour(
            start_position=self._start_position,
            flight_profile=self._flight_profile,
            minimum_altitude_override=self._minimum_altitude_override,
        )


sensor_rig = data_lab.SensorRig().add_camera(
    name="Front",
    width=768,
    height=768,
    field_of_view_degrees=70,
    pose=Transformation.from_euler_angles(
        angles=[-90, 0.0, 0.0], order="xyz", degrees=True, translation=[0.0, 0.0, 0.0]
    ),
    annotation_types=[AnnotationTypes.SemanticSegmentation2D],
)


seed = 1995

# Create scenario
scenario = data_lab.Scenario(sensor_rig=sensor_rig)
scenario.random_seed = seed

# Set weather variables and time of day
scenario.environment.time_of_day.set_category_weight(data_lab.TimeOfDays.Day, 1.0)
scenario.environment.clouds.set_constant_value(0.5)
scenario.environment.rain.set_constant_value(0.0)
scenario.environment.wetness.set_uniform_distribution(min_value=0.1, max_value=0.3)

# Select an environment
location = data_lab.Location(name="SJ_EssexAndBradford")
scenario.set_location(location)

# Load map locally to find a random spawn point and its XYZ coordinates
# this could be done in the EgoDroneBehavior itself, but we need to pass the XYZ coordinates to PD generators, so
# we do it outside.
umd_map = load_map(location)
map_query = MapQuery(umd_map)

# Ensure that the starting position is a random backyard
start_pose = map_query.get_random_area_location(area_type=Area.AreaType.YARD, random_seed=scenario.random_seed)

# If there are no yards
if start_pose is None:
    raise PdError("Failed to find Yard location to spawn. Please try another map")

# map query gives us ground position, but we want our Drone to start 0.25 above ground
start_pose.translation[2] += 0.25

# read from csv
with AnyPath(r"sample_flight_profile_ascending.csv").open() as fp:
    flight_profile = [
        (
            float(row[0]),
            Transformation(
                translation=[row[1], row[2], row[3]],
                quaternion=[float(row[4]), float(row[5]), float(row[6]), float(row[7])],
            ),
        )
        for row in csv.reader(fp, delimiter=",", quoting=csv.QUOTE_NONNUMERIC)
    ]


# Place ourselves in the world through a custom simulation agent. Don't use an asset so we don't see anything flying
# attach our EgoDroneBehavior from above
scenario.add_ego(
    data_lab.CustomSimulationAgents.create_ego_vehicle(
        sensor_rig=sensor_rig,
        asset_name="",
        lock_to_ground=False,
    ).set_behaviour(
        EgoDroneFlightProfileBehaviour(
            start_position=start_pose.translation,
            flight_profile=flight_profile,
            minimum_altitude_override=start_pose.translation[2],
        )
    )
)


def preview_scenario(
    scenario,
    number_of_scenes: int = 1,
    frames_per_scene: int = 10,
    annotations_to_show: List[AnnotationType] = None,
    show_image_for_n_seconds: float = 2,
    **kwargs,
):
    AnyPath("out").mkdir(exist_ok=True)
    for frame, scene in data_lab.create_frame_stream(
        scenario=scenario, frames_per_scene=frames_per_scene, number_of_scenes=number_of_scenes, **kwargs
    ):
        for camera_frame in frame.camera_frames:
            write_png(
                obj=camera_frame.image.rgb,
                path=AnyPath(f"out/{camera_frame.sensor_name}_{camera_frame.frame_id:0>18}.png"),
            )

            show_sensor_frame(
                sensor_frame=camera_frame,
                frames_per_second=show_image_for_n_seconds,
                annotations_to_show=annotations_to_show,
            )


preview_scenario(
    scenario=scenario,
    frames_per_scene=30,
    sim_capture_rate=10,
    sim_instance=SimulationInstance(name="<instance name>"),
    render_instance=RenderInstance(name="<instance name>"),
)
