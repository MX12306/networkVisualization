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
import igraphLayout
import graphfunc
import networkx as nx
import json
import numpy as np
import math
import codecs
import similarityTools
import csv
import itertools
import myutil
from functools import partial
from multiprocessing import Pool
import copy

define("port", default=22333, type=int, help="run on the given port")
client_file_root_path = os.path.join(os.path.split(__file__)[0], '../')
client_file_root_path = os.path.abspath(client_file_root_path)

NetworkData = database.NetworkData()
LocalGraph = graphfunc.LocalGraph()


class getRecentDataHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")

    def get(self):
        # 时间轴获取统计数据
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = self.get_argument('params')
        params = json.loads(params)
        data = NetworkData.getDataByRecentTime(params)
        self.write({'data': data})


class getLayoutData(tornado.web.RequestHandler):
    # 计算前端选择布局后提交的数据
    def get(self):
        print("进入get")
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = self.get_argument('params')
        params = json.loads(params)
        layoutType = params['layout_type']
        networkLevel = int(params['network_level'])
        data = []
        if networkLevel != 0:
            startLevel = networkLevel * 100
            endLevel = startLevel + 100
            for item in nowSelectedData:
                if startLevel <= int(item['net_level']) < endLevel:
                    data.append(item)
        else:
            data = copy.deepcopy(nowSelectedData)
        if len(data):
            links = []
            temp_nodes = []
            nodes = []
            nodes_id = []
            start = time.clock()
            for row in data:
                source = row['trans_node_global_no']
                source_type = row['trans_node_type']
                source_palsy = row['trans_palsy_level']
                source_control = row['trans_control_level']
                target = row['recv_node_golbal_no']
                target_type = row['recv_node_type']
                target_palsy = row['recv_palsy_level']
                target_control = row['recv_control_level']
                flow = row['flow']
                link = {'source': source, 'target': target, 'flow': flow}
                temp_nodes.append({
                    'id': source,
                    'nodeType': source_type,
                    'palsy': source_palsy,
                    'control': source_control
                })
                temp_nodes.append({
                    'id': target,
                    'nodeType': target_type,
                    'palsy': target_palsy,
                    'control': target_control
                })
                links.append(link)
            for item in temp_nodes:
                if item['id'] not in nodes_id:
                    nodes_id.append(item['id'])
                    nodes.append(item)
                else:
                    index = nodes_id.index(item['id'])
                    del nodes[index]
                    del nodes_id[index]
                    nodes.append(item)
                    nodes_id.append(item['id'])

            tmp_links = []
            # 去重
            for link in links:
                key = {
                    'source': link['source'],
                    'target': link['target'],
                    'flow': 0,
                    'times': 0,
                }
                if key not in tmp_links:
                    tmp_links.append(key)

            for item in tmp_links:
                for link in links:
                    if link['source'] == item['source'] and link['target'] == item['target']:
                        item['flow'] = item['flow'] + link['flow']
                        item['times'] = item['times'] + 1
            links = tmp_links

            end = time.clock()
            diff_time = end - start
            print("spend time for build graph: " + str(diff_time))

            # 计算flow
            for node in nodes:
                flow_in = 0
                flow_out = 0
                for link in links:
                    if node['id'] == link['source']:
                        flow_out = flow_out + link['flow']
                    if node['id'] == link['target']:
                        flow_in = flow_in + link['flow']
                node['flow_in'] = flow_in
                node['flow_out'] = flow_out
                node['flow'] = flow_in + flow_out
            result = {'nodes': nodes, 'links': links}
            start = time.clock()
            result = igraphLayout.cal_back_layout_data(result, layoutType)
            end = time.clock()
            diff_time = end - start
            print("spend time for calculate layout: " + str(diff_time))
            self.write(result)
            LocalGraph.updatelocaldata(nodes, result['links'])
        else:
            result = {'nodes': [], 'links': []}
            self.write(result)

    def post(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        print('post')
        params = self.get_argument('params')
        params = json.loads(params)
        layoutType = params['layout_type']
        data = params['layoutData']
        data = json.loads(data)
        start = time.clock()
        result = igraphLayout.cal_back_layout_data(data, layoutType)
        end = time.clock()
        diff_time = end - start
        print("spend time for calculate layout: " + str(diff_time))
        # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",result['nodes'][0])
        self.write(result)


class getDim2(tornado.web.RequestHandler):
    # 获取降维数据
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        # print(params)
        type = int(params['type'])
        # type = int(json.loads(self.get_argument('type')))
        nodesobj = LocalGraph.getdim2(type)
        evt_unpacked = {
            'nodes': nodesobj,
            # 'edges': list(LocalGraph.G.edges()),
            'outlier': LocalGraph.outlierrecord
        }
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class changeOutlierType(tornado.web.RequestHandler):
    # 改变检测outlier的方法
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        type = int(params['type'])
        LocalGraph.outliertype = type
        evt_unpacked = {}
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class getAttr(tornado.web.RequestHandler):
    # 获取指定节点的指定属性变化记录
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        nodes = json.loads(params['nodes'])
        tmpattr, nodesattr = LocalGraph.getAttr(nodes)
        evt_unpacked = {
            "attr": tmpattr,
            'nodes': nodesattr,
            "start": LocalGraph.rangestart,
            "end": LocalGraph.rangeend
        }
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class choosenone(tornado.web.RequestHandler):
    # 获取指定节点的指定属性变化记录
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        LocalGraph.choosenone()
        evt_unpacked = {}
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class gettree(tornado.web.RequestHandler):
    # 获取指定节点的指定属性变化记录
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        nodes = params['nodes']
        evt_unpacked = LocalGraph.singlesel(nodes)
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class getSPs(tornado.web.RequestHandler):
    # 获取指定节点的指定属性变化记录
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        nodes = params['nodes']
        evt_unpacked = LocalGraph.multisel(nodes)
        # print(evt_unpacked)
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class getFlow(tornado.web.RequestHandler):
    # 获取指定节点的指定属性变化记录
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        nodes = json.loads(params['nodes'])
        evt_unpacked = LocalGraph.flowdist(nodes)
        # print(evt_unpacked)
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class getData2(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        print('params', params)
        timeRange = json.loads(params['data'])
        print('timeRange', timeRange)
        global nowSelectedData
        start = time.clock()
        nowSelectedData = NetworkData.getTimeRangeData(timeRange[0],
                                                       timeRange[1])
        end = time.clock()
        diff_time = end - start
        print("spend time for get timeline data: " + str(diff_time))
        evt_unpacked = {'message': 'timeRangeData', 'data': nowSelectedData}
        evt = json.dumps(evt_unpacked)
        self.write(evt)
        LocalGraph.rangestart = LocalGraph.linuxtimestamp(timeRange[0])
        LocalGraph.rangeend = LocalGraph.linuxtimestamp(timeRange[1])


class getAnomalyLayoutData(tornado.web.RequestHandler):
    # 读取异常数据并且计算布局
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        links = []
        nodes = []
        temp_nodes = []
        nodes_id = []
        tmp_links = []

        data = NetworkData.getAnomalyData("event2")

        for row in data:
            source = row['trans_node_global_no']
            target = row['recv_node_golbal_no']
            flow = row['flow']
            recv_num_list = []
            recv_culster_list = []
            trans_num_list = []
            trans_culster_list = []

            for n in range(1, 31):
                recv_num_list.append({'key': 'recv_num_' + str(n), 'value': row['recv_num_' + str(n)]})
            for n in range(1, 21):
                # recv_culster_list.append(row['recv_cluster_'+str(n)])
                recv_culster_list.append({'key': 'recv_cluster_' + str(n), 'value': row['recv_cluster_' + str(n)]})

            for n in range(1, 31):
                # trans_num_list.append(row['trans_num_'+str(n)])
                trans_num_list.append({'key': 'trans_num_' + str(n), 'value': row['trans_num_' + str(n)]})
            for n in range(1, 21):
                trans_culster_list.append({'key': 'trans_cluster_' + str(n), 'value': row['trans_cluster_' + str(n)]})

            # 空值处理
            if (source != None and target != None):
                link = {'source': source, 'target': target, 'flow': flow}

                links.append(link)

                if target not in nodes_id:
                    nodes_id.append(target)
                    nodes.append(
                        {'id': target, 'flow': flow, 'flow_in': flow, 'flow_out': 0, 'attr_num_list': recv_num_list,
                         'attr_culster_list': recv_culster_list})
                else:
                    index = nodes_id.index(target)
                    temp = nodes[index]
                    temp['flow_in'] = temp['flow_in'] + flow
                    temp['flow'] = temp['flow'] + temp['flow_in']
                    del nodes_id[index]
                    del nodes[index]
                    nodes_id.append(target)
                    nodes.append(temp)

                if source not in nodes_id:
                    nodes_id.append(source)
                    nodes.append(
                        {'id': source, 'flow': flow, 'flow_in': 0, 'flow_out': flow, 'attr_num_list': trans_num_list,
                         'attr_culster_list': trans_culster_list})
                else:
                    index = nodes_id.index(source)
                    temp = nodes[index]
                    temp['flow_out'] = temp['flow_out'] + flow
                    temp['flow'] = temp['flow'] + temp['flow_out']
                    del nodes_id[index]
                    del nodes[index]
                    nodes_id.append(source)
                    nodes.append(temp)
            else:
                if source == None:
                    # temp_nodes.append({'id': target})
                    if target not in nodes_id:
                        nodes_id.append(target)
                        nodes.append(
                            {'id': target, 'flow': flow, 'flow_in': flow, 'flow_out': 0, 'attr_num_list': recv_num_list,
                             'attr_culster_list': recv_culster_list})
                    else:
                        index = nodes_id.index(target)
                        temp = nodes[index]
                        temp['flow_in'] = temp['flow_in'] + flow
                        temp['flow'] = temp['flow'] + temp['flow_in']
                        del nodes_id[index]
                        del nodes[index]
                        nodes_id.append(target)
                        nodes.append(temp)

                if target == None:
                    if source not in nodes_id:
                        nodes_id.append(source)
                        # nodes.append({'id': source,'flow':flow,'flow_in':0,'flow_out':flow})
                        nodes.append({'id': source, 'flow': flow, 'flow_in': 0, 'flow_out': flow,
                                      'attr_num_list': trans_num_list, 'attr_culster_list': trans_culster_list})

                    else:
                        index = nodes_id.index(source)
                        temp = nodes[index]
                        temp['flow_out'] = temp['flow_out'] + flow
                        temp['flow'] = temp['flow'] + temp['flow_out']
                        del nodes_id[index]
                        del nodes[index]
                        nodes_id.append(source)
                        nodes.append(temp)

        # 边处理
        for link in links:
            key = {
                'source': link['source'],
                'target': link['target'],
                'flow': 0,
                'times': 0,
            }
            if key not in tmp_links:
                tmp_links.append(key)
        for item in tmp_links:
            for link in links:
                if link['source'] == item['source'] and link['target'] == item['target']:
                    item['flow'] = item['flow'] + link['flow']
                    item['times'] = item['times'] + 1
        links = tmp_links
        global AnomalyLayoutDataResult
        AnomalyLayoutDataResult = {'nodes': nodes, 'links': links}
        AnomalyLayoutDataResult = igraphLayout.cal_back_layout_data(
            AnomalyLayoutDataResult, 'kk')
        evt = json.dumps(AnomalyLayoutDataResult)
        self.write(evt)


class detectAnomalyOnFlow(tornado.web.RequestHandler):
    # 异常检测代码
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")

        print('异常检测代码')
        nodes = []
        links = []
        AnomalyNodes = []
        global AnomalyLayoutDataResult  # 由于前端传输局过来经常失败所以这里采用了全局变量

        nodes = AnomalyLayoutDataResult['nodes'];
        links = AnomalyLayoutDataResult['links'];

        for node in nodes:
            sumFlow = node['flow']
            flow_out = 0
            flow_in = 0
            for link in links:
                if link['source'] == node['id']:
                    flow_out = flow_out + link['flow']
                if link['target'] == node['id']:
                    flow_in = flow_in + link['flow']
            if (flow_in + flow_out) != sumFlow:
                AnomalyNodes.append({'id': node['id'], 'flow_difference': sumFlow - (flow_in + flow_out), 'node': node})

        evt = json.dumps(AnomalyNodes)
        self.write(evt)

    pass


class detectSimilarity(tornado.web.RequestHandler):
    # 相似性检测
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        nodes = []
        nodesSimilarity = []
        params = json.loads(self.get_argument('params'))
        nodeId = params['nodeId']  # 获取前端单选的节点
        global AnomalyLayoutDataResult
        nodes = AnomalyLayoutDataResult['nodes'];
        currentNode = {}
        # 找出当前被选中的节点的数据
        for node in nodes:
            if node['id'] == nodeId:
                currentNode = node

        # 计算相似性
        for node in nodes:
            cs = similarityTools.cosine_similarity(currentNode['attr_num_list'], node['attr_num_list'])
            js = similarityTools.jaccardSimilarity(currentNode['attr_culster_list'], node['attr_culster_list'])
            nodesSimilarity.append({'id': node['id'], 'Similarity': (cs + js)[0]})
        nodesSimilarity = sorted(nodesSimilarity, key=lambda x: x['Similarity'], reverse=True)
        mostSimList = nodesSimilarity[0:10]
        print(mostSimList)
        self.write(json.dumps(mostSimList))


class getTimeLineJson(tornado.web.RequestHandler):
    # 从预先计算好的json文件中，获取timeline全局流量
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        print('params', params)
        filePath = '../data/timeLineData_all.json'
        with codecs.open(filePath, 'r', 'utf-8') as load_f:
            load_dict = json.load(load_f)
        evt = json.dumps(load_dict)
        self.write(evt)


class getAccompanyJson(tornado.web.RequestHandler):
    # 从预先计算好的json文件中，获取timeline全局流量
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        print('params', params)
        filePath = '../data/tsconfig.json'
        with codecs.open(filePath, 'r', 'utf-8') as load_f:
            load_dict = json.load(load_f)
        evt = json.dumps(load_dict)
        self.write(evt)


class getAccompanyData(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        print('params', params)
        timeRange = json.loads(params['data'])
        print('timeRange', timeRange)
        start = time.clock()
        nowSelectedData = NetworkData.getTimeRangeData(timeRange[0],
                                                       timeRange[1])
        end = time.clock()
        diff_time = end - start
        print("spend time for get timeline data: " + str(diff_time))
        evt_unpacked = {'message': 'timeRangeData', 'data': nowSelectedData}
        evt = json.dumps(evt_unpacked)
        self.write(evt)


class getAccompanyCSV(tornado.web.RequestHandler):
    # 从预先计算好的json文件中，获取timeline全局流量
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = json.loads(self.get_argument('params'))
        print('params', params)
        filePath = '../data/accompany.csv'
        result = {'data': []}
        count = 0
        with open(filePath, 'r', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for i in reader:
                if (count != 0):
                    item = {};
                    item['id'] = i[0]
                    item['event_begintime'] = i[1]
                    item['event_endtime'] = i[2]
                    item['recv_node_golbal_no'] = i[3]
                    item['trans_node_global_no'] = i[4]
                    item['net_level'] = i[5]
                    result['data'].append(item)
                count = 1
        evt = json.dumps(result)
        self.write(evt)


class getMultilayerData(tornado.web.RequestHandler):
    # 读取分层数据并计算布局
    def get(self):
        print("进入get")
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = self.get_argument('params')
        params = json.loads(params)
        layoutType = params['layout_type']
        networkLevel = int(params['network_level'])
        data = []

        startLevel = networkLevel * 100
        endLevel = startLevel + 100

        getMultiData = NetworkData.getAnomalyData("event4")
        for item in getMultiData:
            if startLevel <= int(item['net_level']) < endLevel:
                data.append(item)
        if len(data):
            links = []
            temp_nodes = []
            nodes = []
            nodes_id = []
            for row in data:
                source = row['trans_node_global_no']
                target = row['recv_node_golbal_no']
                link = {'source': source, 'target': target}
                temp_nodes.append({
                    'id': source
                })
                temp_nodes.append({
                    'id': target
                })
                links.append(link)
            for item in temp_nodes:
                if item['id'] not in nodes_id:
                    nodes_id.append(item['id'])
                    nodes.append(item)
                else:
                    index = nodes_id.index(item['id'])
                    del nodes[index]
                    del nodes_id[index]
                    nodes.append(item)
                    nodes_id.append(item['id'])

            tmp_links = []
            for link in links:
                key = {
                    'source': link['source'],
                    'target': link['target']
                }
                if key not in tmp_links:
                    tmp_links.append(key)

            myindex = 0
            for item in tmp_links:
                for link in links:
                    if link['source'] == item['source'] and link['target'] == item['target']:
                        item['id'] = myindex
                        myindex = myindex + 1
            links = tmp_links

            result = {'nodes': nodes, 'links': links}
            result = igraphLayout.cal_back_layout_data(result, layoutType)
            self.write(result)
        else:
            result = {'nodes': [], 'links': []}
            self.write(result)


class getLink(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = self.get_argument('params')
        params = json.loads(params)
        common = params['common']
        networkLevel = int(params['network_level'])

        data = []

        startLevel = networkLevel * 100
        endLevel = startLevel + 100

        getMultiData = NetworkData.getAnomalyData("event4")
        for item in getMultiData:
            if startLevel <= int(item['net_level']) < endLevel:
                data.append(item)
        if len(data):
            links = []
            temp_nodes = []
            nodes = []
            nodes_id = []
            for row in data:
                source = row['trans_node_global_no']
                target = row['recv_node_golbal_no']
                link = {'source': source, 'target': target}
                temp_nodes.append({
                    'id': source
                })
                temp_nodes.append({
                    'id': target
                })
                links.append(link)
            for item in temp_nodes:
                if item['id'] not in nodes_id:
                    nodes_id.append(item['id'])
                    nodes.append(item)
                else:
                    index = nodes_id.index(item['id'])
                    del nodes[index]
                    del nodes_id[index]
                    nodes.append(item)
                    nodes_id.append(item['id'])

            tmp_links = []
            for link in links:
                key = {
                    'source': link['source'],
                    'target': link['target']
                }
                if key not in tmp_links:
                    tmp_links.append(key)

            myindex = 0
            for item in tmp_links:
                for link in links:
                    if link['source'] == item['source'] and link['target'] == item['target']:
                        item['id'] = myindex
                        myindex = myindex + 1
            links = tmp_links

            result = {'nodes': nodes, 'links': links, 'level': networkLevel}
            G = nx.Graph()
            for source in result['links']:
                G.add_edge(source['target'], source['source'], id=source['id'])
            shortPath = {'node': [], 'link': []}  # 返回最短路径的节点和边
            path = dict(nx.all_pairs_shortest_path(G))
            short_path_name = path[common[0]][common[1]]
            shortPath['node'] = short_path_name
            pairs = []
            for (index, item) in enumerate(short_path_name):
                if index == len(short_path_name) - 1:
                    break
                pairs.append(G.edges[short_path_name[index], short_path_name[index + 1]]['id'])
            for (index, item) in enumerate(pairs):
                pairs[index] = str(networkLevel) + '_' + str(item)
            shortPath['link'] = pairs
            self.write(shortPath)


class findsubgraph(tornado.web.RequestHandler):
    def post(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")
        params = self.get_argument('params')
        params = json.loads(params)
        skeleton_json = params['skeleton']  # json.loads变为对象
        d = params['index']
        G = nx.Graph()
        for link in skeleton_json['links']:
            G.add_edge(link['target'], link['source'], id=link['id'])
        for c in sorted(nx.algorithms.components.connected_components(G)):
            if d in nx.Graph(nx.subgraph(G, c)).nodes:
                skeleton_sub = nx.subgraph(G, c)
                break
        edge_id_list = {}
        index = 0
        for c in sorted(nx.algorithms.components.connected_components(G)):
            component_graph = nx.Graph(nx.subgraph(G, c))  # 深度拷贝
            component_len_edges = myutil.find_number_of_edges(nx.subgraph(G, c))  # 数据图边数
            sub_len_nodes = myutil.find_number_of_nodes(skeleton_sub)  # 查询图的节点数
            sub_len_edges = myutil.find_number_of_edges(skeleton_sub)  # 查询图的边数

            if sub_len_edges > component_len_edges:
                continue
            choose_list = component_graph.nodes

            for i in itertools.combinations(choose_list, sub_len_nodes):
                nodes = list(i)
                subgraph = G.subgraph(nodes)
                if nx.algorithms.isomorphism.is_isomorphic(subgraph, skeleton_sub):
                    edge_id = []
                    for item in list(subgraph.edges):
                        edge_id.append(G[item[0]][item[1]]['id'])
                    edge_id_list[index] = edge_id
                    index = index + 1
        result = {'data': edge_id_list}
        self.write(result)

class getTopNodeData(tornado.web.RequestHandler):
    # 前端传来选中节点ID以及时间范围，返回时间范围内与该节点最相似的top10
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")

        params = json.loads(self.get_argument('params'))
        print('params', params)
        timerange = params['timerange']
        p_timerange = {}
        for key in timerange:
            p_timerange[key] = timerange[key][0: 4] + timerange[key][5: 7] + timerange[key][8: 10] + timerange[key][11: 13] + timerange[key][14: 16] + timerange[key][17: 19] + '000000'
        id = params['id']

        data = NetworkData.getTopData(p_timerange, id)
        # print(data)

        # 这里是节点属性数据
        nodes_obj = {
            data[0]['recv_node_golbal_no']: {
                'attr_num_list': [],
                'attr_cluster_list': []
            }
        }
        for i in range(1, 31):
            temp_obj = {
                'key': 'num_' + str(i),
                'value': data[0]['recv_num_' + str(i)]
            }
            nodes_obj[data[0]['recv_node_golbal_no']]['attr_num_list'].append(temp_obj)
        for i in range(1, 21):
            temp_obj = {
                'key': 'cluster' + str(i),
                'value': data[0]['recv_cluster_' + str(i)]
            }
            nodes_obj[data[0]['recv_node_golbal_no']]['attr_cluster_list'].append(temp_obj)

        for item in data:
            if item['recv_node_golbal_no'] not in nodes_obj:
                nodes_obj[item['recv_node_golbal_no']] = {
                    'attr_num_list': [],
                    'attr_cluster_list': []
                }
                for i in range(1, 31):
                    temp_obj = {
                        'key': 'num_' + str(i),
                        'value': item['recv_num_' + str(i)]
                    }
                    nodes_obj[item['recv_node_golbal_no']]['attr_num_list'].append(temp_obj)
                for i in range(1, 21):
                    temp_obj = {
                        'key': 'cluster_' + str(i),
                        'value': item['recv_cluster_' + str(i)]
                    }
                    nodes_obj[item['recv_node_golbal_no']]['attr_cluster_list'].append(temp_obj)
            if item['trans_node_global_no'] not in nodes_obj:
                nodes_obj[item['trans_node_global_no']] = {
                    'attr_num_list': [],
                    'attr_cluster_list': []
                }
                for i in range(1, 31):
                    temp_obj = {
                        'key': 'num_' + str(i),
                        'value': item['trans_num_' + str(i)]
                    }
                    nodes_obj[item['trans_node_global_no']]['attr_num_list'].append(temp_obj)
                for i in range(1, 21):
                    temp_obj = {
                        'key': 'cluster_' + str(i),
                        'value': item['trans_cluster_' + str(i)]
                    }
                    nodes_obj[item['trans_node_global_no']]['attr_cluster_list'].append(temp_obj)

        # 这里假设所选节点的属性缺失了
        for i in range(0, 5):
            nodes_obj[id]['attr_num_list'][i]['value'] = None
            nodes_obj[id]['attr_cluster_list'][i]['value'] = None

        # 这里是节点ID数据
        nodes_id = []
        for node_id in nodes_obj:
            nodes_id.append(node_id)

        nodesSimilarity = []

        for node_id in nodes_id:
            temp_attr_num_list1 = []
            temp_attr_num_list2 = []
            temp_attr_cluster_list1 = []
            temp_attr_cluster_list2 = []
            temp_k = 0
            for i in range(0, 30):
                if nodes_obj[id]['attr_num_list'][i]['value'] != None and nodes_obj[node_id]['attr_num_list'][i]['value'] == None:
                    temp_k = 1
                    break

            if temp_k == 0:
                for i in range(0, 30):
                    if nodes_obj[id]['attr_num_list'][i]['value'] != None and nodes_obj[node_id]['attr_num_list'][i]['value'] != None:
                        temp_attr_num_list1.append(nodes_obj[id]['attr_num_list'][i])
                        temp_attr_num_list2.append(nodes_obj[node_id]['attr_num_list'][i])
                cs = similarityTools.cosine_similarity(temp_attr_num_list1, temp_attr_num_list2)

                for i in range(0, 20):
                    if nodes_obj[id]['attr_cluster_list'][i]['value'] != None and nodes_obj[node_id]['attr_cluster_list'][
                        i]['value'] != None:
                        temp_attr_cluster_list1.append(nodes_obj[id]['attr_cluster_list'][i])
                        temp_attr_cluster_list2.append(nodes_obj[node_id]['attr_cluster_list'][i])
                js = similarityTools.jaccardSimilarity(temp_attr_cluster_list1, temp_attr_cluster_list2)[0]

                nodesSimilarity.append({'id': node_id, 'Similarity': js + cs})
            elif temp_k == 1:
                nodesSimilarity.append({'id': node_id, 'Similarity': 0})

        nodesSimilarity = sorted(nodesSimilarity, key=lambda x: x['Similarity'], reverse=True)
        mostSimList = nodesSimilarity[1:11]  # 这里是top10

        # 这里是top10的属性数据
        mostSimList_attr = {}
        for top in mostSimList:
            mostSimList_attr[top['id']] = {}
            for i in range(1, 31):
                mostSimList_attr[top['id']]['num_' + str(i)] = nodes_obj[top['id']]['attr_num_list'][i - 1]
            for i in range(1, 21):
                mostSimList_attr[top['id']]['cluster_' + str(i)] = nodes_obj[top['id']]['attr_cluster_list'][i - 1]
        selectNode_attr = {}
        for i in range(1, 31):
            selectNode_attr['num_' + str(i)] = nodes_obj[id]['attr_num_list'][i - 1]
        for i in range(1, 21):
            selectNode_attr['cluster_' + str(i)] = nodes_obj[id]['attr_cluster_list'][i - 1]

        self.write(json.dumps([mostSimList, mostSimList_attr, selectNode_attr]))


class getChartData(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Access-Control-Allow-Origin',
                        '*')  # 添加响应头，允许指定域名的跨域请求
        self.set_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.set_header("Access-Control-Allow-Methods",
                        "PUT,POST,GET,DELETE,OPTIONS")

        params = json.loads(self.get_argument('params'))
        print('params', params)
        timerange = params['timerange']
        p_timerange = {}
        for key in timerange:
            p_timerange[key] = timerange[key][0: 4] + timerange[key][5: 7] + timerange[key][8: 10] + timerange[key][11: 13] + timerange[key][14: 16] + timerange[key][17: 19] + '000000'
        data_id = params['id']

        data = NetworkData.getTopData(p_timerange, data_id)
        # print(data)

        # 这里是节点属性数据
        nodes_obj = {}

        for item in data:
            if item['recv_node_golbal_no'] not in nodes_obj:
                nodes_obj[item['recv_node_golbal_no']] = {
                    'attr_num_list': [],
                    'attr_cluster_list': []
                }
                for i in range(1, 31):
                    temp_obj = {
                        'key': 'num_' + str(i),
                        'value': item['recv_num_' + str(i)]
                    }
                    nodes_obj[item['recv_node_golbal_no']]['attr_num_list'].append(temp_obj)
                for i in range(1, 21):
                    temp_obj = {
                        'key': 'cluster_' + str(i),
                        'value': item['recv_cluster_' + str(i)]
                    }
                    nodes_obj[item['recv_node_golbal_no']]['attr_cluster_list'].append(temp_obj)
            if item['trans_node_global_no'] not in nodes_obj:
                nodes_obj[item['trans_node_global_no']] = {
                    'attr_num_list': [],
                    'attr_cluster_list': []
                }
                for i in range(1, 31):
                    temp_obj = {
                        'key': 'num_' + str(i),
                        'value': item['trans_num_' + str(i)]
                    }
                    nodes_obj[item['trans_node_global_no']]['attr_num_list'].append(temp_obj)
                for i in range(1, 21):
                    temp_obj = {
                        'key': 'cluster_' + str(i),
                        'value': item['trans_cluster_' + str(i)]
                    }
                    nodes_obj[item['trans_node_global_no']]['attr_cluster_list'].append(temp_obj)

        # 这里假设所选节点的属性缺失了
        for i in range(0, 5):
            nodes_obj[data_id]['attr_num_list'][i]['value'] = None
            nodes_obj[data_id]['attr_cluster_list'][i]['value'] = None

        # 这里是节点ID数据
        nodes_id = []
        for node_id in nodes_obj:
            nodes_id.append(node_id)

        nodesSimilarity = []

        for node_id in nodes_id:
            temp_attr_num_list1 = []
            temp_attr_num_list2 = []
            temp_attr_cluster_list1 = []
            temp_attr_cluster_list2 = []
            temp_k = 0
            for i in range(0, 30):
                if nodes_obj[data_id]['attr_num_list'][i]['value'] != None and nodes_obj[node_id]['attr_num_list'][i][
                    'value'] == None:
                    temp_k = 1
                    break

            if temp_k == 0:
                for i in range(0, 30):
                    if nodes_obj[data_id]['attr_num_list'][i]['value'] != None and nodes_obj[node_id]['attr_num_list'][i][
                        'value'] != None:
                        temp_attr_num_list1.append(nodes_obj[data_id]['attr_num_list'][i])
                        temp_attr_num_list2.append(nodes_obj[node_id]['attr_num_list'][i])
                cs = similarityTools.cosine_similarity(temp_attr_num_list1, temp_attr_num_list2)

                for i in range(0, 20):
                    if nodes_obj[data_id]['attr_cluster_list'][i]['value'] != None and \
                            nodes_obj[node_id]['attr_cluster_list'][
                                i]['value'] != None:
                        temp_attr_cluster_list1.append(nodes_obj[data_id]['attr_cluster_list'][i])
                        temp_attr_cluster_list2.append(nodes_obj[node_id]['attr_cluster_list'][i])
                js = similarityTools.jaccardSimilarity(temp_attr_cluster_list1, temp_attr_cluster_list2)[0]

                nodesSimilarity.append({'id': node_id, 'Similarity': js + cs})
            elif temp_k == 1:
                nodesSimilarity.append({'id': node_id, 'Similarity': 0})

        nodesSimilarity = sorted(nodesSimilarity, key=lambda x: x['Similarity'], reverse=True)

        # 这里按时间（秒）取数据
        c_data = {}
        mostSimList2 = nodesSimilarity[0:11]
        for item in mostSimList2:
            c_data[item['id']] = []
        # print(c_data)
        for id in c_data:
            now_time = time.mktime(time.strptime(timerange['start'], "%Y-%m-%d %H:%M:%S"))
            for d in data:
                dtime = d['event_begintime']
                dtime = dtime[0: 4] + '-' + dtime[4: 6] + '-' + dtime[6: 8] + ' ' + dtime[8: 10] + ':' + dtime[10: 12] + ':' + dtime[12: 14]
                dtime = time.mktime(time.strptime(dtime, "%Y-%m-%d %H:%M:%S"))
                if now_time == dtime:
                    if id == d['recv_node_golbal_no']:
                        tempTime = now_time
                        tempTimeData = {
                            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tempTime)),
                            'attributes': {}
                        }
                        for i in range(1, 31):
                            tempTimeData['attributes']['num_' + str(i)] = d['recv_num_' + str(i)]
                        for i in range(1, 21):
                            tempTimeData['attributes']['cluster_' + str(i)] = d['recv_cluster_' + str(i)]
                        c_data[id].append(tempTimeData)
                        now_time = now_time + 1
                    elif id == d['trans_node_global_no']:
                        tempTime = now_time
                        tempTimeData = {
                            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tempTime)),
                            'attributes': {}
                        }
                        for i in range(1, 31):
                            tempTimeData['attributes']['num_' + str(i)] = d['trans_num_' + str(i)]
                        for i in range(1, 21):
                            tempTimeData['attributes']['cluster_' + str(i)] = d['trans_cluster_' + str(i)]
                        c_data[id].append(tempTimeData)
                        now_time = now_time + 1
                elif now_time < dtime:
                    tempTime = now_time
                    tempTimeData = {
                        'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tempTime)),
                        'attributes': {}
                    }
                    for i in range(1, 31):
                        tempTimeData['attributes']['num_' + str(i)] = None
                    for i in range(1, 21):
                        tempTimeData['attributes']['cluster_' + str(i)] = None
                    c_data[id].append(tempTimeData)
                    now_time = now_time + 1

        # print(c_data[id])
        # print(id)

        self.write(json.dumps(c_data))


if __name__ == "__main__":
    tornado.options.parse_command_line()
    print(
        'server running at 127.0.0.1:%d ...' % (tornado.options.options.port))
    print(client_file_root_path)
    app = tornado.web.Application(
        handlers=[
            (r'/recent-data', getRecentDataHandler),
            (r'/get-layout-data', getLayoutData),
            (r'/getDim2', getDim2),
            (r'/changeOutlierType', changeOutlierType),
            (r'/getAttr', getAttr),
            (r'/choosenone', choosenone),
            (r'/gettree', gettree),
            (r'/getSPs', getSPs),
            (r'/getFlow', getFlow),
            (r'/getData2', getData2),
            (r'/get-timeLine-json', getTimeLineJson),
            (r'/detect-anomaly-onflow', detectAnomalyOnFlow),
            (r'/detect-similarity', detectSimilarity),
            (r'/get-anomaly-layout-data', getAnomalyLayoutData),
            (r'/get-accompany-json', getAccompanyJson),
            (r'/get-accompany-csv', getAccompanyCSV),
            (r'/get-multi-layer-data', getMultilayerData),
            (r'/getLink', getLink),
            (r'/findsubgraph', findsubgraph),
            (r'/get-top-node-data', getTopNodeData),
            (r'/get-chart-data', getChartData),
            (r'/(.*)', tornado.web.StaticFileHandler, {
                'path': client_file_root_path,
                'default_filename': 'index.html'
            })  # fetch client files
        ],
        debug=True,
    )

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
