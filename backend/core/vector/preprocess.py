"""clean an image before tracing: find the background, smooth, and snap to a small flat palette.

vtracer works best on flat colours with crisp edges. photos, jpegs and anti-aliased artwork
have noise and in-between colours, which is what causes muddy colours and jagged paths.
numpy and pillow only.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

# two colours closer than this (in lab units) count as the same colour
SAME_COLOUR_DISTANCE = 7.0
BACKGROUND_DISTANCE = 14.0
# fully saturated colours used to mark transparent areas of png files
MARKER_CANDIDATES = [(255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (0, 0, 255)]


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """srgb (uint8 or float 0..255, shape (..., 3)) to cie lab (float32)."""
    linear = rgb.astype(np.float32) / 255.0
    linear = np.where(linear > 0.04045, ((linear + 0.055) / 1.055) ** 2.4, linear / 12.92)
    matrix = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]], dtype=np.float32)
    xyz = linear @ matrix.T / np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1).astype(np.float32)


def detect_background(rgb: np.ndarray) -> tuple[int, int, int] | None:
    """returns the solid background colour if most of the image border is one colour."""
    border = np.concatenate([rgb[:2].reshape(-1, 3), rgb[-2:].reshape(-1, 3),
                             rgb[:, :2].reshape(-1, 3), rgb[:, -2:].reshape(-1, 3)])
    # most common colour, found on a coarse grid so noise does not split it
    bins = (border // 16).astype(np.int32)
    keys = bins[:, 0] * 256 + bins[:, 1] * 16 + bins[:, 2]
    top = np.bincount(keys).argmax()
    candidate = np.median(border[keys == top], axis=0)
    distance = np.linalg.norm(rgb_to_lab(border) - rgb_to_lab(candidate[None, :]), axis=1)
    close = distance < BACKGROUND_DISTANCE
    if close.mean() < 0.6:
        return None
    return tuple(int(channel) for channel in np.median(border[close], axis=0))


def _kmeans(points: np.ndarray, count: int, rng: np.random.Generator, rounds: int = 10) -> np.ndarray:
    """k-means++ start, so small accent colours are picked up instead of averaged away."""
    centres = [points[rng.integers(len(points))]]
    nearest = np.sum((points - centres[0]) ** 2, axis=1)
    for _ in range(1, count):
        if nearest.sum() <= 1e-6:
            break
        centres.append(points[rng.choice(len(points), p=nearest / nearest.sum())])
        nearest = np.minimum(nearest, np.sum((points - centres[-1]) ** 2, axis=1))
    centres = np.array(centres, dtype=np.float32)
    for _ in range(rounds):
        owner = np.argmin(((points[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2), axis=1)
        for index in range(len(centres)):
            members = points[owner == index]
            if len(members):
                centres[index] = members.mean(axis=0)
    return centres


def _flat_mask(rgb: np.ndarray) -> np.ndarray:
    """pixels away from edges and noise (colour barely changes within 2 pixels): the best ones to learn the palette from."""
    signed = rgb.astype(np.int16)
    change = np.zeros(rgb.shape[:2], dtype=np.int16)
    for axis in (0, 1):
        for step in (-2, 2):
            change = np.maximum(change, np.abs(signed - np.roll(signed, step, axis=axis)).max(axis=2))
    return change < 12


def build_palette(rgb: np.ndarray, count: int, background: tuple[int, int, int] | None, seed: int = 7) -> np.ndarray:
    """returns palette colours as rgb float array (n, 3), most common first."""
    rng = np.random.default_rng(seed)
    pixels = rgb.reshape(-1, 3)
    usable = _flat_mask(rgb).reshape(-1)
    if background is not None:
        usable &= np.linalg.norm(rgb_to_lab(pixels) - rgb_to_lab(np.array(background, dtype=np.float32)[None, :]), axis=1) > BACKGROUND_DISTANCE
    if usable.sum() < 500:  # photos or tiny images: no flat areas, use everything
        usable = np.ones(len(pixels), dtype=bool)
    candidates = np.flatnonzero(usable)
    chosen = rng.choice(candidates, size=min(40000, len(candidates)), replace=False)
    sample_rgb = pixels[chosen].astype(np.float32)
    sample_lab = rgb_to_lab(sample_rgb)
    centres = _kmeans(sample_lab, count, rng)
    owner = np.argmin(((sample_lab[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2), axis=1)
    sizes = np.bincount(owner, minlength=len(centres))
    # merge near-identical centres, keeping the larger one
    kept: list[int] = []
    for index in np.argsort(-sizes):
        if sizes[index] == 0:
            continue
        if all(np.linalg.norm(centres[index] - centres[other]) >= SAME_COLOUR_DISTANCE for other in kept):
            kept.append(int(index))
    # true colour of each cluster = mean of the original pixels in it (not the lab centre)
    colours = {index: sample_rgb[owner == index].mean(axis=0) for index in kept}
    kept = _drop_edge_blends(colours, sizes, background)
    return np.array([colours[index] for index in kept], dtype=np.float32)


def _distance_to_segment(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> tuple[float, float]:
    """distance from a point to the line between two colours, and how far along it (0..1) the closest spot is."""
    line = end - start
    length_squared = float(line @ line)
    if length_squared < 1e-6:
        return float("inf"), 0.0
    along = float((point - start) @ line) / length_squared
    return float(np.linalg.norm(point - (start + np.clip(along, 0, 1) * line))), along


def _drop_edge_blends(colours: dict, sizes: np.ndarray, background) -> list[int]:
    """anti-aliasing creates in-between colours along edges (pink between red and white).
    a small colour on the straight line between two other colours (in rgb, where blending happens) is such a blend."""
    kept = list(colours)
    total = max(1, sum(int(sizes[index]) for index in kept))
    for index in sorted(kept, key=lambda value: sizes[value]):
        if sizes[index] > 0.12 * total or len(kept) <= 2:
            continue
        others = [colours[other] for other in kept if other != index]
        if background is not None:
            others.append(np.array(background, dtype=np.float32))
        blend = False
        for first in range(len(others)):
            for second in range(first + 1, len(others)):
                gap, along = _distance_to_segment(colours[index], others[first], others[second])
                if gap < 22.0 and 0.08 < along < 0.92:
                    blend = True
        if blend:
            kept.remove(index)
    return kept


def snap_to_palette(rgb: np.ndarray, palette: np.ndarray, background: tuple[int, int, int] | None, majority_size: int = 3, min_patch_area: int = 0) -> np.ndarray:
    """repaint every pixel with its nearest palette colour (the background counts as a colour too).

    pixels on an edge are blends of the two colours either side. such a pixel may only take a colour
    that really exists next to it, otherwise a green line appears between blue and yellow."""
    colours = palette if background is None else np.vstack([palette, np.array(background, dtype=np.float32)])
    colours_lab = rgb_to_lab(colours)
    height, width = rgb.shape[:2]
    flat = rgb.reshape(-1, 3)
    labels = np.empty(len(flat), dtype=np.uint8)
    nearest_distance = np.empty(len(flat), dtype=np.float32)
    for start in range(0, len(flat), 200_000):
        chunk = rgb_to_lab(flat[start:start + 200_000])
        part = np.sqrt(((chunk[:, None, :] - colours_lab[None, :, :]) ** 2).sum(axis=2))
        labels[start:start + 200_000] = np.argmin(part, axis=1)
        nearest_distance[start:start + 200_000] = part.min(axis=1)

    # only edge pixels that are not an exact palette colour need a second look
    calm = _flat_mask(rgb).reshape(-1)
    candidates = np.flatnonzero((~calm) & (nearest_distance > 12.0))
    if len(candidates):
        # which colours exist nearby: look at the calm pixels of each colour in a small window
        radius = max(2, round(width / 300))
        nearby = np.zeros((len(candidates), len(colours)), dtype=bool)
        calm_labels = np.where(calm, labels, 255).reshape(height, width)
        for index in range(len(colours)):
            present = Image.fromarray(((calm_labels == index).astype(np.uint8)) * 255)
            nearby[:, index] = np.asarray(present.filter(ImageFilter.MaxFilter(2 * radius + 1))).reshape(-1)[candidates] > 0
        has_choice = nearby.any(axis=1)
        chosen = candidates[has_choice]
        edge_lab = rgb_to_lab(flat[chosen])
        edge_distance = np.sqrt(((edge_lab[:, None, :] - colours_lab[None, :, :]) ** 2).sum(axis=2))
        labels[chosen] = np.argmin(np.where(nearby[has_choice], edge_distance, np.inf), axis=1)

    label_image = Image.fromarray(labels.reshape(height, width), mode="L")
    if majority_size > 1:
        # drops lone pixels left by anti-aliasing so edges stay clean
        label_image = label_image.filter(ImageFilter.ModeFilter(majority_size))
    final_labels = np.asarray(label_image)
    if min_patch_area > 0:
        final_labels = merge_small_patches(final_labels, min_patch_area)
    exact = np.rint(colours).astype(np.uint8)
    return exact[final_labels]


def label_patches(labels: np.ndarray) -> tuple[np.ndarray, int]:
    """numbers every connected patch of one label (4-way connectivity). numpy only.
    returns (patch id for every pixel, number of patches)."""
    height, width = labels.shape
    flat = labels.reshape(-1)
    starts = np.ones(flat.shape, dtype=bool)
    starts[1:] = flat[1:] != flat[:-1]
    starts[::width] = True  # a new row always starts a new run
    run_of_pixel = (np.cumsum(starts) - 1).reshape(height, width)
    run_count = int(run_of_pixel.max()) + 1
    # runs that touch vertically and share a label belong to the same patch
    same = labels[1:] == labels[:-1]
    pairs = np.unique(run_of_pixel[:-1][same].astype(np.int64) * run_count + run_of_pixel[1:][same])
    parent = np.arange(run_count)

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for upper, lower in zip((pairs // run_count).tolist(), (pairs % run_count).tolist()):
        root_upper, root_lower = find(upper), find(lower)
        if root_upper != root_lower:
            parent[max(root_upper, root_lower)] = min(root_upper, root_lower)
    roots = np.array([find(node) for node in range(run_count)])
    _, patch_of_run = np.unique(roots, return_inverse=True)
    return patch_of_run[run_of_pixel], int(patch_of_run.max()) + 1


def merge_small_patches(labels: np.ndarray, min_area: int) -> np.ndarray:
    """repaints every patch smaller than min_area pixels with the colour that surrounds it most.
    each tiny patch would otherwise become its own shape in the svg."""
    patches, patch_count = label_patches(labels)
    areas = np.bincount(patches.reshape(-1), minlength=patch_count)
    # a patch also counts as small when it is a hairline: long but only a pixel or two thick
    touches_other = np.zeros(patches.shape, dtype=bool)
    touches_other[1:] |= patches[1:] != patches[:-1]
    touches_other[:-1] |= patches[1:] != patches[:-1]
    touches_other[:, 1:] |= patches[:, 1:] != patches[:, :-1]
    touches_other[:, :-1] |= patches[:, 1:] != patches[:, :-1]
    edge_pixels = np.bincount(patches[touches_other].astype(np.int64), minlength=patch_count)
    thickness = areas / np.maximum(edge_pixels, 1)
    small = (areas < min_area) | ((edge_pixels > 0) & (thickness < (min_area ** 0.5) / 5))
    if not small.any():
        return labels
    colour_count = int(labels.max()) + 1
    votes = np.zeros(patch_count * colour_count, dtype=np.int64)
    # every pixel that touches a different patch votes for the colour it sees across the border
    for axis, shifts in ((0, (1, -1)), (1, (1, -1))):
        for shift in shifts:
            neighbour_patch = np.roll(patches, shift, axis=axis)
            neighbour_label = np.roll(labels, shift, axis=axis)
            edge = (neighbour_patch != patches) & small[patches]
            if axis == 0:  # ignore the wrap-around row / column
                edge[0 if shift == 1 else -1, :] = False
            else:
                edge[:, 0 if shift == 1 else -1] = False
            votes += np.bincount(patches[edge].astype(np.int64) * colour_count + neighbour_label[edge], minlength=votes.size)
    replacement = votes.reshape(patch_count, colour_count).argmax(axis=1).astype(labels.dtype)
    has_neighbour = votes.reshape(patch_count, colour_count).sum(axis=1) > 0
    merge = small & has_neighbour
    return np.where(merge[patches], replacement[patches], labels).astype(labels.dtype)


def pick_marker_colour(rgb: np.ndarray, opaque: np.ndarray) -> tuple[int, int, int]:
    """a colour far from everything in the artwork, used to paint transparent areas."""
    sample = rgb[opaque][::max(1, int(opaque.sum() // 5000))] if opaque.any() else rgb.reshape(-1, 3)[:1]
    sample_lab = rgb_to_lab(sample)
    best, best_gap = MARKER_CANDIDATES[0], -1.0
    for candidate in MARKER_CANDIDATES:
        gap = np.linalg.norm(sample_lab - rgb_to_lab(np.array(candidate, dtype=np.float32)[None, :]), axis=1).min()
        if gap > best_gap:
            best, best_gap = candidate, gap
    return best


def otsu_threshold(grey: np.ndarray) -> int:
    histogram = np.bincount(grey.reshape(-1), minlength=256).astype(np.float64)
    total, weight_all = histogram.sum(), (histogram * np.arange(256)).sum()
    best, background_weight, background_sum = 128, 0.0, 0.0
    best_variance = -1.0
    for level in range(256):
        background_weight += histogram[level]
        if background_weight == 0 or background_weight == total:
            continue
        background_sum += level * histogram[level]
        mean_back = background_sum / background_weight
        mean_front = (weight_all - background_sum) / (total - background_weight)
        variance = background_weight * (total - background_weight) * (mean_back - mean_front) ** 2
        if variance > best_variance:
            best, best_variance = level, variance
    return best
