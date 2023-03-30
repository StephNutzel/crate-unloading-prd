import numpy as np
import pyrealsense2 as rs
from PIL import Image
import cv2

from core.logger import Logger
from core.service import ModelService, CameraService, RobotService
from core.utils import *
from yolov5.models.common import Detections
from core.socketserver import SocketServer
import math


class RobotCommunicator:
    def __init__(self):
        self.server: SocketServer = SocketServer()

    def get_prepare_pose(self):
        return [90.0, -26.1, 95.1, 2.3, 39.7, -48.1]

    def get_home_pose(self):
        return [86.4947357178, -88.8127593994, 116.225532532, 4.04822254181, 80.8361358643, -45.0]

    def get_home_tcp(self):
        return [-58.0, -244.8, 623.8, 90.7, 108.2, -43.0]

    def get_conveyor_pose(self):
        return [-4.19577646255, 53.4715423584, 100.973381042, -3.75705695152, -66.7086486816, -45.0]

    def goto_coords(self, arr):
        self.server.moveCoords(arr)


    def goto_infront_crate(self, arr):
        pos = self.cam_to_world_coords(arr)
        self.server.moveJ(self.get_prepare_pose())
        self.server.moveL([pos[0], 600, pos[2]+1000, 90, 90, -45])

    def goto_cam_coords(self, arr):
        self.server.moveJ([*self.cam_to_world_coords(arr), 90, 90, -45])

    def goto_prepare_pose(self):
        self.server.moveJ(self.get_prepare_pose())

    def goto_home(self):
        self.server.moveJ(self.get_home_pose())

    def goto_conveyor(self):
        self.server.moveJ(self.get_conveyor_pose())

    def cam_to_world_coords(self, pos):
        tcp_pose = self.get_home_tcp()
        camera_pos = np.array([tcp_pose[0], tcp_pose[1], tcp_pose[2]])  # en mètres
        camera_orientation = np.array([tcp_pose[3]/180*math.pi, tcp_pose[4]/180*math.pi, tcp_pose[5]/180*math.pi])  # en radians

        rot_angle = 0
        # Matrice de rotation de la caméra
        rot_matrix = np.array([[np.cos(np.radians(rot_angle)), -np.sin(np.radians(rot_angle)), 0],
                               [np.sin(np.radians(rot_angle)), np.cos(np.radians(rot_angle)), 0],
                               [0, 0, 1]])

        # Matrice de transformation homogène de la caméra par rapport à la base du robot
        rot_matrix = np.matmul(rot_matrix, np.array([[np.cos(camera_orientation[1]), 0, np.sin(camera_orientation[1])],
                                            [0, 1, 0],
                                            [-np.sin(camera_orientation[1]), 0, np.cos(camera_orientation[1])]]))

        rot_matrix = np.matmul(rot_matrix, np.array([[np.cos(camera_orientation[2]), -np.sin(camera_orientation[2]), 0],
                                            [np.sin(camera_orientation[2]), np.cos(camera_orientation[2]), 0],
                                            [0, 0, 1]]))
        trans_matrix = np.eye(4)
        trans_matrix[:3, :3] = rot_matrix
        trans_matrix[:3, 3] = camera_pos
        trans_matrix = np.linalg.inv(trans_matrix)

        # Coordonnées de l'objet vue par la caméra dans le système de coordonnées de la caméra
        camera_coord = np.array([pos[0], pos[1], pos[2]])

        # Convertir la coordonnée dans le système de coordonnées de la base du robot
        homogeneous_coord = np.ones(4)
        homogeneous_coord[:3] = camera_coord
        base_coord = np.matmul(trans_matrix, homogeneous_coord)
        base_coord = base_coord[:3]
        return [base_coord[2], base_coord[1], base_coord[0]]

# z = x or y (it is left or right)

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
        return [cam_coords[0], cam_coords[1], cam_coords[2]-50]

    def get_image(self) -> tuple:
        ret, depth_image, color_image, colorized_depth = CameraService.get_frame(self.pipeline)
        if not ret:
            print("Error: Frame not found")
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
