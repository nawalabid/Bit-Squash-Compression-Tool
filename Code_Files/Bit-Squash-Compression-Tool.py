import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import json
import heapq
import zlib
import sys
import subprocess

# --- Huffman Node ---
class Node:
    def __init__(self,freq,char=None,left=None,right=None,codes={}):
        self.char=char
        self.freq=freq
        self.left=left
        self.right=right
        self.codes=codes
    def __lt__(self,other):
        return self.freq < other.freq

# --- Compression ---
class file_compression:
    def __init__(self):
        self.ch_freq = {}
    def file(self,chunk_size,original_file):
        self.ch_freq = {}
        with open(original_file,"rb") as f:
            while True:
                chunk=f.read(chunk_size)
                if not chunk: break
                for i in chunk:
                    self.ch_freq[i]=self.ch_freq.get(i,0)+1
        with open("dp_1_frequency.json","w") as f:
            json.dump({str(k):v for k,v in self.ch_freq.items()}, f, indent=4)
    def convert_heap(self):
        min_heap=[Node(count,ch) for ch,count in self.ch_freq.items()]
        heapq.heapify(min_heap)
        return min_heap
    def build_huffman_tree(self):
        min_heap=self.convert_heap()
        if not min_heap: return None
        while len(min_heap)>1:
            node1=heapq.heappop(min_heap)
            node2=heapq.heappop(min_heap)
            heapq.heappush(min_heap,Node(node1.freq+node2.freq,None,node1,node2))
        return min_heap[0]
    def generate_codes(self, root=None):
        if root is None:
            root = self.build_huffman_tree()
        codes={}
        if root is None:
            self.codes=codes
            return codes
        def dfs(node,prefix):
            if node is None: return
            if node.char is not None:
                codes[node.char] = prefix if prefix != "" else "0"
                return
            dfs(node.left,prefix+"0")
            dfs(node.right,prefix+"1")
        dfs(root,"")
        self.codes=codes
        return codes
    def build_bitstring(self, input_path):
        if not getattr(self,'codes',None):
            raise ValueError("Codes not generated.")
        parts=[]
        with open(input_path,"rb") as f:
            data=f.read()
        for b in data:
            parts.append(self.codes[b])
        return "".join(parts)
    @staticmethod
    def pad_bitstring(bitstring):
        padding=(8-(len(bitstring)%8))%8
        if padding: bitstring+="0"*padding
        return bitstring,padding
    @staticmethod
    def bits_to_bytes(bitstring):
        out=bytearray()
        for i in range(0,len(bitstring),8):
            out.append(int(bitstring[i:i+8],2))
        return bytes(out)
    def write_huff_file(self,input_file,out_path="dp_1.huff",compress_header=True):
        bitstring=self.build_bitstring(input_file)
        bitstring_padded,padding=self.pad_bitstring(bitstring)
        payload_bytes=self.bits_to_bytes(bitstring_padded)
        header_dict={str(k):v for k,v in self.codes.items()}
        header_bytes=json.dumps(header_dict).encode("utf-8")
        flag=0
        if compress_header:
            try:
                compressed=zlib.compress(header_bytes)
                if len(compressed)<len(header_bytes):
                    header_bytes=compressed
                    flag=1
            except: flag=0
        header_len=len(header_bytes)
        with open(out_path,"wb") as f:
            f.write(header_len.to_bytes(4,"big"))
            f.write(bytes([flag]))
            f.write(header_bytes)
            f.write(bytes([padding]))
            f.write(payload_bytes)
        return out_path

# --- Decompression ---
class file_decompression:
    def Read_header(self,huffman_file):
        with open(huffman_file,"rb") as f:
            data=f.read()
        header_len=int.from_bytes(data[:4],"big")
        flag=data[4]
        header_start=5
        header_end=header_start+header_len
        header_bytes=data[header_start:header_end]
        if flag==1:
            header_json=zlib.decompress(header_bytes).decode("utf-8")
        else:
            header_json=header_bytes.decode("utf-8")
        codes=json.loads(header_json)
        padding_len=data[header_end]
        compressed_data=data[header_end+1:]
        return codes,compressed_data,padding_len
    def Re_build_huffman(self,codes):
        root=Node(0)
        for char_code,huff_code in codes.items():
            current=root
            byte_val=int(char_code)
            for bit in huff_code:
                if bit=="0":
                    if current.left is None:
                        current.left=Node(0)
                    current=current.left
                else:
                    if current.right is None:
                        current.right=Node(0)
                    current=current.right
            current.char=byte_val
        return root
    def bytes_to_bitstring(self,compressed_data,padding_len):
        parts=[format(byte,'08b') for byte in compressed_data]
        bitstring="".join(parts)
        if padding_len>0:
            bitstring=bitstring[:-padding_len]
        return bitstring
    def decompress(self,root,bitstring):
        decoded=[]
        current_node=root
        for bit in bitstring:
            current_node=current_node.left if bit=="0" else current_node.right
            if current_node.char is not None:
                decoded.append(current_node.char)
                current_node=root
        return decoded
    def write_decoded_file(self,decoded_bytes,output_file):
        with open(output_file,"wb") as f:
            f.write(bytes(decoded_bytes))

# --- GUI ---
class HuffmanGUI(tk.Tk):
    SKIP_EXT={'.png','.jpg','.jpeg','.pdf','.zip','.gz','.rar','.7z'}
    def __init__(self):
        super().__init__()
        self.title("Huffman Compression Tool")
        self.geometry("1300x750")
        self.config(bg="#f5f0e1")  # original background
        self.file_path=None
        self.huff_file_path=None
        self.progress_value=tk.IntVar(value=0)
        self.create_widgets()

    def create_widgets(self):
        # Heading
        tk.Label(self, text="-|- BIT SQUASH -|-", font=("Segoe UI", 26, "bold"),
                 fg="#4b0082", bg="#f5f0e1").pack(anchor="w", padx=20, pady=12)

        # Buttons Frame
        btn_frame = tk.Frame(self, bg="#f5f0e1")
        btn_frame.pack(fill="x", padx=20, pady=6)

        # Left buttons
        left_buttons = [
            ("📄 Browse TXT", "#9b59b6","#6a1b9a", self.load_txt),
            ("📊 Browse CSV", "#8e44ad","#5b0e8a", self.load_csv),
            ("📁 Browse Any File", "#ab47bc","#7a2a9a", self.browse_file),
            ("🔒 Compress", "#5a2a83","#3b0e60", self.compress_action)
        ]

        # Right buttons
        right_buttons = [
            ("📂 Browse Huff", "#6a1b9a","#4b0073", self.browse_huff),
            ("📥 Decompress", "#7b4fa3","#4e2d78", self.do_decompress)
        ]

        # Add left buttons
        for text,color,dark,cmd in left_buttons:
            btn=tk.Button(btn_frame,text=text,bg=color,fg="white",
                          font=("Segoe UI",11,"bold"),width=18,bd=0,relief="raised",
                          command=cmd)
            btn.pack(side="left", padx=6, pady=4)
            btn.bind("<Enter>", lambda e,b=btn,d=dark: b.config(bg=d))
            btn.bind("<Leave>", lambda e,b=btn,c=color: b.config(bg=c))

        # Add right buttons
        for text,color,dark,cmd in right_buttons:
            btn=tk.Button(btn_frame,text=text,bg=color,fg="white",
                          font=("Segoe UI",11,"bold"),width=18,bd=0,relief="raised",
                          command=cmd)
            btn.pack(side="right", padx=6, pady=4)
            btn.bind("<Enter>", lambda e,b=btn,d=dark: b.config(bg=d))
            btn.bind("<Leave>", lambda e,b=btn,c=color: b.config(bg=c))

        # Panels
        # --- Panels Frame ---
        panels_frame = tk.Frame(self, bg="#f5f0e1")
        panels_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Left Panel (Original Text)
        left_panel = tk.LabelFrame(panels_frame, text="Original Text",
                                   fg="#4b0082", bg="#fff", font=("Segoe UI", 12, "bold"))
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=6)
        panels_frame.grid_columnconfigure(0, weight=2)
        panels_frame.grid_rowconfigure(0, weight=1)

        scroll_orig = tk.Scrollbar(left_panel)
        scroll_orig.pack(side="right", fill="y")
        self.text_original = tk.Text(left_panel, wrap="word", bg="#fff", fg="#000", font=("Consolas", 11),
                                     yscrollcommand=scroll_orig.set)
        self.text_original.pack(fill="both", expand=True, padx=6, pady=6)
        scroll_orig.config(command=self.text_original.yview)

        # Right Panel (Encoded Preview + Tree + Ratio)
        right_panel = tk.Frame(panels_frame, bg="#f5f0e1")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=6)
        panels_frame.grid_columnconfigure(1, weight=3)
        right_panel.grid_rowconfigure(0, weight=20)  # Encoded Preview
        right_panel.grid_rowconfigure(1, weight=20)  # Huffman Tree
        right_panel.grid_rowconfigure(2, weight=1)  # Ratio Stats

        # Encoded Preview
        enc_group = tk.LabelFrame(right_panel, text="Encoded Preview (first 1k chars)",
                                  fg="#4b0082", bg="#fff", font=("Segoe UI", 12, "bold"))
        enc_group.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        scroll_enc = tk.Scrollbar(enc_group)
        scroll_enc.pack(side="right", fill="y")
        self.text_encoded = tk.Text(enc_group, wrap="none", bg="#f0e6fa", fg="#2c003e", font=("Consolas", 11),
                                    yscrollcommand=scroll_enc.set)
        self.text_encoded.pack(fill="both", expand=True, padx=6, pady=6)
        scroll_enc.config(command=self.text_encoded.yview)

        # Huffman Tree
        tree_group = tk.LabelFrame(right_panel, text="Huffman Tree (ASCII preview)",
                                   fg="#4b0082", bg="#fff", font=("Segoe UI", 12, "bold"))
        tree_group.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        scroll_tree = tk.Scrollbar(tree_group)
        scroll_tree.pack(side="right", fill="y")
        self.text_tree = tk.Text(tree_group, wrap="none", bg="#fff", fg="#000", font=("Consolas", 11),
                                 yscrollcommand=scroll_tree.set)
        self.text_tree.pack(fill="both", expand=True, padx=6, pady=6)
        scroll_tree.config(command=self.text_tree.yview)

        # Ratio Stats (BELOW Huffman Tree)
        ratio_panel = tk.LabelFrame(right_panel, text="Ratio Stats",
                                    fg="#4b0082", bg="#e6d4f0", font=("Segoe UI", 12, "bold"))
        ratio_panel.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        self.lbl_original_size = tk.Label(ratio_panel, text="Original: -", bg="#e6d4f0", font=("Segoe UI", 12, "bold"))
        self.lbl_original_size.pack(padx=6, pady=2, anchor="w")
        self.lbl_compressed_size = tk.Label(ratio_panel, text="Compressed: -", bg="#e6d4f0",
                                            font=("Segoe UI", 12, "bold"))
        self.lbl_compressed_size.pack(padx=6, pady=2, anchor="w")
        self.lbl_ratio_value = tk.Label(ratio_panel, text="Saved: -", bg="#e6d4f0", fg="#4b0082",
                                        font=("Segoe UI", 16, "bold"))
        self.lbl_ratio_value.pack(padx=6, pady=6, anchor="w")




        # Progress + Status
        info_frame = tk.Frame(self, bg="#f5f0e1")
        info_frame.pack(fill="x", padx=20, pady=6)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=20, troughcolor="#fff", background="#6a1b9a")
        self.progress=ttk.Progressbar(info_frame, variable=self.progress_value, maximum=100, style="TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True, padx=6)
        self.lbl_status=tk.Label(info_frame, text="Status: Ready", bg="#f5f0e1", fg="#555", font=("Segoe UI",11))
        self.lbl_status.pack(side="left", padx=6)

    # --- Loaders, Compression, Decompression Methods ---
    def browse_file(self):
        file = filedialog.askopenfilename(title="Select File")
        self.load_file(file)
    def load_txt(self):
        file = filedialog.askopenfilename(title="Select TXT", filetypes=[("Text files","*.txt")])
        self.load_file(file)
    def load_csv(self):
        file = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files","*.csv")])
        self.load_file(file)
    def load_file(self,file):
        if file:
            self.file_path = file
            self.lbl_status.config(text=f"Selected {os.path.basename(file)}")
            try:
                with open(file,"r",errors="ignore") as f:
                    text=f.read()
            except:
                text=f"Binary or non-text content: {os.path.basename(file)}"
            self.text_original.delete("1.0",tk.END)
            self.text_original.insert(tk.END,text)

    def browse_huff(self):
        file=filedialog.askopenfilename(title="Select Huff File", filetypes=[("Huff files","*.huff")])
        if file:
            self.huff_file_path=file
            self.lbl_status.config(text=f"Huff selected: {os.path.basename(file)}")
            try:
                with open(file,"rb") as f:
                    data=f.read()
                self.text_original.delete("1.0",tk.END)
                self.text_original.insert(tk.END,str(data[:1000]))
            except:
                pass

    def compress_action(self):
        if not self.file_path:
            self.lbl_status.config(text="Select a file first")
            return
        self.progress_value.set(0); self.update()
        try:
            _, ext=os.path.splitext(self.file_path)
            ext=ext.lower()
            if ext==".huff":
                messagebox.showwarning("Already Compressed","This file is already a Huffman file.")
                return
            compressor=file_compression()
            compressor.file(4096,self.file_path)
            root=compressor.build_huffman_tree()
            codes=compressor.generate_codes(root)
            out_file=os.path.splitext(self.file_path)[0]+".huff"
            compressor.write_huff_file(self.file_path,out_file,compress_header=True)
            bitstring=compressor.build_bitstring(self.file_path)
            self.text_encoded.delete("1.0",tk.END)
            self.text_encoded.insert(tk.END,bitstring[:1000])
            self.text_tree.delete("1.0",tk.END)
            self.text_tree.insert(tk.END,"\n".join([f"{k}:{v}" for k,v in sorted(codes.items(), key=lambda x:(len(x[1]),x[1]))]))
            orig_size=os.path.getsize(self.file_path)
            comp_size=os.path.getsize(out_file)
            saved_percent = 100*(1 - comp_size/orig_size) if orig_size else 0
            self.lbl_original_size.config(text=f"Original: {orig_size} bytes")
            self.lbl_compressed_size.config(text=f"Compressed: {comp_size} bytes")
            self.lbl_ratio_value.config(text=f"Saved: {saved_percent:.2f}%" if saved_percent>=0 else f"Expansion: {abs(saved_percent):.2f}%")
            self.progress_value.set(100)
            self.lbl_status.config(text=f"Compression complete — {os.path.basename(out_file)}")
            messagebox.showinfo("Compression Successful", f"File saved:\n{out_file}")
        except Exception as e:
            self.lbl_status.config(text=f"Error: {e}")
            self.progress_value.set(0)

    def do_decompress(self):
        if not self.huff_file_path:
            self.lbl_status.config(text="No Huff file selected. Use 'Browse Huff' first.")
            return
        try:
            decompressor=file_decompression()
            codes,compressed_data,padding_len=decompressor.Read_header(self.huff_file_path)
            root=decompressor.Re_build_huffman(codes)
            bitstring=decompressor.bytes_to_bitstring(compressed_data,padding_len)
            decoded_list=decompressor.decompress(root,bitstring)
            suggested=os.path.splitext(os.path.basename(self.huff_file_path))[0]+"_decoded"
            try: _=bytes(decoded_list).decode("utf-8"); suggested+=".txt"
            except: suggested+=".bin"
            out_path=filedialog.asksaveasfilename(title="Save decompressed file as",
                                                  initialfile=suggested,
                                                  defaultextension=os.path.splitext(suggested)[1],
                                                  filetypes=[("All files","*.*")])
            if not out_path:
                self.lbl_status.config(text="Decompression cancelled.")
                return
            decompressor.write_decoded_file(decoded_list,out_path)
            try: decoded_text=bytes(decoded_list).decode("utf-8",errors="ignore")
            except: decoded_text=str(decoded_list[:1000])
            self.text_original.delete("1.0",tk.END)
            self.text_original.insert(tk.END,decoded_text)
            self.lbl_status.config(text=f"Decompressed successfully: {os.path.basename(out_path)}")
            messagebox.showinfo("Decompression Successful", f"File saved:\n{out_path}")
        except Exception as e:
            self.lbl_status.config(text=f"Error: {e}")

if __name__=="__main__":
    app = HuffmanGUI()
    app.mainloop()
