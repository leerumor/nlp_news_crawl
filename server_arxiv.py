import os.path

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import logging

from tornado.options import define, options
define("port", default=8001, help="run on the given port", type=int)

class ArxivNLPHandler(tornado.web.RequestHandler):
    def get(self):
        field = "NLP"
        ua = self.request.headers['User-Agent']
        isMobile = False if ua.find("Mobile") == -1 else True
        logging.info(f"> {field} > {isMobile}")
        self.render(f'arxiv_{field}.html')

class ArxivCVHandler(tornado.web.RequestHandler):
    def get(self):
        field = "CV"
        ua = self.request.headers['User-Agent']
        isMobile = False if ua.find("Mobile") == -1 else True
        logging.info(f"> {field} > {isMobile}")
        self.render(f'arxiv_{field}.html')

class ArxivIRHandler(tornado.web.RequestHandler):
    def get(self):
        field = "IR"
        ua = self.request.headers['User-Agent']
        isMobile = False if ua.find("Mobile") == -1 else True
        logging.info(f"> {field} > {isMobile}")
        self.render(f'arxiv_{field}.html')

if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
            (r'/', ArxivNLPHandler), 
            (r'/nlp', ArxivNLPHandler),
            (r'/cv', ArxivCVHandler),
            (r'/ir', ArxivIRHandler)],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=True
    )

    # 启动为多进程模型的方法为：摒弃listen方法
    # http_server = tornado.httpserver.HTTPServer(app)
    # http_server.bind(options.port, options.host)
    # http_server.start(num_processes=0) # tornado将按照cpu核数来fork进程
    # tornado.ioloop.IOLoop.instance().start()

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()