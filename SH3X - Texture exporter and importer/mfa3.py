import os
import struct
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox

def getint32(b, offs=0):
    return struct.unpack('<i', b[offs:offs+4])[0]

def getuint32(b, offs=0):
    return struct.unpack('<I', b[offs:offs+4])[0]

class MFAViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("MFA Viewer")
        self.mfa_data = None
        self.mfa_path = None
        self.total_byte_size_label = tk.Label(root, text="Total byte size of file: Not loaded")
        self.total_byte_size_label.pack()
        self.data_offset_positions = {}
        
        # Create a file open button
        self.open_button = ttk.Button(root, text="Open MFA File", command=self.load_mfa)
        self.open_button.pack()

        # Create a treeview to show the file entries
        self.tree = ttk.Treeview(root, columns=("Name", "Size", "Offset", "Data Offset"))
        self.tree.heading('#0', text='Index')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Size', text='Size')
        self.tree.heading('Offset', text='Offset')
        self.tree.heading('Data Offset', text='Data Offset')
        self.tree.pack(expand=True, fill='both')

        # Create an extract button
        self.extract_button = ttk.Button(root, text="Extract Selected File", command=self.extract_file)
        self.extract_button.pack()
        
        # Create an import button
        self.import_button = ttk.Button(root, text="Import New File", command=self.import_file)
        self.import_button.pack()

    def load_mfa(self):
        path = filedialog.askopenfilename()
        if path:
            self.mfa_path = path
            with open(path, 'rb') as f:
                self.mfa_data = bytearray(f.read())

            self.populate_treeview()

    def populate_treeview(self):
        buf = self.mfa_data
        self.tree.delete(*self.tree.get_children())

        # Adjust the offset for the first block
        offs = 0xB8 if buf[0x60] == 0x4E else 0xD8
        block_offs = 0
        
        self.total_bytesize = getuint32(buf, offs + 0x4)
        self.total_byte_size_label.config(text=f"Total byte size of file: {self.total_bytesize}")
        
        while offs < len(buf):
            num_files = getint32(buf, offs)
            total_bytesize = getuint32(buf, offs + 0x4)
            for i in range(num_files):
                name_offs = getuint32(buf, offs + i * 0x10 + 0x8) + block_offs
                data_offs = getuint32(buf, offs + i * 0x10 + 0xC) + block_offs + 0x800
                self.data_offset_positions[i] = offs + i * 0x10 + 0xC
                data_size = getuint32(buf, offs + i * 0x10 + 0x14)

                name_end_offs = name_offs
                while buf[name_end_offs] != 0:
                    name_end_offs += 1
                filename = buf[name_offs:name_end_offs].decode(
                    encoding='ascii', errors='replace').strip()
                if len(filename) == 0:
                    filename = "_unnamed_{}_{}.bin".format(i, block_offs)

                # Insert the file data into the treeview
                self.tree.insert("", 'end', text=str(i), values=(filename, data_size, hex(name_offs), hex(data_offs)))

            block_offs += total_bytesize + 0x800
            offs = block_offs + 0x8

    def extract_file(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "No file selected")
            return

        # Get the details of the selected file
        file_data = self.tree.item(selected_item)
        file_index = int(file_data['text'])
        filename, file_size, name_offset, data_offset = file_data['values']

        # Convert offsets from hex string to integer
        name_offset = int(name_offset, 16)
        data_offset = int(data_offset, 16)

        # Ask user where to save the extracted file
        out_path = filedialog.asksaveasfilename(defaultextension=".*", initialfile=filename)
        if out_path:
            # Perform the extraction
            with open(out_path, 'wb') as out_file:
                out_file.write(self.mfa_data[data_offset:data_offset + int(file_size)])
            messagebox.showinfo("Success", "File extracted to " + out_path)
            
    def import_file(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "No file selected for import")
            return

        # Get the details of the selected file
        file_data = self.tree.item(selected_item)
        file_index = int(file_data['text'])
        original_filename, original_size, name_offset, data_offset = file_data['values']

        # Convert offsets from hex string to integer
        data_offset = int(data_offset, 16)
        original_size = int(original_size)

        # Ask user to select the new file to import
        new_file_path = filedialog.askopenfilename()
        if not new_file_path:
            return  # User cancelled the file selection dialog

        with open(new_file_path, 'rb') as new_file:
            new_file_data = new_file.read()

        # Calculate the size difference
        size_difference = len(new_file_data) - original_size
    
        # If the new file is larger, we need to shift data
        if size_difference > 0:
            # Update the total byte size and its display in the GUI
            self.total_bytesize += size_difference
            self.total_byte_size_label.config(text=f"Total byte size of file: {self.total_bytesize}")
        
            # Update the total byte size in the MFA data
            total_byte_size_offset = 0xDC
            self.mfa_data[total_byte_size_offset:total_byte_size_offset + 4] = struct.pack('<I', self.total_bytesize)
        
            # Shift the data to make space for the new file
            self.mfa_data = (self.mfa_data[:data_offset + original_size] +
                            b'\x00' * size_difference +
                            self.mfa_data[data_offset + original_size:])

            # Update the size in the file entry
            size_offset = data_offset - 0x14
            self.mfa_data[size_offset:size_offset + 4] = struct.pack('<I', len(new_file_data))

            # Update offsets for subsequent files
            for i in range(file_index + 1, len(self.tree.get_children())):
                child_id = self.tree.get_children()[i]
                child_data = self.tree.item(child_id)
                child_values = child_data['values']
                child_data_offset = int(child_values[3], 16)
                
                # Calculate the new data offset for this file
                new_child_data_offset = child_data_offset + size_difference - 0x800
                
                # Get the MFA file position for the current file's data offset
                file_entry_data_offset_pos = self.data_offset_positions[i]
                
                # Update the data offset in the MFA data
                self.mfa_data[file_entry_data_offset_pos:file_entry_data_offset_pos + 4] = struct.pack('<I', new_child_data_offset)
    
            
                # Update the data offset in the treeview
                self.tree.item(child_id, values=(child_values[0], child_values[1], child_values[2], hex(new_child_data_offset)))


        elif size_difference < 0:
            messagebox.showerror("Error", "The new file must not be smaller than the original.")
            return
        else:
            # If the new file is the same size, just replace the data
            self.mfa_data[data_offset:data_offset + original_size] = new_file_data

        # Confirm successful import
        messagebox.showinfo("Success", "File imported successfully")

        # Save the modified MFA data back to the file
        with open(self.mfa_path, 'wb') as mfa_file:
            mfa_file.write(self.mfa_data)
            
            
        

        

if __name__ == "__main__":
    root = tk.Tk()
    app = MFAViewer(root)
    root.mainloop()
