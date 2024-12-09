# 🖨  ESC/POS Printer Emulator
A ESC/POS Printer Emulator written in Python.

## Installation
1. Download the printer_emulator.py file on your OS
2. Make sure that no other process are listening to port 9100
   In a terminal:
   - List all processes listening on port 9100: lsof -i :9100
   - Kill all processes using port 9100: sudo kill XXXXX
3. Run the script: python3 printer_emulator.py
4. You can now print in your emulator sending the raw datas like for a normal thermal printer using your computer IP and port 9100.

## Limitations
As of now, it is not possible to:
- Print images
- Print big/small characters
- Some others limitations not checked as of now

## Contribution
We are of course open to any contribution helping make this software better ;)
