#!/usr/bin/env python

import http.server
import json
import os
import subprocess
import sys
import tempfile

import multipart
import pytesseract
import yattag

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def path_query(self):
        if '?' in self.path:
            path, query = self.path.split('?', maxsplit=1)
            return (path, query)
        else:
            return (self.path, '')

    def read_content(self):
        content_length = int(self.headers['Content-Length'])
        return self.rfile.read(content_length)

    def do_POST(self):
        path, query = self.path_query()

        handlers = {
            '/selfupgrade': self.selfupgrade_POST,
            '/tesseract': self.tesseract_POST,
            '/uppercase': self.uppercase_POST,
        }

        try:
            handlers[path]()
        except KeyError:
            self.send_error(code=404)

    def selfupgrade_POST(self):
        pull = subprocess.run(['git', 'pull'], capture_output=True)
        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='text/plain')
        self.end_headers()
        self.wfile.write(f'Exit code: {pull.returncode}\n'.encode('utf-8'))
        self.wfile.write(f'stdout:\n{pull.stdout}\n'.encode('utf-8'))
        self.wfile.write(f'stderr:\n{pull.stderr}\n'.encode('utf-8'))
        if pull.stdout == b'Already up to date.\n':
            self.wfile.write(b'Nothing to do.')
        else:
            self.wfile.write(b'Restarting...')
            sys.exit(0)

    def parse_multipart_content_type(self):
        try:
            content_type, boundary = self.headers['Content-Type'].split(';', maxsplit=1)
        except ValueError:
            self.send_error(code=400)
            return

        if content_type != 'multipart/form-data':
            self.send_error(code=415)
            return

        k, v = boundary.split('=', maxsplit=1)
        if k.strip() != 'boundary':
            self.send_error(code=400)
            return

        return v

    def tesseract_POST(self):
        boundary = self.parse_multipart_content_type()
        if boundary is None:
            return
        mp = multipart.MultipartParser(
            stream=self.rfile,
            boundary=boundary,
            content_length=int(self.headers['Content-Length']),
        )
        (image,) = mp.get_all(name='image')

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(image.raw)
            data = [
                line.split('\t')
                for line in pytesseract.image_to_data(tmp.name).splitlines()
            ]

        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='text/html')
        self.end_headers()

        doc = yattag.Doc()
        doc.asis('<!DOCTYPE html>\n')
        with doc.tag('html'):
            with doc.tag('head'):
                doc.stag('meta', charset='UTF-8')
                with doc.tag('title'):
                    doc.text('Tesseract API')
                with doc.tag('style', type='text/css'):
                    doc.text('table, td { border: 1px solid black; }')

            with doc.tag('body'):
                with doc.tag('table'):
                    with doc.tag('thead'):
                        with doc.tag('tr'):
                            for header in data[0]:
                                with doc.tag('td'):
                                    doc.text(header)
                    with doc.tag('tbody'):
                        for line in data[1:]:
                            with doc.tag('tr'):
                                for field in line:
                                    with doc.tag('td'):
                                        doc.text(field)

        self.wfile.write(doc.getvalue().encode('utf-8'))

    def uppercase_POST(self):
        if self.headers['Content-Type'] != 'application/json':
            self.send_error(code=415)
            return

        body = json.loads(self.read_content())
        q = body['q']
        response_json = {'r': q.upper()}
        response = json.dumps(response_json).encode('utf-8')

        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='application/json')
        self.send_header(keyword='Content-Length', value=str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def tesseract_GET_HEAD(self, only_head: bool):
        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='text/html')
        self.end_headers()

        if only_head:
            return

        doc = yattag.Doc()
        doc.asis('<!DOCTYPE html>\n')
        with doc.tag('html'):
            with doc.tag('head'):
                doc.stag('meta', charset='UTF-8')
                with doc.tag('title'):
                    doc.text('Tesseract API')

            with doc.tag('body'):
                with doc.tag('form', method='POST', enctype='multipart/form-data'):
                    doc.stag('input', name='image', type='file')
                    doc.stag('input', type='submit')

        self.wfile.write(doc.getvalue().encode('utf-8'))

    def root_GET_HEAD(self, only_head: bool):
        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='text/html')
        self.end_headers()

        if only_head:
            return

        self.wfile.write(b'''<!DOCTYPE html>
        <html>
        <head><title>API landing page</title></head>
        <body>This is just to confirm you've reached the server.</body>
        </html>
        ''')

    def do_GET_HEAD(self, only_head: bool):
        path, query = self.path_query()

        handlers = {
            '/tesseract': self.tesseract_GET_HEAD,
            '/': self.root_GET_HEAD,
        }

        try:
            handlers[path](only_head=only_head)
        except KeyError:
            self.send_error(code=404)

    def do_GET(self):
        self.do_GET_HEAD(only_head=False)

    def do_HEAD(self):
        self.do_GET_HEAD(only_head=True)

port = int(os.environ.get('PORT', '8080'))
httpd = http.server.HTTPServer(('', port), RequestHandler)
httpd.serve_forever()
