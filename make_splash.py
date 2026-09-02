from PIL import Image, ImageDraw, ImageFont

W, H = 420, 260
BG = (30, 30, 46)
ACCENT = (120, 170, 255)
TEXT = (235, 235, 245)
SUBTEXT = (160, 165, 185)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)


def load_font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


title_font = load_font("segoeuib.ttf", 30)
sub_font = load_font("segoeui.ttf", 15)

draw.rectangle([0, 0, W - 1, 5], fill=ACCENT)

title = "iOS Log Viewer"
bbox = draw.textbbox((0, 0), title, font=title_font)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) / 2, 100), title, font=title_font, fill=TEXT)

sub = "Загрузка..."
bbox = draw.textbbox((0, 0), sub, font=sub_font)
sw = bbox[2] - bbox[0]
draw.text(((W - sw) / 2, 150), sub, font=sub_font, fill=SUBTEXT)

img.save(r"D:\VS Code\Projects\iOS_Logger\splash.png")
print("saved")
