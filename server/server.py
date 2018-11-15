# -*- coding: utf-8 -*-
import requests
import time
import random
import json
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
import os
import sys
import database
from tornado.options import define, options
import tornado.websocket
import datetime

# import frq_path_stat
define("port", default=22333, type=int, help = "run on the given port")

# client_file_root_path = os.path.join(os.path.split(__file__)[0],'../client')
client_file_root_path = os.path.join(os.path.split(__file__)[0],'../')
client_file_root_path = os.path.abspath(client_file_root_path)

NetworkData = database.NetworkData()



class demoMysqlHandler(tornado.web.RequestHandler):
    def post(self):
      self.set_header('Access-Control-Allow-Origin','*')  # 添加响应头，允许指定域名的跨域请求
      self.set_header("Access-Control-Allow-Headers", "X-Requested-With");  
      self.set_header("Access-Control-Allow-Methods", "PUT,POST,GET,DELETE,OPTIONS"); 
      constraint=self.get_argument('constraint')
      constraint = json.loads(constraint)
      self.write({'suc':'post success'})

    def get(self):
      self.set_header('Access-Control-Allow-Origin','*')  # 添加响应头，允许指定域名的跨域请求
      self.set_header("Access-Control-Allow-Headers", "X-Requested-With");  
      self.set_header("Access-Control-Allow-Methods", "PUT,POST,GET,DELETE,OPTIONS"); 
      params = self.get_argument('params')
      params = json.loads(params)
      print(params)
      data = NetworkData.getData(params)
      self.write(data)

# json encode for numpy ndarray and so on
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    print('server running at 127.0.0.1:%d ...'%(tornado.options.options.port))
    print(client_file_root_path)
    app = tornado.web.Application(
        handlers=[
                  (r'/demo-mysql', demoMysqlHandler),
                  # (r'/checkClassName', checkClassNameHandler),
                  # (r'/queryCarList', queryCarListHandler),
                  (r'/(.*)', tornado.web.StaticFileHandler, {'path': client_file_root_path,
                                               'default_filename': 'index.html'}) # fetch client files
                  ],
        debug=True,
    )


    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
