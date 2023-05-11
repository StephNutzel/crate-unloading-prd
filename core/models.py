from pandas import DataFrame
from core.utils import CrateUtils
import cv2
import numpy as np
import math
from core.logger import Logger
import pyrealsense2 as rs
import time
from matplotlib import pyplot as plt
from PIL import Image


class CratesData:
    def __init__(self, df: DataFrame, color_image, depth_image, colorized_depth):
        self.df = df
        self.color_image = color_image
        self.depth_image = depth_image
        self.colorized_depth = colorized_depth
        self._append_dataframe_center()
        self._append_dataframe_depth()

    def find_contours(self, aug_image):
        contours, hierarchy = cv2.findContours(aug_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) is 0:
            Logger.error("Error contours not found!")
            return None, None
        max_contour = max(contours, key=cv2.contourArea)  # Find the largest contour (hopefully the crate)
        x, y, w, h = cv2.boundingRect(max_contour)

        # Get smallest box
        rect = cv2.minAreaRect(max_contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        return box, [x, y, w, h]

    def _find_angle_center(self, box):
        angle: float
        point_a: tuple = None
        point_b: tuple = None
        # Get the top two points
        for point in box:
            if point_a is None:
                point_a = point
                continue
            if point_b is None:
                point_b = point
                continue
            if point[1] < point_b[1]:
                p_temp = point_b
                point_b = point
                point = p_temp
            if point[1] < point_a[1]:
                point_a = point

        center: tuple = (((point_b[0] - point_a[0]) / 2) + point_a[0], ((point_b[1] - point_a[1]) / 2 + point_a[1]))
        angle = (math.atan2((point_b[0] - point_a[0]), abs(point_b[1] - point_a[1])) * 180 / math.pi)
        angle = (angle / abs(angle)) * (90 - abs(angle))
        print(f"Angle: {angle}")
        return angle, center

    def get_pickup_data(self, data):
        # Get images
        color_image = cv2.cvtColor(np.uint8(self.color_image), cv2.COLOR_RGB2BGR)
        aug_image = cv2.cvtColor(np.uint8(self.colorized_depth), cv2.COLOR_RGB2GRAY)

        # bounding box position from ML detection
        elem = data

        # for index, elem in self.df.iterrows():
        p1 = [max(int(CrateUtils.get_x_min(elem)) + 100, 0), max(int(CrateUtils.get_y_min(elem)) + 10, 0)]
        # p2 = [min(int(CrateUtils.get_x_max(elem))-50, 640), min(int(CrateUtils.get_y_max(elem))-10, 480)]
        p2 = [min(int(CrateUtils.get_x_max(elem)) - 100, 640), min(int(CrateUtils.get_y_max(elem)) - 10, 480)]
        # break

        Logger.debug(f"Point 1: {p1}")
        Logger.debug(f"Point 2: {p2}")

        # create a mask using highest crate bounding box loacation
        mask = np.zeros(aug_image.shape[:2], np.uint8)
        mask[0:p2[1], p1[0]:p2[0]] = 255

        # compute the bitwise AND using the mask
        masked_img = cv2.bitwise_and(aug_image, aug_image, mask=mask)

        # gaussian blur
        blur = cv2.GaussianBlur(masked_img, (7, 7), cv2.BORDER_DEFAULT)

        # binary thresh
        ret, binary_image = cv2.threshold(blur, 50, 255, cv2.THRESH_BINARY)

        # Remove holes
        kernel_close = np.ones((7, 7), np.uint8)
        binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel_close)

        kernel_open = np.ones((7, 7), np.uint8)
        binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel_open)

        # Find contours
        box, bounding_box = self.find_contours(binary_image)
        if (box is None):
            return None, None

        Logger.info(box)

        # find angle and
        angle, center = self._find_angle_center(box)

        return angle, center

    def _append_dataframe_center(self):
        center_point = []
        for index, elem in self.df.iterrows():
            center_point.append(CrateUtils.get_center(elem))
        self.df['center_x'] = [e[0] for e in center_point]
        self.df['center_y'] = [e[1] for e in center_point]

    def _append_dataframe_depth(self):
        depth: list[int] = []
        for index, elem in self.df.iterrows():
            center = CrateUtils.get_center(elem)
            depth.append(self.calc_depth(center))
        self.df['depth'] = depth

    def calc_depth(self, center):
        y_transform = 0  # margin to mitigate the change that the handle of a crate is in the center
        width = 48
        height = 48
        # return self.depth_image[min(int(center[0]), 639)][min(int(center[1]), 479)]
        return CrateUtils.get_avg_depth(int(center[0]), int(center[1] + y_transform), width, height, self.depth_image)

    def sort_by_height(self):
        self.df.sort_values(by=['ymax'], ascending=True, inplace=True)

    def get(self, index):
        return self.df.iloc[index]

    def size(self):
        return len(self.df.index)

    def __str__(self):
        return str(self.df)
