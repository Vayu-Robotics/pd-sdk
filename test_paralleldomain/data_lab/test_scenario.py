import dataclasses
from tempfile import TemporaryDirectory
from typing import Callable, List, Optional
from unittest import mock
from unittest.mock import MagicMock

import numpy as np
import pd.state
import pytest
from pd.data_lab import SimState, sim_stream_from_discrete_scenario
from pd.data_lab.config.distribution import EnumDistribution
from pd.data_lab.config.environment import TimeOfDays
from pd.data_lab.config.location import Location
from pd.data_lab.generators.custom_generator import CustomAtomicGenerator
from pd.data_lab.generators.non_atomics import NonAtomicGeneratorMessage
from pd.data_lab.generators.simulation_agent import SimulationAgentBase
from pd.data_lab.render_instance import AbstractRenderInstance
from pd.data_lab.scenario import Scenario, SimulatedScenarioCollection
from pd.data_lab.sim_instance import AbstractSimulationInstance, FromDiskSimulation
from pd.label_engine import LabelData
from pd.management import Ig
from pd.session import SimSession, StepSession
from pd.state import state_to_bytes

from paralleldomain.data_lab import (
    CustomSimulationAgent,
    CustomSimulationAgentBehaviour,
    CustomSimulationAgents,
    ExtendedSimState,
    create_frame_stream,
    encode_sim_states,
)
from paralleldomain.data_lab.config.sensor_rig import SensorConfig, SensorRig
from paralleldomain.data_lab.generators.debris import DebrisGeneratorParameters
from paralleldomain.data_lab.generators.ego_agent import AgentType, EgoAgentGeneratorParameters
from paralleldomain.data_lab.generators.position_request import (
    LaneSpawnPolicy,
    LocationRelativePositionRequest,
    PositionRequest,
)
from paralleldomain.data_lab.generators.traffic import TrafficGeneratorParameters
from paralleldomain.model.annotation import AnnotationTypes, AnnotationIdentifier
from paralleldomain.utilities.any_path import AnyPath
from paralleldomain.utilities.transformation import Transformation
from test_paralleldomain.data_lab.constants import LOCATION_VERSION, LOCATIONS


class MockRenderInstance(AbstractRenderInstance):
    def __init__(self, scenario: Scenario):
        super().__init__()
        self.scenario = scenario
        self.session = mock.MagicMock()
        self.session.update_state = self.update_state
        self._mock_step_ig = mock.MagicMock()
        self._last_timestamp = -1.0

    def query_sensor_data(self, agent_id, sensor_name, buffer_type):
        sensor = next(iter([s for s in self.scenario.sensor_rig.sensor_configs if s.display_name == sensor_name]))
        width = sensor.camera_intrinsic.width
        height = sensor.camera_intrinsic.height
        if pd.state.SensorBuffer.SEGMENTATION == buffer_type:
            data = (np.ones((height, width, 2), dtype=int) * 255).astype(np.uint8)
        elif pd.state.SensorBuffer.INSTANCES == buffer_type:
            data = (np.ones((height, width, 2), dtype=int) * 255).astype(np.uint8)
        elif pd.state.SensorBuffer.RGB == buffer_type:
            data = (np.ones((height, width, 3), dtype=int) * 255).astype(np.uint8)
        elif pd.state.SensorBuffer.NORMALS == buffer_type:
            data = (np.ones((height, width, 3), dtype=int) * 255).astype(np.uint8)
        else:
            raise NotImplementedError()
        sensor_data = pd.state.SensorData(data=data, width=width, height=height)
        return sensor_data

    def update_state(self, sim_state: pd.state.State):
        assert sim_state.simulation_time_sec > self._last_timestamp, "Timestamps sent to the ig need to increase"
        self._last_timestamp = float(sim_state.simulation_time_sec)

    def __enter__(self) -> StepSession:
        self._last_timestamp = -1.0
        self._simulation_time = 0.0
        return self.session

    def __exit__(self):
        pass

    @property
    def step_ig(self) -> Optional[Ig]:
        return self._mock_step_ig

    @property
    def loaded_location(self) -> Optional[Location]:
        return self.scenario.location


class MockSimulationInstance(AbstractSimulationInstance):
    def __init__(self, scenario: Scenario, ego_agent: Optional[SimulationAgentBase]):
        super().__init__()
        self.scenario = scenario
        self._ego_agent = ego_agent
        self.query_sim_state_calls = 0

    def query_sim_state(self) -> pd.state.State:
        self._simulation_time_sec += self.scenario.sim_state.scenario_gen.sim_update_time
        self._ego_agent.step_agent.pose = np.eye(4) * self._simulation_time_sec
        sim_state = pd.state.State(
            simulation_time_sec=self._simulation_time_sec,
            world_info=pd.state.WorldInfo(location="SF_6thAndMission_medium"),
            agents=[self._ego_agent.step_agent],
        )
        self.query_sim_state_calls += 1
        return sim_state

    def __enter__(self) -> SimSession:
        super().__enter__()
        ego_agent = self._ego_agent
        if ego_agent is None:
            ego_agent = mock.MagicMock()
            ego_agent.agent_id = 42
            ego_agent.step_agent = pd.state.ModelAgent(
                id=42,
                asset_name="",
                pose=np.eye(4),
                velocity=(0.0, 0.0, 0.0),
                sensors=[s.to_step_sensor() for s in self.scenario.sensor_rig.sensor_configs],
            )
        self._ego_agent = ego_agent
        self._session = mock.MagicMock()
        self._session.raycast = None
        self._session.load_scenario_generation.return_value = (self.scenario.location.name, ego_agent.agent_id)
        self._simulation_time_sec = 0.0
        return self._session

    def __exit__(self):
        super().__exit__()
        self._simulation_time_sec = 0.0

    @property
    def session(self) -> SimSession:
        return self._session


class MockLabelEngineInstance:
    def __init__(self, scenario: Scenario, ego_agent: Optional[SimulationAgentBase]):
        super().__init__()
        self.scenario = scenario
        self.ego_agent = ego_agent

    def set_unique_scene_name(self, name):
        pass

    def get_annotation_data(
        self, stream_name: str, sensor_id: int, sensor_name: str, frame_timestamp: str
    ) -> LabelData:
        if self.ego_agent is None:
            ego_agent_id = 42
        else:
            ego_agent_id = self.ego_agent.agent_id
        sensor = next(s for s in self.scenario.sensor_rig.sensor_configs if s.display_name == sensor_name)
        width = sensor.camera_intrinsic.width
        height = sensor.camera_intrinsic.height
        data = MagicMock()
        data.timestamp = frame_timestamp
        data.sensor_name = f"{sensor.display_name}-{ego_agent_id}"
        data.label = stream_name
        data.data_as_rgb = np.ones((height, width, 3), dtype=np.uint8) * 255
        data.data_as_segmentation_ids = np.ones((height, width), dtype=np.uint16)
        data.data_as_instance_ids = np.ones((height, width), dtype=np.uint16)
        return data

    def __enter__(self) -> "MockLabelEngineInstance":
        return self

    def __exit__(self):
        ...


class TestScenario:
    @pytest.fixture()
    def location(self):
        map_name = list(LOCATIONS.keys())[0]
        location = LOCATIONS[map_name]
        return location

    @pytest.fixture
    def mixed_scenario(self, location: Location) -> Scenario:
        sensor_rig = SensorRig(
            sensor_configs=[
                SensorConfig.create_camera_sensor(
                    name="Front",
                    width=1920,
                    height=1080,
                    field_of_view_degrees=70,
                    pose=Transformation.from_euler_angles(
                        angles=[2.123, 3.0, -180.0], order="yxz", degrees=True, translation=[10.1, -12.0, 2.0]
                    ),
                    annotation_types=[
                        AnnotationTypes.SurfaceNormals2D,
                        AnnotationTypes.SemanticSegmentation2D,
                        AnnotationTypes.InstanceSegmentation2D,
                    ],
                )
            ]
        )

        scenario = Scenario(sensor_rig=sensor_rig)
        scenario.set_location(location)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Day, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Dawn, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Dusk, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Night, 1.0)
        # Place other agents
        scenario.add_agents(
            generator=TrafficGeneratorParameters(
                spawn_probability=0.8,
                position_request=PositionRequest(
                    location_relative_position_request=LocationRelativePositionRequest(
                        agent_tags=["EGO"],
                        max_spawn_radius=200.0,
                    )
                ),
            )
        )

        class BlockEgoBehaviour(CustomSimulationAgentBehaviour):
            def __init__(self, dist_to_ego: float = 5.0):
                super().__init__()
                self.dist_to_ego = dist_to_ego

            def set_inital_state(
                self,
                sim_state: SimState,
                agent: CustomSimulationAgent,
                random_seed: int,
                raycast: Optional[Callable],
            ):
                agent.set_pose(pose=np.eye(4))

            def update_state(
                self,
                sim_state: SimState,
                agent: CustomSimulationAgent,
                raycast: Optional[Callable] = None,
            ):
                pass

            def clone(self) -> "BlockEgoBehaviour":
                return BlockEgoBehaviour(dist_to_ego=self.dist_to_ego)

        @dataclasses.dataclass
        class MyObstacleGenerator(CustomAtomicGenerator):
            number_of_agents: int = 1

            def create_agents_for_new_scene(self, state: SimState, random_seed: int) -> List[CustomSimulationAgent]:
                agents = []
                for _ in range(int(self.number_of_agents)):
                    agent = CustomSimulationAgents.create_object(asset_name="portapotty_01").set_behaviour(
                        BlockEgoBehaviour()
                    )
                    agents.append(agent)
                return agents

            def clone(self):
                return MyObstacleGenerator(
                    number_of_agents=self.number_of_agents,
                )

        scenario.add_agents(MyObstacleGenerator())
        return scenario

    @pytest.fixture
    def atomic_only_scenario(self, location: Location) -> Scenario:
        sensor_rig = SensorRig(
            sensor_configs=[
                SensorConfig.create_camera_sensor(
                    name="Front",
                    width=1920,
                    height=1080,
                    field_of_view_degrees=70,
                    pose=Transformation.from_euler_angles(
                        angles=[2.123, 3.0, -180.0], order="yxz", degrees=True, translation=[10.1, -12.0, 2.0]
                    ),
                    annotation_types=[
                        AnnotationTypes.SurfaceNormals2D,
                        AnnotationTypes.SemanticSegmentation2D,
                        AnnotationTypes.InstanceSegmentation2D,
                    ],
                )
            ]
        )

        scenario = Scenario(sensor_rig=sensor_rig)
        scenario.set_location(location)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Day, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Dawn, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Dusk, 1.0)
        scenario.environment.time_of_day.set_category_weight(TimeOfDays.Night, 1.0)
        # Place other agents
        scenario.add_agents(
            generator=TrafficGeneratorParameters(
                spawn_probability=0.8,
                position_request=PositionRequest(
                    location_relative_position_request=LocationRelativePositionRequest(
                        agent_tags=["EGO"],
                        max_spawn_radius=200.0,
                    )
                ),
            )
        )

        return scenario

    @pytest.fixture
    def atomic_only_scenario_storage_path(self, atomic_only_scenario: Scenario) -> AnyPath:
        with TemporaryDirectory() as tmp_dir:
            tmp_file = AnyPath(tmp_dir) / "test.json"
            atomic_only_scenario.save_scenario(path=tmp_file)
            yield tmp_file

    def check_atomic_only_scenario(self, scenario: Scenario, target_locatio: Location):
        assert scenario.sensor_rig is not None
        assert len(scenario.sensor_rig.sensors) == 1
        assert len(scenario.sensor_rig.cameras) == 1
        assert len(scenario.sensor_rig.camera_names) == 1
        assert "Front" in scenario.sensor_rig.camera_names

        camera = scenario.sensor_rig.cameras[0]
        assert camera.is_camera
        assert camera.camera_intrinsic.width == 1920
        assert camera.camera_intrinsic.height == 1080
        assert camera.camera_intrinsic.fov == 70.0
        assert AnnotationTypes.SurfaceNormals2D in camera.annotations_types
        assert AnnotationTypes.SemanticSegmentation2D in camera.annotations_types
        assert AnnotationTypes.InstanceSegmentation2D in camera.annotations_types
        extrinsic = camera.sensor_to_ego
        roll, pitch, yaw = extrinsic.as_euler_angles(order="xyz", degrees=True)
        # Definition in RFU, we test in FLU so rotation direction changed
        assert np.allclose(pitch, -3.0)
        assert np.allclose(roll, 2.123)
        assert np.allclose(yaw, -180.0)
        y, x, z = extrinsic.translation
        # test if translation is in FLU
        assert np.allclose(-1 * x, 10.1)
        assert np.allclose(y, -12.0)
        assert np.allclose(z, 2.0)

        assert target_locatio.name == scenario.location.name
        # assert "v2.0.1" == scenario.location.version

        time_of_day_distribution = scenario.environment.time_of_day
        assert len(time_of_day_distribution.buckets) == 4
        tod = [b.value for b in time_of_day_distribution.buckets]
        assert all([b.probability == 1.0 for b in time_of_day_distribution.buckets])
        assert "DAWN" in tod
        assert "DAY" in tod
        assert "DUSK" in tod
        assert "NIGHT" in tod

        assert len(scenario.pd_generators) == 1
        assert not isinstance(scenario.pd_generators[0], NonAtomicGeneratorMessage)

    def test_load_from_json_with_sensor_rig(self, atomic_only_scenario_storage_path: AnyPath, location: Location):
        scenario = Scenario.load_scenario(path=atomic_only_scenario_storage_path)
        self.check_atomic_only_scenario(scenario=scenario, target_locatio=location)

    def test_save_and_load_from_json_with_sensor_rig(
        self, atomic_only_scenario_storage_path: AnyPath, location: Location
    ):
        scenario = Scenario.load_scenario(path=atomic_only_scenario_storage_path)

        with TemporaryDirectory() as tmp_dir:
            tmp_file = AnyPath(tmp_dir) / "test.json"
            scenario.save_scenario(path=tmp_file)

            new_reload_scenario = Scenario.load_scenario(path=tmp_file)
            self.check_atomic_only_scenario(scenario=new_reload_scenario, target_locatio=location)

    def test_add_atomics(self, atomic_only_scenario: Scenario):
        scenario = atomic_only_scenario

        assert len(scenario.pd_generators) == 1
        scenario.add_ego(
            generator=EgoAgentGeneratorParameters(
                agent_type=AgentType.VEHICLE,
                position_request=PositionRequest(
                    lane_spawn_policy=LaneSpawnPolicy(
                        lane_type=EnumDistribution(
                            probabilities={"Drivable": 1.0},
                        )
                    )
                ),
            ),
        )

        assert len(scenario.pd_generators) == 2

        scenario.add_objects(
            generator=DebrisGeneratorParameters(
                max_debris_distance=25.0,
                spawn_probability=0.7,
                debris_asset_tag="trash_bottle_tall_01",
                position_request=PositionRequest(
                    location_relative_position_request=LocationRelativePositionRequest(
                        agent_tags=["EGO"],
                    )
                ),
            )
        )

        assert len(scenario.pd_generators) == 3

        # Place other agents
        scenario.add_agents(
            generator=TrafficGeneratorParameters(
                spawn_probability=0.8,
                position_request=PositionRequest(
                    location_relative_position_request=LocationRelativePositionRequest(
                        agent_tags=["EGO"],
                        max_spawn_radius=200.0,
                    )
                ),
            )
        )

        assert len(scenario.pd_generators) == 4

        cloned = scenario.clone()

        assert len(cloned.pd_generators) == 4

    def test_save_load_and_add_atomics(self, atomic_only_scenario: Scenario):
        scenario = atomic_only_scenario
        # Place other agents
        scenario.add_agents(
            generator=TrafficGeneratorParameters(
                spawn_probability=0.8,
                position_request=PositionRequest(
                    location_relative_position_request=LocationRelativePositionRequest(
                        agent_tags=["EGO"],
                        max_spawn_radius=200.0,
                    )
                ),
            )
        )

        assert len(scenario.pd_generators) == 2

        with TemporaryDirectory() as tmp_dir:
            tmp_file = AnyPath(tmp_dir) / "test.json"
            tmp_file = str(tmp_file.absolute())
            scenario.save_scenario(path=tmp_file)

            new_reload_scenario = Scenario.load_scenario(path=tmp_file)

            assert len(new_reload_scenario.pd_generators) == 2
            new_reload_scenario.add_objects(
                generator=DebrisGeneratorParameters(
                    max_debris_distance=25.0,
                    spawn_probability=0.7,
                    debris_asset_tag="trash_bottle_tall_01",
                    position_request=PositionRequest(
                        location_relative_position_request=LocationRelativePositionRequest(
                            agent_tags=["EGO"],
                        )
                    ),
                )
            )

            assert len(new_reload_scenario.pd_generators) == 3
            cloned = new_reload_scenario.clone()
            assert len(cloned.pd_generators) == 3

    def run_mocked_frame_generation(
        self,
        scenario: Scenario,
        ego_agent: SimulationAgentBase = None,
        frames_per_scene: int = 10,
        number_of_scenes: int = 1,
    ):
        sensor_rig = scenario.sensor_rig
        render_instance = MockRenderInstance(scenario=scenario)
        sim_instance = MockSimulationInstance(scenario=scenario, ego_agent=ego_agent)
        label_engine_instance = MockLabelEngineInstance(scenario=scenario, ego_agent=ego_agent)

        frame_count = 0
        for frame, scene in create_frame_stream(
            scenario=scenario,
            scene_indices=list(range(number_of_scenes)),
            frames_per_scene=frames_per_scene,
            sim_instance=sim_instance,
            render_instance=render_instance,
            label_engine_instance=label_engine_instance,
            use_label_engine=True,
            dataset_name="test",
            available_annotation_identifiers=[
                AnnotationIdentifier(annotation_type=a) for a in sensor_rig.available_annotations
            ],
        ):
            assert len(frame.camera_names) == len(sensor_rig.cameras)
            for camera_frame in frame.camera_frames:
                img = camera_frame.image.rgb
                sensor = next(
                    iter(
                        [
                            s
                            for s in scenario.sensor_rig.sensor_configs
                            if camera_frame.sensor_name.startswith(s.display_name)
                        ]
                    )
                )
                width = sensor.camera_intrinsic.width
                height = sensor.camera_intrinsic.height
                assert img.shape == (height, width, 3)
                frame_count += 1
        assert frame_count == (frames_per_scene * len(sensor_rig.cameras)) * number_of_scenes

    def test_scenario_custom(self):
        cnt_mock = mock.MagicMock()
        cnt_mock.setup_count = 0
        cnt_mock.update_state_count = 0
        cnt_mock.clone_count = 0

        class TestBehaviour(CustomSimulationAgentBehaviour):
            def __init__(self, counter: mock.MagicMock):
                self.counter = counter

            def set_initial_state(
                self,
                sim_state: ExtendedSimState,
                agent: CustomSimulationAgent,
                random_seed: int,
                raycast: Optional[Callable] = None,
            ):
                self.counter.setup_count += 1

            def update_state(
                self, sim_state: ExtendedSimState, agent: CustomSimulationAgent, raycast: Optional[Callable] = None
            ):
                self.counter.update_state_count += 1

            def clone(self) -> "TestBehaviour":
                self.counter.clone_count += 1
                return TestBehaviour(counter=self.counter)

        sensor_rig = SensorRig().add_camera(
            name="Front",
            width=1920,
            height=1080,
            field_of_view_degrees=70,
            pose=Transformation.from_euler_angles(
                angles=[0.0, 0.0, 0.0], order="xyz", degrees=True, translation=[0.0, 0.0, 2.0]
            ),
        )

        scenario = Scenario(sensor_rig=sensor_rig)
        scenario.set_location(Location(name="SF_6thAndMission_medium", version=LOCATION_VERSION))
        ego_agent = CustomSimulationAgents.create_ego_vehicle(sensor_rig=sensor_rig).set_behaviour(
            TestBehaviour(counter=cnt_mock)
        )
        scenario.add_ego(ego_agent)
        frames_per_scene = 100
        update_calls = (
            (frames_per_scene - 1) * scenario.sim_state.scenario_gen.sim_capture_rate
            + scenario.sim_state.scenario_gen.start_skip_frames
            + 1
        )
        self.run_mocked_frame_generation(scenario=scenario, ego_agent=ego_agent, frames_per_scene=frames_per_scene)
        assert cnt_mock.setup_count == 1
        assert cnt_mock.update_state_count == update_calls
        assert cnt_mock.clone_count == 1

    # def test_scenario_custom_and_atomic(self):
    #     cnt_mock = mock.MagicMock()
    #     cnt_mock.setup_count = 0
    #     cnt_mock.update_state_count = 0
    #     cnt_mock.clone_count = 0
    #
    #     class TestBehaviour(CustomSimulationAgentBehaviour):
    #         def __init__(self, counter: mock.MagicMock):
    #             self.counter = counter
    #
    #         def set_initial_state(
    #             self,
    #             sim_state: ExtendedSimState,
    #             agent: CustomSimulationAgent,
    #             random_seed: int,
    #             raycast: Optional[Callable] = None,
    #         ):
    #             self.counter.setup_count += 1
    #
    #         def update_state(
    #             self, sim_state: ExtendedSimState, agent: CustomSimulationAgent, raycast: Optional[Callable] = None
    #         ):
    #             self.counter.update_state_count += 1
    #
    #         def clone(self) -> "TestBehaviour":
    #             self.counter.clone_count += 1
    #             return TestBehaviour(counter=self.counter)
    #
    #     sensor_rig = SensorRig().add_camera(
    #         name="Front",
    #         width=1920,
    #         height=1080,
    #         field_of_view_degrees=70,
    #         pose=Transformation.from_euler_angles(
    #             angles=[0.0, 0.0, 0.0], order="xyz", degrees=True, translation=[0.0, 0.0, 2.0]
    #         ),
    #     )
    #
    #     scenario = Scenario(sensor_rig=sensor_rig)
    #     scenario.set_location(Location(name="SF_6thAndMission_medium", version=LOCATION_VERSION))
    #     ego_agent = CustomSimulationAgents.create_ego_vehicle(sensor_rig=sensor_rig).set_behaviour(
    #         TestBehaviour(counter=cnt_mock)
    #     )
    #     scenario.add_agents(ego_agent)
    #
    #     scenario.add_agents(
    #         generator=TrafficGeneratorParameters(
    #             spawn_probability=0.8,
    #             position_request=PositionRequest(
    #                 location_relative_position_request=LocationRelativePositionRequest(
    #                     agent_tags=["EGO"],
    #                     max_spawn_radius=200.0,
    #                 )
    #             ),
    #         )
    #     )
    #
    #     frames_per_scene = 100
    #     update_calls = (
    #         (frames_per_scene - 1) * scenario.sim_state.scenario_gen.sim_capture_rate
    #         + scenario.sim_state.scenario_gen.start_skip_frames
    #         + 1
    #     )
    #     # We use the mocked ego_agent here to avoid having SimulationAgent and CustomVehicleSimulationAgent
    #     # with same agent id in the sim state.
    #     self.run_mocked_frame_generation(scenario=scenario, ego_agent=ego_agent, frames_per_scene=frames_per_scene)
    #     assert cnt_mock.setup_count == 1
    #     assert cnt_mock.update_state_count == update_calls
    #     assert cnt_mock.clone_count == 1

    def test_scenario_atomics_in_loop(self, atomic_only_scenario: Scenario):
        for _ in range(3):
            self.run_mocked_frame_generation(scenario=atomic_only_scenario)

    def test_scenario_atomics_multiple_scenes(self, atomic_only_scenario: Scenario):
        self.run_mocked_frame_generation(scenario=atomic_only_scenario, number_of_scenes=3, frames_per_scene=10)

    @pytest.mark.parametrize(
        "yield_every_sim_state",
        [True, False],
    )
    def test_sim_state_encode(self, yield_every_sim_state: bool, atomic_only_scenario: Scenario):
        sim_instance = MockSimulationInstance(scenario=atomic_only_scenario, ego_agent=None)

        number_of_scenes = 4
        frames_per_scene = 20
        start_skip_frames = 10

        with TemporaryDirectory() as tmp_dir:
            tmp_dir = AnyPath(tmp_dir)

            encode_sim_states(
                scenario=atomic_only_scenario,
                output_folder=tmp_dir,
                scene_indices=list(range(number_of_scenes)),
                start_skip_frames=start_skip_frames,
                frames_per_scene=frames_per_scene,
                sim_instance=sim_instance,
                render_instance=None,
                yield_every_sim_state=yield_every_sim_state,
            )

            every_frame_and_warmup_count = number_of_scenes * (
                frames_per_scene - 1
            ) * atomic_only_scenario.sim_state.scenario_gen.sim_capture_rate + number_of_scenes * (
                start_skip_frames + 1
            )
            assert sim_instance.query_sim_state_calls == every_frame_and_warmup_count

            assert len(list(tmp_dir.iterdir())) == number_of_scenes
            for dir in tmp_dir.iterdir():
                files_in_scene_dir = [f for f in dir.iterdir() if f.suffix == ".pd"]
                if yield_every_sim_state is True:
                    target_num_stored_sim_states = (
                        frames_per_scene - 1
                    ) * atomic_only_scenario.sim_state.scenario_gen.sim_capture_rate + (start_skip_frames + 1)
                    assert len(files_in_scene_dir) == target_num_stored_sim_states
                else:
                    assert len(files_in_scene_dir) == frames_per_scene
                for file in dir.iterdir():
                    assert file.name.endswith(".pd")
                    decoded = pd.state.bytes_to_state(file.open("rb").read())
                    assert isinstance(decoded, pd.state.State)
                    # in our mock we just add 1 agent
                    assert len(decoded.agents) == 1

    def test_discrete_scenario_yields_same_states(self, mixed_scenario: Scenario):
        class StreetCreepBehaviour(CustomSimulationAgentBehaviour):
            def __init__(
                self,
                speed: float = 5.0,
            ):
                super().__init__()
                self.speed = speed
                self._initial_pose: Transformation = np.eye(4)

            def set_initial_state(
                self,
                sim_state: ExtendedSimState,
                agent: CustomSimulationAgent,
                random_seed: int,
                raycast: Optional[Callable] = None,
            ):
                agent.set_pose(pose=np.eye(4))

            def update_state(
                self, sim_state: ExtendedSimState, agent: CustomSimulationAgent, raycast: Optional[Callable] = None
            ):
                agent.set_pose(pose=self._initial_pose + agent.pose)

            def clone(self) -> "StreetCreepBehaviour":
                return StreetCreepBehaviour(
                    speed=self.speed,
                )

        ego_agent = CustomSimulationAgents.create_ego_vehicle(sensor_rig=mixed_scenario.sensor_rig).set_behaviour(
            StreetCreepBehaviour()
        )
        mixed_scenario.add_ego(ego_agent)

        sim_instance = MockSimulationInstance(scenario=mixed_scenario, ego_agent=ego_agent)

        number_of_scenes = 4
        frames_per_scene = 20

        with TemporaryDirectory() as tmp_dir:
            tmp_dir = AnyPath(tmp_dir)

            encode_sim_states(
                scenario=mixed_scenario,
                output_folder=tmp_dir,
                scene_indices=list(range(number_of_scenes)),
                frames_per_scene=frames_per_scene,
                sim_instance=sim_instance,
                render_instance=None,
                yield_every_sim_state=True,
            )

            sim_instance_1 = FromDiskSimulation()
            sim_instance_2 = FromDiskSimulation()
            scene_dir = AnyPath(f"{tmp_dir}/scene_000000")
            state_stream_1 = sim_instance_1.state_generator(folder=scene_dir)
            state_stream_2 = sim_instance_2.state_generator(folder=scene_dir)
            for state_1, state_2 in zip(state_stream_1, state_stream_2):
                state_1_bytes = state_to_bytes(state_1)
                state_2_bytes = state_to_bytes(state_2)
                assert state_1_bytes == state_2_bytes

    def test_sim_stream_from_scenario_yields_same_states(self, mixed_scenario: Scenario):
        class StreetCreepBehaviour(CustomSimulationAgentBehaviour):
            def __init__(
                self,
                speed: float = 5.0,
            ):
                super().__init__()
                self.speed = speed
                self._initial_pose: Transformation = np.eye(4)

            def set_initial_state(
                self,
                sim_state: SimState,
                agent: CustomSimulationAgent,
                random_seed: int,
                raycast: Optional[Callable] = None,
            ):
                agent.set_pose(pose=np.eye(4))

            def update_state(
                self, sim_state: SimState, agent: CustomSimulationAgent, raycast: Optional[Callable] = None
            ):
                agent.set_pose(pose=self._initial_pose + agent.pose)

            def clone(self) -> "StreetCreepBehaviour":
                return StreetCreepBehaviour(
                    speed=self.speed,
                )

        ego_agent = CustomSimulationAgents.create_ego_vehicle(sensor_rig=mixed_scenario.sensor_rig).set_behaviour(
            StreetCreepBehaviour()
        )
        mixed_scenario.add_ego(ego_agent)

        sim_instance_1 = MockSimulationInstance(scenario=mixed_scenario, ego_agent=ego_agent)
        sim_instance_2 = FromDiskSimulation()
        sim_instance_3 = FromDiskSimulation()

        number_of_scenes = 4
        frames_per_scene = 20
        start_skip_frames = 5

        with TemporaryDirectory() as tmp_dir:
            tmp_dir = AnyPath(tmp_dir)

            encode_sim_states(
                scenario=mixed_scenario,
                output_folder=tmp_dir,
                scene_indices=list(range(number_of_scenes)),
                frames_per_scene=frames_per_scene,
                start_skip_frames=start_skip_frames,
                sim_instance=sim_instance_1,
                render_instance=None,
                yield_every_sim_state=True,
            )

            collection = SimulatedScenarioCollection(storage_folder=tmp_dir)
            collection_2 = SimulatedScenarioCollection(storage_folder=tmp_dir)
            discrete_scenario_1 = collection.get_discrete_scenario(scene_index=0)
            discrete_scenario_2 = collection_2.get_discrete_scenario(scene_index=0)
            state_stream_1 = sim_stream_from_discrete_scenario(
                discrete_scenario=discrete_scenario_1,
                sim_state_type=ExtendedSimState,
                sim_instance=sim_instance_2,
                render_instance=None,
            )
            states_1 = [state_reference.state for state_reference in state_stream_1]
            assert len(states_1) == frames_per_scene
            state_stream_2 = sim_stream_from_discrete_scenario(
                discrete_scenario=discrete_scenario_2,
                sim_state_type=ExtendedSimState,
                sim_instance=sim_instance_3,
                render_instance=None,
            )
            states_2 = [state_reference.state for state_reference in state_stream_2]
            assert len(states_2) == frames_per_scene
            for state_1, state_2 in zip(states_1, states_2):
                state_1_bytes = state_to_bytes(state_1)
                state_2_bytes = state_to_bytes(state_2)
                assert state_1_bytes == state_2_bytes
