import struct
import sys
import os
from PIL import Image
from image_processing import convert_bgra_to_rgba, save_images
from typing import List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import logging

# Setup basic logging
logging.basicConfig(filename='palette_processing.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def detect_pattern(chunk, patterns):
    count_80 = sum(1 for i in range(3, len(chunk), 4) if chunk[i] == 0x80)
    index_of_first_alignment = chunk.find(b'\x00\x00\x00\x00')

    print(f"\nChunk content at index: {chunk.hex(' ')}")
    print(f"Count of '80' endings in correct position in this chunk: {count_80}")

    if count_80 == 16:
        print("Detected pattern: 64 bytes of data and 192 bytes of padding.")
        return 1
    elif count_80 == 48:
        print("Detected pattern: 192 bytes of data and 64 bytes of padding.")
        return 2
    elif count_80 == 8:
        print("Detected pattern: 32 bytes of data and 32 bytes of padding.")
        return 3
    elif count_80 == 32:
        print("Detected pattern: 128 bytes of data and 128 bytes of padding.")
        return 4
    elif (count_80 == 30 or count_80 == 31) and index_of_first_alignment != -1:
        print("Detected pattern: 128 bytes of data and 128 bytes of padding with alignment.")
        return 5
    elif count_80 % 2 != 0 and index_of_first_alignment != -1:
        print("Detected pattern: Odd number of '80's with alignment.")
        return 6
    elif count_80 == 38:
        print("Detected pattern: 160 bytes of data and 96 bytes of padding.")
        return 7

    print("Pattern unclear, falling back to manual mode.")
    return 0

def remove_padding(palette_data):
    patterns = {
        1: (64, 192),
        2: (192, 64),
        3: (32, 32),
        4: (128, 128),
        5: (128, 128, 'Alignment'),
        6: (0, 0, 'Odd Alignment'),
        7: (160, 96),   # New pattern
        0: "Manual"
    }

    block_data_list = []
    index = 0
    total_length = len(palette_data)
    apply_to_all = False

    while index < total_length:
        chunk_size = 256 if index + 256 <= total_length else 64
        chunk = palette_data[index:min(index+chunk_size, total_length)]
        pattern_key = detect_pattern(chunk, patterns)
        
        print("\nAvailable Patterns:")
        for key, value in patterns.items():
            print(f"{key}: {value}")
        print(f"Suggested pattern for block at index {index}: {patterns.get(pattern_key, 'Unknown')}")

        choice = int(input("Select a pattern for the block (or 0 for manual mode): ") or pattern_key)

        if choice == 0:
            palette_size = int(input("Enter the palette size for this block: "))
            padding_size = int(input("Enter the padding size for this block: "))
        else:
            pattern = patterns.get(choice, (64, 192))
            if len(pattern) == 3:  # Handling special cases
                palette_size, padding_size, _ = pattern
            else:
                palette_size, padding_size = pattern

        if index == 0 or choice == 0:
            apply_all_choice = input("Apply this pattern to the entire palette section? (yes/no): ").lower()
            apply_to_all = (apply_all_choice == "yes")
        elif apply_to_all:
            print(f"Using the chosen pattern for block at index: {index}")

        if index + palette_size > total_length:
            print("Warning: Block size exceeds remaining data length. Adjusting palette size.")
            palette_size = total_length - index

        block_data = palette_data[index:index + palette_size]
        block_data_list.append(block_data)
        index += palette_size + padding_size

        # Log the processed block details
        logging.info(f'Block processed at index {index}: Palette Size={palette_size}, Padding Size={padding_size}, Pattern={patterns.get(choice, "Manual")}')

    else:
        index += 1

    processed_data = b''.join(block_data_list)
    return processed_data



# Usage example
# raw_palette_data = ... (load your raw palette data here)
# processed_palette_data = remove_padding(raw_palette_data)



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
                raw_palette_data = f.read(palette_data_size)
                palette_data = remove_padding(raw_palette_data)

                # Save the raw palette data before any calculations
                with open(f"output/raw_palette_{palette_data_offset:x}.bin", "wb") as raw_file:
                    raw_file.write(raw_palette_data)
                # Calculate blocks and colors per block
                nBlocks = (palette_data_size // entry_size) // bypp
                colorsPerBlock = entry_size // bypp
                palette = [None] * (colorsPerBlock * nBlocks)
    
                for block in range(nBlocks):
                    # Calculate the starting position of the block within the palette_data
                    block_start = block * entry_size
                    block_end = block_start + entry_size
    
                    # Ensure the block_end does not exceed the length of palette_data
                    if block_end > len(palette_data):
                        print(f"Warning: Block end ({block_end}) exceeds palette data length ({len(palette_data)})!")
                        break
    
                    # Extract the data for this block from palette_data
                    block_data = palette_data[block_start:block_end]
    
                    # Convert block_data bytes to list of tuples representing colors
                    palette[block * colorsPerBlock:(block + 1) * colorsPerBlock] = [
                        (block_data[i], block_data[i + 1], block_data[i + 2], block_data[i + 3])
                        for i in range(0, len(block_data), 4)]
                    
                    if len(block_data) != entry_size:
                        print(f"Warning: Number of bytes read in palette block != entry_size! (Expected {entry_size}, got {len(block_data)})")
                        break
    
    
                    # Seek to the next block
                    f.seek(256 - entry_size, 1)  # 1 denotes relative positioning
                    
                    
    
                # Swapping colors logic
                swapDistance = 32
                swapSize = 8
                if len(palette) > 8:
                    for i in range(8, len(palette) - swapDistance, swapDistance):
                        swapBlock = i + swapSize
                        if swapBlock + swapSize > len(palette):
                            print("Palette doesn't have enough colors left for swapping.")
                            break
                        palette[i:swapBlock], palette[swapBlock:swapBlock+swapSize] = palette[swapBlock:swapBlock+swapSize], palette[i:swapBlock]
                
    
                # Move the file pointer to the start of the next texture header
                f.seek(palette_data_offset + palette_data_size)
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
                with open(f"output/palette_{palette_data_offset:x}.bin", "wb") as palette_file:
                    palette_file.write(palette_data)
                    
                # save for each palette file
                palette_file_path = f"output/palette_{palette_data_offset:x}.bin"
                # Find the next texture header
                texture_header_offset = data.find(texture_header_pattern, texture_header_offset + 1)
                if texture_header_offset == -1:
                    break

    return textures  # Adjust this to include any other necessary data.
    
def visualize_palettes(filenames):  # Accept filenames as an argument
    texture_data_list = analyze_textures(filenames)  # Pass filenames to analyze_textures
    extracted_palettes = [texture_data["palette"] for texture_data in texture_data_list]

    for palette in extracted_palettes:
        colors = [(r/255, g/255, b/255, a/255) for (r, g, b, a) in palette]
        plt.figure(figsize=(10, 2))
        data = np.zeros((10, len(colors), 4))
        for i, color in enumerate(colors):
            data[:, i, :] = color
        plt.imshow(data, aspect='auto')
        plt.axis('off')
        plt.show()
        
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
        palette_data = texture["palette_data"]
        bypp = texture["bypp"]

        # Use the bpp value from the texture header
        bpp = texture["bpp"]

        # Unswizzle the texture data
        unswizzled_data = unswizzle_texture(texture_data, width, height, bpp)

        # Check if unswizzled_data is not None before writing it to a file
        if unswizzled_data:
            # Save the raw unswizzled data
            with open(os.path.join(output_dir, f"raw_unswizzled_{filename}.bin"), "wb") as f:
                f.write(unswizzled_data)

            # Convert the unswizzled data to an image
            image = Image.frombytes("L", (width, height), unswizzled_data)
            
            image.show()

            # Save the image as a PNG file
            output_path = os.path.join(output_dir, f"output_{filename}.png")  # Change file extension to .png
            image.save(output_path, format="PNG")  # Change format argument to "PNG"

    print(f"All textures unswizzled and saved to: {output_dir}")


def process_palette_data(palette_data, palette_data_size, entry_size, bypp):
    # Calculate blocks and colors per block
    nBlocks = (palette_data_size // entry_size) // bypp
    colorsPerBlock = entry_size // bypp
    palette = [None] * (colorsPerBlock * nBlocks)

    for block in range(nBlocks):
        # Calculate the starting position of the block within the palette_data
         block_start = block * entry_size
         block_end = block_start + entry_size
    
         # Ensure the block_end does not exceed the length of palette_data
         if block_end > len(palette_data):
             print(f"Warning: Block end ({block_end}) exceeds palette data length ({len(palette_data)})!")
             break
    
         # Extract the data for this block from palette_data
         block_data = palette_data[block_start:block_end]
    
         # Convert block_data bytes to list of tuples representing colors
         palette[block * colorsPerBlock:(block + 1) * colorsPerBlock] = [
             (block_data[i], block_data[i + 1], block_data[i + 2], block_data[i + 3])
             for i in range(0, len(block_data), 4)]
         
         if len(block_data) != entry_size:
             print(f"Warning: Number of bytes read in palette block != entry_size! (Expected {entry_size}, got {len(block_data)})")
             break
    
    
         # Seek to the next block
         f.seek(256 - entry_size, 1)  # 1 denotes relative positioning

    # Swapping colors logic
    swapDistance = 32
    swapSize = 8
    if len(palette) > 8:
        for i in range(8, len(palette) - swapDistance, swapDistance):
            swapBlock = i + swapSize
            if swapBlock + swapSize > len(palette):
                print("Palette doesn't have enough colors left for swapping.")
                break
            palette[i:swapBlock], palette[swapBlock:swapBlock+swapSize] = palette[swapBlock:swapBlock+swapSize], palette[i:swapBlock]

    return palette

def apply_palette_to_textures(textures, output_dir):
    for texture in textures:
        width = texture["width"]
        height = texture["height"]
        filename = texture["filename"]
        palette = texture["palette"]  # Fetch the palette data from the texture object

        # Load the raw unswizzled data
        input_path = os.path.join(output_dir, f"raw_unswizzled_{filename}.bin")
        try:
            with open(input_path, "rb") as f:
                unswizzled_data = f.read()
        except FileNotFoundError:
            print(f"File not found: {input_path}. Skipping this texture.")
            continue

        # Convert the raw unswizzled data to an image and switch mode to "P" (paletted)
        image = Image.frombytes("L", (width, height), unswizzled_data).convert("P")

        # Construct the palette in a format suitable for PIL
        pil_palette = []
        for color in palette:
            if color is not None:
                pil_palette.extend(color[:-1])  # exclude alpha
        # Check if the palette has been properly constructed
        if not pil_palette:
            print(f"Empty palette for texture {filename}. Skipping this texture.")
            continue

        # Apply the palette to the image
        image.putpalette(pil_palette)

        # Save the paletted image (P mode)
        p_mode_output_path = os.path.join(output_dir, f"output_{filename}_P.png")
        image.save(p_mode_output_path, format="PNG")

        # Convert the image to RGBA mode and save
        rgba_image = image.convert("RGBA")
        rgba_output_path = os.path.join(output_dir, f"output_{filename}_RGBA.png")  # Change file extension to .png
        rgba_image.save(rgba_output_path, format="PNG")

    print(f"All textures have been colorized and saved to: {output_dir}")

