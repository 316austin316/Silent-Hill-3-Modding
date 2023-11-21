import os
import sys
import struct
from tkinter import Tk, filedialog, Button, Label, Entry, StringVar


def err(msg):
    print("Error: {}".format(msg))
    sys.exit(1)

def getuint32(b, offs=0):
    return struct.unpack('<I', b[offs:offs+4])[0]

def read_original_mfa(mfapath):
    if not os.path.exists(mfapath):
        err("MFA path not found: {}".format(mfapath))

    with open(mfapath, 'rb') as f:
        buf = f.read()
        
    # Print the total size of the MFA file
    print("Total MFA file size:", len(buf))

    # Determine the offset for the first block
    offs = 0xB8 if buf[0x60] == 0x4E else 0xD8
    print("First block offset:", hex(offs))
    
    blocks = []
    block_index = -1
    block_offs = 0
    header = buf[:offs]
    file_entries = []
    
    print("Beginning to read blocks and file entries...")
    
    while offs < len(buf):
        block_index += 1
        num_files = getuint32(buf, offs)
        if num_files < 0:
            err('Unexpected start of block, expected file count at {}'.format(hex(offs)))
        total_bytesize = getuint32(buf, offs + 0x4)
        print("\nBlock index:", block_index, "Number of files:", num_files, "Total block size:", total_bytesize)
        print("Total block size at offset", hex(offs + 0x4), ":", hex(total_bytesize))
        # Store the block including its header (assuming header is 8 bytes)
        block_data = buf[offs - 0x8 : offs + total_bytesize + 0x800]
        blocks.append((block_index, offs - 0x8, block_data))

        for i in range(num_files):
            name_offs = getuint32(buf, offs + i * 0x10 + 0x8) + block_offs
            print(f"File {i}: Name offset = {hex(name_offs)}")
            unk = getuint32(buf, offs + i * 0x10 + 0x10)
            data_offs_pointer = offs + i * 0x10 + 0xC
            print(f"Pointer to data offset (hex address): {hex(data_offs_pointer)}")  # Added print statement
            
            data_offs = getuint32(buf, offs + i * 0x10 + 0xC) + block_offs + 0x800
            print(f"File {i}: Data offset = {hex(data_offs)}")
            
            
            data_size = getuint32(buf, offs + i * 0x10 + 0x14)
            print(f"File {i}: Data size = {hex(data_size)}")

            name_end_offs = name_offs
            while buf[name_end_offs] != 0:
                name_end_offs += 1
            filename = buf[name_offs:name_end_offs].decode(encoding='ascii', errors='replace').strip()
            print("File:", i, "Name:", filename, "Data offset:", hex(data_offs), "Data size:", data_size)
            if len(filename) == 0:
                filename = "_unnamed_{}_{}.bin".format(i, block_index)
            
            file_entries.append((filename, data_offs, data_size, block_index, unk))

        block_offs += total_bytesize + 0x800
        offs = block_offs + 0x8
        print("Next block offset:", hex(offs))

    data = buf[offs:]
    print("Remaining data size after reading all file entries:", len(data))

    return header, file_entries, data, blocks

def update_file_entries(file_entries, new_files_dir, original_data, blocks):
    new_data = bytearray()
    new_file_entries = []

    # Calculate the start offset for the new file data, which comes after all block headers and file entry metadata
    current_data_offset = sum(len(block[2]) for block in blocks)

    for filename, _, original_size, block_index, unk in file_entries:
        new_file_path = os.path.join(new_files_dir, filename)
        if os.path.isfile(new_file_path):
            with open(new_file_path, 'rb') as f:
                file_data = f.read()
        else:
            # Get the original data offset from the block data
            original_entry_data = next((block_data for bi, _, block_data in blocks if bi == block_index), None)
            name_offset_index = original_entry_data.find(filename.encode('ascii') + b'\x00')
            name_offset, actual_data_offset, data_size = struct.unpack_from('<III', original_entry_data, name_offset_index - 0xC)
            actual_data_offset += 0x800  # Adjusting the actual data offset
            file_data = original_data[actual_data_offset:actual_data_offset + data_size]

        # New file size might be different if the file has been replaced
        new_size = len(file_data)
        
        # The actual data offset is the current_data_offset + 0x800 for the header
        actual_data_offset = current_data_offset + 0x800
        
        # Append the new file entry with the updated size and data offset
        new_file_entries.append((filename, actual_data_offset, new_size, block_index, unk))
        
        # Extend the new data bytearray with the file data
        new_data.extend(file_data)
        
        # Increment the current data offset by the size of this file
        current_data_offset += new_size

    return new_file_entries, new_data


def create_new_mfa(output_path, original_header, updated_file_entries, updated_data, original_blocks):
    with open(output_path, 'wb') as new_mfa:
        # Write the original header first
        new_mfa.write(original_header)

        for block_index, block_offs, block_data in original_blocks:
            # Write the block header from the original block data
            new_mfa.write(block_data[:0x8])

            # Write updated file entries
            block_file_entries = [entry for entry in updated_file_entries if entry[3] == block_index]
            for filename, data_offset, size, _, unk in block_file_entries:
                # Offset in the entry needs to be the actual offset minus 0x800 for the header
                entry_offset = data_offset - 0x800
                new_mfa.write(struct.pack('<IIII', 0, 0, entry_offset, size))

            # Write file data
            for _, data_offset, size, _, _ in block_file_entries:
                file_data = updated_data[data_offset:data_offset + size]
                new_mfa.write(file_data)

            # Pad to align to 0x800 bytes
            remainder = (new_mfa.tell() - block_offs) % 0x800
            if remainder != 0:
                new_mfa.write(b'\x00' * (0x800 - remainder))

    print(f"New MFA file created at {output_path}")









def gui():
    root = Tk()
    root.title("MFA Editor")

    # Variables to store file paths
    original_mfa_path = StringVar()
    folder_path = StringVar()
    new_mfa_path = StringVar()

    # Functions for buttons
    def select_original_mfa():
        path = filedialog.askopenfilename(filetypes=[("MFA files", "*.mfa")])
        original_mfa_path.set(path)

    def select_folder():
        path = filedialog.askdirectory()
        folder_path.set(path)

    def select_new_mfa():
        path = filedialog.asksaveasfilename(filetypes=[("MFA files", "*.mfa")], defaultextension=".mfa")
        new_mfa_path.set(path)

    def run_script():
        original_header, original_file_entries, original_data, original_blocks = read_original_mfa(original_mfa_path.get())
        updated_file_entries, updated_data = update_file_entries(original_file_entries, folder_path.get(), original_data, original_blocks)
        create_new_mfa(new_mfa_path.get(), original_header, updated_file_entries, updated_data, original_blocks)



    # GUI layout
    Label(root, text="Original MFA file:").grid(row=0, column=0, sticky='w')
    Entry(root, textvariable=original_mfa_path, width=50).grid(row=0, column=1)
    Button(root, text="Browse", command=select_original_mfa).grid(row=0, column=2)

    Label(root, text="Folder with updated files:").grid(row=1, column=0, sticky='w')
    Entry(root, textvariable=folder_path, width=50).grid(row=1, column=1)
    Button(root, text="Browse", command=select_folder).grid(row=1, column=2)

    Label(root, text="New MFA file:").grid(row=2, column=0, sticky='w')
    Entry(root, textvariable=new_mfa_path, width=50).grid(row=2, column=1)
    Button(root, text="Browse", command=select_new_mfa).grid(row=2, column=2)

    Button(root, text="Run", command=run_script).grid(row=3, column=0, columnspan=3, pady=10)

    root.mainloop()

# Call the GUI function
gui()

