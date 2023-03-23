import numpy as np
import pyrealsense2 as rs
from PIL import Image
import cv2

from core.logger import Logger
from core.service import ModelService, CameraService, RobotService
from core.utils import *
from yolov5.models.common import Detections
import math



class RobotController:
    def __init__(self):
        self.robot = RobotService.connect_robot()

    def test_coords(self):
        self.robot.MoveL([-413.042, 1095.847, 572.319,  -108.184, -0.674, 46.740])
        self.robot.MoveL([24.799, 35.312, 555.736,  -108.184, -0.674, 46.740])
        self.robot.MoveL([-441.859, 790.234, 511.569,  -108.184, -0.674, 46.740])
        self.robot.MoveL([72.488, 766.831, 579.819,  -108.184, -0.674, 46.740])
        self.robot.MoveL([58.012, 352.964, 503.736,  -108.184, -0.674, 46.740])

    def get_home_pose(self):
        return [86.4947357178, -88.8127593994, 116.225532532, 4.04822254181, 80.8361358643, -45.0]

    def goto_home(self):
        self.robot.MoveJ(self.get_home_pose())
        # self.robot.MoveL([680.000, -34.506, 772.500,  0.000, 90.000, -0.000])

    def goto_conveyor(self):
        self.robot.MoveJ([-4.19577646255, 53.4715423584, 100.973381042, -3.75705695152, -66.7086486816, -45.0])

    def goto_crate(self, crate_coords):
        pass

    def goto_infront_crate(self, crate_coords):
        pass

    def digitalIO(self, a):  # set the digital output ON or OFF
        if int(a) == 1:
            self.robot.set_digital_output(1, 1)
            print("ON")
        elif int(a) == 0:
            self.robot.set_digital_output(1, 0)
            print("OFF")


class ModelController:
    def __init__(self, app):
        self.app = app
        self.model = ModelService.load_model()

    def detect(self, array: np.ndarray) -> Detections:
        array[:, :, 0], array[:, :, 2] = array[:, :, 2], array[:, :, 0].copy()
        image: Image = Image.fromarray(array.astype('uint8'), 'RGB')
        path = save_img(image)
        return self.model(path)

class CameraController:
    def __init__(self, app):
        self.depth_sensor = None
        self.profile = None
        self.is_connected = None
        self.app = app
        self.context = rs.context()
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.initialize()
        # self.profile.get_device().query_sensors()[0].set_option(rs.option.alternate_ir, False)

    def initialize(self):
        self.is_connected = self.attempt_connection()
        self.profile = self.pipeline.get_active_profile()
        self.depth_sensor = self.profile.get_device().query_sensors()[0]
        self.depth_sensor.set_option(rs.option.enable_auto_exposure, False)


    def get_intrinsics(self):
        intr = rs.video_stream_profile(self.profile.get_stream(rs.stream.depth)).get_intrinsics()
        return intr

    def get_cam_coords(self, data):
        depth: float = data['depth']
        center_x: float = data['center_x']
        center_y: float = data['center_y']
        cam_coords = rs.rs2_deproject_pixel_to_point(self.get_intrinsics(), [center_x, center_y], depth=depth)
        return cam_coords

    def get_image(self) -> tuple:
        ret, depth_image, color_image = CameraService.get_frame(self.pipeline)
        if not ret:
            print("Error: Frame not found")
        return depth_image, color_image

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
