# File: batch_analysis.py

import os
import struct
import logging

# Configure logging
logging.basicConfig(filename='analysis.log', level=logging.INFO, format='%(message)s')

def analyze_textures(filename):
    textures = []
    try:
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
    
                # print the texture header values and offset
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
                # Read the palette header
                palette_header_offset = texture_data_offset + data_size - (0x20 if header_size == 112 else 0)
                f.seek(palette_header_offset)
                palette_header = f.read(0x30)
                print(f"  Palette Offset: {palette_header_offset:#x}")
                # Extract relevant values from the palette header
                palette_data_size = struct.unpack("<I", palette_header[0:4])[0]
                bypp = struct.unpack("<B", palette_header[12:13])[0]
                entry_size = struct.unpack("<B", palette_header[14:15])[0]
                # print the palette header values
                print (f" palette data size: {struct.unpack('<I', palette_header[0:4])[0]}")
                print(f"  entry_size: {entry_size}")
                print (f" bypp: {struct.unpack('<B', palette_header[12:13])[0]}")
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
                    "offset": texture_data_offset,
                    "bypp": bypp,
                    "entry_size": entry_size,
                    "palette_header_info": (palette_data_size, bypp),
                    "total_size": total_size,
                    "filename": f"texture_{texture_data_offset:x}.bin".replace(":", "_")
                }
                
                # Format the texture information as a string
                texture_info = "\n".join(f"{key}: {value}" for key, value in texture.items())
                
                # Log the texture information
                logging.info(f"Texture information for file {filename}:\n{texture_info}\n")
                
                # Add the texture to the list of textures
                textures.append(texture)
                
                # Update texture_header_offset to the next occurrence of texture_header_pattern
                texture_header_offset = data.find(texture_header_pattern, texture_header_offset + 1)
                
                
                # Format the texture information as a string
                texture_info = "\n".join(f"{key}: {value}" for key, value in texture.items())
                
                # Log the texture information
                logging.info(f"Texture information for file {filename}:\n{texture_info}\n")
                
                # Add the texture to the list of textures
                textures.append(texture)
                
    except Exception as e:
        print(f"An error occurred while analyzing {filename}: {str(e)}")
    return textures
            
def batch_analyze(filenames):
    all_textures = []
    for filename in filenames:
        try:
            textures = analyze_textures(filename)
            all_textures.extend(textures)
        except Exception as e:
            logging.error(f"An error occurred while analyzing {filename}: {str(e)}")
    return all_textures
