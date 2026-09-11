def setup_security_headers(app):
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissive enough for Tailwind CDN, Chart.js, QRCode CDN, Google Fonts, and inline scripts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' https: data: blob:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:;"
        )
        return response
