import numpy as np
from pandas import Series


def get_resource(*args):
    return f"resources/{'/'.join(args)}"


def save_img(img, name="img"):
    path = f"tmp/{name}.jpg"
    img.save(path)
    return path


class CrateUtils:
    def __init__(self):
        pass

    @staticmethod
    def get_x_max(elem: Series) -> float:
        return elem['xmax']

    @staticmethod
    def get_x_min(elem: Series) -> float:
        return elem['xmin']

    @staticmethod
    def get_y_max(elem: Series) -> float:
        return elem['ymax']

    @staticmethod
    def get_y_min(elem: Series) -> float:
        return elem['ymin']

    @staticmethod
    def get_x_size(elem: Series) -> float:
        return CrateUtils.get_x_max(elem) - CrateUtils.get_x_min(elem)

    @staticmethod
    def get_y_size(elem: Series) -> float:
        return CrateUtils.get_y_max(elem) - CrateUtils.get_y_min(elem)

    @staticmethod
    def get_center(elem: Series) -> list:
        return [CrateUtils.get_x_size(elem) / 2 + CrateUtils.get_x_min(elem),
                CrateUtils.get_y_size(elem) / 2 + CrateUtils.get_y_min(elem)]

    @staticmethod
    def get_avg_depth(x, y, width, height, image):
        # TODO - remove
        return 10
        # initialize array
        arr = np.zeros((width, height))

        # make sure the array does not overlap outside of the image
        minX = max(0, int(x - width / 2))
        maxX = min(image.shape[1], int(x + width / 2))
        minY = max(0, int(y - height / 2))
        maxY = min(image.shape[0], int(y + height / 2))

        # fill array with values
        for i in range(minX, maxX):
            for j in range(minY, maxY):
                arr[i - minX][j - minY] = image[j][i]

        arr = arr.flatten()  # flatten 2d array
        arr = arr[arr != 0]  # remove 0's
        hist, bins = np.histogram(arr.flatten(), bins=12)  # histogram and bins

        # print(f"Array: {arr.flatten()}")
        # print(f"Histogram: {hist}")
        # print(f"Bins: {bins}")

        most_common_index = np.argmax(hist)
        most_common_value = bins[most_common_index]
        return most_common_value
