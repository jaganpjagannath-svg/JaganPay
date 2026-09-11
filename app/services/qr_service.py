import io
import base64
import urllib.parse


def build_upi_string(upi_id: str, name: str, amount: float = None, note: str = None) -> str:
    """Build standardized UPI payment URI string."""
    params = {
        "pa": upi_id.strip(),
        "pn": name.strip(),
        "cu": "INR",
        "mode": "02",
        "orgid": "189999",
    }
    if amount and amount > 0:
        params["am"] = f"{amount:.2f}"
    if note:
        params["tn"] = note.strip()

    return "upi://pay?" + urllib.parse.urlencode(params)


def generate_qr_base64(data: str) -> str:
    """Generate a Base64 PNG QR code from payload."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0a0f24", back_color="#ffffff")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        # Fallback to public QR generator API representation or SVG placeholder
        encoded_payload = urllib.parse.quote(data)
        return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_payload}"
