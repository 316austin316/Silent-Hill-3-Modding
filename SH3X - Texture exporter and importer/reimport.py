import png
import struct
import sys
import os
from PIL import Image
from image_processing import convert_bgra_to_rgba, save_images



def convert_rgba_to_bgra(rgba_data):
    """
    Converts RGBA data to BGRA data by swapping the red and blue channels.
    """
    bgra_data = bytearray(len(rgba_data))
    for i in range(0, len(rgba_data), 4):
        bgra_data[i] = rgba_data[i+2] # blue channel
        bgra_data[i+1] = rgba_data[i+1] # green channel
        bgra_data[i+2] = rgba_data[i] # red channel
        bgra_data[i+3] = rgba_data[i+3] # alpha channel
    return bytes(bgra_data)

def import_textures(arc_filename, png_dir):
    with open(arc_filename, "r+b") as f:
        # Iterate over all PNG files in the png_dir
        for png_file in os.listdir(png_dir):
            if png_file.endswith(".png"):
                # Extract the offset from the filename
                offset_str = png_file.split("_")[1].split(".bin")[0]
                texture_data_offset = int(offset_str, 16)

                # Read the texture data from the PNG file
                png_path = os.path.join(png_dir, png_file)
                rgba_data = Image.open(png_path).convert("RGBA").tobytes()
                bgra_data = convert_rgba_to_bgra(rgba_data)

                # Write the new texture data to the file
                f.seek(texture_data_offset)
                f.write(bgra_data)
                print(f"{png_file} data written at offset {texture_data_offset}")


    print(f"All textures imported into {arc_filename}")
