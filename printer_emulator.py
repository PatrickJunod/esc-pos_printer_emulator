import socket
import threading
from enum import Enum
from dataclasses import dataclass

class PrinterCommand(Enum):
    ESC = 0x1B
    GS = 0x1D
    FS = 0x1C
    DLE = 0x10
    EOT = 0x04
    NUL = 0x00
    LF = 0x0A
    CR = 0x0D
    HT = 0x09
    FF = 0x0C
    CAN = 0x18

@dataclass
class PrinterState:
    chars_per_line: int = 48
    alignment: int = 0  # 0=left, 1=center, 2=right
    bold: bool = False
    underline: bool = False
    double_width: bool = False
    double_height: bool = False
    font_size: int = 1
    char_spacing: int = 0
    line_spacing: int = 30
    code_page: int = 0
    white_on_black: bool = False
    upside_down: bool = False
    emphasized: bool = False
    double_strike: bool = False
    font_b: bool = False
    italic: bool = False

class ESCPOSSimulator:
    def __init__(self, port=9100):
        self.port = port
        self.state = PrinterState()
        self.buffer = []
        self.current_line = ""

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('0.0.0.0', self.port))
            server.listen(1)
            print(f"🖨  ESC/POS Printer Simulator listening on port {self.port}")
            print(f"Characters per line: {self.state.chars_per_line}")

            while True:  # Keep accepting new connections
                try:
                    client, addr = server.accept()
                    print(f"\nNew connection from {addr}")
                    self.handle_client(client, addr)
                except Exception as e:
                    print(f"Error handling client: {e}")
                    # Continue listening even if there's an error with one client
                    continue
                
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            print("Server shutting down")
            server.close()

    def handle_client(self, client, addr):
        data_buffer = bytearray()
        try:
            while True:
                data = client.recv(1024)
                if not data:
                    break
                data_buffer.extend(data)
                
            if data_buffer:
                self.process_data(data_buffer)
                
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            client.close()

    def process_data(self, data):
        print("\nReceived data (hex):")
        print(' '.join(f'{b:02x}' for b in data))

        i = 0
        while i < len(data):
            byte = data[i]
            
            if byte == PrinterCommand.ESC.value:
                i = self.handle_esc_sequence(data, i)
            elif byte == PrinterCommand.GS.value:
                i = self.handle_gs_sequence(data, i)
            elif byte == PrinterCommand.FS.value:
                i = self.handle_fs_sequence(data, i)
            elif byte == PrinterCommand.LF.value:
                self.flush_line()
                i += 1
            elif byte == PrinterCommand.CR.value:
                i += 1
            elif 32 <= byte <= 126:  # Printable ASCII
                self.current_line += chr(byte)
                i += 1
            else:
                i += 1

        self.print_buffer()

    def handle_esc_sequence(self, data, i):
        if i + 1 >= len(data):
            return i + 1

        cmd = data[i + 1]
        if cmd == 0x40:  # ESC @ Initialize printer
            self.state = PrinterState()
            return i + 2
        elif cmd == 0x61:  # ESC a n Select justification
            if i + 2 < len(data):
                self.flush_line()
                self.state.alignment = data[i + 2] % 3
            return i + 3
        elif cmd == 0x45:  # ESC E n Turn emphasized mode on/off
            if i + 2 < len(data):
                self.state.emphasized = bool(data[i + 2])
            return i + 3
        elif cmd == 0x64:  # ESC d n Print and feed n lines
            if i + 2 < len(data):
                self.flush_line()
                for _ in range(data[i + 2]):
                    self.buffer.append("")
            return i + 3
        elif cmd == 0x24:  # ESC $ nL nH Set absolute print position
            return i + 4
        elif cmd == 0x74:  # ESC t n Select character code table
            if i + 2 < len(data):
                self.state.code_page = data[i + 2]
            return i + 3
        elif cmd == 0x21:  # ESC ! n Select print mode(s)
            if i + 2 < len(data):
                n = data[i + 2]
                self.state.font_b = bool(n & 1)
                self.state.emphasized = bool(n & 8)
                self.state.double_height = bool(n & 16)
                self.state.double_width = bool(n & 32)
            return i + 3
        
        return i + 2

    def handle_gs_sequence(self, data, i):
        if i + 1 >= len(data):
            return i + 1

        cmd = data[i + 1]
        if cmd == 0x56:  # GS V n Cut paper
            self.flush_line()
            self.buffer.append("-" * self.state.chars_per_line)
            return i + 3
        elif cmd == 0x21:  # GS ! n Select character size
            if i + 2 < len(data):
                n = data[i + 2]
                width_mag = ((n & 0x70) >> 4) + 1
                height_mag = (n & 0x07) + 1
                self.state.font_size = max(width_mag, height_mag)
            return i + 3
        
        return i + 2

    def handle_fs_sequence(self, data, i):
        if i + 1 >= len(data):
            return i + 1

        cmd = data[i + 1]
        if cmd == 0x2E:  # FS .
            return i + 2
        
        return i + 2

    def flush_line(self):
        if self.current_line:
            self.buffer.append(self.format_line(self.current_line))
            self.current_line = ""

    def format_line(self, text):
        effective_width = self.state.chars_per_line
        if self.state.double_width:
            effective_width //= 2
        if self.state.font_size > 1:
            effective_width //= self.state.font_size

        # Handle alignment
        if self.state.alignment == 1:  # Center
            text = text.center(effective_width)
        elif self.state.alignment == 2:  # Right
            text = text.rjust(effective_width)
        else:  # Left
            text = text.ljust(effective_width)

        # Handle text formatting
        if self.state.emphasized:
            text = f"\033[1m{text}\033[0m"

        # Scale for double width/height
        if self.state.double_width or self.state.font_size > 1:
            text = ' '.join(list(text))

        return text

    def print_buffer(self):
        if not self.buffer and not self.current_line:
            return

        self.flush_line()
        
        width = self.state.chars_per_line + 2
        print("\n🧾 Receipt Output:")
        print("┌" + "─" * width + "┐")
        
        for line in self.buffer:
            if line.strip():
                print(f"│ {line} │")
            else:
                print(f"│{' ' * width}│")
        
        print("└" + "─" * width + "┘")
        self.buffer = []

if __name__ == "__main__":
    simulator = ESCPOSSimulator()
    simulator.start()