import os
import time
import re
import urllib.request
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

# 创建保存图片的文件夹
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def safe_filename(name):
    # Windows 文件名非法字符替换
    cleaned = re.sub(r'[\\/:*?"<>|]+', '_', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or 'unknown'


def download_image(url, save_path):
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(save_path, 'wb') as f:
            f.write(data)
        return True
    except Exception:
        return False

# 初始化浏览器
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    # 伪装User-Agent
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # 反自动化检测
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    chromedriver_path = r'D:/workspace/TFT_Copilot/lib/chromedriver/chromedriver.exe'
    driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """
    })
    return driver

# 截图并裁剪3D模型区域
def screenshot_and_crop(driver, save_path, crop_box=None):
    driver.save_screenshot(save_path)
    if crop_box:
        img = Image.open(save_path)
        img = img.crop(crop_box)
        img.save(save_path)


def get_hero_cards(driver):
    # 新版页面英雄入口是 /champions/{slug} 的 a 标签
    selectors = [
        'main a[href^="/champions/"][id]',
        'main a[href^="/champions/"]',
        'a[href^="/champions/"]',
    ]
    for selector in selectors:
        cards = driver.find_elements(By.CSS_SELECTOR, selector)
        filtered = []
        seen = set()
        for card in cards:
            href = (card.get_attribute('href') or '').strip()
            text = (card.text or '').strip()
            if not href or '/champions/' not in href:
                continue
            # 过滤顶部导航中的“英雄”链接
            if href.rstrip('/').endswith('/champions'):
                continue
            if not text:
                continue
            if href in seen:
                continue
            seen.add(href)
            filtered.append(card)
        if filtered:
            return filtered
    return []


def get_skin_links(driver):
    # 新版英雄详情页皮肤链接一般跳转到 /model-viewer?id=xxxx
    selectors = [
        'main a[href*="/model-viewer?id="]',
        'a[href*="/model-viewer?id="]',
    ]
    for selector in selectors:
        skins = driver.find_elements(By.CSS_SELECTOR, selector)
        filtered = []
        seen = set()
        for skin in skins:
            href = (skin.get_attribute('href') or '').strip()
            name = (skin.text or '').strip()
            # 获取皮肤图片url
            img_els = skin.find_elements(By.TAG_NAME, 'img')
            img_url = img_els[0].get_attribute('src') if img_els else ''
            if not href or 'model-viewer?id=' not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            filtered.append({
                'name': name or 'default_skin',
                'href': href,
                'img_url': img_url
            })
        if filtered:
            return filtered
    return []

# 主流程
def main():
    base_url = 'https://3d.buguoguo.cn/champions'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.abspath(os.path.join(script_dir, '..'))
    heros_root = os.path.join(workspace_dir, 'heros')
    debug_html_path = os.path.join(workspace_dir, 'page_debug.html')

    driver = get_driver()
    driver.get(base_url)

    # 显式等待页面元素加载
    try:
        WebDriverWait(driver, 30).until(lambda d: len(get_hero_cards(d)) > 0)
    except Exception as e:
        print('等待英雄列表超时，保存页面源码到 page_debug.html')
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.quit()
        return

    ensure_dir(heros_root)

    hero_cards = get_hero_cards(driver)
    heroes = []
    for card in hero_cards:
        href = (card.get_attribute('href') or '').strip()
        name = (card.text or '').strip()
        icon_el = card.find_elements(By.TAG_NAME, 'img')
        icon_url = icon_el[0].get_attribute('src') if icon_el else ''
        heroes.append({'name': name, 'href': href, 'icon_url': icon_url})

    print(f'共找到{len(heroes)}个英雄')

    for idx, hero in enumerate(heroes):
        try:
            name = hero['name']
            hero_url = hero['href']
            icon_url = hero['icon_url']

            print(f'[{idx+1}] {name} {icon_url}')

            hero_dir = os.path.join(heros_root, safe_filename(name))
            ensure_dir(hero_dir)

            # 下载小图标
            if icon_url:
                download_image(icon_url, os.path.join(hero_dir, 'icon.png'))

            # 进入英雄详情页面
            driver.get(hero_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
            )
            time.sleep(1.0)

            skin_links = get_skin_links(driver)
            print(f'  {name} 有{len(skin_links)}个皮肤')

            for sidx, skin in enumerate(skin_links):
                skin_name = skin['name']
                model_url = skin['href']
                skin_img_url = skin['img_url']
                # 优先取文字名，空则用序号名
                skin_title = safe_filename(skin_name) if skin_name.strip() else f'skin_{sidx+1:03d}'
                skin_dir = os.path.join(hero_dir, skin_title)

                # 检查皮肤文件夹是否已存在，存在则跳过
                if os.path.exists(skin_dir):
                    print(f'    跳过已存在皮肤: {skin_title}')
                    continue

                ensure_dir(skin_dir)

                # 下载皮肤缩略图（如果有）
                if skin_img_url:
                    download_image(skin_img_url, os.path.join(skin_dir, 'skin.png'))  

                # 打开模型页面并截图
                model_url = urllib.parse.urljoin(base_url, model_url)
                driver.get(model_url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                time.sleep(2.5)
                screenshot_path = os.path.join(skin_dir, '3d_model.png')
                screenshot_and_crop(driver, screenshot_path)
                print(f'    已保存皮肤和3D模型图片: {skin_title}')

                # 回到英雄详情页继续抓下一套皮肤
                driver.back()
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
                )
                time.sleep(0.8)

            # 处理完当前英雄后回到英雄列表页
            driver.get(base_url)
            WebDriverWait(driver, 20).until(lambda d: len(get_hero_cards(d)) > 0)
            time.sleep(0.8)
        except Exception as e:
            print(f'处理英雄{name}时出错: {e}')
            driver.get(base_url)
            time.sleep(1.5)

    driver.quit()

if __name__ == '__main__':
    main()
