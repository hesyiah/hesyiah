import os
import shutil
import datetime
import sys

# ================= 配置区域 =================

# 1. 高版本 (UWP) 特征
MODERN_SIG_FILE = "plum.sqlite"
# 关联文件 (必须一起提取)
MODERN_RELATED_FILES = ["plum.sqlite", "plum.sqlite-wal", "plum.sqlite-shm"]

# 2. 低版本 (Legacy) 特征
LEGACY_SIG_FILE = "StickyNotes.snt"

# ===========================================

def normalize_path(path):
    return path.strip().strip('"').strip("'")

def analyze_and_extract(base_path):
    print(f"🔍 正在深度扫描路径: {base_path}")
    print("⏳ 正在同时搜索 [Windows 10/11 数据库] 和 [Windows 7/8 .snt 文件]...\n")

    # 准备输出目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = os.path.join(os.getcwd(), f"Forensics_StickyNotes_AllVersions_{timestamp}")
    
    found_count = 0

    # 遍历所有子目录
    for root, dirs, files in os.walk(base_path):
        
        # --- 情况 A: 发现高版本 (SQLite) ---
        if MODERN_SIG_FILE in files:
            found_count += 1
            extract_modern(root, output_root, found_count)

        # --- 情况 B: 发现低版本 (.snt) ---
        if LEGACY_SIG_FILE in files:
            found_count += 1
            extract_legacy(root, output_root, found_count)

    print("-" * 80)
    if found_count == 0:
        print("❌ 未找到任何微软便签数据（无论是新版还是旧版）。")
    else:
        print(f"🎉 扫描完成！共提取 {found_count} 处便签数据。")
        print(f"📂 数据已保存在: {output_root}")
        print("💡 提示: .sqlite 使用 DB Browser 查看，.snt 使用 7-Zip 打开或专门工具解析。")

def extract_modern(source_dir, output_root, index):
    """提取高版本 SQLite 数据"""
    # 尝试识别用户名（通常在 Users/xxx/...）
    user_hint = guess_user_from_path(source_dir)
    folder_name = f"{index:02d}_Modern_Win10_{user_hint}"
    dest_dir = os.path.join(output_root, folder_name)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    print(f"[发现 高版本] {source_dir}")
    print(f"  └── 正在提取到: {folder_name}")

    # 提取三个关键文件
    for fname in MODERN_RELATED_FILES:
        src_file = os.path.join(source_dir, fname)
        dst_file = os.path.join(dest_dir, fname)
        
        if os.path.exists(src_file):
            try:
                shutil.copy2(src_file, dst_file)
                print(f"      ✅ 已提取: {fname}")
            except Exception as e:
                print(f"      ❌ 失败 {fname}: {e}")
        else:
            if fname == "plum.sqlite":
                print(f"      ⚠️ 警告: 主数据库丢失")
    print("")

def extract_legacy(source_dir, output_root, index):
    """提取低版本 .snt 数据"""
    user_hint = guess_user_from_path(source_dir)
    folder_name = f"{index:02d}_Legacy_Win7_{user_hint}"
    dest_dir = os.path.join(output_root, folder_name)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    print(f"[发现 低版本] {source_dir}")
    print(f"  └── 正在提取到: {folder_name}")

    # 提取 .snt 文件
    src_file = os.path.join(source_dir, LEGACY_SIG_FILE)
    dst_file = os.path.join(dest_dir, LEGACY_SIG_FILE)

    try:
        shutil.copy2(src_file, dst_file)
        print(f"      ✅ 已提取: {LEGACY_SIG_FILE}")
    except Exception as e:
        print(f"      ❌ 失败: {e}")
    print("")

def guess_user_from_path(path):
    """辅助函数：尝试从路径中提取用户名"""
    parts = path.replace("\\", "/").split("/")
    # 常见的结构是 .../Users/Username/...
    if "Users" in parts:
        try:
            idx = parts.index("Users")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except:
            pass
    # 或者是 .../AppData/... 的前一级
    if "AppData" in parts:
        try:
            idx = parts.index("AppData")
            if idx - 1 >= 0:
                return parts[idx - 1]
        except:
            pass
    return "UnknownUser"

if __name__ == "__main__":
    print("=== 全版本微软便签取证提取工具 ===")
    print("支持: StickyNotes.snt (Win7/8) 和 plum.sqlite (Win10/11)")
    
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        print("请输入取证镜像挂载点或提取出的文件夹路径:")
        target_dir = input(">>> ")

    target_dir = normalize_path(target_dir)
    
    if os.path.exists(target_dir):
        analyze_and_extract(target_dir)
    else:
        print("❌ 路径不存在，请检查。")