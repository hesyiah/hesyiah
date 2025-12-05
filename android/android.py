import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
def normalize_path(path):
    """清理路径字符串"""
    return path.strip().strip('"').strip("'")

def read_file_content(filepath):
    if not os.path.exists(filepath):
        return None, "文件不存在"
    try:
        # 尝试 utf-8 读取
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), "OK"
    except Exception as e:
        return None, f"读取错误: {str(e)}"

# ================= 提取模块 =================

def extract_telecom_data(base_path):
    rel_path = r"user_de\0\com.android.server.telecom\files\phone-account-registrar-state.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    content, status = read_file_content(full_path)
    if not content:
        return [("电信服务数据", status, os.path.basename(full_path))]
    results = []
    phone_matches = re.findall(r'<(?:handle|subscription_number)>tel:(.*?)</(?:handle|subscription_number)>', content)
    unique_phones = set()
    for p in phone_matches:
        decoded_num = urllib.parse.unquote(p)
        if len(decoded_num) > 5: unique_phones.add(decoded_num)
    results.append(("手机号码", f"{', '.join(unique_phones)}" if unique_phones else "未找到", os.path.basename(full_path)))

    # 提取 ICCID
    iccid_matches = re.findall(r'<id>(\d{18,22})</id>', content)
    unique_ids = set(iccid_matches)
    results.append(("ICCID (SIM卡号)", f"{', '.join(unique_ids)}" if unique_ids else "未找到", os.path.basename(full_path)))

    return results

def extract_imsi_contacts(base_path):
    """模块2: 联系人配置 (IMSI)"""
    rel_path = r"data\com.android.contacts\shared_prefs\com.android.contacts_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    content, status = read_file_content(full_path)

    if not content:
        return [("IMSI (用户识别码)", "文件不存在", os.path.basename(full_path))]

    matches = re.findall(r'\D(460\d{12})\D', content)
    return [("IMSI (用户识别码)", f"{matches[0]}" if matches else "未找到", os.path.basename(full_path))]

def extract_imei_enhanced(base_path):
    """模块3: 电话配置 (IMEI) - 过滤 MEID/ICCID"""
    rel_path = r"user_de\0\com.android.phone\shared_prefs\com.android.phone_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    content, status = read_file_content(full_path)

    if not content:
         return [("IMEI (设备识别码)", status, os.path.basename(full_path))]
    
    found_imeis = set()
    # 策略: 键名匹配 + 15位数字校验
    key_pattern = r'<string name="[^"]*?(?:imei|device_id)[^"]*?">(\d{15})</string>'
    matches = re.findall(key_pattern, content, re.IGNORECASE)
    found_imeis.update(matches)

    # 兜底: 简单正则 (排除 IMSI)
    if not found_imeis:
        raw_matches = re.findall(r'>(\d{15})<', content)
        for m in raw_matches:
            if not m.startswith('460'): found_imeis.add(m)

    return [("IMEI (设备识别码)", f"{', '.join(found_imeis)}" if found_imeis else "⚠️ 未找到", os.path.basename(full_path))]

def extract_wifi_info(base_path):
    rel_path = r"misc\wifi\WifiConfigStore.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    content, status = read_file_content(full_path)
    if not content:
        return [("Wi-Fi 信息", "文件不存在", os.path.basename(full_path))]
    results = []
    ssid_matches = re.findall(r'&quot;(.*?)&quot;', content)
    if not ssid_matches:
        ssid_matches = re.findall(r'<string name="SSID">"(.*?)"</string>', content)
    unique_ssids = set(ssid_matches)
    ssid_display = ', '.join(list(unique_ssids)[:5]) + (f" (共{len(unique_ssids)}个...)" if len(unique_ssids)>5 else "")
    if unique_ssids:
        results.append(("历史 Wi-Fi 名称", f"{ssid_display}", os.path.basename(full_path)))
    else:
        results.append(("历史 Wi-Fi 名称", "", os.path.basename(full_path)))
    mac_regex = r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})'
    mac_matches = re.findall(mac_regex, content)
    valid_macs = {m for m in mac_matches if m != "00:00:00:00:00:00" and m.lower() != "ff:ff:ff:ff:ff:ff"}
    mac_display = ', '.join(list(valid_macs)[:3]) + (f" (共{len(valid_macs)}个...)" if len(valid_macs)>3 else "")
    if valid_macs:
        results.append(("Wi-Fi MAC/BSSID", f"{mac_display}", os.path.basename(full_path)))
    else:
        results.append(("Wi-Fi MAC/BSSID", "未找到", os.path.basename(full_path)))
    return results
def main():
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        print("请输入手机数据提取的【根文件夹】路径:")
        base_path = input(">>> ")
    base_path = normalize_path(base_path)
    print(f"\n正在分析: {base_path}")
    print("-" * 100)
    print(f"{'目标信息':<18} | {'提取结果':<50} | {'来源文件'}")
    print("-" * 100)
    all_results = []
    all_results.extend(extract_telecom_data(base_path))  
    all_results.extend(extract_imsi_contacts(base_path)) 
    all_results.extend(extract_imei_enhanced(base_path)) 
    all_results.extend(extract_wifi_info(base_path))    
    for name, res, source in all_results:
        if len(res) > 50:
            res_print = res[:47] + "..."
        else:
            res_print = res
        print(f"{name:<18} | {res_print:<50} | {source}")
if __name__ == "__main__":
    main()