import struct
import sys
import os



def calculate_palette_info(header, block_size=128):
    num_blocks = header[1]  # Assuming the number of blocks is the second byte of the header
    total_colors = num_blocks * (block_size // 4)  # Since RGB colors occupy 3 bytes
    print(f"Number of blocks: {num_blocks}")
    print(f"Total colors: {total_colors}")
    return num_blocks, total_colors


def read_palette_data(file, header, block_size=128):
    num_blocks, total_colors = calculate_palette_info(header, block_size)
    palette_data = bytearray(total_colors * 4)

    for i in range(num_blocks):
        block_data = file.read(block_size)
        palette_data[i * block_size:i * block_size + block_size] = block_data[:block_size]
        print(f"Read block {i}: {block_data[:block_size]}")
        # Skip padding (128 bytes)
        file.seek(block_size, os.SEEK_CUR)
        print(f"Skipping padding for block {i}")
    return bytes(palette_data)


# Example usage
header = bytes.fromhex("00 20 00 00 00 00 00 00 00 00 00 00 08 00 40 40 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")

with open("C:/Users/defin/Desktop/sh3 code/ps2/chhbb.mdl", "rb") as f:
    # Seek to the palette data location
    # Replace this with the correct file offset for the palette data
    f.seek(1020464)

    palette_data = read_palette_data(f, header)

with open("output.bin", "wb") as output_file:
    output_file.write(palette_data)
