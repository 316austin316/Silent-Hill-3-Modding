import struct
import sys
import os
from PIL import Image
from typing import List, Tuple
import numpy as np
import logging

def process_palette_data(palette_data, palette_data_size, entry_size, bypp):
    """
    Processes the raw palette data and returns a list of RGBA tuples.
    """
    # Each block is 256 bytes; actual data is entry_size bytes
    nBlocks = palette_data_size // 256
    colorsPerBlock = entry_size // bypp
    palette = []

    for block in range(nBlocks):
        block_start = block * 256
        block_end = block_start + entry_size

        # Ensure the block_end does not exceed the length of palette_data
        if block_end > len(palette_data):
            print(f"Warning: Block end ({block_end}) exceeds palette data length ({len(palette_data)})!")
            break

        block_data = palette_data[block_start:block_end]

        # Convert block_data bytes to list of tuples representing colors (RGBA format)
        block_palette = [
            (block_data[i], block_data[i + 1], block_data[i + 2], block_data[i + 3])  # RGBA
            for i in range(0, len(block_data), bypp)
        ]
        palette.extend(block_palette)

    # Swapping colors logic
    swapDistance = 32
    swapSize = 8
    if len(palette) > 8:
        for i in range(8, len(palette) - swapSize, swapDistance):
            swapBlock = i + swapSize
            if swapBlock + swapSize > len(palette):
                print("Palette doesn't have enough colors left for swapping.")
                break
            palette[i:swapBlock], palette[swapBlock:swapBlock+swapSize] = palette[swapBlock:swapBlock+swapSize], palette[i:swapBlock]

    return palette

def analyze_textures(filenames):
    textures = []
    for filename in filenames:
        with open(filename, "rb") as f:
            # Search for the texture header pattern
            texture_header_pattern = b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00"
            data = f.read()
            texture_header_offset = data.find(texture_header_pattern)
            while texture_header_offset != -1:
                # Seek to the texture header
                f.seek(texture_header_offset)
                # Read the texture header
                texture_header = f.read(0x20)
                # Check the pattern to determine the header size
                if texture_header[12:16] == b"\x20\x30\x00\x00":
                    header_size = 96
                elif texture_header[12:16] == b"\x18\x30\x00\x00":
                    header_size = 96
                elif texture_header[12:16] == b"\x08\x30\x00\x00":
                    header_size = 96
                elif texture_header[12:16] == b"\x18\x50\x00\x00":
                    header_size = 128
                elif texture_header[12:16] == b"\x20\x50\x00\x00":
                    header_size = 128
                elif texture_header[12:16] == b"\x08\x20\x00\x00":
                    header_size = 80
                elif texture_header[12:16] == b"\x04\x20\x00\x00":
                    header_size = 112
                else:
                    header_size = 80
                # Calculate the offset of the texture header
                header_offset = f.tell() - 0x20
                # Read the remaining bytes of the texture header
                texture_header += f.read(header_size - 0x20)

                # Parse the values from the texture header
                width = struct.unpack("<H", texture_header[8:10])[0]
                height = struct.unpack("<H", texture_header[10:12])[0]
                bpp = struct.unpack("<B", texture_header[12:13])[0]
                data_size = struct.unpack("<I", texture_header[16:20])[0]
                total_size = struct.unpack("<I", texture_header[20:24])[0]
                data_offset = struct.unpack("<I", texture_header[4:8])[0]

                # Read the texture data
                texture_data_offset = f.tell()
                f.seek(texture_data_offset)
                texture_data = f.read(data_size)

                # Read the palette header
                palette_header_offset = texture_data_offset + data_size - (0x20 if header_size == 112 else 0)
                f.seek(palette_header_offset)
                palette_header = f.read(0x30)

                # Extract relevant values from the palette header
                palette_data_size = struct.unpack("<I", palette_header[0:4])[0]
                bypp = struct.unpack("<B", palette_header[12:13])[0]
                entry_size = struct.unpack("<B", palette_header[14:15])[0]

                # Read the palette data
                palette_data_offset = palette_header_offset + 0x30
                f.seek(palette_data_offset)
                raw_palette_data = f.read(palette_data_size)
                palette_data = raw_palette_data

                # Process the palette data
                palette = process_palette_data(palette_data, palette_data_size, entry_size, bypp)

                # Add the texture information to the list of textures
                texture = {
                    "index": len(textures),
                    "width": width,
                    "palette": palette,
                    "height": height,
                    "bpp": bpp,
                    "data_size": data_size,
                    "data": texture_data,
                    "offset": texture_data_offset,
                    "palette_data": palette_data,
                    "bypp": bypp,
                    "entry_size": entry_size,
                    "palette_header_info": (palette_data_size, bypp),
                    "total_size": total_size,
                    "filename": f"{os.path.basename(filename)}_texture_{texture_data_offset:x}.bin".replace(":", "_")
                }
                textures.append(texture)

                # Create the output directory if it doesn't exist
                if not os.path.exists("output"):
                    os.mkdir("output")
                # Write the texture data to a separate file
                with open(f"output/texture_{texture_data_offset:x}.bin", "wb") as texture_file:
                    texture_file.write(texture_data)
                # Write the palette data to a separate file
                with open(f"output/palette_{palette_data_offset:x}.bin", "wb") as palette_file:
                    palette_file.write(palette_data)

                # Find the next texture header
                texture_header_offset = data.find(texture_header_pattern, texture_header_offset + 1)
                if texture_header_offset == -1:
                    break

    return textures

def unswizzle_8_to_32(p_in_texels, width, height):
    p_swiz_texels = bytearray(width * height)

    for y in range(height):
        for x in range(width):
            block_location = (y & ~0xf) * width + (x & ~0xf) * 2
            swap_selector = (((y + 2) >> 2) & 0x1) * 4
            pos_y = (((y & ~3) >> 1) + (y & 1)) & 0x7
            column_location = pos_y * width * 2 + ((x + swap_selector) & 0x7) * 4

            byte_num = ((y >> 1) & 1) + ((x >> 2) & 2)  # 0, 1, 2, 3

            p_swiz_texels[y * width + x] = p_in_texels[block_location + column_location + byte_num]

    return bytes(p_swiz_texels)

def unswizzle4(p_In_Texels, width, height):
    # Convert the 4bpp input data into 8bpp
    p_Converted_Texels = bytearray(width * height)
    for i in range(width * height // 2):
        index = p_In_Texels[i]
        id2 = (index >> 4) & 0xf
        id1 = index & 0xf
        p_Converted_Texels[i * 2] = id1
        p_Converted_Texels[i * 2 + 1] = id2

    # Use your 8bpp unswizzling function on the converted texels
    p_Unswizzled_Texels = unswizzle_8_to_32(p_Converted_Texels, width, height)

    return bytes(p_Unswizzled_Texels)

def unswizzle_texture(texture_data, width, height, bpp):
    if bpp == 8:
        return unswizzle_8_to_32(texture_data, width, height)
    elif bpp == 4:
        return unswizzle4(texture_data, width, height)
    else:
        raise ValueError(f"Unsupported bpp value: {bpp}")

def unswizzle_and_save(textures, output_dir):
    for texture in textures:
        texture_data = texture["data"]
        width = texture["width"]
        height = texture["height"]
        filename = texture["filename"]
        palette = texture["palette"]
        bpp = texture["bpp"]

        # Unswizzle the texture data
        unswizzled_data = unswizzle_texture(texture_data, width, height, bpp)

        if unswizzled_data:
            # Save the raw unswizzled data
            with open(os.path.join(output_dir, f"raw_unswizzled_{filename}.bin"), "wb") as f:
                f.write(unswizzled_data)

            if bpp in (4, 8):
                # Create an Image with mode 'P' (palettized)
                image = Image.frombytes('P', (width, height), unswizzled_data)
                # Flatten the palette to a list
                flat_palette = []
                for color in palette:
                    flat_palette.extend(color[:3])  # Use RGB channels
                # Ensure the palette has 768 values (256 colors * 3 channels)
                if len(flat_palette) < 768:
                    flat_palette.extend([0] * (768 - len(flat_palette)))
                image.putpalette(flat_palette)
            else:
                # For other bpp values, handle accordingly (e.g., 'L' mode for grayscale)
                image = Image.frombytes('L', (width, height), unswizzled_data)

            # Save the image as a PNG file
            output_path = os.path.join(output_dir, f"output_{filename}.png")
            image.save(output_path, format="PNG")

    print(f"All textures unswizzled and saved to: {output_dir}")

