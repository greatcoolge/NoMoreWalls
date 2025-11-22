#!/usr/bin/env python3
# ========== User Configs Begin ==========
# 以下是可以自定义的配置：
STOP = False              # 暂停抓取节点
NAME_SHOW_TYPE = False    # 在节点名称前添加如 [Vmess] 的标签
NAME_NO_FLAGS  = False    # 将节点名称中的地区旗帜改为文本地区码
NAME_SHOW_SRC  = False    # 在节点名称前显示所属订阅编号 (订阅见 list_result.csv)

import yaml
import json
import base64
from urllib.parse import quote, unquote, urlparse
import requests
from requests_file import FileAdapter
import datetime
import traceback
import binascii
import threading
import sys
import os
import copy
from types import FunctionType as function
from typing import Set, List, Dict, Union, Callable, Any, Optional, Iterable
# from dynamic import AUTOURLS, AUTOFETCH

try: PROXY = open("local_proxy.conf").read().strip()
except FileNotFoundError: LOCAL = False; PROXY = None
else:
    if not PROXY: PROXY = None
    LOCAL = not PROXY

def b64encodes(s: str):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

def b64encodes_safe(s: str):
    return base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8')

def b64decodes(s: str):
    ss = s + '=' * ((4-len(s)%4)%4)
    try:
        return base64.b64decode(ss.encode('utf-8')).decode('utf-8')
    except UnicodeDecodeError: raise
    except binascii.Error: raise

def b64decodes_safe(s: str):
    ss = s + '=' * ((4-len(s)%4)%4)
    try:
        return base64.urlsafe_b64decode(ss.encode('utf-8')).decode('utf-8')
    except UnicodeDecodeError: raise
    except binascii.Error: raise

def resolveRelFile(url: str):
    if url.startswith('file://'):
        basedir = os.path.dirname(os.path.abspath(__file__))
        return url.replace('/./', '/'+basedir.lstrip('/').replace(os.sep, '/')+'/')
    return url

DEFAULT_UUID = '8'*8+'-8888'*3+'-'+'8'*12

CLASH2VMESS = {'name': 'ps', 'server': 'add', 'port': 'port', 'uuid': 'id',
              'alterId': 'aid', 'cipher': 'scy', 'network': 'net', 'servername': 'sni'}
VMESS2CLASH: Dict[str, str] = {}
for k,v in CLASH2VMESS.items(): VMESS2CLASH[v] = k

VMESS_TEMPLATE = {
    "v": "2", "ps": "", "add": "0.0.0.0", "port": "0", "aid": "0", "scy": "auto",
    "net": "tcp", "type": "none", "tls": "", "id": DEFAULT_UUID
}

CLASH_CIPHER_VMESS = "auto aes-128-gcm chacha20-poly1305 none".split()
CLASH_CIPHER_SS = "aes-128-gcm aes-192-gcm aes-256-gcm aes-128-cfb aes-192-cfb \
        aes-256-cfb aes-128-ctr aes-192-ctr aes-256-ctr rc4-md5 chacha20-ietf \
        xchacha20 chacha20-ietf-poly1305 xchacha20-ietf-poly1305".split()
CLASH_SSR_OBFS = "plain http_simple http_post random_head tls1.2_ticket_auth tls1.2_ticket_fastauth".split()
CLASH_SSR_PROTOCOL = "origin auth_sha1_v4 auth_aes128_md5 auth_aes128_sha1 auth_chain_a auth_chain_b".split()

FAKE_IPS = "8.8.8.8; 8.8.4.4; 4.2.2.2; 4.2.2.1; 114.114.114.114; 127.0.0.1; 0.0.0.0".split('; ')
FAKE_DOMAINS = ".google.com .github.com".split()

FETCH_TIMEOUT = (6, 5)

BANNED_WORDS = b64decodes('5rOV6L2uIOi9ruWtkCDova4g57uDIOawlCDlip8g5L2/5YqyIOWKsiDliqrlipsg5Yqg5rK5IOWlsyDmnYMg6L+Q5YqoIG9uZ3RhaXdhbg==').split()

session = requests.Session()
session.trust_env = False
if PROXY and not PROXY == 'NONE':
    session.proxies = {'http': PROXY, 'https': PROXY}
session.headers["User-Agent"] = 'Mozilla/5.0 (X11; Linux x86_64) Clash-verge/v2.4.2 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
session.mount('file://', FileAdapter())

class UnsupportedType(Exception): pass
class NotANode(Exception): pass

class Node:
    gNames: Set[str] = set()
    DATA_TYPE = Dict[str, Any]

    def __init__(self, data: Union[DATA_TYPE, str]) -> None:
        if isinstance(data, dict):
            self.data: Node.DATA_TYPE = data
            self.type = data['type']
        elif isinstance(data, str):
            self.load_url(data)
        else: raise TypeError(f"Got {type(data)}")
        if not self.data['name']:
            self.data['name'] = "未命名"
        if 'password' in self.data:
            self.data['password'] = str(self.data['password'])
        self.data['type'] = self.type
        self.names: Set[str] = {self.data['name']}

    def __str__(self):
        return self.url

    def __hash__(self):
        data = self.data
        try:
            path = ""
            if self.type == 'vmess':
                net: str = data.get('network', '')
                path = net+':'
                if not net: pass
                elif net == 'ws':
                    opts: Dict[str, Any] = data.get('ws-opts', {})
                    path += opts.get('headers', {}).get('Host', '')
                    path += '/'+opts.get('path', '')
                elif net == 'h2':
                    opts: Dict[str, Any] = data.get('h2-opts', {})
                    path += ','.join(opts.get('host', []))
                    path += '/'+opts.get('path', '')
                elif net == 'grpc':
                    path += data.get('grpc-opts', {}).get('grpc-service-name','')
            elif self.type == 'ss':
                opts: Dict[str, Any] = data.get('plugin-opts', {})
                path = opts.get('host', '')
                path += '/'+opts.get('path', '')
            elif self.type == 'ssr':
                path = data.get('obfs-param', '')
            elif self.type == 'trojan':
                path = data.get('sni', '')+':'
                net: str = data.get('network', '')
                if not net: pass
                elif net == 'ws':
                    opts: Dict[str, Any] = data.get('ws-opts', {})
                    path += opts.get('headers', {}).get('Host', '')
                    path += '/'+opts.get('path', '')
                elif net == 'grpc':
                    path += data.get('grpc-opts', {}).get('grpc-service-name','')
            elif self.type == 'vless':
                path = data.get('sni', '')+':'
                net: str = data.get('network', '')
                if not net: pass
                elif net == 'ws':
                    opts: Dict[str, Any] = data.get('ws-opts', {})
                    path += opts.get('headers', {}).get('Host', '')
                    path += '/'+opts.get('path', '')
                elif net == 'grpc':
                    path += data.get('grpc-opts', {}).get('grpc-service-name','')
            elif self.type == 'hysteria2':
                path = data.get('sni', '')+':'
                path += data.get('obfs-password', '')+':'
                # print(self.url)
                # return hash(self.url)
            path += '@'+','.join(data.get('alpn', []))+'@'+data.get('password', '')+data.get('uuid', '')
            hashstr = f"{self.type}:{data['server']}:{data['port']}:{path}"
            return hash(hashstr)
        except Exception:
            print("节点 Hash 计算失败！", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return hash(self.url)

    def __eq__(self, other: Union['Node', Any]):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def load_url(self, url: str):
        try: self.type, dt = url.split("://", 1)
        except ValueError: raise NotANode(url)
        # === Fix begin ===
        if not self.type.isascii():
            self.type = ''.join([_ for _ in self.type if _.isascii()])
            url = self.type+'://'+url.split("://")[1]
        if self.type == 'hy2': self.type = 'hysteria2'
        # === Fix end ===
        loader: Optional[Callable[[str, str], None]] = \
                getattr(self, '_load_'+self.type, None)
        if loader: loader(url, dt)
        else: raise UnsupportedType(self.type)

    def _load_vmess(self, url: str, dt: str):
        v = VMESS_TEMPLATE.copy()
        try: v.update(json.loads(b64decodes(dt)))
        except Exception:
            raise UnsupportedType('vmess', 'SP')
        self.data = {}
        for key, val in v.items():
            if key in VMESS2CLASH:
                self.data[VMESS2CLASH[key]] = val
        self.data['tls'] = (v['tls'] == 'tls')
        self.data['alterId'] = int(self.data['alterId'])
        if v['net'] == 'ws':
            opts = {}
            if 'path' in v:
                opts['path'] = v['path']
            if 'host' in v:
                opts['headers'] = {'Host': v['host']}
            self.data['ws-opts'] = opts
        elif v['net'] == 'h2':
            opts = {}
            if 'path' in v:
                opts['path'] = v['path']
            if 'host' in v:
                opts['host'] = v['host'].split(',')
            self.data['h2-opts'] = opts
        elif v['net'] == 'grpc' and 'path' in v:
            self.data['grpc-opts'] = {'grpc-service-name': v['path']}

    def _load_ss(self, url: str, dt: str):
        info = url.split('@')
        srvname = info.pop()
        if '#' in srvname:
            srv, name = srvname.split('#')
        else:
            srv = srvname
            name = ''
        server, port = srv.split(':')
        try:
            port = int(port)
        except ValueError:
            raise UnsupportedType('ss', 'SP')
        info = '@'.join(info)
        if not ':' in info:
            info = b64decodes_safe(info)
        if ':' in info:
            cipher, passwd = info.split(':')
        else:
            cipher = info
            passwd = ''
        self.data = {'name': unquote(name), 'server': server,
                'port': port, 'type': 'ss', 'password': passwd, 'cipher': cipher}

    def _load_ssr(self, url: str, dt: str):
        if '?' in url:
            parts = dt.split(':')
        else:
            parts = b64decodes_safe(dt).split(':')
        try:
            passwd, info = parts[-1].split('/?')
        except: raise
        passwd = b64decodes_safe(passwd)
        self.data = {'type': 'ssr', 'server': parts[0], 'port': parts[1],
                'protocol': parts[2], 'cipher': parts[3], 'obfs': parts[4],
                'password': passwd, 'name': ''}
        for kv in info.split('&'):
            k_v = kv.split('=', 1)
            if len(k_v) != 2:
                k = k_v[0]
                v = ''
            else: k,v = k_v
            if k == 'remarks':
                self.data['name'] = v
            elif k == 'group':
                self.data['group'] = v
            elif k == 'obfsparam':
                self.data['obfs-param'] = v
            elif k == 'protoparam':
                self.data['protocol-param'] = v

    def _load_trojan(self, url: str, dt: str):
        parsed = urlparse(url)
        self.data = {'name': unquote(parsed.fragment), 'server': parsed.hostname,
                'port': parsed.port, 'type': 'trojan', 'password': unquote(parsed.username)}
        if not parsed.query: return
        for kv in parsed.query.split('&'):
            k,v = kv.split('=', 1)
            if k in ('allowInsecure', 'insecure'):
                self.data['skip-cert-verify'] = (v != '0')
            elif k == 'sni': self.data['sni'] = v
            elif k == 'alpn':
                self.data['alpn'] = unquote(v).split(',')
            elif k == 'type':
                self.data['network'] = v
            elif k == 'serviceName':
                if 'grpc-opts' not in self.data:
                    self.data['grpc-opts'] = {}
                self.data['grpc-opts']['grpc-service-name'] = v
            elif k == 'host':
                if 'ws-opts' not in self.data:
                    self.data['ws-opts'] = {}
                if 'headers' not in self.data['ws-opts']:
                    self.data['ws-opts']['headers'] = {}
                self.data['ws-opts']['headers']['Host'] = v
            elif k == 'path':
                if 'ws-opts' not in self.data:
                    self.data['ws-opts'] = {}
                self.data['ws-opts']['path'] = v

    def _load_vless(self, url: str, dt: str):
        parsed = urlparse(url)
        self.data = {'name': unquote(parsed.fragment), 'server': parsed.hostname,
                'port': parsed.port, 'type': 'vless', 'uuid': unquote(parsed.username)}
        self.data['tls'] = False
        if not parsed.query: return
        for kv in parsed.query.split('&'):
            k,v = kv.split('=', 1)
            if k in ('allowInsecure', 'insecure'):
                self.data['skip-cert-verify'] = (v != '0')
            elif k == 'sni': self.data['servername'] = v
            elif k == 'alpn':
                self.data['alpn'] = unquote(v).split(',')
            elif k == 'type':
                self.data['network'] = v
            elif k == 'serviceName':
                if 'grpc-opts' not in self.data:
                    self.data['grpc-opts'] = {}
                self.data['grpc-opts']['grpc-service-name'] = v
            elif k == 'host':
                if 'ws-opts' not in self.data:
                    self.data['ws-opts'] = {}
                if 'headers' not in self.data['ws-opts']:
                    self.data['ws-opts']['headers'] = {}
                self.data['ws-opts']['headers']['Host'] = v
            elif k == 'path':
                if 'ws-opts' not in self.data:
                    self.data['ws-opts'] = {}
                self.data['ws-opts']['path'] = v
            elif k == 'flow':
                if v.endswith('-udp443'):
                    self.data['flow'] = v
                else: self.data['flow'] = v+'!'
            elif k == 'fp': self.data['client-fingerprint'] = v
            elif k == 'security' and v == 'tls':
                self.data['tls'] = True
            elif k == 'pbk':
                if 'reality-opts' not in self.data:
                    self.data['reality-opts'] = {}
                self.data['reality-opts']['public-key'] = v
            elif k == 'sid':
                if 'reality-opts' not in self.data:
                    self.data['reality-opts'] = {}
                self.data['reality-opts']['short-id'] = v
            # TODO: Unused key encryption

    def _load_hysteria2(self, url: str, dt: str):
        parsed = urlparse(url)
        self.data = {'name': unquote(parsed.fragment), 'server': parsed.hostname,
                'type': 'hysteria2', 'password': unquote(parsed.username)}
        if ':' in parsed.netloc:
            ports = parsed.netloc.split(':')[1]
            if ',' in ports:
                _, self.data['ports'] = ports.split(',',1)
            else:
                self.data['port'] = ports
            try: self.data['port'] = int(self.data['port'])
            except ValueError: self.data['port'] = 443
        else:
            self.data['port'] = 443
        self.data['tls'] = False
        if not parsed.query: return
        k = v = ''
        for kv in parsed.query.split('&'):
            if '=' in kv:
                k,v = kv.split('=', 1)
            else:
                v += '&' + kv
            if k == 'insecure':
                self.data['skip-cert-verify'] = (v != '0')
            elif k == 'alpn':
                self.data['alpn'] = unquote(v).split(',')
            elif k in ('sni', 'obfs', 'obfs-password'):
                self.data[k] = v
            elif k == 'fp': self.data['fingerprint'] = v

    def _load__legacy(self, url: str, dt: str):
        raise NotANode(f"Legacy URL type skipped: {url}")
        # parsed = urlparse(url)

        # 没有 host 直接报错，不生成假节点
        # if not parsed.hostname:
        #     raise NotANode(f"节点 URL 没有 host: {url}")

        # 根据协议设置默认端口
        # default_port = 443 if parsed.scheme == 'https' else 80
        # port = parsed.port or default_port

        # self.data = {
        #     'name': unquote(parsed.fragment) or 'Unnamed',
        #     'type': 'socks5' if getattr(self, 'type', '') == 'socks5' else 'http',
        #     'tls': parsed.scheme == 'https',
        #     'server': parsed.hostname,
        #     'port': port,
        #     'username': parsed.username,
        #     'password': parsed.password
        # }

        # 只保留非 None 的字段
        # self.data = {k: v for k, v in self.data.items() if v is not None}
        
    _load_http = _load__legacy
    _load_https = _load__legacy
    _load_socks5 = _load__legacy

    def update(self, node: 'Node'):
        self.data.update(node.data)
        self.names = self.names.union(node.names)  # ✅ 正确的方式
        # self.names.union(node.names)

    @property
    def name(self):
        def rate(name: str):
            r = 0
            if name.startswith('@'):
                r -= 5
            if any(127462<=ord(c)<=127487 for c in name):
                r += 6
            if '\N{RIGHT-TO-LEFT MARK}' in name:
                r -= 3
            if any(word in name for word in BANNED_WORDS):
                r -= 100
            return r
        return sorted(list(self.names), key=rate)[0]

    def format_name(self, max_len=30):
        name = [ord(c) for c in self.name]
        for ch in '\N{MATHEMATICAL BOLD CAPITAL A}\N{MATHEMATICAL SANS-SERIF BOLD CAPITAL A}':
            name = [
                c - ord(ch) + ord('A') if ord(ch) <= c < ord(ch)+26 else c
                for c in name
            ]
        for ch in ('\N{MATHEMATICAL BOLD SMALL A}\N{MATHEMATICAL SANS-SERIF BOLD SMALL A}'
                    +'\N{REGIONAL INDICATOR SYMBOL LETTER A}'*NAME_NO_FLAGS):
            name = [
                c - ord(ch) + ord('a') if ord(ch) <= c < ord(ch)+26 else c
                for c in name
            ]
        name = ''.join([chr(c) for c in name])
        name = name.replace(chr(10144), '->')
        for word in BANNED_WORDS:
            name = name.replace(word, '*'*len(word))
        if len(name) > max_len:
            name = name[:max_len]
            if '\N{RIGHT-TO-LEFT MARK}' in name:
                name += '\N{LEFT-TO-RIGHT MARK}'
                print(name)
            name += '...'
        if NAME_SHOW_TYPE:
            if self.type in ('ss', 'ssr', 'vless', 'tuic'):
                tp = self.type.upper()
            else:
                tp = self.type.title()
            name = f'[{tp}] ' + name
        if name in Node.gNames:
            i = 0
            new = name
            while new in Node.gNames:
                i += 1
                new = f"{name} #{i}"
            name = new
        self.data['name'] = name

    @property
    def isfake(self) -> bool:
        if STOP: return False
        try:
            if 'server' not in self.data: return True
            if '.' not in self.data['server']: return True
            if self.data['server'] in FAKE_IPS: return True
            if int(str(self.data['port'])) < 20: return True
            for domain in FAKE_DOMAINS:
                if self.data['server'] == domain.lstrip('.'): return True
                if self.data['server'].endswith(domain): return True
            # TODO: Fake UUID
            # if self.type == 'vmess' and len(self.data['uuid']) != len(DEFAULT_UUID):
            #     return True
            if 'sni' in self.data and 'google.com' in self.data['sni'].lower():
                # That's not designed for China
                self.data['sni'] = 'www.bing.com'
        except Exception:
            print("无法验证的节点！", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        return False

    @property
    def url(self) -> str:
        handler: Optional[Callable[[Node.DATA_TYPE], str]] = \
                getattr(self, '_url_'+self.type, None)
        if handler: return handler(self.data)
        else: raise UnsupportedType(self.type)

    def _url_vmess(self, data: DATA_TYPE) -> str:
        v = VMESS_TEMPLATE.copy()
        for key, val in data.items():
            if key in CLASH2VMESS:
                v[CLASH2VMESS[key]] = val
        if v['net'] == 'ws':
            if 'ws-opts' in data:
                try:
                    v['host'] = data['ws-opts']['headers']['Host']
                except KeyError: pass
                if 'path' in data['ws-opts']:
                    v['path'] = data['ws-opts']['path']
        elif v['net'] == 'h2':
            if 'h2-opts' in data:
                if 'host' in data['h2-opts']:
                    v['host'] = ','.join(data['h2-opts']['host'])
                if 'path' in data['h2-opts']:
                    v['path'] = data['h2-opts']['path']
        elif v['net'] == 'grpc':
            if 'grpc-opts' in data:
                if 'grpc-service-name' in data['grpc-opts']:
                    v['path'] = data['grpc-opts']['grpc-service-name']
        if data.get('tls'):
            v['tls'] = 'tls'
        return 'vmess://'+b64encodes(json.dumps(v, ensure_ascii=False))

    def _url_ss(self, data: DATA_TYPE) -> str:
        passwd = b64encodes_safe(data['cipher']+':'+data['password'])
        return f"ss://{passwd}@{data['server']}:{data['port']}#{quote(data['name'])}"

    def _url_ssr(self, data: DATA_TYPE) -> str:
        ret = (':'.join([str(data[_]) for _ in ('server','port',
                                    'protocol','cipher','obfs')]) +
                b64encodes_safe(data['password']) +
                f"remarks={b64encodes_safe(data['name'])}")
        for k, urlk in (('obfs-param','obfsparam'), ('protocol-param','protoparam'), ('group','group')):
            if k in data:
                ret += '&'+urlk+'='+b64encodes_safe(data[k])
        return "ssr://"+ret

    def _url_trojan(self, data: DATA_TYPE) -> str:
        passwd = quote(data['password'])
        name = quote(data['name'])
        ret = f"trojan://{passwd}@{data['server']}:{data['port']}?"
        if 'skip-cert-verify' in data:
            ret += f"allowInsecure={int(data['skip-cert-verify'])}&"
        if 'sni' in data:
            ret += f"sni={data['sni']}&"
        if 'alpn' in data:
            ret += f"alpn={quote(','.join(data['alpn']))}&"
        if 'network' in data:
            if data['network'] == 'grpc':
                ret += f"type=grpc&serviceName={data['grpc-opts']['grpc-service-name']}"
            elif data['network'] == 'ws':
                ret += f"type=ws&"
                if 'ws-opts' in data:
                    try:
                        ret += f"host={data['ws-opts']['headers']['Host']}&"
                    except KeyError: pass
                    if 'path' in data['ws-opts']:
                        ret += f"path={data['ws-opts']['path']}"
        ret = ret.rstrip('&')+'#'+name
        return ret

    def _url_vless(self, data: DATA_TYPE) -> str:
        passwd = quote(data['uuid'])
        name = quote(data['name'])
        ret = f"vless://{passwd}@{data['server']}:{data['port']}?"
        if 'skip-cert-verify' in data:
            ret += f"allowInsecure={int(data['skip-cert-verify'])}&"
        if 'servername' in data:
            ret += f"sni={data['servername']}&"
        if 'alpn' in data:
            ret += f"alpn={quote(','.join(data['alpn']))}&"
        if 'network' in data:
            if data['network'] == 'grpc':
                ret += f"type=grpc&"
                try:
                    ret += f"serviceName={data['grpc-opts']['grpc-service-name']}&"
                except KeyError: pass
            elif data['network'] == 'ws':
                ret += f"type=ws&"
                if 'ws-opts' in data:
                    try:
                        ret += f"host={data['ws-opts']['headers']['Host']}&"
                    except KeyError: pass
                    if 'path' in data['ws-opts']:
                        ret += f"path={data['ws-opts']['path']}"
        if 'flow' in data:
            flow: str = data['flow']
            if flow.endswith('!'):
                ret += f"flow={flow[:-1]}&"
            else: ret += f"flow={flow}-udp443&"
        if 'client-fingerprint' in data:
            ret += f"fp={data['client-fingerprint']}&"
        if data.get('tls'):
            ret += f"security=tls&"
        elif 'reality-opts' in data:
            opts: Dict[str, str] = data['reality-opts']
            ret += f"security=reality&pbk={opts.get('public-key','')}&sid={opts.get('short-id','')}&"
        ret = ret.rstrip('&')+'#'+name
        return ret

    def _url_hysteria2(self, data: DATA_TYPE) -> str:
        passwd = quote(data['password'])
        name = quote(data['name'])
        ret = f"hysteria2://{passwd}@{data['server']}:{data['port']}"
        if 'ports' in data:
            ret += ','+data['ports']
        ret += '?'
        if 'skip-cert-verify' in data:
            ret += f"insecure={int(data['skip-cert-verify'])}&"
        if 'alpn' in data:
            ret += f"alpn={quote(','.join(data['alpn']))}&"
        if 'fingerprint' in data:
            ret += f"fp={data['fingerprint']}&"
        for k in ('sni', 'obfs', 'obfs-password'):
            if k in data:
                ret += f"{k}={data[k]}&"
        ret = ret.rstrip('&')+'#'+name
        return ret

    def _url__legacy(self, data: DATA_TYPE) -> str:
        raise NotANode("Legacy URL type skipped")
        # tp = 'https' if self.type == 'http' and data.get('tls') else self.type
        # part = ''
        # if 'username' in data:
        #     part += data['username']
        # if 'password' in data:
        #     part += ':' + data['password']
        # if part: part += '@'
        # return f"{tp}://{part}{data['server']}:{data['port']}"

    _url_http = _url__legacy
    _url_https = _url__legacy
    _url_socks5 = _url__legacy

    @property
    def clash_data(self) -> DATA_TYPE:
        ret = self.data.copy()
        if 'password' in ret and ret['password'].isdigit():
            ret['password'] = '!!str '+ret['password']
        if 'uuid' in ret and len(ret['uuid']) != len(DEFAULT_UUID):
            ret['uuid'] = DEFAULT_UUID
        if 'group' in ret: del ret['group']
        if 'cipher' in ret and not ret['cipher']:
            ret['cipher'] = 'auto'
        if self.type == 'vless' and 'flow' in ret:
            if ret['flow'].endswith('-udp443'):
                ret['flow'] = ret['flow'][:-7]
            elif ret['flow'].endswith('!'):
                ret['flow'] = ret['flow'][:-1]
        if 'alpn' in ret and isinstance(ret['alpn'], str):
            # 'alpn' is not a slice
            ret['alpn'] = ret['alpn'].replace(' ','').split(',')
        # A temporary fix for mihomo-party's `invalid REALITY short ID` error.
        if 'reality-opts' in ret and 'short-id' in ret['reality-opts']:
            ret['reality-opts']['short-id'] = '!!str '+ret['reality-opts']['short-id']
        return ret

    def supports_clash(self, meta=False) -> bool:
        if self.isfake: return False
        if 'obfs' in self.data and 'obfs-password' not in self.data:
            return False
        if self.type == 'vmess':
            supported = CLASH_CIPHER_VMESS
        elif self.type == 'ss' or self.type == 'ssr':
            supported = CLASH_CIPHER_SS
        elif self.type == 'trojan': return True
        elif not meta: return False
        else: return True
        # Vmess / SS / SSR
        if 'network' in self.data and self.data['network'] in ('h2','grpc'):
            # A quick fix for #2
            self.data['tls'] = True
        if 'cipher' not in self.data: return True
        if not self.data['cipher']: return True
        if self.data['cipher'] not in supported: return False
        try:
            if self.type == 'ssr':
                if 'obfs' in self.data and self.data['obfs'] not in CLASH_SSR_OBFS:
                    return False
                if 'protocol' in self.data and self.data['protocol'] not in CLASH_SSR_PROTOCOL:
                    return False
            if 'plugin-opts' in self.data and 'mode' in self.data['plugin-opts'] \
                    and not self.data['plugin-opts']['mode']: return False
        except Exception:
            print("无法验证的 Clash 节点！", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False
        return True

    def supports_meta(self) -> bool:
        return self.supports_clash(meta=True)

    def supports_ray(self) -> bool:
        if self.isfake: return False
        
        if self.type == 'socks5' and self.data.get('tls'):
            return False
        return True

class Source():
    def __init__(self, url: Union[str, function]) -> None:
        self.url_source: Union[str, function, None]
        if isinstance(url, function):
            self.url: str = "dynamic://"+url.__name__
            self.url_source = url
        elif url.startswith('+'):
            self.url_source = url
            self.date = datetime.datetime.now()# + datetime.timedelta(days=1)
            self.gen_url()
        else:
            self.url: str = url
            self.url_source = None
        self.content: Union[str, Iterable[str], int] = None
        self.sub: Union[List[str], List[Dict[str, str]]] = None
        self.cfg: Dict[str, Any] = {}
        self.exc_queue: List[str] = []

    def gen_url(self):
        assert isinstance(self.url_source, str)
        tags = self.url_source.split()
        url = tags.pop()
        while tags:
            tag = tags.pop(0)
            if tag[0] != '+': break
            if tag == '+date':
                url = self.date.strftime(url)
                self.date -= datetime.timedelta(days=1)
        self.url = url

    def get(self, depth=2) -> None:
        if self.content: return
        try:
            if self.url.startswith("dynamic:"):
                assert isinstance(self.url_source, function)
                self.content: Union[str, Iterable[str]] = self.url_source()
            else:
                global session
                if '#' in self.url:
                    segs = self.url.split('#')
                    self.cfg = dict([_.split('=',1) for _ in segs[-1].split('&')])
                    if 'max' in self.cfg:
                        try:
                            self.cfg['max'] = int(self.cfg['max'])
                        except ValueError:
                            self.exc_queue.append("最大节点数限制不是整数！")
                            del self.cfg['max']
                    if 'ignore' in self.cfg:
                        self.cfg['ignore'] = [_ for _ in self.cfg['ignore'].split(',') if _.strip()]
                    self.url = '#'.join(segs[:-1])
                with session.get(resolveRelFile(self.url), stream=True) as r:
                    if r.status_code != 200:
                        if depth > 0 and isinstance(self.url_source, str):
                            exc = f"'{self.url}' 抓取时 {r.status_code}"
                            self.gen_url()
                            exc += "，重新生成链接：\n\t"+self.url
                            self.exc_queue.append(exc)
                            self.get(depth-1)
                        else:
                            self.content = r.status_code
                        return
                    self.content = self._download(r)
        except KeyboardInterrupt: raise
        except requests.exceptions.RequestException:
            self.content = -1
        except:
            self.content = -2
            exc = "在抓取 '"+self.url+"' 时发生错误：\n"+traceback.format_exc()
            self.exc_queue.append(exc)
        else:
            self.parse()

    def _download(self, r: requests.Response) -> str:
        content = bytes()
        tp = None
        pending = None
        early_stop = False
        for chunk in r.iter_content():
            if early_stop: pending = None; break
            chunk: bytes
            if tp == 'sub':
                content += chunk
                continue
            if pending != None:
                chunk = pending + chunk
                pending = None
            lines = chunk.splitlines()
            if lines and lines[-1] and chunk.endswith(lines[-1]):
                pending = lines.pop()
            while lines:
                lineb = lines.pop(0)
                line = lineb.decode().replace('\\r','').rstrip()
                if not line: continue
                if not tp:
                    if ': ' in line:
                        if line.count(': ') == 1 and line.isalpha():
                            tp = 'yaml'
                    elif line[0] == '#': pass
                    else: tp = 'sub'
                if tp == 'yaml':
                    if content:
                        if line in ("proxy-groups:", "rules:", "script:"):
                            early_stop=True; break
                        content += lineb + b'\n'
                    elif line == "proxies:":
                        content = lineb + b'\n'
                elif tp == 'sub':
                    content = chunk
                    pending = None
                    break
        if pending != None: content += pending
        try:
            ret = content.decode()
        except UnicodeDecodeError:
            exc = "在抓取 '"+self.url+"' 时发生错误：\n"+traceback.format_exc()
            self.exc_queue.append(exc)
            ret = content.decode('ignore')
        return ret

    def parse(self):
        try:
            text = self.content
            if isinstance(text, str):
                if "proxies:" in text:
                    # Clash config
                    config = yaml.full_load(text.replace("!<str>","!!str"))
                    sub = config['proxies']
                elif '://' in text:
                    # V2Ray raw list
                    sub = text.strip().splitlines()
                else:
                    # V2Ray Sub
                    sub = b64decodes(text.strip()).strip().splitlines()
            elif not isinstance(text, (list, tuple)):
                sub = list(text)
            else: sub = text # 动态节点抓取后直接传入列表

            if 'max' in self.cfg and len(sub) > self.cfg['max']:
                self.exc_queue.append(f"此订阅有 {len(sub)} 个节点，最大限制为 {self.cfg['max']} 个，忽略此订阅。")
                self.sub = []
            elif sub and 'ignore' in self.cfg:
                if isinstance(sub[0], str):
                    self.sub = [_ for _ in sub if _.split('://', 1)[0] not in self.cfg['ignore']]
                elif isinstance(sub[0], dict):
                    self.sub = [_ for _ in sub if _.get('type', '') not in self.cfg['ignore']] #type:ignore
                else: self.sub = sub
            else: self.sub = sub
        except KeyboardInterrupt: raise
        except: self.exc_queue.append(
                "在解析 '"+self.url+"' 时发生错误：\n"+traceback.format_exc())



def extract(url: str) -> Union[Set[str], int]:
    global session
    res = session.get(url)
    if res.status_code != 200: return res.status_code
    urls: Set[str] = set()
    mark = '#'+url.split('#', 1)[1] if '#' in url else ''
    for line in res.text.strip().splitlines():
        line = line.strip()
        if line.startswith("http"):
            urls.add(line+mark)
    return urls

merged: Dict[int, Node] = {}
unknown: Set[str] = set()
used: Dict[int, Dict[int, str]] = {}
def merge(source_obj: Source, sourceId=-1):
    global merged, unknown
    sub = source_obj.sub
    if not sub: print("空订阅，跳过！", end='', flush=True); return
    for p in sub:
        if isinstance(p, str) and '://' not in p: continue
        try: n = Node(p)
        except KeyboardInterrupt: raise
        except UnsupportedType as e:
            if len(e.args) == 1:
                print(f"不支持的类型：{e}")
            unknown.add(p)
        except: traceback.print_exc()
        else:
            n.format_name()
            Node.gNames.add(n.data['name'])
            hashn = hash(n)
            if hashn not in merged:
                merged[hashn] = n
            else:
                # merged[hashn].data.update(n.data)  # ✅ 更新节点的 data 字典
                merged[hashn].update(n)
            if hashn not in used:
                used[hashn] = {}
            used[hashn][sourceId] = n.name

def raw2fastly(url: str) -> str:
    if not LOCAL: return url
    url: Union[str, List[str]]
    if url.startswith("https://raw.githubusercontent.com/"):
        # url = url[34:].split('/')
        # url[1] += '@'+url[2]
        # del url[2]
        # url = "https://fastly.jsdelivr.net/gh/"+('/'.join(url))
        # return url
        return "https://ghproxy.cfd/"+url
    return url



def main():
    global merged, AUTOURLS, AUTOFETCH

    # 读取 sources.list
    sources = open("sources.list", encoding="utf-8").read().strip().splitlines()

    # 生成动态链接
    print("正在生成动态链接...")
    for auto_fun in AUTOURLS:
        print("正在生成 '"+auto_fun.__name__+"'... ", end='', flush=True)
        try:
            url = auto_fun()
        except requests.exceptions.RequestException:
            print("失败！")
        except:
            print("错误："); traceback.print_exc()
        else:
            if url:
                if isinstance(url, str):
                    sources.append(url)
                elif isinstance(url, (list, tuple, set)):
                    sources.extend(url)
                print("成功！")
            else:
                print("跳过！")

    # 整理链接
    print("正在整理链接...")
    sources_final: Set[str] = set()
    airports: Set[str] = set()
    for source in sources:
        if not source or source[0] == '#' or source == 'EOF':
            continue
        sub = source
        isairport = sub.startswith('*')
        if isairport:
            sub = sub[1:]
            airports.add(sub)
        elif sub.startswith('+'):
            tags = sub.split()
            sub = tags.pop()
            sub = ' '.join(tags) + ' ' + raw2fastly(sub)
        else:
            sub = raw2fastly(sub)
        if not isairport:
            sources_final.add(sub)

    # 抓取机场列表
    if airports:
        print("正在抓取机场列表...")
        for sub in airports:
            print("合并 '"+sub+"'... ", end='', flush=True)
            try:
                res = extract(sub)
            except KeyboardInterrupt:
                print("正在退出...")
                break
            except requests.exceptions.RequestException:
                print("合并失败！")
            except:
                traceback.print_exc()
            else:
                if isinstance(res, int):
                    print(res)
                else:
                    for url in res:
                        sources_final.add(url)
                    print("完成！")

    sources_final = list(sources_final)
    sources_final.sort()
    sources_obj = [Source(url) for url in (sources_final + AUTOFETCH)]

    # 抓取节点
    print("开始抓取！")
    threads = [threading.Thread(target=_.get, daemon=True) for _ in sources_obj]
    for thread in threads:
        thread.start()
    for i, source in enumerate(sources_obj):
        try:
            for t in range(1, FETCH_TIMEOUT[0]+1):
                print("抓取 '"+source.url+"'... ", end='', flush=True)
                threads[i].join(timeout=FETCH_TIMEOUT[1])
                if not threads[i].is_alive():
                    break
                print(f"{5*t}s")
            else:
                print("超时！")
                continue
            res = source.content
            if not isinstance(res, int):
                print("正在合并... ", end='', flush=True)
                try:
                    merge(source, sourceId=i)
                except KeyboardInterrupt:
                    print("正在退出...")
                    break
                except:
                    print("失败！"); traceback.print_exc()
                else:
                    print("完成！")
            for exc in source.exc_queue:
                print(exc)
            source.exc_queue = []
        except KeyboardInterrupt:
            print("正在退出...")
            break

    # 输出 V2Ray 订阅
    print("\n正在写出 V2Ray 订阅...")
    txt = ""
    unsupports = 0
    for p in merged.values():
        try:
            if p.supports_ray():
                txt += p.url + '\n'
            else:
                unsupports += 1
        except:
            traceback.print_exc()
    for p in unknown:
        txt += p+'\n'

    print(f"共有 {len(merged)-unsupports} 个正常节点，{len(unknown)} 个无法解析节点，共 {len(merged)+len(unknown)} 个，{unsupports} 个不支持 V2Ray。")

    with open("list_raw.txt", 'w', encoding="utf-8") as f:
        f.write(txt)
    with open("list.txt", 'w', encoding="utf-8") as f:
        f.write(b64encodes(txt))
    print("写出完成！")

    # 输出 Clash & Meta 节点列表
    print("\n正在写出节点列表...")
    proxies: List[Node.DATA_TYPE] = []
    proxies_meta: List[Node.DATA_TYPE] = []

    for p in merged.values():
        if p.supports_meta():
            proxies_meta.append(p.clash_data)
            if p.supports_clash():
                proxies.append(p.clash_data)

    os.makedirs("snippets", exist_ok=True)
    with open("snippets/nodes.yml", 'w', encoding="utf-8") as f:
        yaml.dump({'proxies': proxies}, f, allow_unicode=True)
    with open("snippets/nodes.meta.yml", 'w', encoding="utf-8") as f:
        yaml.dump({'proxies': proxies_meta}, f, allow_unicode=True)

    print(f"已输出 {len(proxies)} 个 Clash 节点和 {len(proxies_meta)} 个 Meta 节点")

    # 输出抓取统计
    print("正在写出统计信息...")
    out = "序号,链接,节点数\n"
    for i, source in enumerate(sources_obj):
        out += f"{i},{source.url},"
        try:
            out += f"{len(source.sub)}"
        except:
            out += '0'
        out += '\n'
    out += f"\n总计,,{len(merged)}\n"
    with open("list_result.csv",'w', encoding="utf-8") as f:
        f.write(out)
    print("写出完成！")

if __name__ == '__main__':
    from dynamic import AUTOURLS, AUTOFETCH
    main()
