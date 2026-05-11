"""
每日宏观热点 + 美股资讯自动推送到微信
数据源：DailyHotApi (微博/头条/抖音)
美股数据：AKShare (东方财富数据源，国内直连)
推送方式：Server酱微信推送
"""

import requests
import akshare as ak
import schedule
import time
import logging
from datetime import datetime, timedelta

# ==================== 配置区 ====================
HOT_API_MIRRORS = [
    "https://api-hot.imsyy.top",
    "https://api.guole.fun",
    "https://apinews.geekaso.com",
    "https://api.dailyhot.net",
    "https://dailyhot-api.pages.dev",
]
PLATFORMS = ["weibo", "toutiao", "douyin"]

# 备用数据源：新浪/腾讯热榜
BAIDU_HOT_URL = "https://top.baidu.com/board?tab=realtime"
SINA_HOT_URL = "https://feed.mix.sina.com.cn/api/roll/get?pageid=121&lid=1346&num=50"
TENCENT_HOT_URL = "https://pacaio.match.qq.com/irs/rcd?cid=1&token=49cbb3d5481a9f7e405e1979c03b8d50"

SCKEY_FILE = "sckey.txt"
PUSH_HOUR = 8
PUSH_MINUTE = 0

# 全面过滤黑名单：娱乐八卦 + 社会琐事 + 体育 + 国际花边
FILTER_KEYWORDS = [
    "明星", "绯闻", "综艺", "影视", "网红", "偶像", "粉丝", "出道",
    "恋情", "分手", "结婚", "离婚", "出轨", "整容", "八卦", "热搜第一",
    "演员", "歌手", "导演", "票房", "收视率", "演唱会", "专辑", "单曲",
    "电视剧", "电影", "真人秀", "选秀", "红毯", "颁奖", "影帝", "影后",
    "视帝", "视后", "流量", "饭圈", "应援", "打榜", "控评",
    "爱豆", "塌房", "吃瓜", "瓜", "爆料", "私生活", "花边",
    "肖战", "王一博", "蔡徐坤", "易烊千玺", "迪丽热巴", "杨幂",
    "赵丽颖", "杨洋", "李现", "朱一龙", "王俊凯", "王源",
    "刘亦菲", "刘诗诗", "唐嫣", "Angelababy", "关晓彤",
    "鹿晗", "黄子韬", "吴亦凡", "张艺兴", "范丞丞",
    "娱乐", "追剧", "追星", "嗑CP", "CP", "番位",
    "综艺感", "人设", "翻车", "封杀",
    "春晚", "跨年", "晚会", "直播带货", "带货",
    "抖音网红", "主播", "MCN", "短视频博主",
    "乒乓球", "羽毛球", "篮球", "足球", "世界杯", "奥运会",
    "亚运会", "世锦赛", "中超", "NBA", "CBA", "欧冠",
    "梅西", "C罗", "詹姆斯", "库里", "国足", "女排",
    "赛事", "夺冠", "金牌", "银牌", "决赛", "半决赛",
    "运动员", "教练", "裁判", "比分",
    "国乒", "男团", "女团", "世乒赛", "乒超", "跳水",
    "游泳", "田径", "体操", "举重", "射击", "击剑",
    "二次元", "动漫", "漫画", "cosplay", "手办", "游戏",
    "原神", "崩坏", "王者荣耀", "英雄联盟", "吃鸡",
    "抽卡", "氪金", "手游", "端游", "电竞",
    "消费纠纷", "投诉", "维权", "退货", "差评",
    "外卖", "快递", "网购", "淘宝", "拼多多",
    "宠物", "猫咪", "狗狗", "萌宠",
    "美食", "食谱", "做菜", "打卡", "探店",
    "穿搭", "美妆", "护肤", "口红", "香水",
    "减肥", "健身", "瑜伽", "瘦身",
    "旅游攻略", "景点", "打卡地", "网红店",
    "婚礼", "婚纱", "伴娘", "伴郎",
    "相亲", "恋爱", "情感", "分手", "复合",
    "星座", "算命", "塔罗", "运势",
    "抽奖", "中奖", "锦鲤", "转发",
    "网红", "博主", "UP主", "大V",
    "热搜", "刷屏", "破防", "泪目",
    "皇室", "王妃", "王子", "公主", "国王",
    "选美", "模特", "走秀",
]

# 国内宏观级别关键词（只有命中这些才归入国内要事）
DOMESTIC_MACRO_KEYWORDS = [
    "国务院", "政策", "经济", "GDP", "央行", "降准", "降息",
    "发改委", "财政部", "商务部", "工信部", "证监会", "银保监", "金监总局",
    "利率", "通胀", "通缩", "CPI", "PPI", "PMI",
    "房地产", "楼市", "限购", "房贷", "首付",
    "股市", "A股", "注册制", "退市", "IPO",
    "基金", "债券", "国债", "地方债",
    "财政", "税收", "减税", "专项债", "赤字",
    "产业", "新能源", "光伏", "风电", "储能", "锂电",
    "芯片", "半导体", "国产替代", "自主可控",
    "AI", "人工智能", "大模型", "算力", "数据要素",
    "5G", "6G", "数字经济", "信创",
    "稀土", "锂矿", "铜", "铝", "钢铁",
    "粮食", "猪肉", "农产品",
    "石油", "天然气", "煤炭", "电力",
    "碳", "双碳", "碳中和", "排放",
    "基建", "一带一路", "重大工程",
    "反腐", "纪检", "巡视", "落马",
    "立法", "监管", "反垄断", "合规",
    "自贸区", "自贸港", "开发区",
    "医保", "集采", "创新药",
    "军工", "国防", "航天", "卫星",
    "人口", "生育", "养老", "延迟退休",
    "就业", "失业率",
    "进出口", "贸易", "顺差", "逆差",
    "消费", "内需", "扩内需",
    "金融", "银行", "保险", "信托",
    "汇率", "人民币", "外汇",
    "并购", "重组", "混改",
    "产能", "供给侧", "去产能",
    "补贴", "扶持", "激励",
    "试点", "推广", "落地",
    "国安部", "公安部", "外交部", "国防部", "司法部",
    "自然资源部", "生态环境部", "住建部", "交通部", "水利部",
    "农业农村部", "卫健委", "应急管理部", "审计署", "统计局",
    "网信办", "发改委", "科技部", "教育部", "文旅部",
    "关税", "关税政策", "出口退税", "外资", "引进外资",
    "国企改革", "央企", "地方政府", "债务", "化债",
    "货币政策", "财政政策", "宏观调控", "定向降准", "结构性降息",
    "数字人民币", "央行数字货币", "跨境支付", "金融稳定",
    "科创板", "创业板", "北交所", "ST", "重组上市",
    "北向资金", "南向资金", "QFII", "MSCI", "富时罗素",
    "行业整顿", "行业规范", "整治", "清理", "排查",
    "安全", "网络安全", "数据安全", "信息安全", "供应链安全",
]

# 全球金融影响级别关键词（只有命中这些才归入全球要事）
INTERNATIONAL_FINANCE_KEYWORDS = [
    "美联储", "加息", "降息", "缩表", "扩表", "点阵图",
    "非农", "就业数据", "失业率", "CPI", "PCE",
    "美国", "欧盟", "欧洲", "英国", "法国", "德国",
    "日本", "日本央行", "韩元", "韩国",
    "俄罗斯", "乌克兰", "中东", "以色列", "伊朗",
    "关税", "贸易战", "制裁", "脱钩", "封锁", "禁令",
    "原油", "黄金", "铜", "大宗商品", "LME",
    "美元", "美债", "收益率", "倒挂",
    "纳指", "标普", "道指", "美股",
    "地缘", "冲突", "战争", "军事", "军演",
    "北约", "G7", "G20", "APEC", "IMF", "世界银行",
    "外交", "峰会", "协议", "条约",
    "芯片禁令", "出口管制", "实体清单",
    "核", "导弹", "太空", "卫星",
    "汇率", "人民币", "日元", "欧元", "英镑",
    "避险", "风险偏好", "恐慌指数", "VIX",
    "供应链", "断供", "替代",
    "碳关税", "ESG",
    "OPEC", "减产", "增产",
]

# 炒股视角板块映射
SECTOR_IMPACT_MAP = {
    "降准": "利好银行/地产", "降息": "利好地产/消费", "加息": "利空成长股",
    "房地产": "关注地产链", "楼市": "关注地产链", "限购": "关注地产链",
    "芯片": "关注半导体", "半导体": "关注半导体", "国产替代": "关注半导体",
    "AI": "关注算力/大模型", "人工智能": "关注算力/大模型", "大模型": "关注算力/大模型",
    "新能源": "关注新能源链", "光伏": "关注新能源链", "风电": "关注新能源链",
    "锂电": "关注锂电链", "储能": "关注储能链",
    "原油": "关注石油/化工", "石油": "关注石油/化工",
    "黄金": "关注黄金板块", "铜": "关注有色板块",
    "美联储": "关注外资流向", "非农": "关注外资流向",
    "关税": "关注出口链/替代", "制裁": "关注自主可控",
    "医保": "关注医药板块", "集采": "关注医药板块",
    "军工": "关注军工板块", "国防": "关注军工板块",
    "碳": "关注碳中和", "双碳": "关注碳中和",
    "稀土": "关注稀土板块", "锂矿": "关注锂矿板块",
    "猪肉": "关注养殖板块", "粮食": "关注农业板块",
    "人民币": "关注汇率敏感股", "汇率": "关注汇率敏感股",
    "并购": "关注重组概念", "重组": "关注重组概念",
    "退市": "注意避险", "IPO": "关注打新",
    "地缘": "关注避险/军工", "冲突": "关注避险/军工",
    "OPEC": "关注石油链", "减产": "关注石油链",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def fetch_hot_data():
    """抓取三个平台热榜数据并聚合去重，自动尝试多个镜像"""
    all_items = []
    seen_titles = set()

    for platform in PLATFORMS:
        success = False
        for base_url in HOT_API_MIRRORS:
            url = f"{base_url}/{platform}"
            try:
                logger.info(f"请求热榜接口: {url}")
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 200:
                    logger.warning(f"[{platform}] 接口返回非200: {data.get('message')}")
                    continue

                items = data.get("data", [])
                logger.info(f"[{platform}] 获取到 {len(items)} 条热点")

                for item in items:
                    title = item.get("title", "").strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    all_items.append({
                        "title": title,
                        "desc": item.get("desc", "").strip(),
                        "hot": item.get("hot", 0),
                        "platform": platform,
                        "url": item.get("url", ""),
                    })

                success = True
                break

            except Exception as e:
                logger.warning(f"[{platform}] 镜像 {base_url} 请求失败: {e}")
                continue

        if not success:
            logger.error(f"[{platform}] 所有镜像均请求失败")

    if len(all_items) == 0:
        logger.info("所有主要数据源失败，尝试备用数据源...")
        all_items.extend(fetch_sina_hot())
        all_items.extend(fetch_tencent_hot())
        
        seen_titles = set()
        unique_items = []
        for item in all_items:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                unique_items.append(item)
        all_items = unique_items

    logger.info(f"聚合去重后共 {len(all_items)} 条热点")
    return all_items


def fetch_sina_hot():
    """获取新浪热榜数据"""
    items = []
    try:
        logger.info(f"请求新浪热榜接口: {SINA_HOT_URL}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(SINA_HOT_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("result", {}).get("status") != 0:
            logger.warning("新浪热榜接口返回非成功状态")
            return items

        for item in data.get("result", {}).get("data", []):
            title = item.get("title", "").strip()
            if title:
                items.append({
                    "title": title,
                    "desc": item.get("summary", "").strip(),
                    "hot": item.get("hot", 0) or item.get("viewCount", 0),
                    "platform": "sina",
                    "url": item.get("url", ""),
                })
        
        logger.info(f"[新浪] 获取到 {len(items)} 条热点")
        
    except Exception as e:
        logger.warning(f"新浪热榜请求失败: {e}")
    
    return items


def fetch_tencent_hot():
    """获取腾讯热榜数据"""
    items = []
    try:
        logger.info(f"请求腾讯热榜接口: {TENCENT_HOT_URL}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(TENCENT_HOT_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("data", []):
            title = item.get("title", "").strip()
            if title:
                items.append({
                    "title": title,
                    "desc": item.get("intro", "").strip(),
                    "hot": item.get("hotScore", 0) or item.get("readCount", 0),
                    "platform": "tencent",
                    "url": item.get("url", ""),
                })
        
        logger.info(f"[腾讯] 获取到 {len(items)} 条热点")
        
    except Exception as e:
        logger.warning(f"腾讯热榜请求失败: {e}")
    
    return items


def should_filter(title, desc=""):
    """判断是否应被过滤（娱乐/琐事/体育/花边）"""
    text = title + " " + desc
    for kw in FILTER_KEYWORDS:
        if kw in text:
            return True
    return False


def filter_hot_data(items):
    """过滤非宏观内容"""
    before = len(items)
    filtered = [item for item in items if not should_filter(item["title"], item.get("desc", ""))]
    after = len(filtered)
    logger.info(f"过滤非宏观内容: {before} -> {after} (剔除 {before - after} 条)")
    return filtered


def get_sector_impact(title, desc=""):
    """提取炒股视角板块影响标签"""
    text = title + " " + desc
    impacts = []
    for keyword, impact in SECTOR_IMPACT_MAP.items():
        if keyword in text:
            impacts.append(impact)
    return list(set(impacts))[:2]


def classify_and_summarize(items):
    """将热点分类为国内要事和全球要事，各精选3条，附炒股视角摘要"""
    domestic = []
    international = []
    unclassified = []

    CHINA_KEYWORDS = ["中国", "北京", "上海", "深圳", "广州", "香港", "澳门", "台湾",
                      "大陆", "内地", "国务院", "央行", "发改委", "工信部", "财政部",
                      "证监会", "银保监", "商务部", "外交部", "国防部", "国安部",
                      "A股", "港股", "人民币", "央行", "工信部", "网信办", "科技部"]
    
    FOREIGN_COUNTRIES = ["美国", "日本", "韩国", "朝鲜", "俄罗斯", "乌克兰", 
                         "德国", "法国", "英国", "欧盟", "印度", "越南", "泰国",
                         "新加坡", "马来西亚", "印尼", "菲律宾", "澳大利亚", "新西兰",
                         "加拿大", "墨西哥", "巴西", "阿根廷", "南非", "埃及",
                         "中东", "以色列", "伊朗", "沙特", "阿联酋", "土耳其",
                         "意大利", "西班牙", "荷兰", "瑞士", "瑞典", "挪威"]

    for item in items:
        title = item["title"]
        desc = item.get("desc", "")
        text = title + " " + desc

        is_domestic = any(kw in text for kw in DOMESTIC_MACRO_KEYWORDS)
        is_international = any(kw in text for kw in INTERNATIONAL_FINANCE_KEYWORDS)

        if is_international and not is_domestic:
            international.append(item)
        elif is_domestic:
            domestic.append(item)
        else:
            has_china = any(kw in text for kw in CHINA_KEYWORDS)
            has_foreign = any(kw in text for kw in FOREIGN_COUNTRIES)
            
            if has_china and not has_foreign:
                domestic.append(item)
            elif has_foreign:
                international.append(item)
            else:
                unclassified.append(item)

    domestic.sort(key=lambda x: int(x.get("hot", 0) or 0), reverse=True)
    international.sort(key=lambda x: int(x.get("hot", 0) or 0), reverse=True)



    domestic_top3 = domestic[:3]
    international_top3 = international[:3]

    if len(domestic_top3) < 3 and unclassified:
        unclassified.sort(key=lambda x: int(x.get("hot", 0) or 0), reverse=True)
        needed = 3 - len(domestic_top3)
        domestic_top3.extend(unclassified[:needed])


    if len(international_top3) < 3 and unclassified:
        remaining = [item for item in unclassified if item not in domestic_top3]
        needed = 3 - len(international_top3)
        international_top3.extend(remaining[:needed])


    return domestic_top3, international_top3


def format_stock_summary(item):
    """生成精简摘要，附40字内概要"""
    title = item["title"]
    desc = item.get("desc", "")

    summary = f"**{title}**"

    if desc and len(desc) > 4:
        brief = desc.replace("\n", "").replace("\r", "").strip()
        if len(brief) > 40:
            brief = brief[:40] + "..."
        summary += f"——{brief}"

    return summary


def format_hot_summary(domestic, international):
    """格式化热点摘要文案"""
    lines = []

    lines.append("国内：")
    lines.append("")
    if domestic:
        for i, item in enumerate(domestic, 1):
            lines.append(f"{i}.{format_stock_summary(item)}")
            lines.append("")
    else:
        lines.append("暂无重大国内宏观要事")

    lines.append("国际：")
    lines.append("")
    if international:
        for i, item in enumerate(international, 1):
            lines.append(f"{i}.{format_stock_summary(item)}")
            lines.append("")
    else:
        lines.append("暂无重大全球金融要事")

    return "\n".join(lines)


def fetch_nasdaq_data():
    """通过AKShare获取纳斯达克综合指数数据（东方财富数据源）"""
    try:
        logger.info("请求纳斯达克指数数据 (AKShare/东方财富)...")
        df = ak.index_us_stock_sina(symbol=".IXIC")
        if df is None or df.empty:
            logger.warning("AKShare返回空数据，尝试备用接口...")
            return _fetch_nasdaq_fallback()

        last_row = df.iloc[-1]
        close_price = float(last_row.get("收盘", last_row.get("close", 0)))
        prev_close = float(df.iloc[-2].get("收盘", df.iloc[-2].get("close", 0))) if len(df) >= 2 else None
        date_str = str(last_row.get("日期", last_row.get("date", "")))

        if prev_close and prev_close > 0:
            change = round(close_price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)
        else:
            change = 0
            change_pct = 0

        nasdaq_data = {
            "date": date_str,
            "close": close_price,
            "change": change,
            "change_pct": change_pct,
        }

        logger.info(f"纳指数据: 收盘 {close_price} 涨跌 {change} ({change_pct}%)")
        return nasdaq_data

    except Exception as e:
        logger.warning(f"AKShare获取纳指失败: {e}")
        return _fetch_nasdaq_fallback()


def _fetch_nasdaq_fallback():
    """备用方案：通过新浪财经API直接获取纳指数据"""
    try:
        logger.info("尝试备用接口 (新浪财经)...")
        url = "https://hq.sinajs.cn/list=int_nasdaq"
        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "gbk"
        text = resp.text

        match = text.split('="')
        if len(match) < 2:
            logger.warning("新浪财经接口返回格式异常")
            return None

        parts = match[1].split(",")
        if len(parts) < 4:
            logger.warning("新浪财经数据解析失败")
            return None

        close_price = float(parts[3])
        prev_close = float(parts[2])
        change = round(close_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0
        date_str = parts[30] if len(parts) > 30 else ""

        nasdaq_data = {
            "date": date_str,
            "close": close_price,
            "change": change,
            "change_pct": change_pct,
        }

        logger.info(f"纳指数据(新浪): 收盘 {close_price} 涨跌 {change} ({change_pct}%)")
        return nasdaq_data

    except Exception as e:
        logger.error(f"备用接口也失败: {e}")
        return None


def format_nasdaq_section(nasdaq_data):
    """格式化美股数据文案"""
    lines = []
    lines.append("📊 美股纳指收盘")
    lines.append("━━━━━━━━━━")

    if nasdaq_data:
        arrow = "🔴" if nasdaq_data["change"] < 0 else "🟢"
        sign = "+" if nasdaq_data["change"] > 0 else ""
        lines.append(
            f"纳斯达克综合指数 {nasdaq_data['date']}\n"
            f"收盘: {nasdaq_data['close']}\n"
            f"涨跌: {sign}{nasdaq_data['change']} ({sign}{nasdaq_data['change_pct']}%) {arrow}"
        )
    else:
        lines.append("纳指数据获取失败，请手动查看")

    return "\n".join(lines)


def push_to_wechat(title, content, sckey):
    """通过Server酱推送到微信"""
    try:
        url = f"https://sctapi.ftqq.com/{sckey}.send"
        logger.info(f"推送SCKEY: {sckey[:8]}...")

        payload = {
            "title": title,
            "desp": content,
        }

        resp = requests.post(url, data=payload, timeout=15)
        result = resp.json()

        if result.get("code") == 0:
            logger.info(f"推送成功! msgid: {result.get('data', {}).get('msgid', '')}")
        else:
            logger.error(f"推送失败: {result}")

        return result

    except Exception as e:
        logger.error(f"推送异常: {e}")
        return None


def load_sckey_list():
    """从sckey.txt读取SCKEY列表，每行一个"""
    try:
        with open(SCKEY_FILE, "r", encoding="utf-8") as f:
            keys = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        logger.info(f"从 {SCKEY_FILE} 加载到 {len(keys)} 个SCKEY")
        return keys
    except FileNotFoundError:
        logger.error(f"未找到 {SCKEY_FILE}，请创建并添加SCKEY")
        return []


def push_to_all(title, content):
    """推送给列表中所有人"""
    sckey_list = load_sckey_list()
    if not sckey_list:
        logger.error("SCKEY列表为空，无法推送")
        return
    total = len(sckey_list)
    success = 0
    fail = 0
    logger.info(f"开始推送，共 {total} 人")
    for i, sckey in enumerate(sckey_list, 1):
        logger.info(f"推送进度: {i}/{total}")
        result = push_to_wechat(title, content, sckey)
        if result and result.get("code") == 0:
            success += 1
        else:
            fail += 1
    logger.info(f"推送完成: 成功 {success} 人, 失败 {fail} 人")


def run_task():
    """主任务：抓取 -> 过滤 -> 归纳 -> 美股 -> 推送"""
    logger.info("=" * 50)
    logger.info("开始执行每日资讯推送任务")
    logger.info("=" * 50)

    # 1. 抓取热榜
    all_items = fetch_hot_data()
    if not all_items:
        logger.warning("未获取到任何热点数据，任务终止")
        return

    # 2. 过滤非宏观内容
    filtered = filter_hot_data(all_items)

    # 3. 分类归纳（只保留宏观级别）
    domestic, international = classify_and_summarize(filtered)
    hot_summary = format_hot_summary(domestic, international)

    # 4. 美股数据
    nasdaq_data = fetch_nasdaq_data()
    nasdaq_summary = format_nasdaq_section(nasdaq_data)

    # 5. 组装推送内容
    today = datetime.now().strftime("%Y年%m月%d日")
    title = f"📰 每日宏观热点 | {today}"

    content = f"""
# 📰 每日宏观热点

> {today} 早盘参考

---

{hot_summary}

---

{nasdaq_summary}

---

⚠️ 以上信息仅供参考，不构成投资建议
📡 数据来源: 微博/头条/抖音热榜 + 东方财富
"""

    # 6. 推送
    push_to_all(title, content)

    logger.info("=" * 50)
    logger.info("任务执行完毕")
    logger.info("=" * 50)


def schedule_task():
    """定时任务模式：每天早上8:00执行"""
    schedule_time = f"{PUSH_HOUR:02d}:{PUSH_MINUTE:02d}"
    schedule.every().day.at(schedule_time).do(run_task)
    logger.info(f"定时任务已启动，每天 {schedule_time} 自动推送")
    logger.info("按 Ctrl+C 退出")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        logger.info("启动定时任务模式")
        schedule_task()
    else:
        logger.info("启动手动测试模式 (加 --schedule 参数启动定时任务)")
        run_task()
