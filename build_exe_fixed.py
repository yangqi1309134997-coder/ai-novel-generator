"""
AI小说创作工具 Pro - 修复版打包脚本
彻底解决safehttpx和其他第三方库的资源文件问题

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import os
import sys
import subprocess
from pathlib import Path
import shutil

# 项目根目录
PROJECT_ROOT = Path(__file__).parent


def clean_build_dirs():
    """清理之前的构建文件"""
    print("=" * 60)
    print("清理之前的构建文件...")
    print("=" * 60)

    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✓ 已删除: {dir_name}")

    print("✅ 清理完成\n")


def install_dependencies():
    """安装打包所需的依赖"""
    print("=" * 60)
    print("安装/更新打包依赖...")
    print("=" * 60)

    requirements = [
        "pyinstaller>=6.0.0",
        "setuptools>=65.0.0",
    ]

    for req in requirements:
        print(f"检查 {req}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", req])

    print("✅ 依赖安装完成\n")


def check_safehttpx():
    """检查safehttpx的version.txt文件"""
    print("=" * 60)
    print("检查safehttpx安装...")
    print("=" * 60)

    try:
        import safehttpx
        safehttpx_path = Path(safehttpx.__file__).parent
        version_file = safehttpx_path / 'version.txt'

        print(f"safehttpx 路径: {safehttpx_path}")
        print(f"version.txt 存在: {version_file.exists()}")

        if version_file.exists():
            with open(version_file) as f:
                version = f.read().strip()
            print(f"version.txt 内容: {version}")
        else:
            print("⚠️  version.txt 不存在,将使用运行时钩子修复")

        print("✅ safehttpx检查完成\n")
        return True
    except ImportError:
        print("❌ safehttpx未安装")
        print("正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "safehttpx"])
        print("✅ safehttpx安装完成\n")
        return True


def build_with_fixed_spec(portable=True):
    """使用修复后的spec文件打包"""
    print("=" * 60)
    print(f"开始打包({'便携版' if portable else '单文件版'})...")
    print("=" * 60)

    # 使用修复后的spec文件
    spec_file = PROJECT_ROOT / "build_exe_fixed.spec"

    if not spec_file.exists():
        print(f"❌ spec文件不存在: {spec_file}")
        return False

    # PyInstaller参数
    pyinstaller_args = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    # 如果需要单文件版本,修改spec文件
    if not portable:
        print("注意: 单文件版本可能会有启动慢和部分功能问题,推荐使用便携版")

    # 执行打包命令
    print(f"\n执行命令: {' '.join(pyinstaller_args)}\n")
    try:
        subprocess.check_call(pyinstaller_args)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 打包完成！")
    print("=" * 60)

    if portable:
        exe_path = PROJECT_ROOT / 'dist' / 'AI小说创作工具Pro' / 'AI小说创作工具Pro.exe'
        print(f"\n可执行文件位置: {exe_path}")
        print("\n请将整个 dist/AI小说创作工具Pro 文件夹分发给用户")
        print("\n文件夹结构:")
        print("  dist/AI小说创作工具Pro/")
        print("  ├── AI小说创作工具Pro.exe  (主程序)")
        print("  ├── _internal/              (依赖库)")
        print("  └── ...")
    else:
        exe_path = PROJECT_ROOT / 'dist' / 'AI小说创作工具Pro.exe'
        print(f"\n可执行文件位置: {exe_path}")

    print("\n" + "=" * 60)
    print("🎉 打包成功!")
    print("=" * 60)
    return True


def create_readme():
    """创建打包说明文件"""
    readme_content = """# AI小说创作工具 Pro - 使用说明

## 运行程序

### Windows用户
1. 双击 `AI小说创作工具Pro.exe` 启动程序
2. 首次运行可能需要几秒钟时间(加载依赖)
3. 程序会自动在浏览器中打开Web界面

### 如果程序无法运行
1. 确保您的系统已安装 Windows 7 或更高版本
2. 检查是否被杀毒软件拦截(添加信任即可)
3. 查看日志文件: `logs/` 目录

## 目录说明

- `logs/` - 日志文件目录
- `projects/` - 项目保存目录
- `exports/` - 导出文件目录
- `cache/` - 缓存目录
- `config/` - 配置文件目录

## 首次使用

1. 启动程序后,进入"系统设置"标签
2. 添加您的API后端配置
3. 测试连接是否正常
4. 开始创作!

## 技术支持

如遇问题,请查看:
- 日志文件: `logs/` 目录
- 项目网站: [链接]

---

版权所有 © 2026 新疆幻城网安科技有限责任公司
"""

    readme_path = PROJECT_ROOT / "dist" / "AI小说创作工具Pro" / "使用说明.txt"
    readme_path.parent.mkdir(parents=True, exist_ok=True)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"✓ 已创建使用说明: {readme_path}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("AI小说创作工具 Pro - 修复版打包工具")
    print("彻底解决safehttpx等第三方库的打包问题")
    print("=" * 60 + "\n")

    # 清理旧文件
    clean_build_dirs()

    # 安装依赖
    install_dependencies()

    # 检查safehttpx
    check_safehttpx()

    # 选择打包模式
    print("请选择打包模式:")
    print("1. 便携版(文件夹形式,启动快,推荐)")
    print("2. 单文件版(单个exe,体积大,启动慢)")

    choice = input("\n请输入选择 (1/2,默认1): ").strip()

    portable = choice != "2"

    # 开始打包
    success = build_with_fixed_spec(portable=portable)

    if success:
        # 创建使用说明
        create_readme()

        print("\n" + "=" * 60)
        print("🎉 打包流程全部完成!")
        print("=" * 60)
        print("\n建议:")
        print("1. 先运行一次生成的exe,测试是否正常")
        print("2. 检查所有功能是否可用")
        print("3. 确认无误后再分发给用户")
    else:
        print("\n❌ 打包失败,请检查错误信息")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
