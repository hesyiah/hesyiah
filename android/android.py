import os
import re
import sys
import urllib.parse  # 用于解码 %2B 为 +

# ================= 工具函数 =================

def normalize_path(path):
    """清理路径字符串"""
    return path.strip().strip('"').strip("'")

def read_file_content(filepath):
    """安全读取文件内容"""
    if not os.path.exists(filepath):
        return None, "❌ 文件不存在"
    try:
        # 优先尝试 utf-8，失败则忽略错误
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), "OK"
    except Exception as e:
        return None, f"❌ 读取错误: {str(e)}"

# ================= 提取逻辑模块 =================

def extract_telecom_data(base_path):
    """
    模块1：从 phone-account-registrar-state.xml 提取
    目标：手机号, ICCID (Sim卡号), 运营商
    """
    rel_path = r"user_de\0\com.android.server.telecom\files\phone-account-registrar-state.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    
    content, status = read_file_content(full_path)
    if not content:
        return [("电信服务数据", status, os.path.basename(full_path))]

    results = []

    # 1. 手机号 (解码 URL, 如 %2B86...)
    phone_matches = re.findall(r'<(?:handle|subscription_number)>tel:(.*?)</(?:handle|subscription_number)>', content)
    unique_phones = set()
    for p in phone_matches:
        decoded_num = urllib.parse.unquote(p)
        if len(decoded_num) > 5:
            unique_phones.add(decoded_num)
    
    if unique_phones:
        results.append(("手机号码", f"✅ {', '.join(unique_phones)}", os.path.basename(full_path)))
    else:
        results.append(("手机号码", "⚠️ 未找到号码", os.path.basename(full_path)))

    # 2. ICCID (SIM卡物理卡号, 8986开头, 20位)
    # 匹配 <id>8986...</id>
    iccid_matches = re.findall(r'<id>(\d{18,22})</id>', content)
    if iccid_matches:
        results.append(("ICCID (SIM卡号)", f"✅ {', '.join(set(iccid_matches))}", os.path.basename(full_path)))
    else:
        # 尝试从 XML 属性中找
        results.append(("ICCID (SIM卡号)", "⚠️ 未找到", os.path.basename(full_path)))

    # 3. 运营商
    label_matches = re.findall(r'<label>(.*?)</label>', content)
    if label_matches:
         results.append(("运营商", f"✅ {', '.join(set(label_matches))}", os.path.basename(full_path)))

    return results

def extract_imsi_contacts(base_path):
    """
    模块2：从 contacts_preferences.xml 提取
    目标：IMSI (460开头)
    """
    rel_path = r"data\com.android.contacts\shared_prefs\com.android.contacts_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    
    content, status = read_file_content(full_path)
    if not content:
        return [("IMSI (用户识别码)", "❌ 文件不存在", os.path.basename(full_path))]

    # 查找 460 开头的 15 位数字
    # \D 表示前后不是数字，防止截断
    matches = re.findall(r'\D(460\d{12})\D', content)
    if matches:
        return [("IMSI (用户识别码)", f"✅ {matches[0]}", os.path.basename(full_path))]
    else:
        return [("IMSI (用户识别码)", "⚠️ 未找到", os.path.basename(full_path))]

def extract_imei_enhanced(base_path):
    """
    模块3：从 phone_preferences.xml 提取 (增强版)
    目标：IMEI (15位)
    过滤：MEID (14位), ICCID (20位)
    """
    rel_path = r"user_de\0\com.android.phone\shared_prefs\com.android.phone_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    
    content, status = read_file_content(full_path)
    if not content:
         return [("IMEI (设备识别码)", status, os.path.basename(full_path))]
    
    found_imeis = set()

    # 策略 A: 基于您提供的 XML 键名进行精准匹配
    # 匹配 key_imei_slotX, device_id_key, small_device_id_key
    key_pattern = r'<string name="[^"]*?(?:imei|device_id)[^"]*?">(\d{15})</string>'
    matches_keys = re.findall(key_pattern, content, re.IGNORECASE)
    for m in matches_keys:
        found_imeis.add(m)

    # 策略 B: 兜底匹配 (如果键名变了)
    # 查找所有 15 位数字，但必须排除 IMSI (460开头)
    # 注意：IMEI 通常以 86, 35, 99, 01 开头
    value_pattern = r'>(\d{15})<'
    matches_values = re.findall(value_pattern, content)
    for val in matches_values:
        if not val.startswith('460'): # 简单排除 IMSI
            found_imeis.add(val)

    if found_imeis:
        return [("IMEI (设备识别码)", f"✅ {', '.join(found_imeis)}", os.path.basename(full_path))]
    else:
        return [("IMEI (设备识别码)", "⚠️ 未找到有效 IMEI", os.path.basename(full_path))]

# ================= 主程序 =================

def main():
    print("==========================================")
    print("   Android 关键取证数据综合提取工具 v2.0   ")
    print("==========================================\n")
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        print("请提供手机数据提取的【根文件夹】路径")
        print("通常包含 data, user_de, media 等文件夹")
        base_path = input("请输入路径 >>> ")

    base_path = normalize_path(base_path)
    
    if not os.path.exists(base_path):
        print(f"\n[错误] 路径不存在: {base_path}")
        return

    print(f"\n正在扫描: {base_path}")
    print("-" * 95)
    print(f"{'目标信息':<18} | {'提取结果':<45} | {'来源文件'}")
    print("-" * 95)

    all_results = []
    
    # 执行提取
    all_results.extend(extract_telecom_data(base_path))  # 手机号/ICCID
    all_results.extend(extract_imsi_contacts(base_path)) # IMSI
    all_results.extend(extract_imei_enhanced(base_path)) # IMEI (新逻辑)

    # 输出结果
    for name, res, source in all_results:
        print(f"{name:<18} | {res:<45} | {source}")

    print("-" * 95)
    print("扫描完成。")
    print("说明: 若显示 '⚠️'，请确认文件是否存在，或尝试在 shared_prefs 文件夹中手动搜索相关数字。")

if __name__ == "__main__":
    main()