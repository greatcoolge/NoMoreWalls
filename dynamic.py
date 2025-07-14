#!/usr/bin/env python3
import re
import datetime
import requests
import threading
from typing import Set
from fetch import raw2fastly, session, LOCAL
from bs4 import BeautifulSoup
import datetime as dt


# def kkzui():
#     if LOCAL: return
#     res = session.get("https://kkzui.com/jd?orderby=modified")
#     article_url = re.search(r'<a href="(https://kkzui.com/(.*?)\.html)" title="20(.*?)节点(.*?)</a>',res.text).groups()[0]
#     res = session.get(article_url)
#     passwd = re.search(r'<strong>本期密码：(.*?)</strong>',res.text).groups()[0]
#     res = session.post(article_url, data={'secret-key': passwd})
#     sub = res.text.split('<pre')[1].split('</pre>')[0]
#     if '</' in sub:
#         sub = sub.split('</')[-2]
#     if '>' in sub:
#         sub = sub.split('>')[-1]
#     return sub


session = requests.Session()

def fetch_cfmem():
    base_url = "https://www.cfmem.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    # 访问首页
    res = session.get(base_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 正则匹配文章链接和日期
    link_pattern = re.compile(r"https://www\.cfmem\.com/\d{4}/\d{2}/[a-z0-9\-]+\.html")
    date_pattern = re.compile(r"(\d{8})")  # 提取 slug 中的 8 位日期

    candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if link_pattern.match(href) and "节点" in title:
            match = date_pattern.search(href)
            if match:
                try:
                    date_obj = dt.datetime.strptime(match.group(1), "%Y%m%d")
                    candidates.append((date_obj, href))
                except:
                    continue

    if not candidates:
        raise Exception("未找到符合格式的“节点”文章链接")

    # 找到日期最新的文章链接
    article_url = max(candidates, key=lambda x: x[0])[1]

    print("✅ 最新文章链接：", article_url)

    # 接下来你可以继续访问这个文章页面，提取订阅链接或内容...
    # res = session.get(article_url)
    # soup = BeautifulSoup(res.text, 'html.parser')
    # 处理内容...

    return article_url
def sharkdoor():
    res_json = session.get(datetime.datetime.now().strftime(
        'https://api.github.com/repos/sharkDoor/vpn-free-nodes/contents/node-list/%Y-%m?ref=master')).json()
    res = session.get(raw2fastly(res_json[-1]['download_url']))
    nodes: Set[str] = set()
    for line in res.text.split('\n'):
        if '://' in line:
            nodes.add(line.split('|')[-2])
    return nodes

def changfengoss():
    # Unused
    res = session.get(datetime.datetime.now().strftime(
        "https://api.github.com/repos/changfengoss/pub/contents/data/%Y_%m_%d?ref=main")).json()
    return [_['download_url'] for _ in res]

def vpn_fail():
    # The site has been closed
    # if LOCAL: return
    response = session.get("https://vpn.fail/free-proxy/type/v2ray").text
    lines = re.findall(r'<article(.*?)</article', response, re.DOTALL)
    links = set()
    ips = set()
    for line in lines:
        result = re.search(r'<span>(\d+)%</span>', line)
        if result and result.group(1) == '100':
            ips.add(re.search(r'<a href="https://vpn\.fail/free-proxy/ip/(.*?)" style=', line).group(1))

    def get_link(ip: str) -> None:
        try:
            response = session.get(f"https://vpn.fail/free-proxy/ip/{ip}").text
            link = response.split('class="form-control text-center" id="pp2" value="')[1].split('"')[0]
            links.add(link)
        except requests.exceptions.RequestException:
            pass

    threads = [threading.Thread(target=get_link, args=(ip,)) for ip in ips]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return links
      
def w1770946466():
    if LOCAL: return
    res = session.get(raw2fastly("https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/README.md")).text
    subs: Set[str] = set()
    for line in res.strip().split('\n'):
        if line.startswith("`http"):
            sub = line.strip().strip('`')
            if not sub.startswith("https://raw.githubusercontent.com"):
                subs.add(sub)
    return subs

def peasoft():
    return session.get("https://gist.githubusercontent.com/peasoft/8a0613b7a2be881d1b793a6bb7536281/raw/417c1d6a75a53d6c197448762e7c97852d34787f/-").text

AUTOURLS = []
AUTOFETCH = [vpn_fail, sharkdoor, fetch_cfmem]

if __name__ == '__main__':
    print("URL 抓取："+', '.join([_.__name__ for _ in AUTOURLS]))
    print("内容抓取："+', '.join([_.__name__ for _ in AUTOFETCH]))
    import code
    code.interact(banner='', exitmsg='', local=globals())
