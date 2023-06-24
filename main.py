#!/usr/bin/env python

import http.server
import json
import os
import subprocess
import sys

import pytesseract

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def path_query(self):
        if '?' in self.path:
            path, query = self.path.split('?', maxsplit=1)
            return (path, query)
        else:
            return (self.path, '')

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

    def tesseract_POST(self):
        self.send_response(code=501)

    def uppercase_POST(self):
        if self.headers['Content-Type'] != 'application/json':
            self.send_error(code=415)
            return

        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))
        q = body['q']
        response_json = {'r': q.upper()}
        response = json.dumps(response).encode('utf-8')

        self.send_response(code=200)
        self.send_header(keyword='Content-Type', value='application/json')
        self.send_header(keyword='Content-Length', value=str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def tesseract_GET_HEAD(self, only_head: bool):
        self.send_response(code=404)

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
