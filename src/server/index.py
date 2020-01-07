"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from index.index import Index
import logging
import json
import urllib.parse

# index object
index = Index()
index.summary()

class S(BaseHTTPRequestHandler):

    def _set_response_ok(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        json_string = json.dumps(content)
        self.wfile.write(json_string.encode('utf-8'))

    def _set_response_error(self, content):
        self.send_response(403)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        json_string = json.dumps(content)
        self.wfile.write(json_string.encode('utf-8'))

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))

        # read parameters
        s = self.path
        parameters = urllib.parse.parse_qs(s[2:])
        if 'search' in parameters:
            search = parameters['search']

            print(search[0])

            res = index.search(search[0])

            self._set_response_ok(res)
        else:
            self._set_response_error({'message': 'Search string is necessary'})


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()