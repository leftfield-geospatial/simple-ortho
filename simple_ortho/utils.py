"""
   Copyright 2023 Dugal Harris - dugalh@gmail.com

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
import cProfile
import pstats
import tracemalloc
import warnings
import logging
from contextlib import contextmanager
from typing import Tuple, Union, Iterable
import numpy as np
import rasterio as rio
from rasterio.errors import NotGeoreferencedWarning
from rasterio.windows import Window
import cv2

from simple_ortho.enums import Interp

logger = logging.getLogger(__name__)


@contextmanager
def suppress_no_georef():
    """ Context manager to suppress rasterio's NotGeoreferencedWarning. """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=NotGeoreferencedWarning)
        yield


def expand_window_to_grid(win: Window, expand_pixels: Tuple[int, int] = (0, 0)) -> Window:
    """ Expand rasterio window extents to the nearest whole numbers. """
    col_off, col_frac = np.divmod(win.col_off - expand_pixels[1], 1)
    row_off, row_frac = np.divmod(win.row_off - expand_pixels[0], 1)
    width = np.ceil(win.width + 2 * expand_pixels[1] + col_frac)
    height = np.ceil(win.height + 2 * expand_pixels[0] + row_frac)
    exp_win = Window(col_off.astype('int'), row_off.astype('int'), width.astype('int'), height.astype('int'))
    return exp_win


def nan_equals(a: Union[np.ndarray, float], b: Union[np.ndarray, float]) -> np.ndarray:
    """ Compare two numpy objects a & b, returning true where elements of both a & b are nan. """
    return (a == b) | (np.isnan(a) & np.isnan(b))


def distort_image(camera, image: np.ndarray, nodata=0, interp=Interp.nearest):
    """ Return a distorted image given a camera model and source image. """

    if not np.all(np.array(image.shape[::-1]) == camera._im_size):
        raise ValueError("'image' shape should be the same as the 'camera' image size.")

    # create (j, i) pixel coords for distorted image
    j_range = np.arange(0, camera._im_size[0])
    i_range = np.arange(0, camera._im_size[1])
    j_grid, i_grid = np.meshgrid(j_range, i_range, indexing='xy')
    ji = np.row_stack((j_grid.reshape(1, -1), i_grid.reshape(1, -1)))

    # find the corresponding undistorted/ source (j, i) pixel coords
    camera_xyz = camera._pixel_to_camera(ji)
    undist_ji = camera._K_undistort.dot(camera_xyz)[:2].astype('float32')

    # remap the distorted image from the source image
    dist_image = np.full_like(image, fill_value=nodata)
    cv2.remap(
        image, undist_ji[0].reshape(image.shape), undist_ji[1].reshape(image.shape), interp.to_cv(), dst=dist_image,
        borderMode=cv2.BORDER_TRANSPARENT
    )
    return dist_image


@contextmanager
def profiler():
    """ Context manager for profiling in DEBUG log level. """
    if logger.getEffectiveLevel() <= logging.DEBUG:
        proc_profile = cProfile.Profile()
        tracemalloc.start()
        proc_profile.enable()

        yield

        proc_profile.disable()
        # tottime is the total time spent in the function alone. cumtime is the total time spent in the function
        # plus all functions that this function called
        proc_stats = pstats.Stats(proc_profile).sort_stats('cumtime')
        logger.debug(f'Processing times:')
        proc_stats.print_stats(20)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.debug(f"Memory usage: current: {current / 10 ** 6:.1f} MB, peak: {peak / 10 ** 6:.1f} MB")
    else:
        yield


def utm_crs_from_latlon(lat:float, lon: float) -> rio.CRS:
    """ Return a 2D rasterio UTM CRS for the given (lat, lon) coordinates in degrees. """
    # adapted from https://gis.stackexchange.com/questions/269518/auto-select-suitable-utm-zone-based-on-grid-intersection
    zone = int(np.floor((lon + 180) / 6) % 60) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return rio.CRS.from_epsg(epsg)


def validate_collection(template: Iterable, coll: Iterable) -> bool:
    """
    Validate a nested dict / list of values (``coll``) against a nested dict / list of types, tuples of types, and
    values (``template``).  All items in a ``coll`` list are validated against the first item in the corresponding
    ``template`` list.
    """
    # adapted from https://stackoverflow.com/questions/45812387/how-to-validate-structure-or-schema-of-dictionary-in-python
    if isinstance(template, dict) and isinstance(coll, dict):
        # struct is a dict of types or other dicts
        for k in template:
            if k in coll:
                validate_collection(template[k], coll[k])
            else:
                raise KeyError(f"No key: '{k}'.")
    elif isinstance(template, list) and isinstance(coll, list) and len(template) and len(coll):
        # struct is list in the form [type or dict]
        for item in coll:
            validate_collection(template[0], item)
    elif isinstance(template, type):
        # struct is the type of conf
        if not isinstance(coll, template):
            raise TypeError(f"'{coll}' is not an instance of {template}.")
    elif isinstance(template, tuple) and all([isinstance(item, type) for item in template]):
        # struct is a tuple of types
        if not isinstance(coll, template):
            raise TypeError(f"'{coll}' is not an instance of any of {template}.")
    elif isinstance(template, object) and template is not None:
        # struct is the value of conf
        if not coll == template:
            raise ValueError(f"'{coll}' does not equal '{template}'.")
