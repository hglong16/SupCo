import base64
import string

from odoo import http
from odoo.http import request, route, content_disposition
import io
import qrcode
import random


class UserController(http.Controller):

    @http.route('/users/<string:national_id>', type='http', auth="public", website=True)
    def user_info(self, national_id):
        user = request.env['res.users'].sudo().search([('national_id', '=', national_id)], limit=1)

        if user:
            # Get the base URL from system parameters
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

            name = user.name
            dob = user.dob
            national_id = user.national_id
            department = user.department.name
            introduction_letter = user.introduction_letter
            position = user.function
            avatar = user.image_1920.decode("utf-8") if user.image_1920 else None

            # Use the base URL to generate QR code dynamically
            qr = qrcode.QRCode()
            qr.add_data(f"{base_url}/users/{national_id}")
            f = io.StringIO()
            qr.print_ascii(out=f)
            f.seek(0)
            qr_code = f.read()

            return request.render('supco.template_name',
                                  {'name': name,
                                   'dob': dob,
                                   'national_id': national_id,
                                   'department': department,
                                   'function': position,
                                   'qr_code': qr_code,
                                   'image_1920': avatar})
        else:
            return "User not found or You have no right to access."


class LetterController(http.Controller):

    @http.route('/letters/qr/<int:letter_id>', type='http', auth="public", website=True)
    def letter_qr(self, letter_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Fetch the letter's QR code from the database
        letter = http.request.env['supreme.court.letter'].sudo().browse(letter_id)
        if not letter:
            return "Letter not found!"

        qr_code_data = base64.b64decode(letter.qr_code) if letter.qr_code else None
        if not qr_code_data:
            return "QR Code not available!"

        # Generate a unique identifier (token) for the public access
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

        # Save the QR code as a public file with a unique filename
        public_filename = f"public_letter_{letter_id}_{token}.png"
        with open(public_filename, "wb") as qr_file:
            qr_file.write(qr_code_data)

        # Generate QR code from the token
        img = qrcode.make(token)
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)

        # Update response headers to force a download prompt
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', content_disposition(public_filename))
        ]

        return http.request.make_response(buffer.getvalue(), headers=headers)