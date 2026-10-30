# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""From a pixel the model points at to a world point, with the robot's own depth cameras.

A model sees camera images and points at pixels; the skills act on world points. Everything here
reads the observation packet the model was shown (depth, intrinsics, the camera's pose at that
capture), which the agent is allowed to see on any track that grants the robot's pose. Nothing here
is privileged: no object names, boxes or drawer parts.
"""

from __future__ import annotations

import math

import numpy as np

SEARCH_PX = 5  # A pixel without depth takes the nearest valid one within this many pixels.


class PointingError(ValueError):
    """The pixel cannot be turned into a point: unknown camera, outside the image, no depth near it."""


def array(value) -> np.ndarray:
    """A packet field as a NumPy array (the session gives torch tensors or arrays)."""
    return value.cpu().numpy() if hasattr(value, "cpu") else np.asarray(value)


def camera_of(packet, camera: str):
    found = packet.cameras.get(camera)
    if found is None or found.depth is None:
        raise PointingError(f"no depth camera {camera!r}; the cameras are {sorted(packet.cameras)}")
    return found


def world_from_camera(packet, camera: str) -> np.ndarray:
    """The camera's world pose (4x4) at its capture; needs the robot's pose (gt_localization)."""
    found = camera_of(packet, camera)
    try:
        return array(packet.transform("world", found.frame, found.stamp)).astype(float)
    except KeyError as error:
        raise PointingError(f"the camera's world pose is not known on this track ({error})") from error


def valid_pixel(packet, camera: str, u: float, v: float) -> tuple[int, int]:
    """The pixel (column, row) itself when it has valid depth, else the valid pixel within
    ``SEARCH_PX`` on the nearest surface (to the cm), nearest to it: a pixel without depth is mostly
    an object's edge, and a model points at the object, not at what lies behind it."""
    found = camera_of(packet, camera)
    valid = array(found.depth_valid).astype(bool)
    height, width = valid.shape
    col, row = int(round(float(u))), int(round(float(v)))
    if not (0 <= col < width and 0 <= row < height):
        raise PointingError(f"pixel ({col}, {row}) is outside the {width}x{height} image of {camera!r}")
    rows, cols = np.nonzero(
        valid[max(row - SEARCH_PX, 0) : row + SEARCH_PX + 1, max(col - SEARCH_PX, 0) : col + SEARCH_PX + 1]
    )
    if len(rows) == 0:
        raise PointingError(f"no depth near pixel ({col}, {row}) of {camera!r}")
    rows, cols = rows + max(row - SEARCH_PX, 0), cols + max(col - SEARCH_PX, 0)
    if valid[row, col]:
        return col, row
    depth = np.round(array(found.depth)[rows, cols].astype(float), 2)
    best = int(np.lexsort(((rows - row) ** 2 + (cols - col) ** 2, depth))[0])
    return int(cols[best]), int(rows[best])


def camera_point(packet, camera: str, col: int, row: int) -> np.ndarray:
    """The depth return at an exact pixel, in the camera's optical frame [m]."""
    found = camera_of(packet, camera)
    ray = np.linalg.solve(array(found.intrinsics).astype(float), [col, row, 1.0])
    return ray * float(array(found.depth)[row, col])


def world_point(packet, camera: str, u: float, v: float) -> np.ndarray:
    """The world point [m] the pixel (u, v) of ``camera`` sees."""
    col, row = valid_pixel(packet, camera, u, v)
    return (world_from_camera(packet, camera) @ [*camera_point(packet, camera, col, row), 1.0])[:3]


def patch_points(packet, camera: str, u: float, v: float, radius: int) -> np.ndarray:
    """World points [m] of the valid pixels within ``radius`` px of (u, v), shape (n, 3)."""
    found = camera_of(packet, camera)
    depth, valid = array(found.depth).astype(float), array(found.depth_valid).astype(bool)
    height, width = depth.shape
    col, row = int(round(float(u))), int(round(float(v)))
    r0, r1, c0, c1 = (
        max(row - radius, 0),
        min(row + radius + 1, height),
        max(col - radius, 0),
        min(col + radius + 1, width),
    )
    rows, cols = np.nonzero(valid[r0:r1, c0:c1])
    if len(rows) < 3:
        raise PointingError(f"too little depth around pixel ({col}, {row}) of {camera!r}")
    rows, cols = rows + r0, cols + c0
    rays = np.linalg.solve(array(found.intrinsics).astype(float), np.stack([cols, rows, np.ones_like(cols)]))
    points = (rays * depth[rows, cols]).T
    pose = world_from_camera(packet, camera)
    return points @ pose[:3, :3].T + pose[:3, 3]


def facing_normal(packet, camera: str, u: float, v: float, radius: int = 25) -> np.ndarray:
    """The level unit vector out of the vertical surface around the pixel, towards the camera
    (a drawer front's outward direction) [world]. Fits a plane to the depth around the pixel."""
    points = patch_points(packet, camera, u, v, radius)
    centered = points - points.mean(axis=0)
    normal = np.linalg.svd(centered, full_matrices=False)[2][-1]
    level = np.array([normal[0], normal[1], 0.0])
    if np.linalg.norm(level) < 0.5:
        raise PointingError("the surface around the pixel is not vertical (not a drawer front)")
    level /= np.linalg.norm(level)
    to_camera = world_from_camera(packet, camera)[:3, 3] - points.mean(axis=0)
    return level if np.dot(level, to_camera) > 0 else -level


def protruding_point(
    packet, camera: str, u: float, v: float, outward: np.ndarray, radius: int = 10, depth_m: float = 0.01
) -> np.ndarray:
    """The middle of what sticks out furthest along ``outward`` within ``radius`` px of the pixel (a
    handle on a drawer front, when the model pointed near it): the mean of the points within
    ``depth_m`` [m] of the furthest, so along a bar it is near the pixel, not at an end."""
    points = patch_points(packet, camera, u, v, radius)
    along = points @ np.asarray(outward, dtype=float)
    return points[along >= along.max() - depth_m].mean(axis=0)


def support_height(heights: np.ndarray, top: float, clearance_m: float, bin_m: float = 0.01) -> float | None:
    """The surface an object stands on [m]: the highest level (``bin_m`` bins) below ``top`` -
    ``clearance_m`` that holds at least a tenth of the points below it, so a table top wins over
    the floor seen past its edge; None when nothing lies below."""
    below = heights[heights < top - clearance_m]
    if len(below) < 10:
        return None
    levels, counts = np.unique(np.round(below / bin_m), return_counts=True)
    dense = levels[counts >= max(10, 0.1 * len(below))]
    return float((dense.max() if len(dense) else np.median(np.round(below / bin_m))) * bin_m)


def object_box(
    packet,
    camera: str,
    u: float,
    v: float,
    reach_m: float = 0.15,
    clearance_m: float = 0.01,
    min_size_m: float = 0.02,
    unknown_height_m: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """A world-aligned box (centre, size) [m] for what the pixel shows standing on a surface: the
    surface is the highest dense level below the pixel's point within ``reach_m`` (horizontally) of
    it (:func:`support_height`), the object the pixels connected to the pixel that stand more than
    ``clearance_m`` above it and no higher than the pixel's point (2nd-98th percentile extent, so
    stray points do not widen it). Its top is what the depth saw;
    its bottom is the surface, or ``unknown_height_m`` below the top when no surface shows. An
    estimate for grasping and for planning with the object in the hand, not a segmentation."""
    found = camera_of(packet, camera)
    col, row = valid_pixel(packet, camera, u, v)
    depth, valid = array(found.depth).astype(float), array(found.depth_valid).astype(bool)
    intrinsics = array(found.intrinsics).astype(float)
    radius = int(np.clip(np.ceil(reach_m * intrinsics[0, 0] / depth[row, col]), 2, 200))
    height, width = depth.shape
    r0, r1, c0, c1 = (
        max(row - radius, 0),
        min(row + radius + 1, height),
        max(col - radius, 0),
        min(col + radius + 1, width),
    )
    rows, cols = np.mgrid[r0:r1, c0:c1]
    rays = np.linalg.solve(intrinsics, np.stack([cols.ravel(), rows.ravel(), np.ones(cols.size)]))
    pose = world_from_camera(packet, camera)
    points = ((rays * depth[r0:r1, c0:c1].ravel()).T @ pose[:3, :3].T + pose[:3, 3]).reshape(*cols.shape, 3)
    top = points[row - r0, col - c0]
    z = points[..., 2]
    near = valid[r0:r1, c0:c1] & (np.linalg.norm(points[..., :2] - top[:2], axis=-1) <= reach_m)
    surface = support_height(z[near], top[2], clearance_m)
    if surface is None:
        surface = top[2] - unknown_height_m
    above = near & (z > surface + clearance_m) & (z <= top[2] + clearance_m)
    region = np.zeros_like(above)
    region[row - r0, col - c0] = True
    while True:  # Grow the object from the pixel through its 4-neighbours that stand above the surface.
        grown = region.copy()
        grown[1:] |= region[:-1]
        grown[:-1] |= region[1:]
        grown[:, 1:] |= region[:, :-1]
        grown[:, :-1] |= region[:, 1:]
        grown &= above
        grown[row - r0, col - c0] = True
        if (grown == region).all():
            break
        region = grown
    seen = points[region]
    low, high = np.percentile(seen, 2, axis=0), np.percentile(seen, 98, axis=0)
    low[2], high[2] = surface, top[2]
    size = np.maximum(high - low, min_size_m)
    centre = (low + high) / 2
    centre[2] = high[2] - size[2] / 2  # The top stays where the depth saw it.
    return centre, size


def project(packet, camera: str, point) -> tuple[float, float] | None:
    """The pixel (u, v) a world point [m] falls on in ``camera``, or None when it is behind the
    camera or outside the image (for tests and scripted agents that know a point)."""
    found = camera_of(packet, camera)
    local = np.linalg.inv(world_from_camera(packet, camera)) @ [*np.asarray(point, dtype=float), 1.0]
    if local[2] <= 0:
        return None
    pixel = array(found.intrinsics).astype(float) @ (local[:3] / local[2])
    height, width = array(found.depth).shape
    u, v = float(pixel[0]), float(pixel[1])
    return (u, v) if 0 <= u < width and 0 <= v < height else None


def heading_to(base_xy, point) -> float:
    """The heading [rad] that faces a world point from the base."""
    return math.atan2(float(point[1]) - float(base_xy[1]), float(point[0]) - float(base_xy[0]))
