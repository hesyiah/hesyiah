import os
import shutil

# --- 你的目标目录 ---
DEST_DIR = r"E:\expo\hive"

# 需要提取的系统文件
SYSTEM_HIVES = ["SAM", "SYSTEM", "SOFTWARE", "SECURITY", "DEFAULT"]
LOG_EXTENSIONS = [".LOG1", ".LOG2"]

def flat_copy(src_path, dest_dir, new_name=None):
    """
    扁平化复制：直接复制到目标根目录
    如果指定了 new_name，则改名（防止 NTUSER.DAT 冲突）
    同时自动处理 .LOG 日志文件，保持文件名一致
    """
    if not os.path.exists(src_path): return False
    
    # 确定目标文件名
    original_name = os.path.basename(src_path)
    target_name = new_name if new_name else original_name
    
    dest_path = os.path.join(dest_dir, target_name)
    
    try:
        shutil.copy2(src_path, dest_path)
        print(f"    [√] {target_name}")  # 只显示文件名，不显示冗长路径
        
        # 连带复制日志文件，并保持重命名逻辑
        # 例如: NTUSER.DAT -> NTUSER_张三.DAT
        #       NTUSER.DAT.LOG1 -> NTUSER_张三.DAT.LOG1
        for ext in LOG_EXTENSIONS:
            log_src = src_path + ext
            if os.path.exists(log_src):
                log_dest = dest_path + ext # 基于新名字加后缀
                shutil.copy2(log_src, log_dest)
                
    except Exception as e:
        print(f"    [X] 失败 {target_name}: {e}")

def locate_system_root(start_path):
    """ 定位 Windows 根目录和 Config 目录 """
    # 逻辑同上一版，确保能识别 X-Ways 导出的复杂路径
    check_1 = os.path.join(start_path, r"Windows\System32\config")
    if os.path.exists(os.path.join(check_1, "SAM")): return start_path, check_1
        
    check_2 = os.path.join(start_path, r"System32\config")
    if os.path.exists(os.path.join(check_2, "SAM")): return os.path.dirname(start_path), check_2

    if os.path.exists(os.path.join(start_path, "SAM")):
        root = os.path.dirname(os.path.dirname(os.path.dirname(start_path)))
        return root, start_path

    return None, None

def main():
    print("="*60)
    print("  离线注册表提取器 (扁平化版 - 全部存入根目录)")
    print(f"  输出位置: {DEST_DIR}")
    print("="*60)

    # 1. 确保目标目录存在
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)

    while True:
        print("\n请输入嫌疑人镜像路径:")
        user_input = input("> ").strip().strip('"')
        
        if user_input.lower() in ['q', 'exit']: break
        if not user_input: continue

        # 2. 定位路径
        suspect_root, config_path = locate_system_root(user_input)

        if not config_path:
            print(f"[-] 找不到 System32\\config。请确认路径是否正确。")
            continue

        print(f"[+] 正在提取到 -> {DEST_DIR} ...\n")

        # 3. 提取系统 Hive (保持原名)
        # 结果: E:\expo\hive\SAM, E:\expo\hive\SYSTEM...
        for hive in SYSTEM_HIVES:
            flat_copy(os.path.join(config_path, hive), DEST_DIR)

        # 4. 提取 Amcache (保持原名)
        # 结果: E:\expo\hive\Amcache.hve
        amcache_path = os.path.join(suspect_root, r"Windows\AppCompat\Programs\Amcache.hve")
        if not os.path.exists(amcache_path): # 兼容旧系统
             amcache_path = os.path.join(suspect_root, r"Windows\AppCompat\ProgramData\Amcache.hve")
        flat_copy(amcache_path, DEST_DIR)

        # 5. 提取用户 Hive (必须改名！)
        # 结果: E:\expo\hive\NTUSER_张三.DAT
        users_root = os.path.join(suspect_root, "Users")
        if os.path.exists(users_root):
            for user in os.listdir(users_root):
                user_dir = os.path.join(users_root, user)
                if not os.path.isdir(user_dir): continue
                if user.lower() in ["all users", "public", "default", "default user"]: continue
                
                # 提取 NTUSER.DAT -> 改名为 NTUSER_用户名.DAT
                ntuser_src = os.path.join(user_dir, "NTUSER.DAT")
                flat_copy(ntuser_src, DEST_DIR, new_name=f"NTUSER_{user}.DAT")

                # 提取 UsrClass.dat -> 改名为 UsrClass_用户名.dat
                usr_src = os.path.join(user_dir, r"AppData\Local\Microsoft\Windows\UsrClass.dat")
                flat_copy(usr_src, DEST_DIR, new_name=f"UsrClass_{user}.dat")

        print("\n[*] 完成。所有文件已在 E:\\expo\\hive 中。")

if __name__ == "__main__":
    main()