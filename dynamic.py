#!/usr/bin/env python3
import re
import datetime
import requests
import threading
from typing import Set
from fetch import raw2fastly, session, LOCAL


def kkzui():
    if LOCAL: return
    res = session.get("https://kkzui.com/jd?orderby=modified")
    match = re.search(r'<a href="(https://kkzui.com/.*?\.html)" title="20.*?节点.*?</a>', res.text)
    if not match:
        raise Exception("未找到文章链接")
    article_url = match.group(1)

    res = session.get(article_url)
    passwd_match = re.search(r'<strong>本期密码：(.*?)</strong>', res.text)
    if not passwd_match:
        raise Exception("未找到密码")
    passwd = passwd_match.group(1)

    res = session.post(article_url, data={'secret-key': passwd})
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(res.text, 'html.parser')
    pre = soup.find('pre')
    if not pre:
        raise Exception("未找到订阅内容")
    return pre.text.strip()

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
AUTOFETCH = [vpn_fail, sharkdoor]

if __name__ == '__main__':
    print("URL 抓取："+', '.join([_.__name__ for _ in AUTOURLS]))
    print("内容抓取："+', '.join([_.__name__ for _ in AUTOFETCH]))
    import code
    code.interact(banner='', exitmsg='', local=globals())
