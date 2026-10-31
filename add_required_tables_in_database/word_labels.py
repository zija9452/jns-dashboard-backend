# One big centered word per label: python word_labels.py "Light House=15" "Karimabad=15"
import sys
import win32print

PRINTER = "ZDesigner GX420d"

for arg in sys.argv[1:]:
    text, _, n = arg.rpartition("=")
    zpl = f"^XA^FO10,80^A0N,55,55^FB400,1,0,C^FD{text}^FS^XZ"
    h = win32print.OpenPrinter(PRINTER)
    try:
        win32print.StartDocPrinter(h, 1, (text, None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, (zpl * int(n)).encode("ascii"))
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)
    print(f"Sent {n} x {text}")
