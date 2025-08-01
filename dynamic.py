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



session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

def fetch_cfmem():
    base_url = "https://www.cfmem.com/"
    res = session.get(base_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    link_pat = re.compile(r"\d{4}/\d{2}/[a-z0-9\-]+\.html")

    print("🧪 正在扫描首页文章列表...")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        print(f"   链接: {href} | 标题: {title}")

        if "节点" in title and link_pat.search(href):
            full_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
            print(f"✅ 命中节点文章链接：{full_url}")
            candidates.append((title, full_url))
            break  # 只取第一个匹配链接

    if not candidates:
        raise Exception("❌ 未找到包含“节点”的文章链接")

    article_url = candidates[0][1]

    res = session.get(article_url)
    html = res.text

    sub_link_pattern = re.compile(
        r'https://fs\.v2rayse\.com/share/\d{8}/[a-z0-9]{10}\.(?:txt|yaml|yml|json)',
        re.IGNORECASE
    )
    sub_links = sub_link_pattern.findall(html)

    if not sub_links:
        raise Exception("❌ 未提取到任何订阅链接")

    print(f"📦 共提取 {len(sub_links)} 个订阅链接：")
    for link in sub_links:
        print("   🔗", link)

    # 分类整理，存到 subs 集合中，只放纯链接字符串
    subs = set()
    result = {}
    for link in sub_links:
        clean_link = link.strip()
        if clean_link.startswith("http"):
            subs.add(clean_link)
    print(f"📦 共提取 {len(subs)} 个订阅链接，已存入 subs 变量。")
    return subs  # 返回纯链接的集合



def sharkdoor():
    res_json = session.get(datetime.datetime.now().strftime(
        'https://api.github.com/repos/sharkDoor/vpn-free-nodes/contents/node-list/%Y-%m?ref=master')).json()
    if not res_json:          # ← 只加这一行：目录为空就直接返回空集合
        return set()
    res = session.get(raw2fastly(res_json[-1]['download_url']))
    nodes: Set[str] = set()
    for line in res.text.split('\n'):
        if '://' in line:
            nodes.add(line.split('|')[-2])
    return nodes

def sharkdoor_today():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    month_url = datetime.datetime.now().strftime(
        'https://api.github.com/repos/sharkDoor/vpn-free-nodes/contents/node-list/%Y-%m?ref=master'
    )
    res_json = session.get(month_url).json()
    if not res_json:
        return set()

    nodes: Set[str] = set()
    for item in res_json:
        if today in item['name'] and item['name'].endswith('.md'):
            res = session.get(raw2fastly(item['download_url']))
            for line in res.text.splitlines():
                if '://' in line:
                    nodes.add(line.split('|')[-2])
    return nodes


def changfengoss():
    # Unused
    res = session.get(datetime.datetime.now().strftime(
        "https://api.github.com/repos/changfengoss/pub/contents/data/%Y_%m_%d?ref=main")).json()
    return [_['download_url'] for _ in res]

def get_latest_danmaifu_link(max_days: int = 3):
    url = "https://api.github.com/repos/danmaifu/mianfeijiedian/contents/feed?ref=main"
    headers = {"User-Agent": "danmaifu-fetcher"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[{res.status_code}] Failed to fetch directory: {res.text}")
            return None

        data = res.json()

        # 获取过去 N 天的日期字符串
        for i in range(max_days):
            day = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y%m%d")
            target_name = f"v2ray-{day}.txt"

            for item in data:
                if item.get("name") == target_name:
                    print(f"[INFO] Found file: {target_name}")
                    return item.get("download_url")

        print("No matching file found in recent days.")
        return None

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

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

AUTOURLS = [fetch_cfmem, get_latest_danmaifu_link]
AUTOFETCH = [vpn_fail, sharkdoor_today]

if __name__ == '__main__':
    print("URL 抓取："+', '.join([_.__name__ for _ in AUTOURLS]))
    print("内容抓取："+', '.join([_.__name__ for _ in AUTOFETCH]))
    import code
    code.interact(banner='', exitmsg='', local=globals())
