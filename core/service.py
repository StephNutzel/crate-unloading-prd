import pyrealsense2 as rs
import torch
from robodk.robolink import *
import cv2

from core.logger import Logger
from core.utils import *


class RobotService:
    IP_ROBOT = "192.168.0.100"

    @staticmethod
    def connect_robot() -> Item:
        robot: Item = RobotService._find_robot()
        robot_state, robot_valid = RobotService._connect_with_robot(robot)
        while (not robot) or (robot_state[0] < 0):
            robot: Item = RobotService._find_robot()
            robot_state, robot_valid = RobotService._connect_with_robot(robot)
            Logger.warning("No robot found or unable to connect. press enter to try again ('q' to quit)")
            if input(" > ") == 'q':
                return robot
        Logger.info(f"Succesfully connected to robot [{robot}]")
        return robot

    @staticmethod
    def _find_robot() -> Item:
        RDK: Robolink = Robolink()
        robot_list = RDK.ItemList(filter=ITEM_TYPE_ROBOT)
        index = 0
        if len(robot_list) == 1: return robot_list[0]
        for robot in robot_list:
            index += 1
            print(f"{index}: {robot}")
        Logger.info("Please select robot by number")
        user_input = int(input(" > "))
        return robot_list[user_input - 1]

    @staticmethod
    def _connect_with_robot(robot: Item):
        if (robot == None): return None, None
        robot.Connect(robot_ip=RobotService.IP_ROBOT, blocking=True)
        return robot.ConnectedState(), robot.Valid()


class ModelService:
    @staticmethod
    def load_model():
        model = torch.hub.load('yolov5', 'custom', ModelService.get_weights_path(), source='local')
        return model

    @staticmethod
    def get_weights_path():
        return get_resource('run', 'weights', 'best.pt')


class CameraService:
    WIDTH = 640
    HEIGHT = 480

    @staticmethod
    def check_connection(context):
        dev_list = context.query_devices()
        if len(dev_list) == 0:
            return False
        return True

    @staticmethod
    def initialize(pipeline, config):
        Logger.debug("Initializing camera...")
        # Get device product line for setting a supporting resolution
        pipeline_wrapper = rs.pipeline_wrapper(pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)  # BREAKS HERE
        device = pipeline_profile.get_device()
        device_product_line = str(device.get_info(rs.camera_info.product_line))

        config.enable_stream(rs.stream.depth, CameraService.WIDTH, CameraService.HEIGHT, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, CameraService.WIDTH, CameraService.HEIGHT, rs.format.bgr8, 30)

        Logger.debug("Camera initialized")

    @staticmethod
    def get_frame(pipeline):
        frames = pipeline.wait_for_frames()

        align = rs.align(rs.stream.color)
        aligned_frames = align.process(frames)
        color_frame = aligned_frames.first(rs.stream.color)
        depth_frame = aligned_frames.get_depth_frame()

        # Colored Image
        color_image = np.asanyarray(color_frame.get_data(), dtype=np.uint8)
        depth_image = np.asanyarray(depth_frame.get_data())

        # Depth Image
        colorizor = rs.colorizer()
        colorizor.set_option(rs.option.color_scheme, 2)
        colorizor_depth = np.asanyarray(colorizor.colorize(depth_frame).get_data(), dtype=np.uint8)

        return True, depth_image, color_image, colorizor_depth
