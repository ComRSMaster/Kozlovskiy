#!/usr/bin/python3
import os
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from mimetypes import guess_type
from socket import AF_INET6
from socketserver import ThreadingMixIn

from helpers.config import bot_token

token = f'/{bot_token}'


# noinspection PyUnusedLocal
def parse_updates(json_string):
    pass


class Handler(BaseHTTPRequestHandler):

    # noinspection PyPep8Naming
    def do_HEAD(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()

    # noinspection PyPep8Naming
    def do_GET(self):
        path = self.path
        if path == '/':
            path = '/index.html'
        try:
            with open('website' + path, 'rb') as f:
                self.send_response(HTTPStatus.OK)
                c_type = guess_type(path)
                self.send_header("Content-type", c_type if c_type else 'application/octet-stream')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            self.end_headers()

    # noinspection PyPep8Naming
    def do_POST(self):
        if self.path == token and 'content-type' in self.headers and 'content-length' in self.headers and \
                self.headers['content-type'] == 'application/json':
            parse_updates(self.rfile.read(int(self.headers['content-length'])).decode("utf-8"))
            self.send_response(HTTPStatus.OK)
            self.end_headers()

        else:
            self.send_error(HTTPStatus.FORBIDDEN)
            self.end_headers()


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    address_family = AF_INET6


def run_webserver():
    server = ThreadingSimpleServer((os.getenv("IP"), int(os.getenv("PORT"))), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
