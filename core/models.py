from pandas import DataFrame
from core.utils import CrateUtils
import cv2
import numpy as np
import math
import pyrealsense2 as rs


class CratesData:
    def __init__(self, df: DataFrame, rgb_image, depth_image):
        self.df = df
        self.rgb_image = rgb_image
        self.depth_image = depth_image
        self._append_dataframe_center()
        self._append_dataframe_depth()

    def find_contours(self, aug_image):
        contours, hierarchy = cv2.findContours(aug_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) is 0:
            input("Error not box found!")
            return True
        max_contour = max(contours, key=cv2.contourArea)  # Find the largest contour (hopefully the crate)
        x, y, w, h = cv2.boundingRect(max_contour)

        # Get smallest box
        rect = cv2.minAreaRect(max_contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        return box, x, y, w, h

    def find_angle_center(self, box):
        angle: float
        point_a: tuple = None
        point_b: tuple = None
        for point in box:
            if point_a is None:
                point_a = point
                continue
            if point_b is None:
                point_b = point
                continue
            if point[1] < point_a[1]:
                p_temp = point_a
                point_a = point
                point = p_temp
            if point[1] < point_b[1]:
                point_b = point

        center: tuple = ((point_a[0] - point_b[0]) / 2 + point_a[0], abs(point_a[1] - point_b[1]) / 2 + point_a[1])
        angle = (math.atan2((point_b[0] - point_a[0]), abs(point_b[1] - point_a[1])) * 180 / math.pi)
        angle = (angle / abs(angle)) * (90 - abs(angle))
        print(f"Angle: {angle}")
        return angle, center

    def get_pickup_data(self):

        # Get images
        color_image = cv2.cvtColor(self.rgb_image, cv2.COLOR_RGB2BGR)
        aug_image = cv2.cvtColor(self.depth_image, cv2.COLOR_BGR2GRAY)

        # Remove holes
        kernel = np.ones((5, 5), np.uint8)
        aug_image = cv2.morphologyEx(aug_image, cv2.MORPH_OPEN, kernel)
        aug_image = cv2.morphologyEx(aug_image, cv2.MORPH_CLOSE, kernel)

        # Find contours
        box, x, y, w, h = self.find_contours(aug_image)

        # find angle and
        angle, center = self.find_angle_center(box)

        aug_image = cv2.cvtColor(aug_image, cv2.COLOR_GRAY2RGB)
        cv2.drawContours(aug_image, [box], 0, (0, 0, 255), 4)
        cv2.rectangle(aug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow("Box", aug_image)

        key = cv2.waitKey(0)
        if key == ord('q'):
            return False
        return True

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
        return CrateUtils.get_avg_depth(int(center[0]), int(center[1] + y_transform), width, height, self.depth_image)

    def sort_by_height(self):
        self.df.sort_values(by=['center_y'], ascending=False, inplace=True)

    def get(self, index):
        return self.df.iloc[index]

    def size(self):
        return len(self.df.index)

    def __str__(self):
        return str(self.df)
