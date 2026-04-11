import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random

class ElectricityCrawler:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.visited_urls_file = "visited_urls.json"
        self.visited_urls = self.get_visited_urls()
        self.max_depth = 3  # 最大爬取深度
        self.base_urls = [
            # 官方网站
            "https://www.epri.sgcc.com.cn/",  # 国家电网电力科学研究院
            "https://www.cec.org.cn/",  # 中国电力企业联合会
            "https://www.sgcc.com.cn/",  # 国家电网公司
            "https://www.csg.cn/",  # 中国南方电网
            "https://www.nea.gov.cn/",  # 国家能源局
            
            # 行业网站
            "https://www.pcsee.org/",  # 电力系统自动化
            "https://www.ee.cn/",  # 中国电力新闻网
            "https://www.electricitychina.com/",  # 中国电力网
            "https://www.chinapower.com.cn/",  # 中国电力网
            "https://www.powergridtech.com/",  # 电网技术
            
            # 文库和百科
            "https://wenku.baidu.com/",  # 百度文库
            "https://www.zhihu.com/",  # 知乎
            "https://baike.baidu.com/",  # 百度百科
            "https://www.wikiwand.com/zh/",  # Wikiwand
            
            # 技术论坛
            "https://www.dianyuan.com/",  # 电源网
            "https://www.elecfans.com/",  # 电子发烧友
            "https://www.eepw.com.cn/",  # 电子工程世界
            
            # 高校和研究机构
            "https://ee.tsinghua.edu.cn/",  # 清华大学电机工程与应用电子技术系
            "https://ee.pku.edu.cn/",  # 北京大学电子学系
            "https://www.uestc.edu.cn/",  # 电子科技大学
            
            # 标准和规范
            "https://www.gb688.cn/bzgk/gb/",  # 国家标准全文公开系统
            "https://www.sac.gov.cn/",  # 国家标准化管理委员会
            "https://www.iec.ch/",  # 国际电工委员会
            "https://www.ansi.org/"  # 美国国家标准学会
        ]
        self.keywords = [
            "电力巡检", "电力设备", "变压器", "断路器", "线路故障", 
            "电力安全", "电力培训", "电力规范", "故障处理", "电力运维",
            "电网", "配电", "输电", "变电", "电力工程"
        ]
    
    def get_visited_urls(self) -> set:
        """获取已访问的URL列表"""
        if os.path.exists(self.visited_urls_file):
            with open(self.visited_urls_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    
    def save_visited_urls(self):
        """保存已访问的URL列表"""
        with open(self.visited_urls_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.visited_urls), f, ensure_ascii=False, indent=2)
    
    def is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    
    def get_page_content(self, url: str) -> str:
        """获取页面内容"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"获取页面内容失败: {url}, 错误: {e}")
            return ""
    
    def extract_text(self, html: str) -> str:
        """从HTML中提取文本"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(['script', 'style']):
            script.decompose()
        
        # 提取文本
        text = soup.get_text()
        
        # 清理文本
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def should_crawl(self, url: str) -> bool:
        """判断是否应该爬取该URL"""
        if url in self.visited_urls:
            return False
        
        # 过滤掉一些不需要的URL
        unwanted_patterns = [
            'javascript:', 'mailto:', '.pdf', '.jpg', '.png', '.gif',
            'login', 'register', 'signin', 'signup', 'user', 'profile'
        ]
        for pattern in unwanted_patterns:
            if pattern in url:
                return False
        
        # 检查是否包含关键词
        for keyword in self.keywords:
            if keyword in url:
                return True
        
        # 检查是否是文章页面
        article_patterns = ['article', 'news', 'report', 'content', 'detail', 'post', 'blog']
        for pattern in article_patterns:
            if pattern in url.lower():
                return True
        
        return False
    
    def save_content(self, content: str, url: str):
        """保存内容到文件"""
        if len(content) < 500:  # 过滤掉太短的内容
            return
        
        # 生成文件名
        filename = url.split('/')[-1]
        if not filename:
            filename = url.split('/')[-2]
        filename = filename.replace('.', '_').replace('?', '_').replace('&', '_') + '.txt'
        filepath = os.path.join(self.data_dir, filename)
        
        # 保存内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"来源: {url}\n\n{content}")
        
        print(f"保存文件: {filename}")
    
    def crawl(self, url: str, depth: int = 0):
        """爬取单个URL，支持深度控制"""
        if not self.is_valid_url(url) or url in self.visited_urls or depth >= self.max_depth:
            return
        
        print(f"爬取 (深度: {depth}): {url}")
        self.visited_urls.add(url)
        
        # 获取页面内容
        html = self.get_page_content(url)
        if not html:
            return
        
        # 提取文本并保存
        text = self.extract_text(html)
        
        # 检查内容是否包含电力相关关键词
        has_keyword = False
        for keyword in self.keywords:
            if keyword in text:
                has_keyword = True
                break
        
        # 只有包含关键词且长度足够的内容才保存
        if has_keyword or any(pattern in url.lower() for pattern in ['article', 'news', 'report', 'content', 'detail', 'post', 'blog']):
            self.save_content(text, url)
        
        # 提取链接
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # 处理链接
        for link in links:
            href = link.get('href')
            full_url = urljoin(url, href)
            
            if self.should_crawl(full_url):
                # 随机延迟，避免被反爬
                time.sleep(random.uniform(1, 3))
                self.crawl(full_url, depth + 1)
    
    def run(self):
        """运行爬虫"""
        try:
            print(f"开始爬取，共{len(self.base_urls)}个网站")
            print(f"最大爬取深度: {self.max_depth}")
            for i, base_url in enumerate(self.base_urls):
                print(f"爬取网站 {i+1}/{len(self.base_urls)}: {base_url}")
                self.crawl(base_url, depth=0)
                # 每爬取一个基础URL后保存已访问的URL
                self.save_visited_urls()
                # 休息一段时间
                time.sleep(random.uniform(5, 10))
            print("所有网站爬取完毕，爬虫停止运行")
        except KeyboardInterrupt:
            print("爬虫被手动停止")
        finally:
            # 保存已访问的URL
            self.save_visited_urls()
            print("爬虫结束")

if __name__ == "__main__":
    crawler = ElectricityCrawler(data_dir="../data")
    crawler.run()
