import os
import re
import sys
import urllib.parse  # 用于解码 %2B 为 +

def normalize_path(path):
    return path.strip().strip('"').strip("'")

def read_file_content(filepath):
    if not os.path.exists(filepath):
        return None, "❌ 文件不存在"
    try:
        # 尝试 utf-8 读取，如果失败尝试 latin-1
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), "OK"
    except Exception as e:
        return None, f"❌ 读取错误: {str(e)}"

def extract_from_telecom_registrar(base_path):
    """
    专门解析 phone-account-registrar-state.xml
    提取：手机号 (handle/subscription_number), ICCID (id), 运营商 (label)
    """
    rel_path = r"user_de\0\com.android.server.telecom\files\phone-account-registrar-state.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    
    content, status = read_file_content(full_path)
    if not content:
        return [("电信服务数据", status, full_path)]

    extracted_data = []

    # 1. 提取手机号 (处理 URL 编码，如 %2B -> +)
    # 匹配 <handle>tel:xxx</handle> 或 <subscription_number>tel:xxx</subscription_number>
    phone_matches = re.findall(r'<(?:handle|subscription_number)>tel:(.*?)</(?:handle|subscription_number)>', content)
    
    unique_phones = set()
    for p in phone_matches:
        # 解码，例如把 %2B86177... 解码为 +86177...
        decoded_num = urllib.parse.unquote(p)
        if len(decoded_num) > 5:  # 过滤掉过短的无效字符
            unique_phones.add(decoded_num)
    
    if unique_phones:
        extracted_data.append(("手机号码", f"✅ {', '.join(unique_phones)}", full_path))
    else:
        extracted_data.append(("手机号码", "⚠️ 未找到号码", full_path))

    # 2. 提取 ICCID (SIM卡物理卡号，通常在 <id> 标签内，8986开头)
    # XML 片段: <id>89860321245124114178</id>
    id_matches = re.findall(r'<id>(\d{18,22})</id>', content)
    if id_matches:
        # 去重
        unique_ids = list(set(id_matches))
        extracted_data.append(("ICCID (SIM卡号)", f"✅ {', '.join(unique_ids)}", full_path))
    else:
        extracted_data.append(("ICCID (SIM卡号)", "⚠️ 未找到", full_path))

    # 3. 提取运营商标签
    # XML 片段: <label>中国电信</label>
    label_matches = re.findall(r'<label>(.*?)</label>', content)
    if label_matches:
         extracted_data.append(("运营商", f"✅ {', '.join(set(label_matches))}", full_path))

    return extracted_data

def extract_imsi_fallback(base_path):
    """
    尝试从 contacts_preferences 中查找真正的 IMSI (460开头)
    """
    rel_path = r"data\com.android.contacts\shared_prefs\com.android.contacts_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    
    content, status = read_file_content(full_path)
    if not content:
        return ("IMSI (从联系人)", "❌ 文件不存在或无法读取", full_path)

    # 匹配 460 开头的 15 位数字
    matches = re.findall(r'\D(460\d{12})\D', content)
    if matches:
        return ("IMSI (从联系人)", f"✅ {matches[0]}", full_path)
    else:
        return ("IMSI (从联系人)", "⚠️ 未找到 460 开头的IMSI", full_path)

def extract_imei_fallback(base_path):
    """
    尝试提取 IMEI
    """
    rel_path = r"user_de\0\com.android.phone\shared_prefs\com.android.phone_preferences.xml"
    full_path = os.path.join(base_path, os.path.normpath(rel_path))
    content, status = read_file_content(full_path)
    if not content:
         return ("IMEI", status, full_path)
    
    # 宽泛匹配 15 位数字，通常 IMEI 以 35, 86, 99 开头
    matches = re.findall(r'\D(\d{15})\D', content)
    valid_imeis = [m for m in matches if not m.startswith('460') and not m.startswith('8986')]
    
    if valid_imeis:
        return ("IMEI", f"✅ {valid_imeis[0]}", full_path)
    else:
        return ("IMEI", "⚠️ 未找到明显 IMEI", full_path)

def main():
    print("=== Android 关键数据提取 (增强版) ===")
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        print("请输入手机提取数据的【根文件夹】路径：")
        base_path = input(">>> ")

    base_path = normalize_path(base_path)
    print(f"\n正在分析路径: {base_path}")
    print("=" * 90)
    print(f"{'目标信息':<15} | {'提取结果':<40} | {'来源文件'}")
    print("-" * 90)

    # 1. 执行核心提取 (针对你提供的 XML)
    telecom_results = extract_from_telecom_registrar(base_path)
    for name, res, path in telecom_results:
        print(f"{name:<15} | {res:<40} | {os.path.basename(path)}")

    # 2. 执行补充提取 (IMSI 和 IMEI)
    imsi_res = extract_imsi_fallback(base_path)
    print(f"{imsi_res[0]:<15} | {imsi_res[1]:<40} | {os.path.basename(imsi_res[2])}")

    imei_res = extract_imei_fallback(base_path)
    print(f"{imei_res[0]:<15} | {imei_res[1]:<40} | {os.path.basename(imei_res[2])}")
    
    print("=" * 90)
    print("提示: ICCID (8986...) 是 SIM 卡硬件号，IMSI (460...) 是网络识别号。")

if __name__ == "__main__":
    main()