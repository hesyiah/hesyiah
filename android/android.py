import os
import sys

# 定义要查找的目标文件/文件夹清单
# 键为描述，值为相对路径
TARGETS = {
    "IMSI (联系人配置)": r"data\com.android.contacts\shared_prefs\com.android.contacts_preferences.xml",
    "缩略图缓存 (小米)": r"media\0\Android\data\com.miui.gallery\files\gallery_disk_cache",
    "安卓电话服务数据": r"user_de\0\com.android.server.telecom\files\phone-account-registrar-state.xml",
    "IMEI (电话配置)": r"user_de\0\com.android.phone\shared_prefs\com.android.phone_preferences.xml",
    "Wi-Fi 配置/MAC地址": r"misc\wifi\WifiConfigStore.xml"
}

def normalize_path(path):
    """
    清理路径，去除首尾的空白和引号
    """
    return path.strip().strip('"').strip("'")

def check_files(base_path):
    if not os.path.exists(base_path):
        print(f"\n[错误] 路径不存在: {base_path}")
        return

    print(f"\n正在扫描根目录: {base_path}")
    print("=" * 80)
    print(f"{'描述':<25} | {'状态':<12} | {'相对路径'}")
    print("-" * 80)

    found_count = 0

    for desc, relative_path in TARGETS.items():
        # 1. 处理相对路径：去除开头的斜杠，防止 os.path.join 将其视为绝对路径
        clean_rel_path = relative_path.lstrip("\\").lstrip("/")
        
        # 2. 根据操作系统规范化路径分隔符 (Windows用\, Linux用/)
        clean_rel_path = os.path.normpath(clean_rel_path)
        
        # 3. 拼接完整路径
        full_path = os.path.join(base_path, clean_rel_path)

        # 4. 检查是否存在
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                status = "✅ 目录存在"
            else:
                status = "✅ 文件存在"
            found_count += 1
        else:
            status = "❌ 未找到"

        # 5. 输出结果 (使用 ljust 对齐)
        # 注意：包含中文字符时对齐可能略有偏差，这是终端字体特性
        print(f"{desc:<25} | {status:<12} | {clean_rel_path}")

    print("=" * 80)
    print(f"扫描完成。共找到 {found_count} / {len(TARGETS)} 个项目。")

if __name__ == "__main__":
    # 获取用户输入路径
    # 方式1：通过命令行参数传入 python script.py "D:\MobileDump"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    # 方式2：直接运行脚本后输入
    else:
        print("请提供手机数据提取的【根文件夹】路径。")
        print("例如：D:\\Case001\\Extraction\\data 或者 root\\")
        target_dir = input("请输入路径: ")

    target_dir = normalize_path(target_dir)
    check_files(target_dir)