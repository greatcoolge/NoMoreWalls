#!/usr/bin/env python3
import re
import datetime
import requests
import threading
from typing import Set
from fetch import raw2fastly, session, LOCAL
from bs4 import BeautifulSoup
import datetime as dt
from typing import Optional

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



def fetch_latest_cfmem_article():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    base_url = "https://www.cfmem.com/"
    res = session.get(base_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 正则匹配
    link_pat = re.compile(r"https://www\.cfmem\.com/\d{4}/\d{2}/[a-z0-9\-]+\.html")
    date_pat = re.compile(r"/(\d{8})-")  # 提取 slug 中 8 位日期

    candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        if not ("节点" in title and link_pat.match(href)):
            continue

        m = date_pat.search(href)
        if not m:
            continue

        try:
            date_obj = dt.datetime.strptime(m.group(1), "%Y%m%d")
            candidates.append((date_obj, href))
        except:
            continue

    if not candidates:
        raise Exception("❌ 没找到任何节点文章")

    # 取日期最大的那篇
    _, latest_url = max(candidates)
    return latest_url


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
AUTOFETCH = [vpn_fail, sharkdoor, fetch_latest_cfmem_article]

if __name__ == '__main__':
    print("URL 抓取："+', '.join([_.__name__ for _ in AUTOURLS]))
    print("内容抓取："+', '.join([_.__name__ for _ in AUTOFETCH]))
    import code
    code.interact(banner='', exitmsg='', local=globals())
