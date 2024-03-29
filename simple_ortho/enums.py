"""
   Copyright 2021 Dugal Harris - dugalh@gmail.com

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from typing import List
from enum import Enum
from rasterio.enums import Resampling
import cv2


class CameraType(str, Enum):
    """
    Enumeration for the camera model type.
    """
    pinhole = 'pinhole'
    """ Pinhole camera model. """

    brown = 'brown'
    """ 
    Brown-Conrady camera model.  Compatible with `ODM <https://docs.opendronemap.org/arguments/camera-lens/>`_ / 
    `OpenSFM <https://github.com/mapillary/OpenSfM>`_ *brown* parameter estimates; and the 4 & 5-coefficient version of the 
    `general OpenCV distortion model <https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html>`_.  
    """

    fisheye = 'fisheye'
    """ 
    Fisheye camera model.  Compatible with `ODM <https://docs.opendronemap.org/arguments/camera-lens/>`_ / `OpenSFM 
    <https://github.com/mapillary/OpenSfM>`_, and 
    `OpenCV <https://docs.opencv.org/4.7.0/db/d58/group__calib3d__fisheye.html>`_ *fisheye* parameter estimates.  
    """

    opencv = 'opencv'
    """ 
    OpenCV `general camera model <https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html>`_ supporting the full set 
    of distortion coefficient estimates.
    """

    def __repr__(self):
        return self._name_

    def __str__(self):
        return self._name_

    @classmethod
    def from_odm(cls, cam_type: str):
        """ Convert from ODM / OpenSFM projection type. """
        cam_type = 'brown' if cam_type == 'perspective' else cam_type
        if cam_type not in cls.__members__:
            raise ValueError(f"Unsupported ODM / OpenSFM camera type: '{cam_type}'")
        return cls(cam_type)


class Interp(str, Enum):
    """
    Enumeration for common `OpenCV <https://docs.opencv.org/4.8.0/da/d54/group__imgproc__transform.html
    #ga5bb5a1fea74ea38e1a5445ca803ff121>`_ and `rasterio
    https://rasterio.readthedocs.io/en/stable/api/rasterio.enums.html#rasterio.enums.Resampling`_ interpolation types.
    """
    average = 'average'
    """ Average input pixels over the corresponding output pixel area (suited to downsampling). """
    bilinear = 'bilinear'
    """ Bilinear interpolation. """
    cubic = 'cubic'
    """ Bicubic interpolation. """
    lanczos = 'lanczos'
    """ Lanczos windowed sinc interpolation. """
    nearest = 'nearest'
    """ Nearest neighbor interpolation. """

    def __repr__(self):
        return self._name_

    def __str__(self):
        return self._name_

    @classmethod
    def cv_list(cls) -> List:
        """ A list of OpenCV compatible :class:`~rasterio.enums.Interp` values. """
        _cv_list = []
        for interp in list(cls):
            try:
                interp.to_cv()
                _cv_list.append(interp)
            except ValueError:
                pass
        return _cv_list

    def to_cv(self) -> int:
        """ Convert to OpenCV interpolation type. """
        name_to_cv = dict(
            average=cv2.INTER_AREA, bilinear=cv2.INTER_LINEAR, cubic=cv2.INTER_CUBIC, lanczos=cv2.INTER_LANCZOS4,
            nearest=cv2.INTER_NEAREST,
        )
        if self._name_ not in name_to_cv:
            raise ValueError(f"OpenCV does not support '{self._name_}' interpolation.")
        return name_to_cv[self._name_]

    def to_rio(self) -> Resampling:
        """ Convert to rasterio resampling type. """
        return Resampling[self._name_]


class Compress(str, Enum):
    """ Enumeration for ortho compression. """
    jpeg = 'jpeg'
    """ Jpeg (lossy) compression.  """
    deflate = 'deflate'
    """ Deflate (lossless) compression. """
    auto = 'auto'
    """ Use jpeg compression if possible, otherwise deflate. """

    def __repr__(self):
        return self._name_

    def __str__(self):
        return self._name_


class CsvFormat(Enum):
    """ Enumeration for CSV exterior parameter format. """
    xyz_opk = 1
    """ Projected (easting, northing, altitude) position and (omega, phi, kappa) orientation. """
    lla_opk = 2
    """ Geographic (latitude, longitude, altitude) position and (omega, phi, kappa) orientation. """
    xyz_rpy = 3
    """ Projected (easting, northing, altitude) position and (roll, pitch, yaw) orientation. """
    lla_rpy = 4
    """ Geographic (latitude, longitude, altitude) position and (roll, pitch, yaw) orientation. """

    @property
    def is_opk(self) -> bool:
        """ True if format has an (omega, phi, kappa) orientation, otherwise False. """
        return self is CsvFormat.xyz_opk or self is CsvFormat.lla_opk

    @property
    def is_xyz(self) -> bool:
        """ True if format has an (easting, northing, altitude) position, otherwise False. """
        return self is CsvFormat.xyz_opk or self is CsvFormat.xyz_rpy
