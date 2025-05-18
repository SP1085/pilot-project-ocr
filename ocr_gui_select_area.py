import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pytesseract
import cv2
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Global Variables ===
image_path = None
cv_image = None
start_x = start_y = end_x = end_y = 0
rect_id = None

# === เปิดรูปภาพ ===
def select_image():
    global image_path, cv_image
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    if file_path:
        image_path = file_path
        cv_image = cv2.imread(image_path)
        show_image(cv_image)

# === แสดงภาพใน Canvas ===
def show_image(img):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    pil_img = pil_img.resize((600, 400))
    tk_img = ImageTk.PhotoImage(pil_img)
    canvas.image = tk_img
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

# === การลากเมาส์เพื่อเลือกพื้นที่ OCR ===
def on_mouse_down(event):
    global start_x, start_y
    start_x = event.x
    start_y = event.y
    clear_rectangle()

def on_mouse_drag(event):
    global rect_id
    clear_rectangle()
    rect_id = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline="red", width=2)

def on_mouse_up(event):
    global end_x, end_y
    end_x = event.x
    end_y = event.y
    perform_ocr()

def clear_rectangle():
    global rect_id
    if rect_id:
        canvas.delete(rect_id)
        rect_id = None

# === ส่งข้อความไปยัง Google Sheets ===
def send_to_google_sheets(text):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("your-service-account.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("OCR Logs").sheet1  # แก้ชื่อ Google Sheet ตรงนี้ถ้าจำเป็น
        sheet.append_row([text])
    except Exception as e:
        messagebox.showerror("เกิดข้อผิดพลาด", f"ส่งข้อมูลไม่สำเร็จ: {e}")

# === ทำ OCR และส่งผลลัพธ์ ===
def perform_ocr():
    if cv_image is None:
        messagebox.showwarning("ยังไม่ได้เปิดภาพ", "กรุณาเลือกรูปภาพก่อน")
        return

    x_scale = cv_image.shape[1] / 600
    y_scale = cv_image.shape[0] / 400

    x1 = int(min(start_x, end_x) * x_scale)
    y1 = int(min(start_y, end_y) * y_scale)
    x2 = int(max(start_x, end_x) * x_scale)
    y2 = int(max(start_y, end_y) * y_scale)

    x1, x2 = max(0, x1), min(cv_image.shape[1], x2)
    y1, y2 = max(0, y1), min(cv_image.shape[0], y2)

    if x2 <= x1 or y2 <= y1:
        messagebox.showwarning("ตำแหน่งไม่ถูกต้อง", "กรุณาเลือกใหม่")
        return

    cropped = cv_image[y1:y2, x1:x2]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    # ปรับภาพให้อ่านชัดขึ้น
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    _, gray = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

    # OCR
    text = pytesseract.image_to_string(gray, lang='tha+eng')
    result_text.set(text.strip())
    print("OCR Text:", text.strip())

    # ส่งไปยัง Google Sheets
    send_to_google_sheets(text.strip())

# === GUI ===
window = tk.Tk()
window.title("OCR + ส่ง Google Sheets")
window.geometry("700x600")

tk.Button(window, text="เลือกรูปภาพ", command=select_image).pack(pady=10)

canvas = tk.Canvas(window, width=600, height=400, bg="gray")
canvas.pack()
canvas.bind("<Button-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_drag)
canvas.bind("<ButtonRelease-1>", on_mouse_up)

result_text = tk.StringVar()
tk.Label(window, text="ข้อความที่อ่านได้:", font=("Arial", 12)).pack(pady=5)
tk.Label(window, textvariable=result_text, font=("Arial", 14), fg="blue", wraplength=600).pack()

window.mainloop()
