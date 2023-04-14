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
        self.model: ModelController = None
        self.camera: CameraController = None
        self.robotComm: RobotCommunicator = None

    def start(self):
        self.model = ModelController()
        self.camera = CameraController()
        self.robotComm = RobotCommunicator()

        return True

    def update(self):
        # self.robotComm.server.moveJ([89.1, 83.0, 111.2, 179.1, 104.2, -180.2])
        # data, results, crates_data = self.search_crate()
        # angle, center = crates_data.get_pickup_data(data)
        # Logger.info(f"Angle: {angle}, Center: {center}")
        # return wait_input()

        self.robotComm.goto_home()
        # tcp = self.robotComm.server.get_tcp()

        poses = self.robotComm.get_serpent_poses()
        counter = 0
        while True:
            if counter == len(poses):
                break
            pose = poses[counter]
            self.robotComm.server.moveLR(pose)
            data, results, crates_data = self.search_crate()
            if data is None:
                counter += 1
                continue
            angle, center = crates_data.get_pickup_data(data)
            if center is None:
                continue
            Logger.info(f"Angle: {angle}, Center: {center}")
            self.pickup_crate(data, center, angle)
            self.robotComm.goto_conveyor()

        self.robotComm.goto_home()
        self.robotComm.pause()
        return True

    def search_crate(self):
        results, crates_data = self.get_image()
        # Continue to next pose if no crate found
        if crates_data.df.size == 0:
            return None, None, None


        # If crate found, go infront of crate
        for index, data in crates_data.df.iterrows():
            Logger.info(f"depth: {data['depth']}")
            if data['depth'] >= 750:
                continue
            data['depth'] *= 0.9
            cam_coords = self.camera.get_cam_coords(data)
            world_coords = self.robotComm.cam_to_world_coords(cam_coords)
            self.robotComm.goto_infront_crate(world_coords)
            data, new_results, crates_data_new = self.find_pickable_crate()
            return data, new_results, crates_data_new
        return None, None, None


    def find_pickable_crate(self):
        results, crates_data = self.get_image()
        if crates_data.df.size == 0:
            return None, None, None
        for index, data in crates_data.df.iterrows():
            if data['xmax']-data['xmin'] < 200 or data['ymax']-data['ymin'] < 100:
                continue
            return data, results, crates_data
        return None, None, None


    def get_image(self):
        depth_image, color_image, colorized_depth = self.camera.get_image()
        # Get detection results
        results: Detections = self.model.detect(color_image)
        dataframe: DataFrame = results.pandas().xyxy[0]
        # Initialize crate list (get depth of crates) and sort
        crates_data = CratesData(dataframe, color_image, depth_image, colorized_depth)
        crates_data.sort_by_height()
        return results, crates_data


    def pickup_crate(self, data, center, angle):
        data['center_x'] = center[0]
        data['center_y'] = center[1]
        Logger.debug(f"Depth: {data['depth']}")
        Logger.debug(f"Center: {data['center_x']}, {data['center_y']}")
        cam_coords = self.camera.get_cam_coords(data)
        Logger.debug(f"Cam: {cam_coords}")
        world_coords = self.robotComm.cam_to_world_coords(cam_coords)
        Logger.debug(f"World: {world_coords}\n")
        # self.robotComm.server.moveL(world_coords)
        self.robotComm.approach_crate(world_coords)


    def stop(self):
        del self.camera
        del self.model
