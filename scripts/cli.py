#!/usr/bin/env python3
"""
统一命令入口
提供所有项目分析功能的统一调用接口

集成功能：
- 安全扫描（自动）
- 项目检测（自动）
- AST 解析（自动）
- 依赖分析（自动）
- 审计日志（自动）
- 知识图谱（自动）
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加脚本目录到路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


def get_project_dir(args) -> str:
    """获取项目目录"""
    if args.project_dir:
        return os.path.abspath(args.project_dir)

    # 尝试从配置读取
    try:
        from config_manager import ConfigManager
        config = ConfigManager(str(SCRIPTS_DIR))
        workdir = config.get('workdir')
        if workdir:
            return workdir
    except:
        pass

    return os.getcwd()


def cmd_init(args):
    """初始化项目（集成所有功能）"""
    from detector import ProjectDetector

    project_dir = get_project_dir(args)
    result = {
        'project_dir': project_dir,
        'steps': {},
    }

    print(f"正在初始化项目: {project_dir}")

    # Step 1: 安全扫描
    print("\n[1/5] 安全扫描...")
    try:
        from security.sensitive_scanner import SensitiveScanner
        scanner = SensitiveScanner()
        scan_result = scanner.scan(project_dir)

        result['steps']['security'] = {
            'status': 'completed',
            'sensitive_files': len(scan_result.sensitive_files),
            'sensitive_contents': len(scan_result.sensitive_contents),
            'warnings': [],
        }

        if scan_result.sensitive_files:
            print(f"  ⚠️ 发现 {len(scan_result.sensitive_files)} 个敏感文件")
            for f in scan_result.sensitive_files[:3]:
                print(f"    - {f}")
            result['steps']['security']['warnings'].extend(
                [f.file for f in scan_result.sensitive_files[:5]]
            )

        if scan_result.sensitive_contents:
            print(f"  ⚠️ 发现 {len(scan_result.sensitive_contents)} 处敏感内容")
            for c in scan_result.sensitive_contents[:3]:
                print(f"    - {c.file}:{c.line}")

        if not scan_result.sensitive_files and not scan_result.sensitive_contents:
            print("  ✅ 未发现敏感信息")

    except ImportError as e:
        print(f"  ⚠️ 安全模块不可用: {e}")
        result['steps']['security'] = {'status': 'skipped', 'reason': str(e)}

    # Step 2: 项目检测
    print("\n[2/5] 项目检测...")
    detector = ProjectDetector(project_dir)
    detect_result = detector.detect(enable_ast=True, enable_deps=True)

    result['steps']['detection'] = {
        'status': 'completed',
        'project_type': detect_result.get('project_type', 'unknown'),
        'language': detect_result.get('language', 'unknown'),
        'build_system': detect_result.get('build_system', 'unknown'),
        'scale': detect_result.get('scale', 'small'),
    }

    print(f"  项目类型: {detect_result.get('project_type', 'unknown')}")
    print(f"  语言: {detect_result.get('language', 'unknown')}")
    print(f"  构建系统: {detect_result.get('build_system', 'unknown')}")
    print(f"  规模: {detect_result.get('scale', 'small')}")

    # 合并检测结果
    result.update(detect_result)

    # Step 3: AST 解析结果
    if 'code_structure' in detect_result:
        print("\n[3/5] 代码结构分析...")
        code_struct = detect_result['code_structure']
        result['steps']['ast'] = {
            'status': 'completed',
            'functions': code_struct.get('total_functions', 0),
            'classes': code_struct.get('total_classes', 0),
        }
        print(f"  函数: {code_struct.get('total_functions', 0)}")
        print(f"  类: {code_struct.get('total_classes', 0)}")
    else:
        print("\n[3/5] 代码结构分析... 跳过")
        result['steps']['ast'] = {'status': 'skipped'}

    # Step 4: 依赖分析结果
    if 'dependency_analysis' in detect_result:
        print("\n[4/5] 依赖分析...")
        deps = detect_result['dependency_analysis']
        result['steps']['dependencies'] = {
            'status': 'completed',
            'total': deps.get('total', 0),
            'direct': deps.get('direct', 0),
            'circular': deps.get('circular', 0),
            'conflicts': deps.get('conflicts', 0),
        }
        print(f"  总依赖: {deps.get('total', 0)}")
        print(f"  直接依赖: {deps.get('direct', 0)}")
        if deps.get('circular', 0) > 0:
            print(f"  ⚠️ 循环依赖: {deps.get('circular', 0)}")
        if deps.get('conflicts', 0) > 0:
            print(f"  ⚠️ 版本冲突: {deps.get('conflicts', 0)}")
    else:
        print("\n[4/5] 依赖分析... 跳过")
        result['steps']['dependencies'] = {'status': 'skipped'}

    # Step 5: 审计日志
    print("\n[5/5] 记录审计日志...")
    try:
        from security.audit_logger import AuditLogger
        logger = AuditLogger(project_dir)
        logger.log_operation('init', {
            'project_type': detect_result.get('project_type'),
            'language': detect_result.get('language'),
            'scale': detect_result.get('scale'),
        })
        result['steps']['audit'] = {'status': 'completed'}
        print("  ✅ 已记录")
    except ImportError:
        result['steps']['audit'] = {'status': 'skipped'}
        print("  ⚠️ 审计模块不可用")

    print("\n✅ 初始化完成!")

    if args.output:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


def cmd_scan_security(args):
    """扫描敏感信息"""
    from security.sensitive_scanner import SensitiveScanner

    project_dir = get_project_dir(args)
    scanner = SensitiveScanner()
    result = scanner.scan(project_dir)

    output = {
        "project_dir": project_dir,
        "sensitive_files": result.sensitive_files,
        "sensitive_contents": [
            {"file": c.file, "line": c.line, "type": c.type, "matched": c.matched}
            for c in result.sensitive_contents[:20]
        ],
        "total_files": len(result.sensitive_files),
        "total_contents": len(result.sensitive_contents),
    }

    if args.mask:
        output["masked_files"] = result.masked_files

    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_watch(args):
    """启动文件监控"""
    from watcher import ProjectWatcher

    project_dir = get_project_dir(args)
    watcher = ProjectWatcher(project_dir)

    print(f"开始监控: {project_dir}")
    print("按 Ctrl+C 停止")

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\n停止监控")


def cmd_git_changes(args):
    """查看 Git 变更"""
    from utils.git_watcher import GitWatcher

    project_dir = get_project_dir(args)
    watcher = GitWatcher(project_dir)

    if args.type == "uncommitted":
        changes = watcher.get_uncommitted_changes()
        print(json.dumps([{
            'file': c.file_path,
            'type': c.change_type.value,
        } for c in changes], indent=2, ensure_ascii=False))
    elif args.type == "diff" and args.commit:
        changes = watcher.get_diff_files(args.commit)
        print(json.dumps(changes, indent=2, ensure_ascii=False))
    else:
        changes = watcher.get_uncommitted_changes()
        print(json.dumps([{
            'file': c.file_path,
            'type': c.change_type.value,
        } for c in changes], indent=2, ensure_ascii=False))


def cmd_analyze_deps(args):
    """依赖分析"""
    from dependency_analyzer import DependencyAnalyzer

    project_dir = get_project_dir(args)
    analyzer = DependencyAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_analyze_code(args):
    """代码质量分析"""
    from ai_analyzer import AIAnalyzer

    analyzer = AIAnalyzer()

    if args.file:
        result = analyzer.analyze_file(args.file)
    else:
        project_dir = get_project_dir(args)
        result = analyzer.analyze_project(project_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_parse_ast(args):
    """AST 解析"""
    from ast_parser import ASTParser

    parser = ASTParser()

    if args.file:
        result = parser.parse_file(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.project:
        result = parser.parse_project(args.project)
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_diagram(args):
    """生成图表"""
    from diagram_generator import DiagramGenerator

    generator = DiagramGenerator()
    project_dir = get_project_dir(args)

    if args.type == "architecture":
        from detector import ProjectDetector
        detector = ProjectDetector(project_dir)
        project_info = detector.detect()
        result = generator.generate_architecture_diagram(project_info)
    elif args.type == "dependency":
        from dependency_analyzer import DependencyAnalyzer
        analyzer = DependencyAnalyzer(project_dir)
        deps = analyzer.analyze()
        result = generator.generate_dependency_graph(deps.get("dependency_tree", {}))
    else:
        result = f"未知图表类型: {args.type}"

    if args.format == "html":
        print(generator.to_html(result, f"{args.type} diagram"))
    else:
        print(generator.wrap_with_mermaid(result))


def cmd_knowledge_graph(args):
    """知识图谱操作"""
    from knowledge_graph import KnowledgeGraph

    project_dir = get_project_dir(args)
    kg = KnowledgeGraph(project_dir)

    if args.action == "link":
        if not args.qa_id or not args.files:
            print("错误: link 需要 --qa-id 和 --files 参数")
            sys.exit(1)
        files = args.files.split(",")
        result = kg.link_qa_to_code(args.qa_id, files)
        print(json.dumps({"success": result}, ensure_ascii=False))

    elif args.action == "outdated":
        result = kg.check_outdated()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "related":
        if not args.file:
            print("错误: related 需要 --file 参数")
            sys.exit(1)
        result = kg.get_related_qa(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"未知操作: {args.action}")


def cmd_search_qa(args):
    """搜索问答（语义匹配）"""
    project_dir = get_project_dir(args)

    from qa_doc_manager import search_qa
    results = search_qa(project_dir, args.query)

    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_audit_log(args):
    """查看审计日志"""
    from security.audit_logger import AuditLogger

    project_dir = get_project_dir(args)
    logger = AuditLogger(project_dir)

    entries = logger.get_recent_entries(args.limit or 20)

    for entry in entries:
        print(f"[{entry.timestamp}] {entry.operation}: {entry.details}")


def main():
    parser = argparse.ArgumentParser(
        description="项目分析工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init 命令
    p_init = subparsers.add_parser("init", help="初始化项目（集成安全扫描、AST、依赖分析）")
    p_init.add_argument("project_dir", nargs="?", help="项目目录")
    p_init.add_argument("--output", "-o", action="store_true", help="输出详细 JSON")
    p_init.set_defaults(func=cmd_init)

    # scan-security 命令
    p_security = subparsers.add_parser("scan-security", help="扫描敏感信息")
    p_security.add_argument("project_dir", nargs="?", help="项目目录")
    p_security.add_argument("--mask", action="store_true", help="输出脱敏后的内容")
    p_security.set_defaults(func=cmd_scan_security)

    # watch 命令
    p_watch = subparsers.add_parser("watch", help="启动文件监控")
    p_watch.add_argument("project_dir", nargs="?", help="项目目录")
    p_watch.set_defaults(func=cmd_watch)

    # git-changes 命令
    p_git = subparsers.add_parser("git-changes", help="查看 Git 变更")
    p_git.add_argument("project_dir", nargs="?", help="项目目录")
    p_git.add_argument("--type", choices=["uncommitted", "diff"], default="uncommitted", help="变更类型")
    p_git.add_argument("--commit", help="对比的 commit")
    p_git.set_defaults(func=cmd_git_changes)

    # analyze-deps 命令
    p_deps = subparsers.add_parser("analyze-deps", help="依赖分析")
    p_deps.add_argument("project_dir", nargs="?", help="项目目录")
    p_deps.set_defaults(func=cmd_analyze_deps)

    # analyze-code 命令
    p_code = subparsers.add_parser("analyze-code", help="代码质量分析")
    p_code.add_argument("project_dir", nargs="?", help="项目目录")
    p_code.add_argument("--file", "-f", help="分析单个文件")
    p_code.set_defaults(func=cmd_analyze_code)

    # parse-ast 命令
    p_ast = subparsers.add_parser("parse-ast", help="AST 解析")
    p_ast.add_argument("--file", "-f", help="解析单个文件")
    p_ast.add_argument("--project", "-p", help="解析整个项目")
    p_ast.set_defaults(func=cmd_parse_ast)

    # diagram 命令
    p_diagram = subparsers.add_parser("diagram", help="生成图表")
    p_diagram.add_argument("type", choices=["architecture", "sequence", "dependency", "class"], help="图表类型")
    p_diagram.add_argument("project_dir", nargs="?", help="项目目录")
    p_diagram.add_argument("--format", choices=["mermaid", "html"], default="mermaid", help="输出格式")
    p_diagram.set_defaults(func=cmd_diagram)

    # kg 命令 (知识图谱)
    p_kg = subparsers.add_parser("kg", help="知识图谱操作")
    p_kg.add_argument("action", choices=["link", "outdated", "related"], help="操作类型")
    p_kg.add_argument("project_dir", nargs="?", help="项目目录")
    p_kg.add_argument("--qa-id", help="问答 ID")
    p_kg.add_argument("--files", help="文件列表（逗号分隔）")
    p_kg.add_argument("--file", help="单个文件")
    p_kg.set_defaults(func=cmd_knowledge_graph)

    # search-qa 命令
    p_search = subparsers.add_parser("search-qa", help="搜索问答")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("project_dir", nargs="?", help="项目目录")
    p_search.set_defaults(func=cmd_search_qa)

    # audit-log 命令
    p_audit = subparsers.add_parser("audit-log", help="查看审计日志")
    p_audit.add_argument("project_dir", nargs="?", help="项目目录")
    p_audit.add_argument("--limit", "-n", type=int, default=20, help="显示条数")
    p_audit.set_defaults(func=cmd_audit_log)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()