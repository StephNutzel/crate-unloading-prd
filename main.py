import numpy as np
from pandas import DataFrame
from robodk.robolink import Item

import time
import pyrealsense2 as rs
from core.controller import ModelController, CameraController, RobotController, RobotCommunicator
from core.logger import Logger
from core.models import CratesData
from robodk import robomath
import cv2

from yolov5.models.common import Detections


def wait_input():
    Logger.info("Press enter to continue ('q' to quit)")
    user_in = input(" > ")
    if user_in == 'q':
        return False
    return True


class App:
    def __init__(self):
        self.model = None
        self.camera = None

    def start(self):
        self.model: ModelController = ModelController(self)
        self.camera: CameraController = CameraController(self)
        # self.robot: RobotController = RobotController()
        self.robotComm: RobotCommunicator = RobotCommunicator()

        # if self.model is None or self.camera is None:# or self.robot is None:
        #     return False
        return True

    def update(self):
        # self.robot.goto_home()
        # Get and rotate images
        # self.robotComm.server.moveL([-97.9, 272.5, 775.0, 0, 0, 0])
        # time.sleep(10)
        self.robotComm.goto_home()

        depth_image, color_image, colorized_depth = self.camera.get_image()
        color_image = np.rot90(color_image, 1)
        depth_image = np.rot90(depth_image, 1)
        colorized_depth = np.rot90(depth_image, 1)

        # Get detection results
        results: Detections = self.model.detect(color_image)
        dataframe: DataFrame = results.pandas().xyxy[0]

        # Initialize crate list (get depth of crates) and sort
        crates_data = CratesData(dataframe, color_image, depth_image, colorized_depth)
        crates_data.df['xmin']
        crates_data.df['ymin']
        crates_data.df['xmax']
        crates_data.df['ymax']
        crates_data.sort_by_height()

        results.show()
        print(f"Size: {crates_data.size()}")
        for index, data in crates_data.df.iterrows():
            self.pickup_crate(data)

        return wait_input()


    def pickup_crate(self, data):
        print(f"Depth: {data['depth']}")
        cam_coords = self.camera.get_cam_coords(data)
        print(f"Cam: {cam_coords}")
        world_coords = self.robotComm.cam_to_world_coords(cam_coords)
        print(f"World: {world_coords}")
        self.robotComm.goto_infront_crate(cam_coords)




        # world_coords = robomath.Offset(self.robot.robot.Pose(), [*cam_coords, 0, 0, 0])
        # print(f"World: {world_coords}")
        # self.robotComm.goto_coords(world_coords)
        # print(f"Coords: {coords}")

        # Goto first crate
        # self.robot.goto_infront_crate(["TODO"])

        # rs.options.set_option(rs.option.min_distance, 10)

        # depth_image, color_image, colorized_depth = self.camera.get_image()
        # color_image = np.rot90(color_image, 1)
        # depth_image = np.rot90(depth_image, 1)
        # colorized_depth = np.rot90(depth_image, 1)
        #
        # results: Detections = self.model.detect(color_image)
        # dataframe: DataFrame = results.pandas().xyxy[0]
        # crates_data = CratesData(dataframe, color_image, depth_image, colorized_depth)
        # crates_data.sort_by_height()
        # # crates_data.get_pickup_data()
        #
        # self.robotComm.goto_conveyor()

    def stop(self):
        del self.camera
        del self.model
