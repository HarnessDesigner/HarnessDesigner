
import wx
import io
from PIL import Image
from wx.lib.embeddedimage import PyEmbeddedImage


def bytes_data_2_wx_bitmap(data: bytes) -> wx.Bitmap:
    return wx.Bitmap.FromPNGData(data)


def bytes_data_2_wx_image(data: bytes) -> wx.Image:
    return bytes_data_2_wx_bitmap(data).ConvertToImage()


def bytes_data_2_pil_image(data: bytes) -> Image.Image:
    buf = io.BytesIO(data)
    buf.seek(0)
    img = Image.open(buf).convert('RGBA')
    buf.close()
    return img


def wx_bitmap_2_pil_image(bmp: wx.Bitmap) -> Image.Image:
    return wx_image_2_pil_image(wx_bitmap_2_wx_image(bmp))


def wx_image_2_wx_bitmap(wx_img: wx.Image) -> wx.Bitmap:
    return wx_img.ConvertToBitmap()


def wx_bitmap_2_wx_image(bmp: wx.Bitmap) -> wx.Image:
    return bmp.ConvertToImage()


def pil_image_2_wx_bitmap(img: Image.Image) -> wx.Bitmap:
    return wx_image_2_wx_bitmap(pil_image_2_wx_image(img))


def pil_image_2_wx_image(img: Image.Image) -> wx.Image:
    rgb_data = img.convert('RGB').tobytes()
    alpha_data = img.convert('RGBA').tobytes()[3::4]
    return wx.Image(img.size[0], img.size[1], rgb_data, alpha_data)


def wx_image_2_pil_image(wx_img: wx.Image) -> Image.Image:
    rgb_data = bytes(wx_img.GetDataBuffer())
    alpha_data = wx_img.GetAlphaBuffer()
    if alpha_data is not None:
        alpha_img = Image.new('L', (wx_img.GetWidth(), wx_img.GetHeight()))
        alpha_img.frombytes(bytes(alpha_data))

    img = Image.new('RGB', (wx_img.GetWidth(), wx_img.GetHeight()))
    img.frombytes(rgb_data)
    img = img.convert('RGBA')
    if alpha_data is not None:
        img.putalpha(alpha_img)
        alpha_img.close()

    return img


def resize_wx_bitmap(bmp: wx.Bitmap, width: int, height: int = None) -> wx.Bitmap:
    img = wx_bitmap_2_pil_image(bmp)
    if height is None:
        height = int(width * (img.size[1] / img.size[0]))

    ret = img.resize((width, height), resample=Image.Resampling.LANCZOS)
    img.close()
    return pil_image_2_wx_bitmap(ret)


def rotate_wx_bitmap(bmp: wx.Bitmap, angle: float) -> wx.Bitmap:
    img = wx_bitmap_2_pil_image(bmp)
    ret = img.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    img.close()
    return pil_image_2_wx_bitmap(ret)


def rotate_wx_image(wx_img: wx.Image, angle: float) -> wx.Image:
    img = wx_image_2_pil_image(wx_img)
    ret = img.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    img.close()
    return pil_image_2_wx_image(ret)


def wx_image_2_wx_cursor(wx_img: wx.Image, hotspot_x: int | None = None,
                          hotspot_y: int | None = None) -> wx.Cursor:

    if hotspot_x is None:
        hotspot_x = int(wx_img.GetWidth() / 2)
    if hotspot_y is None:
        hotspot_y = int(wx_img.GetHeight() / 2)

    wx_img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot_x)
    wx_img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot_y)

    return wx.Cursor(wx_img)


def pil_image_2_png_bytes(img: Image):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    data = buf.getvalue()
    buf.close()
    return data


def wx_bitmap_2_png_bytes(wx_bmp: wx.Bitmap) -> bytes:
    img = wx_bitmap_2_pil_image(wx_bmp)
    data = pil_image_2_png_bytes(img)
    img.close()
    return data


def wx_image_2_png_bytes(wx_img: wx.Image) -> bytes:
    img = wx_image_2_pil_image(wx_img)
    data = pil_image_2_png_bytes(img)
    img.close()
    return data


