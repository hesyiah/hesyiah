import os
import shutil
import datetime
import sys

# 微软便签的唯一包名标识
STICKY_NOTES_PACKAGE = "Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe"

def normalize_path(path):
    return path.strip().strip('"').strip("'")

def find_and_extract(base_path):
    print(f"正在扫描路径: {base_path}")
    print("这可能需要一些时间，取决于文件夹大小...\n")
    
    found_instances = []

    # 1. 递归遍历目录，寻找便签的特定包名文件夹
    for root, dirs, files in os.walk(base_path):
        if STICKY_NOTES_PACKAGE in dirs:
            # 找到包目录后，拼接出数据存储目录 LocalState
            package_path = os.path.join(root, STICKY_NOTES_PACKAGE)
            local_state_path = os.path.join(package_path, "LocalState")
            
            # 确认 LocalState 是否存在且包含数据库
            if os.path.exists(local_state_path):
                db_path = os.path.join(local_state_path, "plum.sqlite")
                if os.path.exists(db_path):
                    found_instances.append(local_state_path)
    
    if not found_instances:
        print(f"❌ 在该路径下未找到便签数据文件夹 ({STICKY_NOTES_PACKAGE})。")
        return

    print(f"✅ 发现 {len(found_instances)} 个便签数据源。开始提取...\n")

    # 2. 准备输出目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = os.path.join(os.getcwd(), f"Forensics_StickyNotes_{timestamp}")
    
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)

    print(f"{'源路径 (相对)':<40} | {'提取结果':<20} | {'包含文件'}")
    print("-" * 80)

    # 3. 遍历提取每个发现的实例
    count = 0
    for src_dir in found_instances:
        count += 1
        # 为了区分不同用户，尝试从路径中提取用户名，或者简单的使用序号
        # 路径通常包含 ...\Users\用户名\AppData...
        user_folder_name = f"Instance_{count}"
        
        # 简单的路径分析尝试提取用户名
        parts = src_dir.split(os.sep)
        if "Users" in parts:
            try:
                user_index = parts.index("Users") + 1
                if user_index < len(parts):
                    user_folder_name = f"User_{parts[user_index]}"
            except:
                pass
        
        # 创建该实例的独立保存文件夹
        dest_dir = os.path.join(base_output_dir, user_folder_name)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # 需要提取的文件列表
        target_files = ["plum.sqlite", "plum.sqlite-wal", "plum.sqlite-shm"]
        extracted_files = []

        for fname in target_files:
            f_src = os.path.join(src_dir, fname)
            f_dst = os.path.join(dest_dir, fname)
            
            if os.path.exists(f_src):
                try:
                    shutil.copy2(f_src, f_dst)
                    extracted_files.append(fname)
                except Exception as e:
                    print(f"[错误] 复制 {fname} 失败: {e}")

        # 输出状态
        relative_path = "..." + src_dir[-40:] if len(src_dir) > 40 else src_dir
        status = "✅ 成功" if extracted_files else "⚠️ 失败"
        file_list_str = ", ".join(extracted_files)
        
        print(f"{relative_path:<40} | {status:<20} | {file_list_str}")

    print("-" * 80)
    print(f"🎉 提取完成。数据已保存在脚本所在目录下的文件夹：")
    print(f"📂 {base_output_dir}")

if __name__ == "__main__":
    print("=== Windows 便签取证提取工具 ===")
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        print("请提供取证镜像挂载点或提取出的文件夹路径")
        print("例如: E:\\CaseData\\DiskImage\\Users 或 D:\\Export\\Root")
        target_dir = input("请输入路径: ")

    target_dir = normalize_path(target_dir)
    
    if os.path.exists(target_dir):
        find_and_extract(target_dir)
    else:
        print("❌ 输入的路径不存在，请检查。")