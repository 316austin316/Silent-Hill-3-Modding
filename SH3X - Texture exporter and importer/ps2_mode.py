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

def unswizzle_4_to_32(p_in_texels, width, height):
    p_swiz_texels = bytearray(width * height)

    for y in range(height):
        for x in range(width):
            index = y * width + x
            u_pen = ((p_in_texels[index >> 1]) >> ((index & 1) * 4)) & 0xF

            page_x = x & (~0x7F)
            page_y = y & (~0x7F)

            pages_horz = (width + 127) // 128
            pages_vert = (height + 127) // 128

            page_number = (page_y // 128) * pages_horz + (page_x // 128)

            page32_y = (page_number // pages_vert) * 32
            page32_x = (page_number % pages_vert) * 64

            page_location = page32_y * height * 2 + page32_x * 4

            loc_x = x & 0x7F
            loc_y = y & 0x7F

            block_location = ((loc_x & (~0x1F)) >> 1) * height + (loc_y & (~0xF)) * 2
            swap_selector = (((y + 2) >> 2) & 0x1) * 4
            pos_y = (((y & (~3)) >> 1) + (y & 1)) & 0x7

            column_location = pos_y * height * 2 + ((x + swap_selector) & 0x7) * 4

            byte_num = (x >> 3) & 3
            bits_set = (y >> 1) & 1

            set_pix_index = page_location + block_location + column_location + byte_num
            p_swiz_texels[set_pix_index] = (p_swiz_texels[set_pix_index] & (-bits_set)) | (u_pen << (bits_set * 4))

    return bytes(p_swiz_texels)

def unswizzle_texture(texture_data, width, height, bpp):
    if bpp == 8:
        return unswizzle_8_to_32(texture_data, width, height)
    elif bpp == 4:
        return unswizzle_4_to_32(texture_data, width, height)
    else:
        raise ValueError(f"Unsupported bpp value: {bpp}")


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
        unswizzled_data = unswizzle_texture(texture_data, width, height, bpp)

        # Save the raw unswizzled data
        with open(os.path.join(output_dir, f"raw_unswizzled_{filename}.bin"), "wb") as f:
            f.write(unswizzled_data)

        # Convert the unswizzled data to an image
        image = Image.frombytes("L", (width, height), unswizzled_data)

        # Save the image as a BMP file
        output_path = os.path.join(output_dir, f"output_{filename}.bmp")
        image.save(output_path, format="BMP")

    print(f"All textures unswizzled and saved to: {output_dir}")

def combine_palettes_into_image(palette_data, num_palettes, output_path):
    width = 512  # Assuming 256 colors per palette
    height = 512
    raw_bytes = bytearray(width * height * 4)  # 4 bytes per pixel (RGBA)

    for i in range(num_palettes):
        palette_section_start = i * 1024
        palette_section_end = palette_section_start + 1024
        for j in range(palette_section_start, palette_section_end, 4):
            b, g, r, a = palette_data[j:j+4]
            x = (j - palette_section_start) // 4
            y = i
            idx = (y * width + x) * 4
            raw_bytes[idx:idx+4] = r, g, b, a

    # Save the raw bytes to a file
    with open(output_path, "wb") as f:
        f.write(raw_bytes)

def apply_palette_to_textures(textures, output_dir):
    for texture in textures:
        width = texture["width"]
        height = texture["height"]
        filename = texture["filename"]
        palette_data = texture["palette_data"]
        num_palettes = texture["num_palettes"]
        
        # Save the combined palette image
        output_path = os.path.join(output_dir, f"combined_palette_{filename}.bin")
        combine_palettes_into_image(palette_data, num_palettes, output_path)

        # Load the raw unswizzled data
        input_path = os.path.join(output_dir, f"raw_unswizzled_{filename}.bin")
        with open(input_path, "rb") as f:
            unswizzled_data = f.read()

        # Convert the raw unswizzled data to an image
        image = Image.frombytes("L", (width, height), unswizzled_data)

        # Convert the image mode to "P" (paletted)
        image = image.convert("P")

        for i in range(num_palettes):
            # Extract the RGBA palette for the current section
            rgba_palette = []
            palette_section_start = i * 1024
            palette_section_end = palette_section_start + 1024
            for j in range(palette_section_start, palette_section_end, 4):
                b, g, r, a = palette_data[j:j+4]
                rgba_palette.extend([r, g, b, a])

            # Apply the palette to the image
            image.putpalette(rgba_palette, rawmode="RGBA")

            # Convert the image to RGBA mode
            colorized_image = image.convert("RGBA")

            # Save the raw data with applied palette
            raw_data_with_palette = colorized_image.tobytes()
            with open(os.path.join(output_dir, f"raw_with_palette_{filename}_color_palette{i}.bin"), "wb") as f:
                f.write(raw_data_with_palette)

            # Save the image
            output_path = os.path.join(output_dir, f"output_{filename}_color_palette{i}.bmp")
            colorized_image.save(output_path, format="BMP")

    print(f"All textures have been colorized and saved to: {output_dir}")


