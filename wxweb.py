# encoding: utf-8
import web
import urllib2
import hashlib
import json
from bs4 import BeautifulSoup
from WXBizMsgCrypt import WXBizMsgCrypt
import xml.dom.minidom
import sys
import time
import os

reload(sys)
sys.setdefaultencoding('utf-8')
H = {
    "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6"
}
# 路由信息
urls = (
    '/', 'index',
    '/findProduct.action', 'findProduct',
    '/checkSignature', 'checkSignature',
    '/coupon', 'coupon'
)

encodingAESKey = '自己写'
token = "自己写"
appid = "自己写"
daTaoKeAppKey = "自己写"

# 格式化模板信息
def fromatXml(FromUserName, ToUserName, CreateTime, Content):
    return "<xml><ToUserName><![CDATA[" + FromUserName + "]]></ToUserName><FromUserName><![CDATA[" + ToUserName + "]]></FromUserName><CreateTime>" + str(
        CreateTime) + "</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[" + Content + "]]></Content><FuncFlag>0</FuncFlag></xml>"


# 查找商品
def queryProduct(text):
    url = "http://youhui.javalt.cn/index.php?r=l&kw=" + text
    req = urllib2.Request(url, headers=H)
    text = urllib2.urlopen(req).read()
    soup = BeautifulSoup(text)
    list = soup.findAll("li", {"class": "theme-hover-border-color-1  g_over"})
    count = 0
    dict = {}
    for item in list:
        info = {}
        info["name"] = item.div.a.text
        info["image"] = item.img.get("src")
        info["url"] = item.a.get("href")

        data = {}
        data["pid"] = item.a.get("data-gid")
        data["info"] = info

        dict[count] = data
        count = count + 1
    return json.dumps(dict)


def getProduct(id):
    url = "http://api.dataoke.com/index.php?r=port/index&id=" + id + "&appkey="+daTaoKeAppKey+"&v=2"
    req = urllib2.Request(url, headers=H)
    text = urllib2.urlopen(req).read()
    return text


class index:
    def GET(self):
        return "What are you going to do?"


class findProduct:
    def GET(self):
        return queryProduct(web.input().query)


# 微信接口
class checkSignature:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)

    def GET(self):
        data = web.input()
        signature = data.signature
        timestamp = data.timestamp
        nonce = data.nonce
        echostr = data.echostr

        list = [token, timestamp, nonce]
        list.sort()
        sha1 = hashlib.sha1()
        map(sha1.update, list)
        hashcode = sha1.hexdigest()

        if hashcode == signature:
            return echostr

    def POST(self):
        str_xml = web.data()
        decrypt = WXBizMsgCrypt(token, encodingAESKey, appid)
        ret, decryp_xml = decrypt.DecryptMsg(str_xml, web.input().msg_signature, web.input().timestamp,
                                             web.input().nonce)
        dom = xml.dom.minidom.parseString(decryp_xml)
        root = dom.documentElement
        msgType = root.getElementsByTagName('MsgType')[0].firstChild.data
        fromUser = root.getElementsByTagName('FromUserName')[0].firstChild.data
        toUser = root.getElementsByTagName('ToUserName')[0].firstChild.data

        # 判断是否文本信息
        if msgType == 'text':
            content = root.getElementsByTagName('Content')[0].firstChild.data
            pid = None
            try:
                path = './cache/' + fromUser + '.data'
                indexpath = './cache/' + fromUser + '.index'
                # 判断商品信息是否存在
                if os.path.exists(path) and content == '换':
                    # 读取商品信息Json
                    file_object = open(path, 'r')
                    datajson = json.loads(file_object.read())
                    file_object.close()

                    # 读取索引信息
                    file_object = open(indexpath, 'r')
                    index = file_object.read()
                    file_object.close()

                    # 保存索引信息
                    file_object = open(indexpath, 'w')
                    file_object.write(str(int(index) + 1))
                    file_object.close()

                    pid = datajson[index]["pid"]
                else:
                    datajson = queryProduct(content)
                    # 创建文件
                    file_object = open(path, 'w')
                    # 保存商品信息Json
                    file_object.write(datajson)
                    file_object.close()
                    # 创建文件
                    file_object = open(indexpath, 'w')
                    # 保存索引信息
                    file_object.write('1')
                    file_object.close()
                    pid = json.loads(datajson)['0']["pid"]
                hjson = json.loads(getProduct(pid))
                print  hjson["result"]["Title"]
                return self.render.reply_pictext1(fromUser,
                                                  toUser,
                                                  int(time.time()),
                                                  hjson["result"]["Title"],
                                                  '在售价: ' + str(hjson["result"]["Org_Price"]) + '  券后价: ' + str(hjson["result"]["Price"]),
                                                  hjson["result"]["Pic"],
                                                  "http://student.javalt.cn/coupon?pid=" + hjson["result"]["ID"])
            except Exception as e:
                return fromatXml(fromUser, toUser, int(time.time()), "没有查到该商品信息 更多信息可以进入 http://youhui.javalt.cn 查找")
        else:
            return fromatXml(fromUser, toUser, int(time.time()), "请输入正确的关键字 更多信息可以进入 http://youhui.javalt.cn 查找")


# 跳转到领取优惠卷页
class coupon(object):
    def GET(self):
        return "<script>window.location.href='http://youhui.javalt.cn/index.php?r=l/d&id=" + web.input().pid + "&u=718872';</script>"


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
