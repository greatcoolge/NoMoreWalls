import re
import json
import base64
import uuid
import requests
import traceback
import threading
from typing import List, Dict, Union, Set, Any

# 全局变量
FETCH_TIMEOUT = 30  # 假设的默认超时时间
ABFURLS = []
AUTOURLS = []
AUTOFETCH = []
LOCAL = False
STOP = False

class Node:
    names: Set[str] = set()
    DATA_TYPE = Dict[str, Any]

    def __init__(self, data: Union[DATA_TYPE, str]) -> None:
        if isinstance(data, dict):
            self.data: __class__.DATA_TYPE = data
            self.type = data['type']
        elif isinstance(data, str):
            self.load_url(data)
        else: raise TypeError(f"Got {type(data)}")
        if not self.data['name']:
            self.data['name'] = "未命名"
        if 'password' in self.data:
            self.data['password'] = str(self.data['password'])
        self.data['type'] = self.type
        self.name: str = self.data['name']

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
            path += '@'+data.get('alpn', '')+'@'+data.get('password', '')+data.get('uuid', '')
            hashstr = f"{self.type}:{data['server']}:{data['port']}:{path}"
            return hash(hashstr)
        except Exception:
            print("节点 Hash 计算失败！", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return hash('__ERROR__')
    
    def __eq__(self, other: Union['Node', Any]):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def load_url(self, url: str) -> None:
        # 解析 URL，获取节点配置数据
        pass

    @property
    def url(self) -> str:
        # 根据节点类型生成 URL
        if self.type == 'vmess':
            return f"vmess://{base64.b64encode(json.dumps(self.data).encode()).decode()}"
        elif self.type == 'ss':
            return f"ss://{base64.b64encode(f'{self.data['method']}:{self.data['password']}@{self.data['server']}:{self.data['port']}'.encode()).decode()}"
        elif self.type == 'ssr':
            return f"ssr://{base64.b64encode(json.dumps(self.data).encode()).decode()}"
        elif self.type == 'trojan':
            return f"trojan://{base64.b64encode(f'{self.data['password']}@{self.data['server']}:{self.data['port']}'.encode()).decode()}"
        elif self.type == 'vless':
            return f"vless://{base64.b64encode(json.dumps(self.data).encode()).decode()}"
        elif self.type == 'hysteria2':
            return f"hysteria2://{base64.b64encode(json.dumps(self.data).encode()).decode()}"
        return ''

class Source:
    def __init__(self, source_data: List[Dict]):
        self.source_data = source_data

    def gen_url(self) -> List[str]:
        urls = []
        for node_data in self.source_data:
            node = Node(node_data)
            url = node.url
            if url:
                urls.append(url)
        return urls

    def get(self) -> List[Dict]:
        return self.source_data

    def _download(self, url: str) -> List[Dict]:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []

def raw2fastly(url: str) -> str:
    if not LOCAL: return url
    if url.startswith("https://raw.githubusercontent.com/"):
        return "https://mirror.ghproxy.com/" + url
    return url

def main():
    global FETCH_TIMEOUT, ABFURLS, AUTOURLS, AUTOFETCH, LOCAL, STOP

    sources = open("sources.list", encoding="utf-8").read().strip().splitlines()

    print("正在生成动态链接...")
    for auto_fun in AUTOURLS:
        print("正在生成 '"+auto_fun.__name__+"'... ", end='', flush=True)
        try: url = auto_fun()
        except requests.exceptions.RequestException: print("失败！")
        except: print("错误：");traceback.print_exc()
        else:
            if url:
                if isinstance(url, str):
                    sources.append(url)
                elif isinstance(url, (list, tuple, set)):
                    sources.extend(url)
                print("成功！")
            else: print("跳过！")
    
    print("正在整理链接...")
    sources_final: Union[Set[str], List[str]] = set()
    for source in sources:
        if source == 'EOF': break
        if not source: continue
        if source[0] == '#': continue
        sub = raw2fastly(source)
        sources_final.add(sub)

    sources_obj = [Source([{'url': sub}]) for sub in sources_final]

    print("开始抓取！")
    threads = [threading.Thread(target=_.get, daemon=True) for _ in sources_obj]
    for thread in threads: thread.start()
    for i in range(len(sources_obj)):
        try:
            for t in range(1, FETCH_TIMEOUT+1):
                print("抓取 '"+sources_obj[i].url+"'... ", end='', flush=True)
                try: threads[i].join(timeout=FETCH_TIMEOUT)
                except KeyboardInterrupt:
                    print("正在退出...")
                    break
                if not threads[i].is_alive(): break
        except KeyboardInterrupt:
            print("正在退出...")
            break

    # 新增：保存数据到文件
    with open("nodes_output.json", "w", encoding="utf-8") as f:
        all_urls = []
        for source in sources_obj:
            urls = source.gen_url()
            all_urls.extend(urls)
        json.dump(all_urls, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()
