# -*- coding: utf-8 -*-
# by @嗷呜 & Perplexity (Updated 2025-12-02) - 多分辨率选择版
import json
import sys
import threading
import requests
import re
import time
import random
import html as html_parser
from urllib.parse import quote, unquote

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        # 强制使用你提供的反代，保证能拿到页面数据
        self.host = "https://down.nigx.cn/hanime1.me"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Origin': self.host
        }

    def getName(self):
        return "Hanime1"

    def isVideoFormat(self, url):
        return any(ext in (url or '') for ext in ['.m3u8', '.mp4', '.ts'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # =================== 首页与分类 ===================

    def homeContent(self, filter):
        classes = [
            {'type_name': '最新上市', 'type_id': 'latest'},
            {'type_name': '裏番', 'type_id': '裏番'},
            {'type_name': '泡麵番', 'type_id': '泡麵番'},
            {'type_name': 'Motion Anime', 'type_id': 'Motion Anime'},
            {'type_name': '3D動畫', 'type_id': '3D動畫'},
            {'type_name': '同人作品', 'type_id': '同人作品'},
            {'type_name': 'MMD', 'type_id': 'MMD'},
            {'type_name': 'Cosplay', 'type_id': 'Cosplay'},
            {'type_name': '本日排行', 'type_id': 'daily_rank'},
            {'type_name': '本週排行', 'type_id': 'weekly_rank'},
            {'type_name': '本月排行', 'type_id': 'monthly_rank'}
        ]

        sort_filters = [
            {"n": "最新", "v": "最新上市"},
            {"n": "熱門", "v": "人氣爆棚"}
        ]

        filters = {}
        for item in classes:
            filters[item['type_id']] = [
                {"key": "sort", "name": "排序", "value": sort_filters}
            ]

        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        try:
            url = f"{self.host}/search?sort=最新上市"
            content = self.fetch(url, headers=self.getheaders()).text
            vods = self.parse_vod_list(content)
            return {'list': vods}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        sort = extend.get('sort', '最新上市')

        if tid == 'latest':
            url = f"{self.host}/search?sort={sort}&page={page}"
        elif tid == 'daily_rank':
            url = f"{self.host}/search?sort=本日排行&page={page}"
        elif tid == 'weekly_rank':
            url = f"{self.host}/search?sort=本週排行&page={page}"
        elif tid == 'monthly_rank':
            url = f"{self.host}/search?sort=本月排行&page={page}"
        else:
            url = f"{self.host}/search?query={quote(tid)}&sort={sort}&page={page}"

        try:
            content = self.fetch(url, headers=self.getheaders()).text
            vods = self.parse_vod_list(content)
            return {
                'list': vods,
                'page': page,
                'pagecount': page + 1 if len(vods) > 0 else page,
                'limit': 30,
                'total': 9999
            }
        except Exception:
            return {'list': []}

    # =================== 详情页 - 多分辨率版本 ===================

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.host}/watch?v={vid}"

        try:
            html = self.fetch(url, headers=self.getheaders()).text

            # 标题、封面、简介
            title_match = re.search(r'<meta property="og:title" content="(.*?)"', html)
            title = title_match.group(1) if title_match else vid

            pic_match = re.search(r'<meta property="og:image" content="(.*?)"', html)
            pic = pic_match.group(1) if pic_match else ""

            desc_match = re.search(r'<meta property="og:description" content="(.*?)"', html)
            desc = desc_match.group(1) if desc_match else ""

            # 标签功能
            vod_tag_list = []
            rich_tags = []
            
            tag_matches = re.findall(
                r'<div class="single-video-tag"[^>]*>\s*<a[^>]+>(.*?)</a>',
                html, re.S
            )
            
            seen_tags = set()
            for inner_html in tag_matches:
                name = re.sub(r'<[^>]+>', '', inner_html).strip()
                name = re.sub(r'\s*\d+$', '', name).strip()
                name = html_parser.unescape(name).replace('&nbsp;', '')
                
                if name and name not in seen_tags:
                    seen_tags.add(name)
                    vod_tag_list.append(name)
                    target = json.dumps({'id': name, 'name': name}, ensure_ascii=False)
                    rich_tags.append(f'[a=cr:{target}/]{name}[/a]')

            vod_tag_str = ",".join(vod_tag_list)
            vod_content = f"{desc}\n\n🏷️ 标签: {' '.join(rich_tags)}" if rich_tags else desc

            # ========== 多分辨率解析 ==========
            sources = re.findall(r'<source[^>]+src="([^"]+)"', html)
            if not sources:
                sources = re.findall(r'src="([^"]+\.mp4[^"]*)"', html)

            decoded_sources = []
            if sources:
                decoded_sources = [html_parser.unescape(s).replace('&amp;', '&') for s in sources]

            # 智能分辨率分类，支持4K、2K、1080p、720p、480p等
            quality_map = {}
            for s in decoded_sources:
                if '4k' in s.lower() or '2160' in s:
                    quality_map.setdefault('4K', []).append(s)
                elif '2k' in s.lower() or '1440' in s:
                    quality_map.setdefault('2K', []).append(s)
                elif '1080' in s:
                    quality_map.setdefault('1080p', []).append(s)
                elif '720' in s:
                    quality_map.setdefault('720p', []).append(s)
                elif '480' in s:
                    quality_map.setdefault('480p', []).append(s)
                else:
                    quality_map.setdefault('标清', []).append(s)

            # 优先级排序：4K > 2K > 1080p > 720p > 480p > 标清
            quality_order = ['4K', '2K', '1080p', '720p', '480p', '标清']
            play_parts = []
            
            for q in quality_order:
                if q in quality_map and quality_map[q]:
                    best_url = quality_map[q][0]  # 取第一个最佳链接
                    play_url_with_dm = f"{vid}_dm_{best_url}"
                    play_parts.append(f"{q}${play_url_with_dm}")

            # 兜底m3u8
            if not play_parts:
                m3u8_match = re.search(r'source\s*=\s*[\'"](https?://[^\'"]+\.m3u8[^\'"]*)[\'"]', html)
                if m3u8_match:
                    best_url = m3u8_match.group(1).replace('&amp;', '&')
                    play_url_with_dm = f"{vid}_dm_{best_url}"
                    play_parts.append(f"自动${play_url_with_dm}")

            if not play_parts:
                play_parts.append(f"网页播放${url}")

            # 标准播放格式：线路$清晰度1$地址1#清晰度2$地址2#...
            line_name = "书生玩剣ⁱ·*₁＇"
            vod_play_url = f"{line_name}$" + "#".join(play_parts)

            vod = {
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": "Hanime",
                "vod_year": "",
                "vod_area": "Japan",
                "vod_remarks": "Hanime",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": vod_content,
                "vod_tag": vod_tag_str,
                "vod_play_from": line_name,
                "vod_play_url": vod_play_url
            }

            return {'list': [vod]}

        except Exception:
            return {'list': []}

    # =================== 搜索 ===================

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/search?query={quote(key)}&page={pg}"
        try:
            content = self.fetch(url, headers=self.getheaders()).text
            vods = self.parse_vod_list(content)
            return {'list': vods, 'page': pg}
        except Exception:
            return {'list': []}

    # =================== 播放 ===================

    def playerContent(self, flag, id, vipFlags):
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://hanime1.me/',
            'Origin': 'https://hanime1.me'
        }

        if '_dm_' in id:
            vid, url = id.split('_dm_', 1)
            threading.Thread(target=self._preload_danmaku, args=(vid, url)).start()
        else:
            url = id

        if '.mp4' in url or '.m3u8' in url:
            return {'parse': 0, 'playUrl': '', 'url': url, 'header': header}

        return {'parse': 1, 'playUrl': '', 'url': url, 'header': header}

    # =================== 列表解析：保持原样 ===================

    def parse_vod_list(self, html):
        vods = []
        seen = set()

        parts = re.split(r'class="[^"]*search-doujin-videos[^"]*"', html)

        for i in range(1, len(parts)):
            block = parts[i][:4000]
            try:
                url_match = re.search(r'<a[^>]+href="([^"]+)"', block)
                if not url_match: continue
                url = url_match.group(1)

                id_match = re.search(r'v=(\d+)', url)
                if not id_match: continue
                vid = id_match.group(1)

                if vid in seen: continue
                seen.add(vid)

                title = vid
                title_match = re.search(r'class="[^"]*card-mobile-title[^"]*"[^>]*>(.*?)</div>', block)
                if title_match:
                    title = title_match.group(1).strip()

                pic = ""
                img_matches = re.findall(r'<img[^>]+src="([^"]+)"', block)
                found_thumb = False
                for img_src in img_matches:
                    if 'thumbnail' in img_src:
                        pic = img_src
                        found_thumb = True
                        break
                if not found_thumb and len(img_matches) > 1:
                    pic = img_matches[1]
                elif not found_thumb and len(img_matches) > 0:
                    pic = img_matches[0]

                remarks = ""
                dur_match = re.search(r'class="[^"]*card-mobile-duration[^"]*"[^>]*>(.*?)</div>', block)
                if dur_match:
                    remarks = dur_match.group(1).strip()

                vods.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            except Exception:
                pass

        return vods

    # =================== 弹幕支持 ===================

    def localProxy(self, param):
        try:
            xtype = param.get('type', '')
            if xtype == 'hlxdm':
                vid = param.get('path', '')
                times = int(param.get('times', 0))
                comments = self._fetch_comments(vid)
                return self._generate_danmaku_xml(comments, times)
            return [404, 'text/plain', b'']
        except Exception:
            return [500, 'text/plain', b'']

    def _fetch_comments(self, vid):
        """专门解析 Hanime1 的 HTML 评论结构"""
        comments = []
        try:
            url = f"{self.host}/loadComment?id={vid}&type=video&content=comment-tablink"
            res = requests.get(url, headers=self.getheaders(), timeout=5)
            
            # 解析 JSON，获取 comments HTML 字符串
            data = res.json()
            comments_html = data.get('comments', '')
            
            if not comments_html:
                return ["欢迎观看", "Hanime1"]
            
            # 正则提取评论内容：class="comment-index-text" 里的评论正文
            # 匹配第二个 comment-index-text（用户名是第一个，评论是第二个）
            comment_blocks = re.findall(
                r'<div[^>]*class="comment-index-text"[^>]*>(?:[^<]|<[^>]*>)*?</div>\s*<div[^>]*class="comment-index-text"[^>]*>(.*?)</div>',
                comments_html, re.S
            )
            
            # 提取评论文本，去HTML标签
            for block in comment_blocks:
                text = re.sub(r'<[^>]+>', '', block).strip()
                # 过滤纯UI文本，保留真实评论
                if len(text) > 2 and len(text) < 100 and not any(x in text for x in ['加载中', '查看', '回复', '登录', '发表']):
                    comments.append(text)
            
            # 去重并限制数量
            seen = set()
            clean_comments = []
            for c in comments:
                if c not in seen and len(clean_comments) < 60:
                    seen.add(c)
                    clean_comments.append(c)
            
            return clean_comments if clean_comments else ["欢迎观看", "精彩内容"]
            
        except Exception:
            return ["欢迎观看", "Hanime1"]

    def _generate_danmaku_xml(self, comments, duration):
        if duration <= 0:
            duration = 600  # 默认10分钟
            
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<i>']
        xml.append('<d p="0,5,25,16711680,0">弹幕加载成功</d>')
        
        # 如果没评论，添加占位弹幕
        if not comments:
            xml.extend([
                '<d p="5,1,25,16777215,0">暂无评论，欢迎补充~</d>',
                '<d p="15,1,25,16777215,0">Hanime1 高清无码</d>'
            ])
        else:
            # 按视频时长均匀分布评论
            for i, comment in enumerate(comments):
                progress = i / len(comments)
                base_time = progress * duration
                t = round(max(1, min(base_time + random.uniform(-5, 5), duration - 1)), 1)
                
                color = 16777215  # 白色
                if random.random() < 0.15:
                    color = random.randint(0x666666, 0xFFFFFF)
                
                safe_text = html_parser.escape(comment)
                xml.append(f'<d p="{t},1,25,{color},0">{safe_text}</d>')
        
        xml.append('</i>')
        return [200, 'text/xml', '\n'.join(xml)]

    def _preload_danmaku(self, vid, url):
        try:
            time.sleep(1)
            dm_url = f"{self.getProxyUrl()}&path={vid}&times=600&type=hlxdm"
            requests.get(f"http://127.0.0.1:9978/action?do=refresh&type=danmaku&path={quote(dm_url)}", timeout=2)
        except:
            pass

    # =================== 通用工具 ===================

    def getheaders(self, param=None):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Origin': self.host
        }
        return headers
