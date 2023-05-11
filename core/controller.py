import numpy as np
import pyrealsense2 as rs
from PIL import Image
import cv2

from core.logger import Logger
from core.service import ModelService, CameraService, RobotService
from core.utils import *
from yolov5.models.common import Detections
from core.socketserver import SocketServer
from robodk import robomath
import math


class RobotCommunicator:
    def __init__(self):
        self.server: SocketServer = SocketServer()

    def get_serpent_poses(self):
        margin_x = 300
        amount_x = 2
        margin_z = -200
        amount_z = 7
        # start_x = -200
        start = [-200, 500, 700, 90, 90, 0]
        arr = []
        for z in range(amount_z):
            for x in range(amount_x):
                arr.append(
                    [start[0] + (x * margin_x), start[1], start[2] + (z * margin_z), start[3], start[4], start[5]])
        return arr

    def set_suction(self, setOn):
        if (setOn):
            self.server.sendCommand("set:suction_on")
        else:
            self.server.sendCommand("set:suction_off")

    def goto_conveyor(self):
        self.server.sendCommand(f"goto:conveyor")

    def approach_crate(self, arr):
        self.server.sendCommand(f"approach:{arr}")

    def get_prepare_pose(self):
        return [90.0, -26.1, 95.1, 0, 39.7, 0]

    def get_home_pose(self):
        return [123.4, -13.7, 143.3, 46.0, -50.0, -33.6]

    def get_home_tcp(self):
        pass
        # return [-28.0, 428.2, 426.4, 90, 90, 0]
        # return [-185.2, 338.8, 398.0, 90, 90, 0]

    def get_conveyor_pose(self):
        return [-4.19577646255, 53.4715423584, 100.973381042, -3.75705695152, -66.7086486816, 0]

    def goto_coords(self, arr):
        self.server.moveCoords(arr)

    def goto_infront_crate(self, arr):
        self.server.moveL([arr[0], 600, arr[2], 90, 90, 0])

    def goto_prepare_pose(self):
        self.server.moveJ(self.get_prepare_pose())

    def goto_home(self):
        self.server.moveJ(self.get_home_pose())

    def pause(self):
        Logger.debug("set: pause")
        self.server.sendCommand(f"set:pause")

    def cam_to_world_coords(self, pos):
        tcp = self.server.get_tcp()
        return [tcp[0] + pos[0], tcp[1] + pos[2], tcp[2] - pos[1], tcp[3], tcp[4], tcp[5]]


class RobotController:
    def __init__(self):
        self.robot = RobotService.connect_robot()

    def digitalIO(self, a):  # set the digital output ON or OFF
        if int(a) == 1:
            self.robot.set_digital_output(1, 1)
            print("ON")
        elif int(a) == 0:
            self.robot.set_digital_output(1, 0)
            print("OFF")


class ModelController:
    def __init__(self):
        self.model = ModelService.load_model()

    def detect(self, array: np.ndarray) -> Detections:
        array[:, :, 0], array[:, :, 2] = array[:, :, 2], array[:, :, 0].copy()
        image: Image = Image.fromarray(array.astype('uint8'), 'RGB')
        path = save_img(image)
        return self.model(path)


class CameraController:
    def __init__(self):
        self.depth_sensor = None
        self.profile = None
        self.is_connected = None
        self.context = rs.context()
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.initialize()

    def initialize(self):
        self.is_connected = self.attempt_connection()
        self.profile = self.pipeline.get_active_profile()
        self.depth_sensor = self.profile.get_device().query_sensors()[0]
        self.depth_sensor.set_option(rs.option.enable_auto_exposure, False)
        # self.profile.get_device().query_sensors()[0].set_option(rs.option.alternate_ir, False)

    def get_intrinsics(self):
        intr = rs.video_stream_profile(self.profile.get_stream(rs.stream.depth)).get_intrinsics()
        return intr

    def get_cam_coords(self, data):
        depth: float = data['depth']
        center_x: float = data['center_x']
        center_y: float = data['center_y']
        cam_coords = rs.rs2_deproject_pixel_to_point(self.get_intrinsics(), [center_x, center_y], depth=depth)
        return [cam_coords[0], cam_coords[1], cam_coords[2]]

    def get_image(self) -> tuple:
        ret, depth_image, color_image, colorized_depth = CameraService.get_frame(self.pipeline)
        if not ret:
            Logger.error("Frames not found")
        return depth_image, color_image, colorized_depth

    def attempt_connection(self) -> bool:
        conn = CameraService.check_connection(self.context)
        while not conn:
            conn = CameraService.check_connection(self.context)
            Logger.warning("No intel realsense devices found. press enter to try again ('q' to quit)")
            if input(" > ") == 'q':
                return False
        CameraService.initialize(self.pipeline, self.config)
        self.start()
        Logger.info(f"Succesfully connected to intel realsense [{self.context.devices}]")
        return True

    def start(self):
        Logger.debug("Camera starting pipeline...")
        self.profile = self.pipeline.start(self.config)
        Logger.debug("Camera pipeline Started")

    def stop(self):
        Logger.debug("Camera stopping pipeline...")
        self.pipeline.stop()
        Logger.debug("Camera pipeline Stopped")
