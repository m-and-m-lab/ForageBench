"""Perception API mirroring Spot's onboard sensor stack.

Names follow the Boston Dynamics SDK (`ImageClient.get_image_from_sources`,
`frame_helpers.get_a_tform_b`) so agent code can move between simulation and the physical robot.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np

VISION_FRAME = "vision"
"""World-fixed frame used for planning."""
BODY_FRAME = "body"

HAND_COLOR = "hand_color_image"
HAND_DEPTH = "hand_depth_in_hand_color_frame"
# TODO: list the body camera sources exposed by the PhyGS Spot USD.


@dataclass
class ImageResponse:
    source_name: str
    image: np.ndarray
    """HxWx3 uint8 for color sources, or HxW float32 depth in metres."""
    intrinsics: np.ndarray
    """3x3 pinhole camera matrix."""
    frame_name: str
    """Camera frame that the image is expressed in."""


class ImageClient(Protocol):
    def get_image_from_sources(self, source_names: list[str]) -> list[ImageResponse]: ...


class FrameTree(Protocol):
    def get_a_tform_b(self, frame_a: str, frame_b: str) -> np.ndarray:
        """4x4 homogeneous transform mapping points in `frame_b` into `frame_a`."""
        ...


def pixel_to_camera(u: float, v: float, depth: float, intrinsics: np.ndarray) -> np.ndarray:
    """Back-project pixel (u, v) with metric depth into a 3D point in the camera frame."""
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]
    return np.array([(u - cx) * depth / fx, (v - cy) * depth / fy, depth])


def camera_to_world(point: np.ndarray, frames: FrameTree, camera_frame: str) -> np.ndarray:
    """Transform a camera-frame point into the world (`vision`) frame."""
    world_tform_camera = frames.get_a_tform_b(VISION_FRAME, camera_frame)
    return (world_tform_camera @ np.append(point, 1.0))[:3]
