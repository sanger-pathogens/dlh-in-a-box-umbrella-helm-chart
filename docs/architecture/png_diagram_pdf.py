"""Create a consolidated PDF from exported PNG diagrams.

This intentionally avoids third-party dependencies so the IcePanel export
workflow remains runnable in a minimal Python environment.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PAGE_WIDTH = 1190.0
MAX_PAGE_HEIGHT = 1684.0


def write_pngs_as_pdf(png_paths: list[Path], output_path: Path) -> None:
    if not png_paths:
        raise ValueError("at least one PNG is required")

    objects: list[bytes] = [b"", b""]
    page_ids: list[int] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    for index, png_path in enumerate(png_paths, start=1):
        width, height, rgb, alpha = read_rgba_png(png_path)
        alpha_object_id = None
        if any(value != 255 for value in alpha):
            alpha_object_id = add_object(
                stream_object(
                    (
                        f"<< /Type /XObject /Subtype /Image /Width {width} "
                        f"/Height {height} /ColorSpace /DeviceGray "
                        f"/BitsPerComponent 8 /Filter /FlateDecode"
                    ),
                    zlib.compress(alpha),
                )
            )

        smask = f" /SMask {alpha_object_id} 0 R" if alpha_object_id else ""
        image_object_id = add_object(
            stream_object(
                (
                    f"<< /Type /XObject /Subtype /Image /Width {width} "
                    f"/Height {height} /ColorSpace /DeviceRGB "
                    f"/BitsPerComponent 8 /Filter /FlateDecode{smask}"
                ),
                zlib.compress(rgb),
            )
        )

        page_width, page_height = page_size(width, height)
        image_name = f"Im{index}"
        content = f"q {page_width:.2f} 0 0 {page_height:.2f} 0 0 cm /{image_name} Do Q\n".encode(
            "ascii"
        )
        content_object_id = add_object(stream_object("<<", content))
        page_object_id = add_object(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2f} {page_height:.2f}] "
                f"/Resources << /XObject << /{image_name} {image_object_id} 0 R >> >> "
                f"/Contents {content_object_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_object_id)

    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_pdf(objects))


def read_rgba_png(path: Path) -> tuple[int, int, bytes, bytes]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"not a PNG: {path}")

    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    idat_parts: list[bytes] = []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError(f"truncated PNG chunk header: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if None in {width, height, bit_depth, color_type, interlace}:
        raise ValueError(f"missing PNG IHDR: {path}")
    if bit_depth != 8 or color_type != 6 or interlace != 0:
        raise ValueError(f"unsupported PNG format in {path}: bit={bit_depth}, color={color_type}")

    rgba = unfilter_rgba(zlib.decompress(b"".join(idat_parts)), int(width), int(height))
    rgb = bytearray(int(width) * int(height) * 3)
    alpha = bytearray(int(width) * int(height))
    for pixel in range(int(width) * int(height)):
        rgba_offset = pixel * 4
        rgb_offset = pixel * 3
        rgb[rgb_offset : rgb_offset + 3] = rgba[rgba_offset : rgba_offset + 3]
        alpha[pixel] = rgba[rgba_offset + 3]
    return int(width), int(height), bytes(rgb), bytes(alpha)


def unfilter_rgba(raw: bytes, width: int, height: int) -> bytes:
    bytes_per_pixel = 4
    stride = width * bytes_per_pixel
    output = bytearray(width * height * bytes_per_pixel)
    prior = bytearray(stride)
    raw_offset = 0
    out_offset = 0

    for _ in range(height):
        filter_type = raw[raw_offset]
        raw_offset += 1
        scanline = bytearray(raw[raw_offset : raw_offset + stride])
        raw_offset += stride

        for index, value in enumerate(scanline):
            left = scanline[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = prior[index]
            up_left = prior[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 1:
                scanline[index] = (value + left) & 0xFF
            elif filter_type == 2:
                scanline[index] = (value + up) & 0xFF
            elif filter_type == 3:
                scanline[index] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                scanline[index] = (value + paeth(left, up, up_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter: {filter_type}")

        output[out_offset : out_offset + stride] = scanline
        prior = scanline
        out_offset += stride

    return bytes(output)


def paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    up_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def page_size(width: int, height: int) -> tuple[float, float]:
    scale = min(MAX_PAGE_WIDTH / width, MAX_PAGE_HEIGHT / height)
    return width * scale, height * scale


def stream_object(dictionary_prefix: str, payload: bytes) -> bytes:
    return (
        f"{dictionary_prefix} /Length {len(payload)} >>\nstream\n".encode("ascii")
        + payload
        + b"\nendstream"
    )


def render_pdf(objects: list[bytes]) -> bytes:
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
