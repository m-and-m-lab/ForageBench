#!/usr/bin/env python3
"""Regenerate the QR code (standalone asset for slides/poster; not shown on the page).
    python scripts/make_qr.py "https://m-and-m-lab.github.io/ForageBench/"
Writes assets/qr/project_qr.png. Run from the repo root. NOTE: the URL path is
case-sensitive on GitHub Pages -- it must match the repo name exactly."""
import os, sys, qrcode
from qrcode.constants import ERROR_CORRECT_H
URL = sys.argv[1] if len(sys.argv) > 1 else "https://m-and-m-lab.github.io/ForageBench/"
qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=16, border=4)
qr.add_data(URL); qr.make(fit=True)
os.makedirs("assets/qr", exist_ok=True)
qr.make_image(fill_color=(31,81,53), back_color=(255,255,255)).convert("RGB").save("assets/qr/project_qr.png")
print("Wrote assets/qr/project_qr.png ->", URL)
