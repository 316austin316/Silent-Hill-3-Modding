import struct
import sys
import os

# check if the user provided a filename as an argument
if len(sys.argv) < 2:
    print("Usage: extract_textures.py <filename.arc>")
    sys.exit()

# get the filename from the command-line argument
filename = sys.argv[1]

# open the specified .arc file in binary mode
with open(filename, "rb") as f:
    # search for the master header pattern
    master_header_pattern = b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x20\x00\x00\x00"
    data = f.read()
    master_header_offset = data.find(master_header_pattern)
        
    # seek to the first master header
    f.seek(master_header_offset)

    # read the first master header
    master_header = f.read(0x20)

    # parse the values from the master header
    num_textures = master_header[20]
    texture_offset = struct.unpack("<I", master_header[8:12])[0]
    texture_size = struct.unpack(">I", master_header[12:16])[0]

    # print the parsed values
    print("Number of textures:", num_textures)
    print("Texture offset:", hex(texture_offset))
    print("Texture size:", hex(texture_size))

    # iterate over all textures in the section
    print("Starting texture extraction...")

    # seek to the start of the texture header
    f.seek(0x175b64)
    for i in range(num_textures):
        # read the texture header
        texture_header = f.read(0x20)

        # check the pattern to determine the header size
        if texture_header[12:16] == b"\x20\x30\x00\x00":
            header_size = 96
        elif texture_header[12:16] == b"\x20\x50\x00\x00":
            header_size = 128
        else:
            header_size = 80

        # calculate the offset of the texture header
        header_offset = f.tell() - 0x20

        # read the remaining bytes of the texture header
        texture_header += f.read(header_size - 0x20)

        # print the texture header values and offset
        print(f"Texture header for texture {i}: {texture_header}")
        print(f"  Width: {struct.unpack('<H', texture_header[8:10])[0]}")
        print(f"  Height: {struct.unpack('<H', texture_header[10:12])[0]}")
        print(f"  Data size: {struct.unpack('<I', texture_header[16:20])[0]}")
        print(f"  Total size: {struct.unpack('<I', texture_header[20:24])[0]}")

        # parse the values from the texture header
        width = struct.unpack("<H", texture_header[8:10])[0]
        height = struct.unpack("<H", texture_header[10:12])[0]
        data_size = struct.unpack("<I", texture_header[16:20])[0]
        total_size = struct.unpack("<I", texture_header[20:24])[0]

        # read the texture data
        texture_data_offset = f.tell()
        f.seek(texture_data_offset)
        texture_data = f.read(data_size)

        # create the output directory if it doesn't exist
        if not os.path.exists("output"):
            os.mkdir("output")

        # write the texture data to a separate file
        with open(f"output/texture_{i}.bin", "wb") as texture_file:
            texture_file.write(texture_data)

        # Move the file pointer to the start of the next texture header
        f.seek(texture_data_offset + data_size)

    print("Texture location complete.")


