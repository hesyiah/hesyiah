import os
import sys
import ctypes
import subprocess
import re
import datetime
import shutil

# --- 配置区 ---
EVIDENCE_DIR = r"C:\Forensics_Case_Evidence"  # 证据保存根目录

def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_command(cmd):
    """运行系统命令并返回输出"""
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return result.decode('gbk', errors='ignore') # 处理中文 Windows 的编码
    except subprocess.CalledProcessError as e:
        return None

def create_shadow_copy(drive_letter="C:"):
    """使用 WMIC 创建卷影副本并返回 DeviceObject 路径"""
    print(f"[*] 正在为 {drive_letter} 盘创建卷影副本 (VSS)...")
    
    # 1. 创建副本
    create_cmd = f"wmic shadowcopy call create Volume='{drive_letter}\\'"
    output = run_command(create_cmd)
    
    if not output or "ReturnValue = 0;" not in output:
        print("[-] VSS 创建失败。请确保服务已开启且有足够磁盘空间。")
        return None, None

    # 2. 提取 ShadowID
    # 输出示例: ShadowID = "{12345678-1234-...}";
    match = re.search(r'ShadowID = "(\{[0-9A-Fa-f\-]+\})"', output)
    if not match:
        print("[-] 无法解析 ShadowID。")
        return None, None
    
    shadow_id = match.group(1)
    
    # 3. 获取 DeviceObject 路径 (例如 \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1)
    get_path_cmd = f'wmic shadowcopy where "ID=\'{shadow_id}\'" get DeviceObject /value'
    path_output = run_command(get_path_cmd)
    
    path_match = re.search(r'DeviceObject=(.+)', path_output)
    if not path_match:
        print("[-] 无法获取 VSS 设备路径。")
        # 尝试清理
        delete_shadow_copy(shadow_id)
        return None, None
        
    vss_path = path_match.group(1).strip()
    print(f"[+] VSS 创建成功: {vss_path}")
    print(f"[+] Shadow ID: {shadow_id}")
    return vss_path, shadow_id

def delete_shadow_copy(shadow_id):
    """清理卷影副本"""
    print(f"[*] 正在清理卷影副本 ({shadow_id})...")
    cmd = f'wmic shadowcopy where "ID=\'{shadow_id}\'" delete'
    run_command(cmd)
    print("[+] 清理完成。")

def copy_locked_file(vss_root, relative_path, dest_folder, file_name):
    """从 VSS 复制文件"""
    # 构造 VSS 完整路径
    source_path = f"{vss_root}\\{relative_path}\\{file_name}"
    dest_path = os.path.join(dest_folder, file_name)
    
    # 确保目标目录存在
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    # 使用 cmd copy，因为 Python 的 shutil 可能无法处理设备路径
    copy_cmd = f'cmd /c copy "{source_path}" "{dest_path}"'
    
    # 抑制输出
    try:
        subprocess.check_call(copy_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(dest_path):
            size = os.path.getsize(dest_path)
            print(f"    [+] 成功提取: {file_name} ({size/1024:.1f} KB)")
            return True
    except:
        pass
    
    print(f"    [!] 未找到或提取失败: {file_name}")
    return False

def main():
    # 1. 权限检查
    if not is_admin():
        print("[-] 错误: 必须以管理员身份运行此脚本！")
        input("按回车键退出...")
        sys.exit()

    # 2. 初始化目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    case_dir = os.path.join(EVIDENCE_DIR, f"Registry_Export_{timestamp}")
    if not os.path.exists(case_dir):
        os.makedirs(case_dir)
        
    print("="*60)
    print("      Windows 注册表取证提取工具 (Python版)")
    print(f"      证据存储路径: {case_dir}")
    print("="*60)

    # 3. 创建 VSS
    vss_path, shadow_id = create_shadow_copy()
    if not vss_path:
        sys.exit()

    try:
        # 4. 提取系统 Hive
        print("\n[Phase 1] 提取系统 Hive (System32\\Config)...")
        system_hives = ["SAM", "SYSTEM", "SECURITY", "SOFTWARE", "DEFAULT"]
        sys_dest = os.path.join(case_dir, "System_Hives")
        
        for hive in system_hives:
            copy_locked_file(vss_path, r"Windows\System32\config", sys_dest, hive)

        # 5. 提取用户 Hive
        print("\n[Phase 2] 提取用户 Hive (NTUSER.DAT & UsrClass.dat)...")
        users_root = r"C:\Users"
        user_dest_root = os.path.join(case_dir, "User_Hives")
        
        # 遍历实际磁盘的用户目录来获取用户名列表
        if os.path.exists(users_root):
            for user in os.listdir(users_root):
                # 过滤非用户目录
                if user.lower() in ["all users", "default", "default user", "public", "desktop.ini"]:
                    continue
                
                # 检查是否是目录
                if not os.path.isdir(os.path.join(users_root, user)):
                    continue

                print(f"  -> 分析用户: {user}")
                user_evidence_dir = os.path.join(user_dest_root, user)
                
                # 提取 NTUSER.DAT
                copy_locked_file(vss_path, f"Users\\{user}", user_evidence_dir, "NTUSER.DAT")
                
                # 提取 UsrClass.dat (ShellBags)
                # 路径: AppData\Local\Microsoft\Windows\UsrClass.dat
                copy_locked_file(vss_path, f"Users\\{user}\\AppData\\Local\\Microsoft\\Windows", user_evidence_dir, "UsrClass.dat")

    except Exception as e:
        print(f"\n[-] 发生未预期的错误: {e}")

    finally:
        # 6. 清理现场
        print("\n[Phase 3] 清理临时卷影副本...")
        if shadow_id:
            delete_shadow_copy(shadow_id)
        
        print("\n[*] 取证提取结束。")
        input("按回车键退出...")

if __name__ == "__main__":
    main()