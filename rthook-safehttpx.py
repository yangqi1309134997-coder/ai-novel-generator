"""
PyInstaller运行时钩子 - 修复safehttpx的version.txt问题

这个钩子在程序启动时运行,确保safehttpx能找到version.txt文件
"""
import os
import sys

def fix_safehttpx_version():
    """修复safehttpx的version文件问题"""
    try:
        import safehttpx

        # 获取safehttpx的安装路径
        safehttpx_path = os.path.dirname(safehttpx.__file__)

        # version.txt的路径
        version_file = os.path.join(safehttpx_path, 'version.txt')

        # 如果文件不存在,创建一个默认的版本文件
        if not os.path.exists(version_file):
            try:
                # 尝试从__version__属性获取版本号
                version = getattr(safehttpx, '__version__', '0.24.0')

                # 创建version.txt文件
                with open(version_file, 'w') as f:
                    f.write(version)

                print(f"[SafeHTTPX Fix] Created version.txt: {version_file}")
            except Exception as e:
                # 如果创建失败,尝试修改get_version函数
                print(f"[SafeHTTPX Fix] Could not create version.txt: {e}")

                # Monkey patch the get_version function
                import safehttpx
                original_get_version = safehttpx.get_version

                def patched_get_version():
                    try:
                        return original_get_version()
                    except FileNotFoundError:
                        return getattr(safehttpx, '__version__', '0.24.0')

                safehttpx.get_version = patched_get_version
                print("[SafeHTTPX Fix] Patched get_version function")

    except Exception as e:
        print(f"[SafeHTTPX Fix] Error: {e}")

# 在导入时立即执行
fix_safehttpx_version()
