import struct
import sys
import os
from PIL import Image
import pyglet.image.codecs.dds
from image_processing import convert_bgra_to_rgba, save_images

def analyze_textures(filename):
    textures = []
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
            else:
                header_size = 80
            # Calculate the offset of the texture header
            header_offset = f.tell() - 0x20
            # Read the remaining bytes of the texture header
            texture_header += f.read(header_size - 0x20)

            # print the texture header values and offset
            print(f"  Width: {struct.unpack('<H', texture_header[8:10])[0]}")
            print(f"  Height: {struct.unpack('<H', texture_header[10:12])[0]}")
            print(f" bpp: {struct.unpack('<B', texture_header[12:13])[0]}")
            print(f"  Data size: {struct.unpack('<I', texture_header[16:20])[0]}")
            print(f"  Total size: {struct.unpack('<I', texture_header[20:24])[0]}")

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
            palette_header_offset = texture_data_offset + data_size
            f.seek(palette_header_offset)
            palette_header = f.read(0x30)
            # Extract relevant values from the palette header
            palette_data_size = struct.unpack("<I", palette_header[0:4])[0]
            num_palettes = struct.unpack("<H", palette_header[12:14])[0]
            # print the palette header values
            print (f" palette data size: {struct.unpack('<I', palette_header[0:4])[0]}")
            print (f" num_palettes: {struct.unpack('<H', palette_header[12:14])[0]}")
            # Read the palette data
            palette_data_offset = palette_header_offset + 0x30
            f.seek(palette_data_offset)
            palette_data = f.read(palette_data_size)

            # Move the file pointer to the start of the next texture header
            f.seek(palette_data_offset + palette_data_size)
            # Add the texture information to the list of textures
            texture = {
                "index": len(textures),
                "width": width,
                "height": height,
                "bpp": bpp,
                "data_size": data_size,
                "data": texture_data,
                "offset": texture_data_offset,
                "palette_data": palette_data,
                "num_palettes": num_palettes,
                "total_size": total_size,
                "filename": f"texture_{texture_data_offset:x}.bin".replace(":", "_")
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



def unswizzle_and_save(textures, output_dir):
    for texture in textures:
        texture_data = texture["data"]
        width = texture["width"]
        height = texture["height"]
        filename = texture["filename"]
        palette_data = texture["palette_data"]
        num_palettes = texture["num_palettes"]

        # Use the bpp value from the texture header
        bpp = texture["bpp"]

        # Unswizzle the texture data
        unswizzled_data = unswizzle_8_to_32(texture_data, width, height)

        # Convert the unswizzled data to an image
        image = Image.frombytes("L", (width, height), unswizzled_data)

        # Save the image as a BMP file
        output_path = os.path.join(output_dir, f"output_{filename}.bmp")
        image.save(output_path, format="BMP")

    print(f"All textures unswizzled and saved to: {output_dir}")

