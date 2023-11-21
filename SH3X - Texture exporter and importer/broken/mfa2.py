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

    block_index = -1
    block_offs = 0
    header = buf[:offs]
    file_entries = []
    blocks = []
    
    print("Beginning to read blocks and file entries...")
    
    while offs < len(buf):
        block_index += 1
        num_files = getuint32(buf, offs)
        if num_files < 0:
            err('Unexpected start of block, expected file count at {}'.format(hex(offs)))
        total_bytesize = getuint32(buf, offs + 0x4)
        print("\nBlock index:", block_index, "Number of files:", num_files, "Total block size:", total_bytesize)
        print("Total block size at offset", hex(offs + 0x4), ":", hex(total_bytesize))
        
        block_data = buf[offs:offs + total_bytesize + 0x800]
        blocks.append((block_index, block_offs, block_data))

        for i in range(num_files):
            name_offs = getuint32(buf, offs + i * 0x10 + 0x8) + block_offs
            data_offs = getuint32(buf, offs + i * 0x10 + 0xC) + block_offs + 0x800
            data_size = getuint32(buf, offs + i * 0x10 + 0x14)

            name_end_offs = name_offs
            while buf[name_end_offs] != 0:
                name_end_offs += 1
            filename = buf[name_offs:name_end_offs].decode(encoding='ascii', errors='replace').strip()
            print("File:", i, "Name:", filename, "Data offset:", hex(data_offs), "Data size:", data_size)
            if len(filename) == 0:
                filename = "_unnamed_{}_{}.bin".format(i, block_index)
            
            file_entries.append((filename, data_offs, data_size))

        block_offs += total_bytesize + 0x800
        offs = block_offs + 0x8
        print("Next block offset:", hex(offs))

    data = buf[offs:]
    print("Remaining data size after reading all file entries:", len(data))

    return header, file_entries, data, blocks

def update_file_entries(file_entries, new_files_dir, original_data):
    new_data = bytearray()
    new_file_entries = []
    current_data_offset = 0

    print("Original file entries:")
    for entry in file_entries:
        print(entry)

    for filename, original_offset, original_size in file_entries:
        new_file_path = os.path.join(new_files_dir, filename)
        
        if os.path.isfile(new_file_path):
            # File has been updated
            with open(new_file_path, 'rb') as f:
                file_data = f.read()
        else:
            # File hasn't been updated, use original data
            file_data = original_data[original_offset:original_offset + original_size]
        
        # Keep the original filename, but update offset and size
        new_file_entries.append((filename, current_data_offset, len(file_data)))
        new_data.extend(file_data)
        current_data_offset += len(file_data)

    print("Updated file entries:")
    for entry in new_file_entries:
        print(entry)

    return new_file_entries, new_data




def create_new_mfa(output_path, original_header, original_file_entries, updated_file_entries, updated_data, blocks):
    with open(output_path, 'wb') as new_mfa:
        # Write the original header first
        new_mfa.write(original_header)

        # Write each block with updated file entries and data
        for block_index, block_offs, block_data in blocks:
            # Write block data except for the file entries
            block_header_size = 0x8 + len(original_file_entries) * 0x10
            new_mfa.write(block_data[:block_header_size])

            # Write updated file entries
            for file_entry in updated_file_entries:
                if file_entry[2] == block_index:  # Check if the file entry belongs to the current block
                    filename, new_offset, new_size = file_entry
                    encoded_filename = filename.encode('ascii') + b'\x00'
                    file_entry_data = encoded_filename + struct.pack('<I', new_offset) + struct.pack('<I', new_size)
                    new_mfa.write(file_entry_data)

            # Write updated data for the current block
            new_mfa.write(updated_data[block_offs:block_offs + len(block_data)])

        # Add padding to align to 0x800 bytes if necessary
        remainder = len(updated_data) % 0x800
        if remainder != 0:
            padding = b'\x00' * (0x800 - remainder)
            new_mfa.write(padding)

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
        # Function calls
        original_header, original_file_entries, original_data, blocks = read_original_mfa(original_mfa_path.get())
        updated_file_entries, updated_data = update_file_entries(original_file_entries, folder_path.get(), original_data)
        create_new_mfa(new_mfa_path.get(), original_header, original_file_entries, updated_file_entries, updated_data, blocks)



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

if __name__ == "__main__":
    gui()