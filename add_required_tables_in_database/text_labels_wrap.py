# Wrapped text label (up to 3 lines, centered): python text_labels_wrap.py "Some long text=1"
import sys
import win32print

PRINTER = "ZDesigner GX420d"
for arg in sys.argv[1:]:
    text, _, n = arg.rpartition("=")
    zpl = f"^XA^FO10,45^A0N,34,34^FB400,3,6,C^FD{text}^FS^XZ"
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
