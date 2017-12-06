# coding=utf-8
import uuid
import sublime
import sublime_plugin
import threading
import urllib.request as request
import urllib.parse as urlparse
from xml.dom.minidom import parseString


class TrsInfo(object):
    word = ""
    trans = ""
    web_trans = ""
    phonetic = ""

    def __setitem__(self, key, value):
        self


class Youdao(object):

    def __init__(self):
        self._trs_info = TrsInfo()

    def _init_trs(self):
        self._trs_info.word = ""
        self._trs_info.trans = "没有找到相关的汉英互译结果。"
        self._trs_info.web_trans = ""
        self._trs_info.phonetic = ""

    def build_request(self, word):
        words = word.replace("_", " ")
        url = "http://dict.youdao.com/search"
        data = {
            "keyfrom": "deskdict.mini",
            "q": words,
            "doctype": "xml",
            "xmlVersion": 8.2,
            "client": "deskdict",
            "id": "fef0101011fbaf8c",
            "vendor": "unknown",
            "in": "YoudaoDict",
            "appVer": "5.4.46.5554",
            "appZengqiang": 0,
            "le": "eng",
            "LTH": 140
        }

        url = "%s?%s" % (url, urlparse.urlencode(data))
        print(url)
        req = request.Request(url)
        req.add_header('User-Agent', 'Youdao Desktop Dict (Windows 6.1.7601)')
        sublime.status_message(url)
        try:
            html = request.urlopen(req, timeout=10).read()
        except Exception as e:
            print(e)
            sublime.status_message(str(e))
            return []

        dom = parseString(html)
        basic = dom.getElementsByTagName("basic")[0]
        trs = basic.getElementsByTagName("tr")
        print(trs)
        items = []
        for tr in trs:
            try:
                obj = tr.getElementsByTagName("i")[0]
                text = obj.firstChild.wholeText
            except Exception as e:
                print(e)
            else:
                items.append(text)  # .split('；'))
        return items

    def auto_translate(self, words):
        self._init_trs()
        self._trs_info.word = words
        words = words.replace("_", " ")
        url = "http://dict.youdao.com/search"
        data = {"keyfrom": "deskdict.mini", "q": words, "doctype": "xml", "xmlVersion": 8.2,
                "client": "deskdict", "id": "fef0101011fbaf8c", "vendor": "unknown",
                "in": "YoudaoDict", "appVer": "5.4.46.5554", "appZengqiang": 0, "le": "eng", "LTH": 140}

        url = "%s?%s" % (url, urlparse.urlencode(data))
        print(url)
        req = request.Request(url)
        req.add_header('User-Agent', 'Youdao Desktop Dict (Windows 6.1.7601)')
        sublime.status_message(url)
        try:
            html = request.urlopen(req, timeout=10).read()
        except Exception as e:
            sublime.status_message(str(e))
            return self._trs_info
        dom = parseString(html)
        web_trans = self.parser_web_trans(dom)

        simple_dict_nodes = dom.getElementsByTagName("simple-dict")
        if not simple_dict_nodes:
            if web_trans:
                self._trs_info.trans = web_trans
            return self._trs_info
        simple_dict_node = simple_dict_nodes[0]
        trs = self.parse_trs(simple_dict_node)
        if not trs:
            return self._trs_info
        self._trs_info.trans = trs
        self._trs_info.phonetic = self.parse_phonetic(simple_dict_node)
        return self._trs_info

    def parser_web_trans(self, dom):
        web_nodes = dom.getElementsByTagName("web-translation")
        if not web_nodes:
            return ""
        value_nodes = web_nodes[0].getElementsByTagName("value")
        if not value_nodes:
            return ""
        return "<br>".join([obj.firstChild.wholeText for obj in value_nodes if obj.firstChild])

    def get_node_text(self, node, tag):
        nodes = node.getElementsByTagName(tag)
        if not nodes:
            return ""
        if not nodes[0].firstChild:
            return ""
        return nodes[0].firstChild.wholeText

    def parse_phonetic(self, node):
        phonetics = ""
        ukphone = self.get_node_text(node, "ukphone")
        if ukphone:
            phonetics += "英[%s] " % ukphone
        usphone = self.get_node_text(node, "usphone")
        if usphone:
            phonetics += "美[%s]" % usphone
        phone = self.get_node_text(node, "phone")
        if phone:
            phonetics += "[%s]" % phone
        return phonetics

    def parse_trs(self, node):
        if not node:
            return ""
        trs_node = node.getElementsByTagName("trs")
        if not trs_node:
            return ""
        i_nodes = trs_node[0].getElementsByTagName("i")
        try:
            ret_string = "<br>".join([obj.firstChild.wholeText for obj in i_nodes if obj.firstChild])
        except Exception:
            ret_string = ""
        return ret_string


youdao = Youdao()


class ThreadRun(threading.Thread):

    def __init__(self, handler, callback, args=[], cb_args=[], flag=None):
        super(ThreadRun, self).__init__()
        self.setDaemon(True)
        self.handler = handler
        self.callback = callback
        self.args = args
        self.cb_args = cb_args
        self.flag = flag

    def run(self):
        if self.args:
            result = self.handler(*self.args)
        else:
            result = self.handler()

        # if self.flag != global_flag:
        #     return

        if self.cb_args:
            self.callback(result, *self.cb_args)
        else:
            self.callback(result)


class TranslateCommand(sublime_plugin.TextCommand):

    @property
    def current_word(self):
        view = self.view
        current_region = view.sel()[0]
        if current_region.a != current_region.b:
            return view.substr(current_region)
        word = view.word(current_region)
        return view.substr(word)

    def run(self, edit):
        self.flag = str(uuid.uuid4())
        ThreadRun(youdao.build_request, self.show_popup, [self.current_word], flag=self.flag).start()

    def show_popup(self, items):
        self.items = items
        html_content = ''.join(map(lambda v: '<span><a href="%s">%s</a></span>' % (v, v), items))
        html = "<html><body><div>%s</div></body><html>" % html_content
        html = """
        <html>
        <style>
        a{text-decoration: none;};
        ul{list-style:none;text-decoration: none;}
        </style>
        <body>
            <div>
                <strong class="keyword">read</strong>
            </div>
            <div>
                <span class="baav">
                    <span class="pronounce">英<span class="phonetic">[ri:d;red]</span></span>
                    <span class="pronounce">美<span class="phonetic">[rid;rɛd]</span></span>
                </span>
            </div>
            <div class="trans-container">
                <ul>
                    <li>vt. 阅读；读懂，理解</li>
                    <li>vi. 读；读起来</li>
                    <li>n. 阅读；读物</li>
                    <li>adj. 有学问的</li>
                </ul>
            </div>
        </body>
        </html>
        """

        self.view.show_popup(html, max_width=512, on_navigate=self.on_navigate)

    def on_navigate(self, text):
        self.view.hide_popup()
        sublime.set_clipboard(text)
        sublime.status_message('%s copied!' % text)
