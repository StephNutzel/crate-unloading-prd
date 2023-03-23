import numpy as np
from pandas import DataFrame
from robodk.robolink import Item

import pyrealsense2 as rs
from core.controller import ModelController, CameraController, RobotController
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
        self.robot: RobotController = RobotController()

        if self.model is None or self.camera is None or self.robot is None:
            return False
        return True

    def update(self):
        # self.robot.test_coords()
        # self.robot.goto_home()
        # print(self.robot.robot.Pose())
        # print(self.robot.robot.Joints())

        # Get and rotate images
        # self.robot.goto_home()

        depth_image, color_image = self.camera.get_image()
        color_image = np.rot90(color_image, 1)
        depth_image = np.rot90(depth_image, 1)

        # Show input image
        # print(color_image.shape)
        # cv2.imshow("Title", im=color_image)
        # cv2.waitKey(0) == ord('q')
        # cv2.destroyAllWindows()

        # Get detection results
        results: Detections = self.model.detect(color_image)
        dataframe: DataFrame = results.pandas().xyxy[0]

        # Initialize crate list (get depth of crates) and sort
        crates_data = CratesData(dataframe, color_image, depth_image)
        crates_data.sort_by_height()

        print(f"Size: {crates_data.size()}")
        for index, data in crates_data.df.iterrows():
            print(f"Depth: {data['depth']}")
            # cam_coords = self.camera.get_cam_coords(data)
            # coords = robomath.Offset(self.robot.robot.Pose(), [*cam_coords, 0, 0, 0])
            # print(f"Coords: {coords}")

        # Goto first crate
        # self.robot.goto_infront_crate(["TODO"])

        # rs.options.set_option(rs.option.min_distance, 10)

        depth_image, color_image = self.camera.get_image()
        # color_image = np.rot90(color_image, 1)
        # depth_image = np.rot90(depth_image, 1)

        results: Detections = self.model.detect(color_image)
        dataframe: DataFrame = results.pandas().xyxy[0]
        crates_data = CratesData(dataframe, color_image, depth_image)
        crates_data.sort_by_height()
        crates_data.get_pickup_data()

        # results.show()
        # self.robot.goto_conveyor()
        # return wait_input()
        return True

    def stop(self):
        del self.camera
        del self.model
