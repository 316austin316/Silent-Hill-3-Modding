import struct
import sys
import os
from PIL import Image
from image_processing import convert_bgra_to_rgba, save_images

def extract_textures(filename):
    textures = []
    with open(filename, "rb") as f:
        # Search for the master header pattern
        master_header_pattern = b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x20\x00\x00\x00"
        data = f.read()
        master_header_offset = data.find(master_header_pattern)
        while master_header_offset != -1:
            # Seek to the master header
            f.seek(master_header_offset)
            # Read the master header
            master_header = f.read(0x20)
            # Parse the values from the master header
            num_textures = master_header[20]
            texture_offset = struct.unpack("<I", master_header[8:12])[0]
            texture_size = struct.unpack(">I", master_header[12:16])[0]
            # print the parsed values
            print("Number of textures:", num_textures)
            print("Texture offset:", hex(texture_offset))
            print("Texture size:", hex(texture_size))

            # Iterate over all textures in the section
            for i in range(num_textures):
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
                print(f"Texture header for texture {i}: {texture_header}")
                print(f"  Width: {struct.unpack('<H', texture_header[8:10])[0]}")
                print(f"  Height: {struct.unpack('<H', texture_header[10:12])[0]}")
                print(f"  bpp: {struct.unpack('<B', texture_header[12:13])[0]}")
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
                # Create the output directory if it doesn't exist
                if not os.path.exists("output"):
                    os.mkdir("output")
                # Write the texture data to a separate file
                with open(f"output/texture_{texture_data_offset:x}.bin", "wb") as texture_file:
                    texture_file.write(texture_data)
                # Move the file pointer to the start of the next texture header
                f.seek(texture_data_offset + data_size)
                # Add the texture information to the list of textures
                texture = {
                    "index": i,
                    "width": width,
                    "height": height,
                    "bpp": bpp,
                    "data_size": data_size,
                    "data": texture_data,
                    "offset": texture_data_offset,
                    "total_size": total_size,
                    "filename": f"texture_{texture_data_offset:x}.bin"
                }
                textures.append(texture)
            # Find the next master header
            master_header_offset = data.find(master_header_pattern, master_header_offset + 1)
            if master_header_offset == -1:
                break

    return textures
    
def convert_texture_to_image(texture):
    texture_data = texture["data"]
    width = texture["width"]
    height = texture["height"]

    # Convert BGRA data to RGBA
    rgba_data = convert_bgra_to_rgba(texture_data)

    # Convert RGBA data to a Pillow Image object
    img = Image.frombytes("RGBA", (width, height), rgba_data)
    return img

def save_image_to_disk(img, filename, output_dir):
    img_path = os.path.join(output_dir, f"{filename}.png")
    img.save(img_path)


def convert_textures_to_png(textures, output_dir):
    # Iterate over all extracted textures
    for i, texture in enumerate(textures):
        filename = texture["filename"]
        
        # Convert texture to a Pillow Image object
        img = convert_texture_to_image(texture)
        
        # Save the Pillow Image object to disk
        save_image_to_disk(img, filename, output_dir)

    print(f"All textures converted to PNG and saved to: {output_dir}")

